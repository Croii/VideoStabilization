
from math import atan2

import cv2 as cv
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from scipy.ndimage import gaussian_filter1d


def decompose_cumulative(transforms):
    dx = []
    dy = []
    dr = []  # rotation



    # Extract dx, dy, dr from
    for transform in transforms:
        if transform is None:  # Handle potential None transforms
            dx.append(0)
            dy.append(0)
            dr.append(0)
            continue
        dx.append(transform[0, 2])
        dy.append(transform[1, 2])
        dr.append(atan2(transform[1, 0], transform[0, 0]))

    # Calculate CUMULATIVE transforms
    cumulative_dx = np.cumsum(dx).tolist()
    cumulative_dy = np.cumsum(dy).tolist()
    cumulative_dr = np.cumsum(dr).tolist()

    # Prepend 0 for the first frame's reference point
    cumulative_dx.insert(0, 0)
    cumulative_dy.insert(0, 0)
    cumulative_dr.insert(0, 0)

    return cumulative_dx, cumulative_dy, cumulative_dr


class StabilizationSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    # Progress: current step (string), percentage (int)
    progress = pyqtSignal(str, int)
    # Result: stabilized_frames (list), correction_transforms (list), 
    #         raw_dx, raw_dy, raw_dr, 
    #         smoothed_dx, smoothed_dy, smoothed_dr (all lists)
    result = pyqtSignal(list, list, list, list, list, list, list, list)


