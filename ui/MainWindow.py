from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import Utils
from VideoProcessor import VideoProcessor
from ui.VideoDisplayWidget import VideoDisplayWidget

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from ui.VideoDisplayWidget import VideoDisplayWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stabilizer")
        self.setMinimumSize(1080, 720)
        self.setGeometry(0, 0, 1600, 950)
        self.setFixedSize(self.width(), self.height())

        # Buttons
        self.button1 = QPushButton("Load Video", self)
        self.button2 = QPushButton("Save", self)
        self.button3 = QPushButton("Stabilize", self)
        self.play_button = QPushButton("Play", self)
        self.stop_button = QPushButton("Stop", self)





        self.video_widget = VideoDisplayWidget()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self.slider_moved)

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)
        button_layout.addWidget(self.button3)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)

        layout.addWidget(self.video_widget)
        layout.addWidget(self.slider)


        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Button connections
        self.button1.clicked.connect(self.load_video)
        self.button2.clicked.connect(self.save_video)
        self.button3.clicked.connect(self.stabilize_video)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)


        # Initialize variables
        self.frames_before = None
        self.frames_after = None
        self.current_frame_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)




        # Apply styles
        self.apply_styles()

    def stop_video(self):
        self.timer.stop()

    def play_video(self):
        if not self.frames_before:
            print("No video loaded!")
            return
        self.timer.start(33)

    def next_frame(self):
        if self.frames_before and self.current_frame_index < len(self.frames_before):
            self.update_frame(self.current_frame_index)
            self.slider.setValue(self.current_frame_index)
            self.current_frame_index += 1
        else:
            self.timer.stop()  # Stop when the video ends

    def slider_moved(self, index):
        self.current_frame_index = index
        if self.frames_before and self.frames_after:
            self.update_frame(index)

    def update_frame(self, index):
        if 0 <= index < len(self.frames_before):
            self.video_widget.setFrames(self.frames_before[index], self.frames_after[index])

    def apply_styles(self):
        self.button1.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.button2.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.button3.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.setStyleSheet("background-color:#FFF8DC;")

    def load_frames(self, before_list, after_list):
        if not before_list or not after_list:
            print("Error: Frame lists are empty or None.")
            return
        self.frames_before = before_list
        self.frames_after = after_list
        self.slider.setMaximum(len(self.frames_before) - 1)
        self.slider.setValue(0)
        self.update_frame(0)

    def load_video(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()[0]
            try:
                self.frames_before = Utils.load_video(selected_files)
                if not self.frames_before:
                    raise ValueError("No frames loaded from the video.")
                self.slider.setMaximum(len(self.frames_before) - 1)
                self.slider.setValue(0)
                self.update_frame(0)
            except Exception as e:
                print(f"Error loading video: {e}")


    def save_video(self):

        if self.frames_after == None:
            print("No video was processed!")
            return


        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Save File")
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]


    def start_processing(self):
        if not self.frames_before:
            return

        self.processor = VideoProcessor(self.frames_before)
        self.processor_thread = QThread()
        self.processor.moveToThread(self.processor_thread)

        self.processor_thread.started.connect(self.processor.process)
        self.processor.frame_processed.connect(self.update_frame_from_thread)

    def update_frame_from_thread(self,before, after):
        self.video_widget.setFrames(before, after)


    def stabilize_video(self):
        if self.frames_before is None:
            print("No file was selected!")
            return

        print("Stabilize button clicked")