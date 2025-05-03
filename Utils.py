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

def save_video(self):
    if not self.frames_after:
        print("No frames to save!")
        return

    height, width, channels = self.frames_after[0].shape
    fps = 30  # Or set based on your actual video

    # Choose path (optional: QFileDialog for UI)
    output_path = "stabilized_output.mp4"
    fourcc = cv.VideoWriter_fourcc(*'mp4v')
    out = cv.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in self.frames_after:
        out.write(frame)

    out.release()
    print(f"Video saved to {output_path}")

def plot(data,legend):
    plt.plot(data)
    plt.legend(legend)
    plt.show()