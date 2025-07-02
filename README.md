# VideoStabilization

**Author:** Croitoru Robert (Croii)

**Description:**  
A Python desktop application to stabilize shaky videos by detecting feature points, estimating inter-frame motion, and correcting camera trajectory. It provides a simple GUI built with PyQt5 for loading, stabilizing, comparing, and saving videos.

---

## Features

✅ Load videos (mp4, avi, mov, mkv)  
✅ View original and stabilized videos side by side  
✅ Motion estimation and affine transformation for stabilization  
✅ Save stabilized video  
✅ Simple GUI built with PyQt5

---

## Tech Stack

- Python
- OpenCV
- NumPy
- SciPy
- PyQt5

---

## Core Algorithms

- **Corner Detection:** `cv2.goodFeaturesToTrack` (Shi-Tomasi)
  - `maxCorners=200`
  - `qualityLevel=0.1`
  - `minDistance=30`
  - `blockSize=3`

- **Optical Flow Tracking:** `cv2.calcOpticalFlowPyrLK`
  - `winSize=(20, 20)`
  - `maxLevel=3`
  - `criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)`

- **Motion Estimation:** `cv2.estimateAffinePartial2D`
  - `method=cv2.RANSAC`
  - `ransacReprojThreshold=5.0`

- **Frame Warping:** `cv2.warpAffine` or `cv2.warpPerspective`
  - `flags=cv2.INTER_LINEAR`
  - `borderMode=cv2.BORDER_CONSTANT`

- **Smoothing Trajectory:** `scipy.ndimage.gaussian_filter1d`

Frames are stored as `numpy.ndarray` (shape: height × width × 3), with BGR color channels. Video frames are managed as a Python list for easy sequential processing.

---

## How It Works

1. Load a video from the GUI.
2. Detect feature points in frames using Shi-Tomasi.
3. Track points between frames via Lucas-Kanade optical flow.
4. Estimate affine transforms to align frames.
5. Smooth the camera trajectory to remove abrupt motions.
6. Warp frames based on the smoothed trajectory.
7. Save the stabilized video.

---

## Run Locally

```bash
git clone https://github.com/Croii/VideoStabilization.git
cd VideoStabilization
pip install -r requirements.txt
python main.py
