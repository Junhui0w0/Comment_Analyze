import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QMovie


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GIF 로딩 테스트")
        self.setGeometry(300, 300, 400, 300)

        self.loading_label = QLabel(self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("background-color: rgba(255, 255, 255, 200);")
        self.loading_label.setGeometry(0, 0, 400, 300)

        # QMovie 객체로 GIF 지정
        self.loading_movie = QMovie("ui\\loading.gif")
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.hide()  # 처음엔 숨김

        # 버튼 생성
        self.button = QPushButton("테스트", self)
        self.button.clicked.connect(self.show_loading)

        # 레이아웃 설정
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.button)
        layout.addStretch()
        self.setCentralWidget(central_widget)

    def show_loading(self):
        self.loading_label.show()
        self.loading_movie.start()

        # 2초 후 숨기기 (테스트용)
        QTimer.singleShot(2000, self.hide_loading)

    def hide_loading(self):
        self.loading_movie.stop()
        self.loading_label.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())