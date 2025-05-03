from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# class MainWindow (QMainWindow) :
#     def __init__(self):
#         super().__init__()
#         self.setGeometry(30, 30, 1600, 950)
#         self.initUI()
#
#         #buttons
#         self.load_button = QPushButton("Load video")
#         self.load_button = QPushButton("Save video")
#         self.load_button = QPushButton("Stabilize")
#
#         to
#
#     def initUI(self):
#
#         pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stabilizer")
        self.setMinimumSize(1080, 720)
        self.setGeometry(0,0,1600,950)

        self.setFixedSize(self.width(), self.height())


        #buttens
        self.button1 = QPushButton("Load", self)
        self.button2 = QPushButton("Save", self)
        self.button3 = QPushButton("Stabilize", self)

        # layout = QStackedLayout()
        # layout.addWidget(self.button1)
        # layout.addWidget(self.button2)
        # layout.addWidget(self.button3)
        self.init()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor("#F5D6B1"))

        rect = QRect(0, 23, 1600, 70)
        painter.drawRect(rect)



    def init(self):
        self.button1.setGeometry(29,34, 160,45)
        self.button2.setGeometry(244,34, 160,45)
        self.button3.setGeometry(459,34, 160,45)
        self.button1.setStyleSheet("background-color:#C67D58;"
                                   "color:#F5D6B1;"
                                   )
        self.button2.setStyleSheet("background-color:#C67D58;"
                                   "color:#F5D6B1;"
                                   )
        self.button3.setStyleSheet("background-color:#C67D58;"
                                   "color:#F5D6B1;"
                                   )
        self.setStyleSheet("background-color:#FFF8DC;")


        pass