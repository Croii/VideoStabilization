from PyQt5.QtCore import Qt, QThreadPool, pyqtSlot
import cv2 as cv
from PyQt5.QtCore import Qt, QThreadPool, pyqtSlot
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QSlider,
                             QPushButton, QMainWindow, QWidget, QFileDialog,
                             QProgressBar, QLabel)

import Utils
from VideoWidget import VideoWidget
from ui.StabilizationWorker import StabilizationWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stabilizer")

        # Adjusted minimum size slightly for better layout with progress/error
        self.setMinimumSize(1080, 950)
        self.setGeometry(100, 100, 1600, 1000)  # Example position/size

        # --- Internal State ---
        self.updating_ui = False  # Flag to prevent recursive UI updates
        self.frames_before = None
        self.frames_after = None
        self.worker = None  # Reference to the stabilization worker
        self.thread_pool = QThreadPool()  # Thread pool for the worker

        # Stabilization results data
        self.dx, self.dy, self.dr = None, None, None
        self.smoothed_dx, self.smoothed_dy, self.smoothed_dr = None, None, None
        self.correction_transforms = None

        # --- UI Elements ---

        # Buttons
        self.load_button = QPushButton("Load Video")
        self.save_button = QPushButton("Save Stabilized")
        self.stabilize_button = QPushButton("Stabilize")
        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")

        # Initial button states
        self.save_button.setEnabled(False)
        self.stabilize_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.play_button.setVisible(False)
        self.stop_button.setVisible(False)

        # Video Widgets and Labels
        self.before_video = VideoWidget(None)
        self.after_video = VideoWidget(None)
        self.before_label = QLabel("Original Video")
        self.before_label.setAlignment(Qt.AlignCenter)
        self.after_label = QLabel("Stabilized Video")
        self.after_label.setAlignment(Qt.AlignCenter)

        # Slider for video navigation
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)  # Start at 0 max
        self.slider.setEnabled(False)
        self.slider.setVisible(False)

        # Progress Bar and Label
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)  # Explicitly set range
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        # Error Label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; padding: 5px;")  # Add some padding
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)

        # --- Layouts ---

        # Main vertical layout
        self.main_layout = QVBoxLayout()

        # Button layout (horizontal)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.stabilize_button)
        button_layout.addStretch()  # Push play/stop to the right
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)
        self.main_layout.addLayout(button_layout)

        # Error label layout (add early for visibility)
        self.main_layout.addWidget(self.error_label)

        # Video layout (horizontal for side-by-side)
        video_layout = QHBoxLayout()

        # Container for 'Before' video and label
        before_container = QVBoxLayout()
        before_container.addWidget(self.before_label)
        before_container.addWidget(self.before_video)
        video_layout.addLayout(before_container)

        # Container for 'After' video and label
        after_container = QVBoxLayout()
        after_container.addWidget(self.after_label)
        after_container.addWidget(self.after_video)
        video_layout.addLayout(after_container)

        self.main_layout.addLayout(video_layout)

        # Slider layout (horizontal with spacing)
        slider_layout = QHBoxLayout()
        slider_layout.addSpacing(50)
        slider_layout.addWidget(self.slider)
        slider_layout.addSpacing(50)
        self.main_layout.addLayout(slider_layout)

        # Progress layout (horizontal)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label, 1)  # Label takes some space
        progress_layout.addWidget(self.progress_bar, 4)  # Bar takes more space
        self.main_layout.addLayout(progress_layout)

        # Add stretch at the bottom
        self.main_layout.addStretch()

        # Set up the central widget
        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

        # --- Connections ---
        self.load_button.clicked.connect(self.load_video)
        self.save_button.clicked.connect(self.save_video)
        self.stabilize_button.clicked.connect(self.stabilize_video)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)

        # Connect frame changes from, video widget to slider update
        self.before_video.frameChanged.connect(self.update_slider_from_video)
        # Connect slider value changes to video frame update
        self.slider.valueChanged.connect(self.update_video_from_slider)

        self.apply_styles()

    def apply_styles(self):
        """Applies styling to widgets."""
        button_style = ("QPushButton {"
                        "  background-color:#C67D58;"
                        "  color:#F5D6B1;"
                        "  padding: 6px 12px;"
                        "  border-radius: 4px;"
                        "  border: 1px solid #a56846;"  # Added subtle border
                        "}"
                        "QPushButton:hover { background-color: #d78e6a; }"  # Hover effect
                        "QPushButton:pressed { background-color: #b56d4e; }"  # Pressed effect
                        "QPushButton:disabled { background-color: #cccccc; color: #666666; border: 1px solid #aaaaaa; }"

                        )

        self.load_button.setStyleSheet(button_style)
        self.save_button.setStyleSheet(button_style)
        self.stabilize_button.setStyleSheet(button_style)
        self.play_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)

        # Main background
        self.setStyleSheet("QMainWindow { background-color:#FFF8DC; }")

        # Labels style
        label_style = "QLabel { color: #5f4c3a; font-weight: bold; }"
        self.before_label.setStyleSheet(label_style)
        self.after_label.setStyleSheet(label_style)
        self.progress_label.setStyleSheet("QLabel { color: #333333; }")  # Progress text color

    # --- Action Methods ---

    def load_video(self):
        """Opens a file dialog to load a video."""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Video File")
        # Common video formats filter
        file_dialog.setNameFilter("Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            try:
                self.hide_error()  # Hide previous errors on new load attempt
                print(f"Loading video from: {selected_file}")
                # Load frames
                loaded_frames = Utils.load_video(selected_file)

                if not loaded_frames:
                    raise ValueError("No frames could be loaded from the selected file.")
                if len(loaded_frames) <= 1:
                    raise ValueError("Video must contain at least two frames.")

                # --- Successfully loaded ---
                self.frames_before = loaded_frames
                print(f"Successfully loaded {len(self.frames_before)} frames.")

                # Reset stabilization results
                self.frames_after = None
                self.dx, self.dy, self.dr = None, None, None  # Clear plot data too
                self.smoothed_dx, self.smoothed_dy, self.smoothed_dr = None, None, None

                # Update 'Before' video widget
                self.before_video.set_frames(self.frames_before)
                # Reset 'After' video widget
                self.after_video.set_frames(None)  # Clear the after video panel

                # Update slider
                self.slider.setMaximum(len(self.frames_before) - 1)
                self.slider.setValue(0)
                self.slider.setEnabled(True)
                self.slider.setVisible(True)

                # Update button states
                self.stabilize_button.setEnabled(True)
                self.save_button.setEnabled(False)  # Can't save until stabilized
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                self.play_button.setVisible(True)
                self.stop_button.setVisible(True)

            except Exception as e:
                error_msg = f"Error loading video: {e}"
                print(error_msg)
                self.show_error(error_msg)
                # Reset UI to safe state on load failure
                self.frames_before = None
                self.frames_after = None
                self.before_video.set_frames(None)
                self.after_video.set_frames(None)
                self.stabilize_button.setEnabled(False)
                self.save_button.setEnabled(False)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.play_button.setVisible(False)
                self.stop_button.setVisible(False)
                self.slider.setMaximum(0)
                self.slider.setEnabled(False)
                self.slider.setVisible(False)
                return  # Stop further execution in load_video

    def stabilize_video(self):
        """Starts the video stabilization process in a worker thread."""
        if not self.frames_before:
            self.show_error("Load a video first.")
            return

        if self.worker is not None:
            self.show_error("Stabilization is already in progress.")
            return

        # Reset previous results and UI state for stabilization
        self.frames_after = None
        self.after_video.set_frames(None)
        self.save_button.setEnabled(False)
        self.stabilize_button.setEnabled(False)  # Disable during processing
        self.load_button.setEnabled(False)  # Disable during processing
        # self.play_button.setEnabled(False)  # Disable playback during processing
        # self.stop_button.setEnabled(False)
        self.hide_error()

        # Show and reset progress bar/label
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting stabilization...")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        # --- Prepare and start worker ---
        sigma_value = 10
        self.worker = StabilizationWorker(self.frames_before, sigma=sigma_value)

        # Connect signals
        self.worker.stabilization_signals.progress.connect(self.update_progress)
        self.worker.stabilization_signals.result.connect(self.stabilization_completed)
        self.worker.stabilization_signals.finished.connect(self.stabilization_finished)
        self.worker.stabilization_signals.error.connect(self.stabilization_error)

        print("Starting stabilization worker thread...")
        # Start the worker in the global thread pool
        self.thread_pool.start(self.worker)

    def save_video(self):
        """Saves the stabilized video frames to a file."""
        if not self.frames_after:
            self.show_error("No stabilized video to save. Stabilize first.")
            return

        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Save Stabilized Video")
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        # Default to mp4, allow others
        file_dialog.setNameFilter("MP4 Video (*.mp4);;AVI Video (*.avi);;All Files (*)")
        file_dialog.setDefaultSuffix("mp4")
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            if not selected_file: return  # User cancelled

            print(f"Saving stabilized video to: {selected_file}")
            try:
                height, width, _ = self.frames_after[0].shape
                # Use mp4v codec for MP4 files, check compatibility if saving other formats
                fourcc = cv.VideoWriter_fourcc(*'mp4v')

                fps = 30
                out = cv.VideoWriter(selected_file, fourcc, fps, (width, height))

                if not out.isOpened():
                    raise IOError(f"Could not open video writer for '{selected_file}'")

                for i, frame in enumerate(self.frames_after):
                    # Ensure frame is BGR format for VideoWriter
                    if frame.ndim == 3 and frame.shape[2] == 3:
                        out.write(frame)
                    else:
                        print(f"Warning: Skipping invalid frame {i} during save.")

                out.release()
                print(f"Video saved successfully to {selected_file}")


            except Exception as e:
                error_msg = f"Error saving video: {e}"
                print(error_msg)
                self.show_error(error_msg)

    def play_video(self):
        """Starts playback in both video widgets."""
        if not self.frames_before:
            print("No video loaded to play.")
            return

        # Start timer for 'Before' video
        self.before_video.start_timer()
        # Start timer for 'After' video only if it has frames
        if self.frames_after:
            self.after_video.start_timer()

    def stop_video(self):
        """Stops playback in both video widgets."""
        self.before_video.stop_timer()
        self.after_video.stop_timer()  # Safe to call even if no frames/timer running

    # --- Signal Handling Slots ---

    @pyqtSlot(list, list, list, list, list, list, list, list)
    def stabilization_completed(self, stabilized_frames, correction_transforms,
                                dx, dy, dr, smoothed_dx, smoothed_dy, smoothed_dr):
        """Handles the 'result' signal from the worker."""
        print("Stabilization data received from worker.")

        if not stabilized_frames:
            print("Stabilization completed but returned no frames.")
            self.stabilization_error("Processing completed but no frames were generated.")
            return

        # Store the results
        self.frames_after = stabilized_frames
        self.correction_transforms = correction_transforms
        self.dx, self.dy, self.dr = dx, dy, dr
        self.smoothed_dx, self.smoothed_dy, self.smoothed_dr = smoothed_dx, smoothed_dy, smoothed_dr

        # Update the 'After' video widget
        self.after_video.set_frames(self.frames_after)
        self.save_button.setEnabled(True)  # Enable save now
        print(f"Loaded {len(self.frames_after)} stabilized frames into 'After' widget.")



    @pyqtSlot()
    def stabilization_finished(self):
        """Handles the 'finished' signal from the worker."""
        print("Stabilization worker thread has finished.")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # Re-enable buttons that were disabled during processing
        self.stabilize_button.setEnabled(True)
        self.load_button.setEnabled(True)
        if self.frames_before:  # Only enable playback if a video is loaded
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)

        self.worker = None  # Clear the worker reference

    @pyqtSlot(str)
    def stabilization_error(self, error_message):
        """Handles the 'error' signal from the worker."""
        print(f"Stabilization Error Signal Received: {error_message}")
        self.show_error(f"Stabilization Failed: {error_message}")
        # Clean up UI state related to stabilization results
        self.frames_after = None
        self.after_video.set_frames(None)
        self.save_button.setEnabled(False)


    @pyqtSlot(str, int)
    def update_progress(self, message, value):
        """Handles the 'progress' signal from the worker."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(value)

    # --- UI Update Synchronization ---

    @pyqtSlot(int)
    def update_slider_from_video(self, index):
        """Updates slider position when video frame changes (e.g., during playback)."""
        if not self.updating_ui:  # Prevent loop if slider change triggered video change
            self.updating_ui = True
            self.slider.setValue(index)

            # Also sync the 'After' video if it exists and isn't the source
            if self.frames_after and self.sender() == self.before_video:
                self.after_video.change_frame(index)  # Directly change frame without starting timer

            self.updating_ui = False

    @pyqtSlot(int)
    def update_video_from_slider(self, index):
        """Updates video frames when the slider is moved manually."""
        if not self.updating_ui:  # Prevent loop if video change triggered slider change
            self.updating_ui = True

            # Stop playback temporarily if active
            before_was_playing = self.before_video.timer.isActive()
            after_was_playing = self.after_video.timer.isActive()
            if before_was_playing: self.before_video.stop_timer()
            if after_was_playing: self.after_video.stop_timer()

            # Change frame in both widgets
            if self.frames_before:
                self.before_video.change_frame(index)
            if self.frames_after:
                self.after_video.change_frame(index)

            # Resume playback if it was active
            if before_was_playing: self.before_video.start_timer()
            # Only resume 'after' if it exists AND was playing
            if after_was_playing and self.frames_after: self.after_video.start_timer()

            self.updating_ui = False

    # --- Helper Methods ---

    def show_error(self, message):
        """Displays an error message in the UI."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def hide_error(self):
        """Hides the error message label."""
        self.error_label.setText("")
        self.error_label.setVisible(False)
