import requests
import sys
from io import BytesIO

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PIL import Image, ImageTk

# from func.func_get_image import download_images
from func_get_image import download_images

import webbrowser

with open("api\\api_kakao.txt", 'r', encoding='utf-8') as f:
    API_KAKAO = f.readline()

# def fetch_place_info(place_name, front_img): #region matzip, img
#     # 예: Kakao API 호출
#     headers = {"Authorization": f'KakaoAK {API_KAKAO}'}
#     params = {"query": place_name}
#     res = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=headers, params=params)
#     data = res.json()

#     if data['documents']:
#         place = data['documents'][0]
#         return {
#             "name": place['place_name'],
#             "address": place['road_address_name'],
#             "url": place['place_url'],
#             "category": place['category_name'],
#             "image" : front_img
#             # "x": place['x'], "y": place['y']
#         }
    
#     return None

def fetch_place_info(place_name, region):
    headers = {"Authorization": f'KakaoAK {API_KAKAO}'}
    params = {"query": place_name}
    res = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=headers, params=params)
    data = res.json()

    if data['documents']:
        place = data['documents'][0]

        #가게명 추출 후 이미지 다운
        name = place['place_name']
        download_images(f'{region} {name} 가게 외부사진', 1, '가게')
        download_images(f'{region} {name} 음식사진', 3, '음식')


        return {
            "name": place['place_name'],
            "address": place['road_address_name'],
            "url": place['place_url'],
            "category": place['category_name'],
            "image" : f'downloaded_images\\{region} {name} 가게 외부사진.jpg',
            "phone" : place.get("phone", "없음"),
            # "x": place['x'], "y": place['y']
        }
    
    return None

def get_rounded_pixmap(pixmap, radius, size): #이미지 둥글게
    pixmap = pixmap.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    rounded = QPixmap(size, size)
    rounded.fill(Qt.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return rounded

class ClickableLabel(QLabel):
    clicked = pyqtSignal()  # PyQt5 시그널

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

class ImageGridDialog(QDialog): #1행 3열로 이미지 출력
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("가게 음식사진")
        self.setFixedSize(600, 200)
        self.setStyleSheet("""
            QDialog{
                background-color:white;               
            }

            QFrame{
                padding: 0px;
            }
        """)

        layout = QHBoxLayout(self)

        for path in image_paths:
            label = QLabel()
            pixmap = QPixmap(path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            rounded = get_rounded_pixmap(pixmap, radius=12, size=180)
            label.setPixmap(rounded)

            # label.setPixmap(pixmap)
            label.setFixedSize(180, 180)
            layout.addWidget(label)

class PlaceCard(QFrame):
    def __init__(self, place):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #ccc;
                padding: 10px;
            }
        """)
        self.init_ui(place)

    def show_image_grid(self, image_paths):
        dialog = ImageGridDialog(image_paths, self)
        dialog.exec_()

    def init_ui(self, place):
        layout = QHBoxLayout()
        image_label = ClickableLabel()
        image_label.setStyleSheet("""
            QFrame{
                padding: 0px;
            }
        """)
        image_label.setFixedSize(120, 120)
        pixmap = QPixmap(place["image"])
        if not pixmap.isNull():
            rounded = get_rounded_pixmap(pixmap, radius=12, size=120)
            image_label.setPixmap(rounded)

        region = place["address"].split()[0]  # 예: 서울
        name = place["name"]
        print(f'region = {region}, name = {name}')        
        image_paths = [
            f'downloaded_images\\{region} {name} 음식사진_0.jpg',
            f'downloaded_images\\{region} {name} 음식사진_1.jpg',
            f'downloaded_images\\{region} {name} 음식사진_2.jpg'
        ]

        image_label.clicked.connect(lambda: self.show_image_grid(image_paths))
        # pixmap = QPixmap(place["image"])
        # if not pixmap.isNull():
        #     rounded = get_rounded_pixmap(pixmap, radius=12, size=120)
        #     image_label.setPixmap(rounded)
        # image_label.setFixedSize(120, 120)
        layout.addWidget(image_label)

        text_layout = QVBoxLayout()

        text_info = f"""<b>가게이름:</b> {place['name']}<br>
<b>카테고리:</b> {place['category']}<br><br>

<b>주소:</b> {place['address']}<br>
<b>전화번호:</b> {place['phone']}"""
        label = QLabel(text_info)
        label.setStyleSheet("font-size: 13px; color: #333;")
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)

        btn = QPushButton("지도 바로가기")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #5CA8F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b92dc;
            }
        """)
        btn.clicked.connect(lambda: webbrowser.open(place["url"]))

        text_layout.addWidget(label)
        text_layout.addWidget(btn, alignment=Qt.AlignLeft)
        layout.addLayout(text_layout)
        self.setLayout(layout)

