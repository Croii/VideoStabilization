from PyQt5.QtCore import Qt, QThread, QThreadPool
from PyQt5.QtWidgets import QVBoxLayout, QFrame, QHBoxLayout, QSlider, QPushButton, QMainWindow, QWidget, QFileDialog, \
    QProgressBar, QLabel

import Utils
from VideoWidget import VideoWidget
from ui.StabilizationWorker import StabilizationWorker
import cv2 as cv


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stabilizer")
        self.setMinimumSize(1080, 900)  # Increased height to accommodate 800x800 video
        self.setGeometry(0, 0, 1600, 1000)

        # Flag to prevent recursive updates
        self.updating_ui = False
        self.dx = None
        self.dy = None
        self.dr = None
        self.stabilization_thread = None

        # Buttons
        self.load_button = QPushButton("Load Video")
        self.save_button = QPushButton("Save")
        self.stabilize_button = QPushButton("Stabilize")
        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        self.play_button.setVisible(False)
        self.stop_button.setVisible(False)

        # Video widget placeholder (will be created after loading video)
        self.video_widget = None

        # Slider for video navigation
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setVisible(False)  # Hide slider until video is loaded

        # Create a main layout
        self.main_layout = QVBoxLayout()

        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.stabilize_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)

        # Add button layout to main layout
        self.main_layout.addLayout(button_layout)

        # Create a container for the video with a fixed size
        # self.video_container = QFrame()
        # self.video_container.setFrameStyle(QFrame.StyledPanel)
        # self.video_container.setFixedSize(800, 800)
        video_layout = QHBoxLayout()
        self.before_label = QLabel("Original Video")
        self.before_label.setAlignment(Qt.AlignCenter)
        self.after_label = QLabel("Stabilized Video")
        self.after_label.setAlignment(Qt.AlignCenter)
        before_container = QVBoxLayout()
        after_container = QVBoxLayout()
        self.before_video = VideoWidget(None)
        self.after_video = VideoWidget(None)
        # Create a layout for positioning the video widget within the container
        before_container.addWidget(self.before_label)
        before_container.addWidget(self.before_video)
        after_container.addWidget(self.after_label)
        after_container.addWidget(self.after_video)

        video_layout.addLayout(before_container)
        video_layout.addLayout(after_container)

        self.main_layout.addLayout(video_layout)

        # Add video container to main layout, centered horizontally
        # video_container_layout = QHBoxLayout()
        # video_container_layout.addStretch()
        # video_container_layout.addWidget(self.video_container)
        # video_container_layout.addStretch()
        # self.main_layout.addLayout(video_container_layout)

        # Add slider to main layout with some horizontal margins
        slider_layout = QHBoxLayout()
        slider_layout.addSpacing(50)
        slider_layout.addWidget(self.slider)
        slider_layout.addSpacing(50)
        self.main_layout.addLayout(slider_layout)

        # Add some stretch at the bottom
        self.main_layout.addStretch()

        # Set up the central widget
        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

        #progress bar for stabilization process
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)


        # Button signals
        self.load_button.clicked.connect(self.load_video)
        self.save_button.clicked.connect(self.save_video)
        self.stabilize_button.clicked.connect(self.stabilize_video)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.before_video.frameChanged.connect(self.update_slider)
        self.slider.valueChanged.connect(self.slider_moved)

        # Initialize variables
        self.frames_before = None
        self.frames_after = None

        # Apply styles
        self.apply_styles()

    def apply_styles(self):
        button_style = ("background-color:#C67D58;"
                        "color:#F5D6B1;"
                        "padding: 6px 12px;"
                        "border-radius: 4px")

        self.load_button.setStyleSheet(button_style)
        self.save_button.setStyleSheet(button_style)
        self.stabilize_button.setStyleSheet(button_style)
        self.play_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)
        self.setStyleSheet("background-color:#FFF8DC;")
        # self.video_container.setStyleSheet("background-color:#000000;")

    def load_frames(self, before_list, after_list):
        if not before_list or not after_list:
            print("Error: Frame lists are empty or None.")
            return
        self.frames_before = before_list
        self.frames_after = after_list


    def stabilize_video(self):
        if not self.frames_before:
            print("No video was loaded!")
            return

        if len(self.frames_before) <= 1:
            print("Insufficient frames!")
            return

        #activating the progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        #preparing the thread
        self.worker = StabilizationWorker(self.frames_before)
        self.thread_pool = QThreadPool()

        #connecting signals
        self.worker.stabilization_signals.progress.connect(self.update_progress_bar)
        self.worker.stabilization_signals.result.connect(self.stabilization_completed)
        self.worker.stabilization_signals.finished.connect(self.stabilization_completed)
        self.thread_pool.start(self.worker)

    def stabilization_completed(self, stabilized_frames, transforms, dx, dy, dr, smoothed_dx, smoothed_dy, smoothed_dr):
        print("Stabilization has finished")

        # Store the stabilized frames
        self.frames_after = stabilized_frames

        # Update the after video widget
        self.after_video.set_frames(self.frames_after)

        # Enable the save button
        self.save_button.setEnabled(True)

        # Hide the progress bar
        self.progress_bar.setVisible(False)
    def update_progress_bar(self, value):
        self.progress_bar.setVisible(value)

    def load_video(self):
        """
        Loads the video and enables the stop start buttons
        displays a slider

        :return:
        """
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

                #enabling the slider
                # self.slider.setMaximum(len(self.frames_before) - 1)
                # self.slider.setValue(0)
                # self.slider.setVisible(True)  # Show slider now that we have a video

                #update before video widget
                self.before_video.set_frames(self.frames_before)

                #update slider
                self.slider.setMaximum(len(self.frames_before) - 1)
                self.slider.setValue(0)
                self.slider.setEnabled(True)
                self.slider.setVisible(True)

                #enable stabilize button
                self.stabilize_button.setEnabled(True)
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)

                self.play_button.setVisible(True)
                self.stop_button.setVisible(True)

                #reset after video

                self.frames_after = None
                self.after_video.set_frames(None)
                self.save_button.setEnabled(False)

            except Exception as e:
                print(f"Error loading video: {e}")
                return

    def save_video(self):
        if self.frames_after is None:
            print("No video was processed!")
            return

        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Save File")
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            height, width, _ = self.frames_after[0].shape
            out = cv.VideoWriter(selected_file, cv.VideoWriter_fourcc(*'mp4v'), 30, (width, height))
            for frame in self.frames_after:
                out.write(frame)
            out.release()
            print(f"Video saved to {selected_file}")

    def play_video(self):
        if self.frames_before is None:
            print("No video attached")
            return


        self.before_video.start_timer()
        if self.frames_after:
            self.after_video.start_timer()


    def stop_video(self):
        self.before_video.stop_timer()
        self.after_video.stop_timer()


    def update_slider(self, index):
        """Update slider position without triggering the valueChanged signal"""
        if self.updating_ui:
            return

        self.updating_ui = True
        self.slider.setValue(index)

        if self.frames_after:
            self.after_video_change_frame(index)

        self.updating_ui = False

    def slider_moved(self):
        """Handle slider movement and update video frame"""
        if self.updating_ui:
            return

        self.updating_ui = True
        index = self.slider.value()

        before_was_playing = False
        after_was_playing = False
        if self.before_video.timer.isActive():
            before_was_playing = True
            self.before_video.stop_timer()

        if self.after_video.timer.isActive():
            after_was_playing = True
            self.after_video.stop_timer()

        self.before_video.change_frame(index)
        if self.frames_after:
            self.after_video.change_frame(index)

        if before_was_playing:
            self.before_video.start_timer()

        if after_was_playing and self.frames_after:
            self.after_video.start_timer()

        self.updating_ui = False



    def update_frame(self, index):
        """Helper method to update frame display"""
        if self.video_widget:
            self.video_widget.change_frame(index)
