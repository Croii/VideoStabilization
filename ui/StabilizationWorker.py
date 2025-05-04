from math import atan2

import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from scipy.ndimage import gaussian_filter1d

from Stabilization import stabilization


####################
#l1 stabilization inserted there
#smoothed gaussian
#maybe moving average
###################
def decompose_cumulative(transforms):
    dx = []
    dy = []
    dr = [] #rotation

    for transform in transforms:
        dx.append(transform[0][2])
        dy.append(transform[1][2])
        dr.append(atan2(transform[1][0], transform[0][0]))

    for i in range(1, len(transforms)):
        dx[i] = dx[i - 1] + dx[i]
        dy[i] = dy[i - 1] + dy[i]
        dr[i] = dr[i - 1] + dr[i]

    return dx,dy,dr



class StabilizationSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)

    progress = pyqtSignal(int) # for progress bar
    result = pyqtSignal(list,list,list,list,list,list,list,list) # frames, transforms, dx, dy, dr, smoothed_dx,smoothed_dy, smoothed_dr

class StabilizationWorker(QRunnable):


    def __init__(self, frames, method="Gaussian", crop="Autocrop"):
        super().__init__()
        self.method = method
        self.optimal_transforms = None
        self.crop = crop
        self.frames = frames
        self.stabilization_signals = StabilizationSignals()
        self.transforms = None
        self.dx = None
        self.dy = None
        self.dr = None

        self.smoothed_dx = None
        self.smoothed_dy = None
        self.smoothed_dr = None

        self.stabilized_frames = None
    @pyqtSlot()
    def run(self):
        if not self.frames or len(self.frames) <= 1:
            self.stabilization_signals.finished.emit()
            return

        try:
            print("stabilization started")

            self.transforms = self.get_transforms()
            cumulative_features = decompose_cumulative(transforms=self.transforms)
            self.stabilized_frames = self.gaussian_stabilization(cumulative_features)
            if self.method == 'Gaussian':
                self.optimal_transforms = self.gaussian_stabilization(cumulative_features)

        finally:
            self.stabilization_signals.result.emit(self.stabilized_frames, self.optimal_transforms, self.dx, self.dy, self.dr, self.smoothed_dx, self.smoothed_dy, self.smoothed_dr)
            self.stabilization_signals.finished.emit()
            print("stabilization finished")


    def gaussian_stabilization(self, cumulative_features):
        (dx,dy,dr) = cumulative_features

        self.dx = dx
        self.dy = dy
        self.dr = dr


        smoothed_dx = gaussian_filter1d(dx, sigma=100)
        smoothed_dy = gaussian_filter1d(dy, sigma=100)
        smoothed_dr = gaussian_filter1d(dr, sigma=100)

        self.smoothed_dx = smoothed_dx.tolist()
        self.smoothed_dy = smoothed_dy.tolist()
        self.smoothed_dr = smoothed_dr.tolist()

        diff_dx = smoothed_dx - dx
        diff_dy = smoothed_dy - dy
        diff_rot = smoothed_dr - dr
        optimal_transforms = []
        for i in range(len(dx)):
            transform = np.array([[np.cos(diff_rot[i]), -np.sin(diff_rot[i]), diff_dx[i]],
                                  [np.sin(diff_rot[i]), np.cos(diff_rot[i]), diff_dy[i]],
                                  [0, 0, 1]])
            # transform = np.array([[1, 0, diff_dx[i]],
            #                       [0, 1, diff_dy[i]],
            #                       [0, 0, 1]])
            optimal_transforms.append(transform)
        return optimal_transforms



    def stabilize(self, frames, transforms):
        self.compute_optimal_path_transform(transforms, self.method)
        stabilized_frames = []
        for i in range(len(frames) - 1):
            h, w = frames[i].shape[:2]
            transform = self.optimal_transforms[i]
            stabilized = cv.warpPerspective(frames[i], transform, (w, h))
            stabilized_frames.append(stabilized)

        return stabilized_frames

    def get_transforms(self):

        # Params for ShiTomasi corner detection
        feature_params = dict(maxCorners=200,
                              qualityLevel=0.1,
                              minDistance=30,
                              blockSize=3)

        # Parameters for lucas kanade optical flow
        lk_params = dict(winSize=(20, 20),
                         maxLevel=3,
                         criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

        transforms = []

        old_gray = cv.cvtColor(self.frames[0], cv.COLOR_BGR2GRAY)
        # old_gray = cv.GaussianBlur(old_gray, (5, 5), 0)

        p0 = cv.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

        for i in range(1, len(self.frames)):
            #update progress

            new_gray = cv.cvtColor(self.frames[i], cv.COLOR_BGR2GRAY)
            # new_gray = cv.GaussianBlur(new_gray, (5, 5), 0)
            # can add additional masking for discarding bad points
            # maybe reusing the older ones
            p0 = cv.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
            p1, st, err = cv.calcOpticalFlowPyrLK(old_gray, new_gray, p0, None, **lk_params)

            if p1 is not None:
                # here I need to look for outliers
                good_new = p1[st == 1]
                good_old = p0[st == 1]

                # Estimation matrix
                # current_transform, _ = cv.findHomography(good_old, good_new, method=cv.RANSAC) #ransac more research needed a factor of five

                current_transform, _ = cv.estimateAffine2D(good_old, good_new, method=cv.RANSAC)  # ransac more research
                # needed a factor of five

                # transform it to affine
                current_transform = np.vstack([current_transform, [0, 0, 1]])
                transforms.append(current_transform)

            old_gray = new_gray.copy()
        return transforms
