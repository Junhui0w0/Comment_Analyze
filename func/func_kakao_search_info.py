# import tkinter as tk
import requests
import sys
from io import BytesIO
# from tkinter import ttk

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea,
    QHBoxLayout, QMainWindow, QFrame
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt


from PIL import Image, ImageTk

from func.func_get_image import download_images
# from func_get_image import download_images

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
            "image" : f'downloaded_images\\{region} {name} 가게 외부사진.jpg'
            # "x": place['x'], "y": place['y']
        }
    
    return None


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

    def init_ui(self, place):
        layout = QHBoxLayout()

        # 이미지
        image_label = QLabel()
        pixmap = QPixmap(place["image"])
        if not pixmap.isNull():
            pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            image_label.setPixmap(pixmap)
        image_label.setFixedSize(120, 120)
        layout.addWidget(image_label)

        # 텍스트 & 버튼
        text_layout = QVBoxLayout()

        text_info = f"""<b>가게이름:</b> {place['name']}<br>
<b>주소:</b> {place['address']}<br>
<b>카테고리:</b> {place['category']}"""
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


class PlaceListWindow(QMainWindow):
    def __init__(self, place_list):
        super().__init__()
        self.place_list = place_list
        self.offset = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 100, 600, 850)

        # ▶ 중앙 위젯
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #f2f2f2;")
        self.setCentralWidget(main_widget)

        # ▶ 사용자 타이틀바
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🍽 맛집 리스트")
        title.setStyleSheet("font-weight: bold; color: black; font-size: 16px; padding-left: 10px;")

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

        # ▶ 콘텐츠 영역
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
            card = PlaceCard(place)  # 기존 카드 위젯
            vbox.addWidget(card)
            vbox.addSpacing(10)
        vbox.addStretch()
        scroll.setWidget(container)

        # ▶ 전체 레이아웃 조립
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addLayout(title_bar)
        layout.addWidget(scroll)

    # ▶ 창 드래그 이동 지원
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None





if __name__ == "__main__":
    test_data = [
        {
            "name": "삼겹살천국",
            "address": "서울특별시 강남구 테헤란로 123",
            "url": "https://place.map.kakao.com/12345678",
            "category": "한식 > 고기집",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg"
        },
        {
            "name": "명동돈까스",
            "address": "서울특별시 중구 명동길 9",
            "url": "https://place.map.kakao.com/23456789",
            "category": "일식 > 돈까스",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg"
        },
        {
            "name": "초밥이야기",
            "address": "부산광역시 해운대구 해운대로 456",
            "url": "https://place.map.kakao.com/34567890",
            "category": "일식 > 초밥",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg"
        },
        {
            "name": "라면대통령",
            "address": "대전광역시 유성구 대학로 99",
            "url": "https://place.map.kakao.com/45678901",
            "category": "일식 > 라멘",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg"
        },
        {
            "name": "홍콩반점",
            "address": "인천광역시 남동구 예술로 21",
            "url": "https://place.map.kakao.com/56789012",
            "category": "중식 > 중화요리",
            "image": "downloaded_images\\경주 경주십원빵 대릉원 가게 외부사진.jpg"
        }
    ]
        
    app = QApplication(sys.argv)
    window = PlaceListWindow(test_data)
    window.show()
    sys.exit(app.exec_())
    # # 테스트

    # lst = ['돈가스', '양곱창','신발원','새우교자','백탄','양곱창집','톤쇼우', '나가하마만게츠','레인스트릿']
    # place_json_data = []
    # for text in lst:
    #     place = fetch_place_info(f'부산 {text}')
    #     place_json_data.append(place)
    #     print(place)
