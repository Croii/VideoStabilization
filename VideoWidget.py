import sys
import cv2 as cv
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton,
                            QWidget, QSlider, QFileDialog, QHBoxLayout,
                            QSizePolicy, QFrame, QGridLayout, QSpacerItem)

import Utils

class VideoWidget(QWidget):
    frameChanged = pyqtSignal(int)

    def __init__(self, frames):
        super().__init__()
        self.setMinimumSize(800, 800)
        self.setMaximumSize(800, 800)
        self.setFixedSize(800,800)
        self.frames = frames
        self.current_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.display_width = 800
        self.display_height = 800

        if frames and len(frames) > 0:
            self.change_frame(0)
        else:
            # Create a black background
            background = np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)
            self.image = QImage(
                background.data,
                background.shape[1],
                background.shape[0],
                background.shape[1] * 3,
                QImage.Format_RGB888
            )

    def resize_frame(self, frame):
        """Resize frame to fit in display area while maintaining aspect ratio"""
        h, w = frame.shape[:2]
        aspect_ratio = w / h

        # Calculate new dimensions while maintaining aspect ratio
        if aspect_ratio > 1:  # Width > Height
            new_width = self.display_width
            new_height = int(new_width / aspect_ratio)
        else:  # Height > Width or square
            new_height = self.display_height
            new_width = int(new_height * aspect_ratio)

        # Resize the frame
        resized_frame = cv.resize(frame, (new_width, new_height), interpolation=cv.INTER_AREA)

        # Create a black background
        background = np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)

        # Calculate position to center the image
        y_offset = (self.display_height - new_height) // 2
        x_offset = (self.display_width - new_width) // 2

        # Place the resized image on the background
        background[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized_frame

        return background
    # def resize_frame(self, frame):
    #     """Resize frame to fit in 800x800 while maintaining aspect ratio"""
    #     h, w = frame.shape[:2]
    #     aspect_ratio = w / h
    #
    #     # Calculate new dimensions while maintaining aspect ratio
    #     if aspect_ratio > 1:  # Width > Height
    #         new_width = self.display_width
    #         new_height = int(new_width / aspect_ratio)
    #     else:  # Height > Width or square
    #         new_height = self.display_height
    #         new_width = int(new_height * aspect_ratio)
    #
    #     # Resize the frame
    #     resized_frame = cv.resize(frame, (new_width, new_height), interpolation=cv.INTER_AREA)
    #
    #     # Create a black background of 800x800
    #     background = np.zeros((self.display_height, self.display_width, 3), dtype=np.uint8)
    #
    #     # Calculate position to center the image
    #     y_offset = (self.display_height - new_height) // 2
    #     x_offset = (self.display_width - new_width) // 2
    #
    #     # Place the resized image on the background
    #     background[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized_frame
    #
    #     return background

    def update_frame(self):
        if not self.frames or self.current_index >= len(self.frames) - 1:
            self.current_index = 0
        else:
            self.current_index += 1

        self.change_frame(self.current_index)
        self.frameChanged.emit(self.current_index)


    def set_frames(self,frames):
        self.frames = frames
        self.current_index = 0
        if frames and len(frames) > 0:
            self.change_frame(0)

    def paintEvent(self, event):
        if hasattr(self, 'image'):
            painter = QPainter(self)
            painter.drawImage(0, 0, self.image)

    def start_timer(self, fps = 30):
        interval  = int(1000/ fps)
        self.timer.start(interval)

    def stop_timer(self):
        self.timer.stop()

    def change_frame(self, index):
        if not self.frames or not (0 <= index < len(self.frames)):
            return


        self.current_index = index
        frame = self.frames[self.current_index].copy()

        # Resize frame maintaining aspect ratio
        frame = self.resize_frame(frame)

        # Convert to RGB for display
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        self.image = QImage(
            frame.data,
            frame.shape[1],
            frame.shape[0],
            frame.shape[1] * 3,
            QImage.Format_RGB888
        )

        self.update()
        # We don't emit the signal here - it will be emitted by the caller