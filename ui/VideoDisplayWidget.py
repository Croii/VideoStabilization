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
        if before is None or after is None:
            print("Error: One or both frames are None.")
            return
        if before.shape != after.shape:
            print("Error: Frame shapes do not match.")
            return
        self.before_frame = before
        self.after_frame = after
        self.update()

    def paintEvent(self, event):
        if self.before_frame is None or self.after_frame is None:
            return

        painter = QPainter(self)

        h, w, ch = self.before_frame.shape
        bytes_per_line = ch * w
        qimg_before = QImage(self.before_frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        qimg_after = QImage(self.after_frame.data, w, h, bytes_per_line, QImage.Format_BGR888)

        widget_width = self.width()
        widget_height = self.height()
        split_pixel = int(self.split_pos * widget_width)

        # Draw the images scaled to the widget size
        painter.drawImage(QRect(0, 0, split_pixel, widget_height), qimg_before)
        painter.drawImage(QRect(split_pixel, 0, widget_width - split_pixel, widget_height), qimg_after)

        # Draw the split line
        painter.setPen(QColor("#FF0000"))
        painter.drawLine(split_pixel, 0, split_pixel, widget_height)

    def mousePressEvent(self, event):
        if abs(event.x() - self.split_pos * self.width()) < 10:
            self.dragging = True

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.split_pos = min(max(event.x() / self.width(), 0.0), 1.0)
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False