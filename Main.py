import sys

from PyQt5.QtWidgets import QApplication

from ui.MainWindow import MainWindow


def main():
    # path = "Input/1.mp4"
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()