class StabilizationWorker(QRunnable):

    def __init__(self, frames, method="Gaussian", crop="Autocrop", sigma=50):  # Add sigma
        super().__init__()
        self.method = method
        self.crop = crop  
        self.sigma = sigma  # Smoothing factor
        self.frames = frames
        self.stabilization_signals = StabilizationSignals()

        # Results storage
        self.frame_transforms = None  # Raw transforms between frames
        self.optimal_correction_transforms = None  # Transforms to apply for stabilization
        self.dx, self.dy, self.dr = None, None, None  # Raw cumulative paths
        self.smoothed_dx, self.smoothed_dy, self.smoothed_dr = None, None, None  # Smoothed paths
        self.stabilized_frames = None  # The final output images

    @pyqtSlot()
    def run(self):
        if not self.frames or len(self.frames) <= 1:
            self.stabilization_signals.error.emit("Not enough frames to stabilize.")
            self.stabilization_signals.finished.emit()
            return

        try:
            n_frames = len(self.frames)
            print("Stabilization started")
            self.stabilization_signals.progress.emit("Calculating motion...", 10)

            # --- 1. Get Transforms ---
            self.frame_transforms = self.get_frame_transforms()
            if not self.frame_transforms or len(self.frame_transforms) != n_frames - 1:
                raise ValueError("Failed to compute sufficient  transforms.")
            print(f"Computed {len(self.frame_transforms)}  transforms.")
            self.stabilization_signals.progress.emit("Decomposing motion...", 40)

            # --- 2. Decompose into Cumulative Paths ---
            # decompose_cumulative should return lists of length n_frames
            self.dx, self.dy, self.dr = decompose_cumulative(self.frame_transforms)
            if not (len(self.dx) == n_frames and len(self.dy) == n_frames and len(self.dr) == n_frames):
                raise ValueError("Cumulative path length mismatch.")
            print("Decomposed cumulative paths.")
            self.stabilization_signals.progress.emit("Calculating smoothed path...", 60)

            # --- 3. Calculate Optimal Correction Transforms (Smoothing) ---
            if self.method == 'Gaussian':
                # This calculates N correction transforms (one for each frame including the first)
                self.optimal_correction_transforms = self.calculate_gaussian_correction()
            else:
                self.optimal_correction_transforms = [np.eye(3) for _ in range(n_frames)]
                # If no smoothing, smoothed path is the same as raw path
                self.smoothed_dx, self.smoothed_dy, self.smoothed_dr = self.dx, self.dy, self.dr

            if not self.optimal_correction_transforms or len(self.optimal_correction_transforms) != n_frames:
                raise ValueError("Failed to compute sufficient correction transforms.")
            print(f"Calculated {len(self.optimal_correction_transforms)} correction transforms.")
            self.stabilization_signals.progress.emit("Applying stabilization warp...", 80)

            # --- 4. Apply Correction Transforms to Generate Stabilized Frames ---
            self.stabilized_frames = self.apply_warp(self.frames, self.optimal_correction_transforms)
            if not self.stabilized_frames or len(self.stabilized_frames) != n_frames:
                raise ValueError("Failed to generate sufficient stabilized frames.")
            print(f"Generated {len(self.stabilized_frames)} stabilized frames.")
            self.stabilization_signals.progress.emit("Stabilization complete.", 100)

            # --- 5. Emit Results ---
            # Ensure all lists passed have the expected length (n_frames)
            self.stabilization_signals.result.emit(
                self.stabilized_frames,  # List of warped image frames (N)
                self.optimal_correction_transforms,  # List of correction matrices (N)
                self.dx, self.dy, self.dr,  # Raw cumulative paths (N)
                self.smoothed_dx, self.smoothed_dy, self.smoothed_dr  # Smoothed paths (N)
            )

        except Exception as e:
            print(f"Error during stabilization: {e}")
            import traceback
            traceback.print_exc()
            self.stabilization_signals.error.emit(f"Error: {e}")
        finally:
            print("Stabilization finished signal.")
            self.stabilization_signals.finished.emit()

    def calculate_gaussian_correction(self):
        """Calculates the smoothed path and the necessary correction transforms."""
        if not self.dx or not self.dy or not self.dr:
            raise ValueError("Raw cumulative paths (dx, dy, dr) not calculated yet.")

        n_frames = len(self.dx)

        # Smooth the cumulative paths (length N)
        self.smoothed_dx = gaussian_filter1d(self.dx, sigma=self.sigma).tolist()
        self.smoothed_dy = gaussian_filter1d(self.dy, sigma=self.sigma).tolist()
        self.smoothed_dr = gaussian_filter1d(self.dr, sigma=self.sigma).tolist()

        # Calculate the difference needed for correction (length N)
        # diff = smoothed - raw. This is the transform to apply to the *original* frame's path
        # to get it onto the *smoothed* path.
        diff_dx = np.array(self.smoothed_dx) - np.array(self.dx)
        diff_dy = np.array(self.smoothed_dy) - np.array(self.dy)
        diff_dr = np.array(self.smoothed_dr) - np.array(self.dr)

        correction_transforms = []
        for i in range(n_frames):
            # Construct the 3x3 matrix that applies this correction
            cos_r = np.cos(diff_dr[i])
            sin_r = np.sin(diff_dr[i])
            tx = diff_dx[i]
            ty = diff_dy[i]

            # Affine matrix: [[cos(r), -sin(r), tx], [sin(r), cos(r), ty], [0, 0, 1]]
            transform = np.array([
                [cos_r, -sin_r, tx],
                [sin_r, cos_r, ty],
                [0, 0, 1]
            ], dtype=np.float32)
            correction_transforms.append(transform)

        return correction_transforms

    def apply_warp(self, original_frames, correction_transforms):
        """Applies the correction transforms to the original frames."""
        stabilized_output_frames = []
        n_frames = len(original_frames)

        if len(correction_transforms) != n_frames:
            print(
                f"Warning: Mismatch frame count ({n_frames}) and correction transforms ({len(correction_transforms)})")
            return original_frames  # Return original if transforms are wrong length

        for i in range(n_frames):
            frame = original_frames[i]
            transform = correction_transforms[i]
            h, w = frame.shape[:2]

            try:
                # Apply the correction transform to the frame
                stabilized = cv.warpPerspective(frame, transform, (w, h), flags=cv.INTER_LINEAR,
                                                borderMode=cv.BORDER_CONSTANT)  # Add border handling
                stabilized_output_frames.append(stabilized)

                # Emit progress
                if (i + 1) % 10 == 0:
                    percent = 80 + int(((i + 1) / n_frames) * 20)  # Scale 80-100%
                    self.stabilization_signals.progress.emit(f"Warping frame {i + 1}/{n_frames}", percent)


            except cv.error as e:
                print(f"Error warping frame {i}: {e}. Appending original frame.")
                stabilized_output_frames.append(frame.copy())  # Append original on error

        return stabilized_output_frames

    def get_frame_transforms(self):
        """Calculates the transform from frame i to frame i+1."""
        # Params for ShiTomasi corner detection
        feature_params = dict(maxCorners=200, qualityLevel=0.1, minDistance=30, blockSize=3)
        # Parameters for lucas kanade optical flow
        lk_params = dict(winSize=(20, 20), maxLevel=3,
                         criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

        frame_transforms = []

        if not self.frames: return []

        old_gray = cv.cvtColor(self.frames[0], cv.COLOR_BGR2GRAY)


        n_frames = len(self.frames)

        for i in range(n_frames - 1):  # Iterate N-1 times for N frames
            new_gray = cv.cvtColor(self.frames[i + 1], cv.COLOR_BGR2GRAY)

            # --- Feature Tracking ---
            # Find features in the *previous* frame
            p0 = cv.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

            if p0 is None or len(p0) < 10:  # Need sufficient points
                print(f"Warning: Not enough features found at frame {i}. Using identity transform.")
                frame_transforms.append(np.eye(3, dtype=np.float32))
                old_gray = new_gray.copy()
                continue  # Skip to next frame pair

            # Calculate optical flow
            p1, st, err = cv.calcOpticalFlowPyrLK(old_gray, new_gray, p0, None, **lk_params)

            # Select good points
            if p1 is not None and st is not None:
                good_new = p1[st == 1]
                good_old = p0[st == 1]
            else:
                good_new, good_old = np.array([]), np.array([])  # Empty arrays

            # --- Transform Estimation ---
            current_transform = None
            if len(good_new) >= 4 and len(good_old) >= 4:
                try:
                    # Use estimateAffine2D as before
                    affine_matrix, mask = cv.estimateAffinePartial2D(good_old, good_new, method=cv.RANSAC,
                                                                     ransacReprojThreshold=5.0)

                    if affine_matrix is not None:
                        # Convert 2x3 affine to 3x3 affine matrix
                        current_transform = np.vstack([affine_matrix, [0, 0, 1]])
                    else:
                        print(f"Warning: estimateAffinePartial2D failed at frame {i}. Using identity.")
                        current_transform = np.eye(3, dtype=np.float32)

                except cv.error as e:
                    print(f"Error estimating transform at frame {i}: {e}. Using identity.")
                    current_transform = np.eye(3, dtype=np.float32)
            else:
                print(
                    f"Warning: Not enough good points ({len(good_new)}) found for transform estimation at frame {i}. Using identity.")
                current_transform = np.eye(3, dtype=np.float32)

            frame_transforms.append(current_transform.astype(np.float32))  # Ensure float type

            # Update old frame and features for next iteration
            old_gray = new_gray.copy()

            # --- Progress Update ---
            percent = 10 + int(((i + 1)     / (n_frames - 1)) * 30)
            self.stabilization_signals.progress.emit(f"Tracking frame {i + 1}/{n_frames - 1}", percent)

        return frame_transforms