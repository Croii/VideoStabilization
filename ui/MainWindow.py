from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QFrame, QHBoxLayout, QSlider, QPushButton, QMainWindow, QWidget, QFileDialog

import Utils
from VideoWidget import VideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stabilizer")
        self.setMinimumSize(1080, 900)  # Increased height to accommodate 800x800 video
        self.setGeometry(0, 0, 1600, 1000)

        # Flag to prevent recursive updates
        self.updating_ui = False

        # Buttons
        self.button1 = QPushButton("Load Video")
        self.button2 = QPushButton("Save")
        self.button3 = QPushButton("Stabilize")
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
        self.slider.valueChanged.connect(self.slider_moved)
        self.slider.setVisible(False)  # Hide slider until video is loaded

        # Create a main layout
        self.main_layout = QVBoxLayout()

        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)
        button_layout.addWidget(self.button3)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)

        # Add button layout to main layout
        self.main_layout.addLayout(button_layout)

        # Create a container for the video with a fixed size
        self.video_container = QFrame()
        self.video_container.setFrameStyle(QFrame.StyledPanel)
        self.video_container.setFixedSize(800, 800)

        # Create a layout for positioning the video widget within the container
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Add video container to main layout, centered horizontally
        video_container_layout = QHBoxLayout()
        video_container_layout.addStretch()
        video_container_layout.addWidget(self.video_container)
        video_container_layout.addStretch()
        self.main_layout.addLayout(video_container_layout)

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

        # Button connections
        self.button1.clicked.connect(self.load_video)
        self.button2.clicked.connect(self.save_video)
        # self.button3.clicked.connect(self.stabilize_video)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)

        # Initialize variables
        self.frames_before = None
        self.frames_after = None

        # Apply styles
        self.apply_styles()

    def apply_styles(self):
        self.button1.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.button2.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.button3.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.play_button.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.stop_button.setStyleSheet("background-color:#C67D58; color:#F5D6B1;")
        self.setStyleSheet("background-color:#FFF8DC;")
        self.video_container.setStyleSheet("background-color:#000000;")

    def load_frames(self, before_list, after_list):
        if not before_list or not after_list:
            print("Error: Frame lists are empty or None.")
            return
        self.frames_before = before_list
        self.frames_after = after_list

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
                self.slider.setVisible(True)  # Show slider now that we have a video

            except Exception as e:
                print(f"Error loading video: {e}")
                return

            # Clean up any existing video widget
            if self.video_widget:
                self.video_layout.removeWidget(self.video_widget)
                self.video_widget.deleteLater()
                self.video_widget = None

            # Create a new widget and add it to the video container layout
            self.video_widget = VideoWidget(self.frames_before)

            # Clear any previous widgets in the video layout
            while self.video_layout.count():
                item = self.video_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add the new video widget to the layout
            self.video_layout.addWidget(self.video_widget)

            # Connect signal AFTER the widget has been created
            self.video_widget.frameChanged.connect(self.update_slider)

            # Activate the playing buttons
            self.play_button.setVisible(True)
            self.stop_button.setVisible(True)

            # Show initial frame
            self.update_frame(0)

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
            # Add your save logic here

    def play_video(self):
        if self.video_widget is None:
            print("No video attached")
            return

        if self.video_widget.current_index >= len(self.video_widget.frames):
            self.video_widget.current_index = 0

        self.video_widget.start_timer()

    def stop_video(self):
        if self.video_widget is None:
            print("No video attached")
            return
        self.video_widget.stop_timer()

    def update_slider(self, index):
        """Update slider position without triggering the valueChanged signal"""
        if self.updating_ui:
            return

        self.updating_ui = True
        self.slider.setValue(index)
        self.updating_ui = False

    def slider_moved(self):
        """Handle slider movement and update video frame"""
        if self.updating_ui or self.video_widget is None:
            return

        self.updating_ui = True
        index = self.slider.value()

        # Stop timer temporarily if running
        was_running = False
        if self.video_widget.timer.isActive():
            was_running = True
            self.video_widget.stop_timer()

        self.video_widget.change_frame(index)
        self.video_widget.frameChanged.emit(index)  # Emit the signal here

        # Restart timer if it was running before
        if was_running:
            self.video_widget.start_timer()

        self.updating_ui = False

    def update_frame(self, index):
        """Helper method to update frame display"""
        if self.video_widget:
            self.video_widget.change_frame(index)
