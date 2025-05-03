from math import atan2

import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

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


class stabilization:
    def __init__(self, method):
        self.method = method
        self.optimal_transforms = None

    def compute_optimal_path_transform(self, transforms, method):
        cumulative_features = decompose_cumulative(transforms)
        if method == 'gaussian':
            self.optimal_transforms = self.gaussian_stabilization(cumulative_features)


    def gaussian_stabilization(self, cumulative_features):
        (dx,dy,rot) = cumulative_features
        smoothed_dx = gaussian_filter1d(dx, sigma=100)
        smoothed_dy = gaussian_filter1d(dy, sigma=100)
        smoothed_rot = gaussian_filter1d(rot, sigma=100)
        diff_dx = smoothed_dx - dx
        diff_dy = smoothed_dy - dy
        diff_rot = smoothed_rot - rot
        optimal_transforms = []
        for i in range(len(dx)):
            # transform = np.array([[np.cos(diff_rot[i]), -np.sin(diff_rot[i]), diff_dx[i]],
            #                       [np.sin(diff_rot[i]), np.cos(diff_rot[i]), diff_dy[i]],
            #                       [0, 0, 1]])
            transform = np.array([[1, 0, diff_dx[i]],
                                  [0, 1, diff_dy[i]],
                                  [0, 0, 1]])
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

    def get_transforms(frames):

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

        old_gray = cv.cvtColor(frames[0], cv.COLOR_BGR2GRAY)
        # old_gray = cv.GaussianBlur(old_gray, (5, 5), 0)

        p0 = cv.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

        for i in range(1, len(frames)):
            new_gray = cv.cvtColor(frames[i], cv.COLOR_BGR2GRAY)
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
