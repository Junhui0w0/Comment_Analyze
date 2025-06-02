import requests
import sys
import json
from io import BytesIO

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PIL import Image, ImageTk

try:
    from func.func_get_image import download_images  # main에서 실행 시
except ImportError:
    from func_get_image import download_images       # 단독 실행 시

import webbrowser

cur_region = ''

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

def fetch_place_info(place_name, region, category):
    if category == '맛집':

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
    
    elif category == '명소':
        download_images(f'{place_name}', 3, '명소')

        return{
            "name":f"{place_name}",
            "image_1":f"downloaded_images\\{place_name}_0.jpg",
            "image_2":f"downloaded_images\\{place_name}_1.jpg",
            "image_3":f"downloaded_images\\{place_name}_2.jpg"
        }

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

class ChatbotStreamWorker(QThread):
    new_text = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, question):
        super().__init__()
        self.question = question

    def run(self):
        url = "http://localhost:1234/v1/chat/completions"
        prompt = f"""
        당신은 여행 정보를 친절하고 자연스럽게 한국어로 전달하는 가이드입니다.
        질문을 정확히 이해하고 한국어로 간결하게 답해주세요.
        교통수단은 '버스', '지하철', '택시', '도보' 등으로 분류하여 알려주세요.
        버스 노선은 최대 5개만 답해주세요.
        각 항목은 띄어쓰기를 추가하여 가시성을 높여주세요.
        
        사용자질문: {self.question}

        답변: 
        """
        payload = {
            "model": "llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "당신은 여행 정보를 친절하고 자연스럽게 소개하는 한국어 작가입니다."},
                {"role": "user", "content": prompt.strip()}
            ],
            "stream": True,
            "temperature": 0.4,
            "max_tokens": 400
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True)
            for line in response.iter_lines():
                if line:
                    if line.decode("utf-8").strip() == "data: [DONE]":
                        break
                    data = json.loads(line.decode("utf-8").replace("data: ", ""))
                    delta = data['choices'][0]['delta'].get('content', '')
                    self.new_text.emit(delta)
        except Exception as e:
            self.new_text.emit(f"❌ 오류 발생: {str(e)}")

        self.finished.emit()

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

        name = place["name"]
        print(f'region = {cur_region}, name = {name}')        
        image_paths = [
            f'downloaded_images\\{cur_region} {name} 음식사진_0.jpg',
            f'downloaded_images\\{cur_region} {name} 음식사진_1.jpg',
            f'downloaded_images\\{cur_region} {name} 음식사진_2.jpg'
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

class MyeongsoCard(QFrame):
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
        # 전체 수직 레이아웃
        layout = QVBoxLayout()

        # 1. 텍스트 라벨 (명소 이름)
        label = QLabel(f"명소이름: {place['name']}")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        # 2. 이미지 수평 레이아웃
        image_layout = QHBoxLayout()
        image_layout.setSpacing(10)

        for key in ["image_1", "image_2", "image_3"]:
            image_label = QLabel()
            image_label.setFixedSize(120, 120)
            image_label.setStyleSheet("padding: 0px;")

            pixmap = QPixmap(place[key])
            if not pixmap.isNull():
                rounded = get_rounded_pixmap(pixmap, radius=12, size=120)
                image_label.setPixmap(rounded)

            image_layout.addWidget(image_label)

        layout.addLayout(image_layout)
        self.setLayout(layout)


class PlaceListChatWindow(QDialog):
    def __init__(self, place_list, parent=None):
        super().__init__(parent)
        self.place_list = place_list
        self.offset = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.initUI()

    def initUI(self):
        self.resize(1100, 850)
        self.setStyleSheet("background-color: transparent;")

        bg_frame = QFrame(self)
        bg_frame.setObjectName("bg_frame")
        bg_frame.setStyleSheet("""
            QFrame#bg_frame {
                background-color: #f2f2f2;
                border-radius: 12px;
            }
        """)
        bg_layout = QHBoxLayout(bg_frame)
        bg_layout.setContentsMargins(10, 10, 10, 10)

        # 좌측: 맛집/명소 리스트
        list_layout = QVBoxLayout()
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

        list_layout.addLayout(title_bar)

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

        self.myeongso_lst = []
        container = QWidget()
        vbox = QVBoxLayout(container)
        for place in self.place_list:
            if 'image_1' not in place:
                card = PlaceCard(place)
                vbox.addWidget(card)
                vbox.addSpacing(10)
            else:
                self.myeongso_lst.append(place)

        for myeongso in self.myeongso_lst:
            card = MyeongsoCard(myeongso)
            vbox.addWidget(card)
            vbox.addSpacing(10)

        vbox.addStretch()
        scroll.setWidget(container)

        list_layout.addWidget(scroll)
        bg_layout.addLayout(list_layout, 3)

        # 우측: 챗봇 영역
        chatbot_frame = QFrame()
        chatbot_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #ccc;
                padding: 12px;
            }
        """)
        chatbot_layout = QVBoxLayout(chatbot_frame)
        chatbot_layout.setSpacing(10)

        title_label = QLabel("💬 여행 챗봇")
        title_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        chatbot_layout.addWidget(title_label)

        self.response_box = QTextBrowser()
        self.response_box.setPlaceholderText("질문 내용에 대한 답변")
        self.response_box.setStyleSheet("font-size: 13px; border: 1px solid #ccc; border-radius: 6px; padding: 6px;")
        chatbot_layout.addWidget(self.response_box, stretch=3)

        self.input_box = QTextEdit()
        self.input_box.setFixedHeight(80)
        self.input_box.setPlaceholderText("질문 내용 작성")
        self.input_box.setStyleSheet("font-size: 13px; border: 1px solid #ccc; border-radius: 6px; padding: 6px;")
        chatbot_layout.addWidget(self.input_box)

        self.ask_btn = QPushButton("질문하기")
        self.ask_btn.setCursor(Qt.PointingHandCursor)
        self.ask_btn.setStyleSheet("""
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
        self.ask_btn.clicked.connect(self.handle_chatbot)
        chatbot_layout.addWidget(self.ask_btn, alignment=Qt.AlignRight)

        bg_layout.addWidget(chatbot_frame, 2)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(bg_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def handle_chatbot(self):
        question = self.input_box.toPlainText().strip()
        if not question:
            self.response_box.setText("❗ 질문을 입력해 주세요.")
            return

        self.response_box.clear()
        self.response_box.setText("⌛ 답변을 생성 중입니다...\n")
        self.worker = ChatbotStreamWorker(question)
        self.worker.new_text.connect(self.append_response_text)
        self.worker.finished.connect(self.finish_response)
        self.worker.start()

    def append_response_text(self, text):
        self.response_box.moveCursor(QTextCursor.End)
        self.response_box.insertPlainText(text)
        self.response_box.moveCursor(QTextCursor.End)

    def finish_response(self):
        self.response_box.append("\n\n✅ 답변 완료")

    def mouseMoveEvent(self, event):
        if self.offset and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


def execute(data_lst):
    dialog = PlaceListChatWindow(data_lst)
    dialog.exec_()



if __name__ == "__main__":
    cur_region = '경주'
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
        },

        {
            "name":"해운대",
            "image_1":"downloaded_images\\부산 해운대_0.jpg",
            "image_2":"downloaded_images\\부산 해운대_1.jpg",
            "image_3":"downloaded_images\\부산 해운대_2.jpg"
        }
    ]
        
    # app = QApplication(sys.argv)
    # window = PlaceListWindow(test_data)
    # window.show()
    # sys.exit(app.exec_())

    app = QApplication(sys.argv)
    window = PlaceListChatWindow(test_data)
    window.show()
    sys.exit(app.exec_())
