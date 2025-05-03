import cv2 as cv
import matplotlib.pyplot as plt


def load_video(path):
    frames = []
    capture = cv.VideoCapture(path)

    while capture.isOpened():
        ret, frame = capture.read()
        if not ret:
            break
        frames.append(frame)

    capture.release()

    return frames

def plot(data,legend):
    plt.plot(data)
    plt.legend(legend)
    plt.show()