class PlaceListWindow(QDialog):
    def __init__(self, place_list, parent=None):
        super().__init__(parent)
        self.place_list = place_list
        self.offset = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.initUI()

    def initUI(self):
        self.resize(600, 850)
        self.setStyleSheet("background-color: transparent;")

        bg_frame = QFrame(self)
        bg_frame.setObjectName("bg_frame")
        bg_frame.setStyleSheet("""
            QFrame#bg_frame {
                background-color: #f2f2f2;
                border-radius: 12px;
            }
        """)
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(10, 10, 10, 10)

        title_bar = QHBoxLayout()
        title = QLabel("🍽 맛집 리스트")
        title.setStyleSheet("font-weight: bold; font-size: 16px; padding-left: 10px;")

        btn_min = QPushButton("-")
        btn_max = QPushButton("□")
        btn_close = QPushButton("✕")

        for btn in (btn_min, btn_max, btn_close):
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    color: black;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #C0C0C0;
                }
            """)

        btn_min.clicked.connect(self.showMinimized)
        btn_max.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(title)
        title_bar.addStretch()
        title_bar.addWidget(btn_min)
        title_bar.addWidget(btn_max)
        title_bar.addWidget(btn_close)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                margin: 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #888;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        container = QWidget()
        vbox = QVBoxLayout(container)
        for place in self.place_list:
            card = PlaceCard(place)
            vbox.addWidget(card)
            vbox.addSpacing(10)
        vbox.addStretch()
        scroll.setWidget(container)

        bg_layout.addLayout(title_bar)
        bg_layout.addWidget(scroll)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(bg_frame)

    # 창 드래그 이동 지원
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


def execute(data_lst):
    dialog = PlaceListWindow(data_lst)
    dialog.exec_() 



if __name__ == "__main__":
    test_data = [
        {
            "name": "경주십원빵 대릉원",
            "address": "경주 강남구 테헤란로 123",
            "url": "https://place.map.kakao.com/12345678",
            "category": "한식 > 고기집",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg",
            "phone" : "010-1234-5678"
        },
        {
            "name": "교동집밥 경주황리단길점",
            "address": "경주 중구 명동길 9",
            "url": "https://place.map.kakao.com/23456789",
            "category": "일식 > 돈까스",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg",
            "phone" : "010-1234-5678"
        },
        {
            "name": "길한우",
            "address": "경주 해운대구 해운대로 456",
            "url": "https://place.map.kakao.com/34567890",
            "category": "일식 > 초밥",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg",
            "phone" : "010-1234-5678"
        },
        {
            "name": "면타작",
            "address": "경주 유성구 대학로 99",
            "url": "https://place.map.kakao.com/45678901",
            "category": "일식 > 라멘",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg",
            "phone" : "010-1234-5678"
        },
        {
            "name": "뽀빠이짜장",
            "address": "경주 남동구 예술로 21",
            "url": "https://place.map.kakao.com/56789012",
            "category": "중식 > 중화요리",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg",
            "phone" : "010-1234-5678"
        }
    ]
        
    app = QApplication(sys.argv)
    window = PlaceListWindow(test_data)
    window.show()
    sys.exit(app.exec_())
