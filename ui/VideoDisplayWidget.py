
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QImage, QColor
from PyQt5.QtCore import Qt, QRect

class VideoDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.before_frame = None
        self.after_frame = None
        self.split_pos = 0.5
        self.dragging = False

    def setFrames(self, before, after):
        self.before_frame = before
        self.after_frame = after
        self.update()

    def paintEvent(self):
        if self.before_frame is None or self.after_frame is None:
            return

        painter = QPainter(self)

        h,w,ch = self.before_frame.shape
        bytes_per_line = ch * w
        qimg_before = QImage(self.before_frame.data, w, h, bytes_per_line, QImage.FormatBGR888)
        qimg_after = QImage(self.after_frame.data, w, h, bytes_per_line, QImage.FormatBGR888)


