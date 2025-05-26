import sys
import requests

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from func.func_GetComments import get_top_comments
from func.func_output_txt import output_by_txt

from func.func_openchat_chat import summary_comments, execute
import func.func_openchat_chat

file_path = ''

# YouTube API Key - 유튜브 댓글 추출에 필요한 API 키 읽어오기
with open("api\\api_key.txt", "r") as f:
    YOUTUBE_API_KEY = f.read()

def get_filename():
    return file_path
    
class LoadingOverlay(QWidget): #Loading GIF 출력하는 Class
    def __init__(self, parent=None):
        super().__init__(parent) #파라미터로 parent 입력되면 상속
        self.setAttribute(Qt.WA_StyledBackground, True) #setStyleSheet("background-color: ...") 사용 가능
        self.setStyleSheet("background-color: rgba(255, 255, 255, 180);") #배경색상 -> 흰색 / 투명도 180
        self.setFixedSize(parent.size()) #parent size 상속
        self.setAttribute(Qt.WA_TransparentForMouseEvents) #loading gif을 적용되는 위젯이 마우스 이벤트 무시하게 됨

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter) #중앙 정렬

        gif_path = "ui\\loading.gif" #gif 경로 
        self.label = QLabel() #QLabel -> 화면에 출력
        self.movie = QMovie(gif_path) #QMovie -> 움직이는 데이터만 처리

        if not self.movie.isValid(): #예외 디버깅
            print("⚠️ loading.gif 로딩 실패:", gif_path)

        self.label.setMovie(self.movie) #라벨에 movie 적용 -> 움직이는 물체를 화면에 출력해주기 위함
        self.movie.start()

        layout.addWidget(self.label)
        self.setLayout(layout)
        self.hide() #-> 특정 이벤트가 수행될 때 마다 GIF 출력 (기본값은 hide)

    def show(self): #특정 이벤트 수행될 때 gif 출력
        self.movie.start()
        self.raise_() #최상단 위치 -> 다른 위젯에 가리지 않게
        super().show()

    def hide(self):
        self.movie.stop()
        super().hide()

class AnalyzeWorker(QThread):#Anaylze 버튼을 눌렀을 때 수행
    finished = pyqtSignal(list) 
    error = pyqtSignal(str)

    def __init__(self, selected_videos):
        super().__init__()
        self.selected_videos = selected_videos

    def run(self):
        try:
            all_results = []
            for video_widget in self.selected_videos: #내가 선택한 video
                video_data = video_widget.video_data
                video_id = video_data.get('videoId')
                if not video_id:
                    continue
                comments = get_top_comments(video_id, top_n=100) #선택한 영상에서 댓글 추출
                func.func_openchat_chat.video_title = video_data.get('title', 'No Title') 
                file_path = output_by_txt(video_id, comments, video_data.get('title', 'No Title')) #추출한 댓글(str) -> txt 파일로 변환

                result_data = func.func_openchat_chat.summary_comments(file_path) #댓글 내용 기반으로 AI 요약 -> 맛집, 명소, 팁 추출
                if isinstance(result_data, list):  # 안전성 확보 -> 만약 result_data의 데이터 타입이 list가 아니면 잘못된 것
                    all_results.extend(result_data)

            self.finished.emit(all_results)

        except Exception as e:
            self.error.emit(str(e))

class SearchWorker(QThread): #검색란에 영상 제목 검색 후 수행할 클래스
    search_completed = pyqtSignal(list)  # 리스트 형태로 비디오 데이터 emit

    def __init__(self, query, api_key):
        super().__init__()
        self.query = query #내가 입력한 영상 제목(쿼리)
        self.api_key = api_key

    def run(self):
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': self.query,
                'key': self.api_key,
                'type': 'video',
                'maxResults': 15 #출력할 유튜브 영상의 최대 갯수
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            video_ids = []
            video_id_to_snippet = {}

            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                video_id = item.get('id', {}).get('videoId')
                if video_id:
                    video_ids.append(video_id)
                    snippet["videoId"] = video_id
                    video_id_to_snippet[video_id] = snippet

            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                'part': 'statistics',
                'id': ','.join(video_ids),
                'key': self.api_key
            }

            stats_response = requests.get(stats_url, params=stats_params)
            stats_response.raise_for_status()
            stats_data = stats_response.json()

            video_stats = {item['id']: item['statistics'] for item in stats_data.get('items', [])}

            # 최종 데이터 패킹
            video_list = []
            for video_id in video_ids:
                snippet = video_id_to_snippet.get(video_id, {})
                stats = video_stats.get(video_id, {})
                snippet["commentCount"] = stats.get("commentCount", "알 수 없음")
                video_list.append(snippet)

            self.search_completed.emit(video_list)

        except Exception as e:
            print(f"SearchWorker Error: {e}")
            self.search_completed.emit([])


class ClickableLabel(QLabel): #클릭기능이 추가된 QLabel 구현
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        self.clicked.emit()

class VideoWidget(QWidget): #영상 제목 검색 후 출력되는 정보 -> 썸네일, 영상제목, 영상 설명, 댓글 수
    def __init__(self, video_data, parent=None):
        super().__init__(parent)
        self.video_data = video_data or {}
        self.selected = False
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()

        thumbnails = self.video_data.get('thumbnails', {}) #썸네일
        medium_thumb = thumbnails.get('medium', {}) #좋아요 수
        thumbnail_url = medium_thumb.get('url', '')

        self.img_label = ClickableLabel() #썸네일은 클릭이 가능한 Label
        pixmap = QPixmap()
        if thumbnail_url:
            try:
                image_data = requests.get(thumbnail_url).content
                pixmap.loadFromData(image_data)
            except Exception as e:
                print(f"썸네일 로드 실패: {e}")
                pixmap = QPixmap("placeholder.jpg")
        else:
            pixmap = QPixmap("placeholder.jpg")

        thumbnail_width = 240
        thumbnail_height = 160
        self.img_label.setFixedSize(thumbnail_width, thumbnail_height) #썸네일 크기 지정
        self.img_label.setPixmap(pixmap.scaled(
            thumbnail_width, thumbnail_height,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        ))

        # self.img_label.setStyleSheet("border-radius: 6px;border: 1px solid #222;")
        self.img_label.setStyleSheet("""
            ClickableLabel{border-radius: 6px;border: 1px solid #222;}
            ClickableLabel:hover{background:#ADB6FF;} """) #UI 효과
        
        self.img_label.clicked.connect(self.toggle_selection) #클릭 이벤트 연결

        content_layout = QVBoxLayout()

        self.title_label = QLabel(self.video_data.get('title', 'No Title')) #제목 추출
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #202020;")

        comment_count = self.video_data.get("commentCount", "알 수 없음") #댓글 수 추출

        channel = QLabel(f"Channel: {self.video_data.get('channelTitle', 'Unknown')} | 댓글수: {comment_count}")
        channel.setStyleSheet("color: #707070; font-size: 12px;")

        description = QLabel(self.video_data.get('description', 'No Description')[:100] + "...") #영상 설명 추출
        description.setWordWrap(True)
        description.setStyleSheet("color: #505050; font-size: 13px;")

        content_layout.addWidget(self.title_label)
        content_layout.addWidget(channel)
        content_layout.addWidget(description)

        layout.addWidget(self.img_label)
        layout.addLayout(content_layout)

        self.setLayout(layout)
        self.setStyleSheet("""
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        """)

    def toggle_selection(self):
        parent_app = self.window()
        if not isinstance(parent_app, YouTubeSearchApp):
            return

        if not self.selected: #선택했을 때
            self.img_label.setStyleSheet("""
    border-radius: 6px;
    border: 1px solid #222;
    background-color: #6B70FF;
""")
            self.selected = True
            parent_app.add_to_selected(self)
        else: #선택 해제했을 때
            self.img_label.setStyleSheet("""
                ClickableLabel{border-radius: 6px;border: 1px solid #222;}
                ClickableLabel:hover{background:#ADB6FF;} """)
            self.selected = False
            parent_app.remove_from_selected(self)

class YouTubeSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)
        self.selected_videos = []
        self.initUI()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.offset = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.setFixedSize(self.size())

    def initUI(self):
        self.setWindowTitle('YouTube Search')
        self.setGeometry(300, 300, 800, 600)

        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #ffffff;")
        self.setCentralWidget(main_widget)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📺 유튜브 댓글 분석")
        title.setStyleSheet("font-weight: bold; color: black; padding-left: 10px;")

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

        layout = QVBoxLayout()

        layout.setContentsMargins(5, 5, 5, 5)  # 바깥 여백 제거
        layout.addLayout(title_bar)  # 타이틀 바 삽입

        search_bar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색 할 내용을 입력해주세요.")
        self.search_input.setStyleSheet("""
    QLineEdit {
        border: 2px solid #ccc;
        border-radius: 6px;
        padding: 10px;
        font-size: 14px;
    }
""")

        btn_style = """
            QPushButton {
                font-size: 14px;
                background-color: #0078d7;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005fa1;
            }
        """

        search_btn = QPushButton("Search")
        search_btn.setStyleSheet(btn_style)
        search_btn.clicked.connect(self.search_videos)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(btn_style.replace("#0078d7", "#FF0000").replace("#005fa1", "#C80000"))
        clear_btn.clicked.connect(self.clear_selected_videos)

        next_btn = QPushButton("Next")
        next_btn.setStyleSheet(btn_style.replace("#0078d7", "#28a745").replace("#005fa1", "#1e7e34"))
        next_btn.clicked.connect(self.show_selected_videos)

        search_bar_layout.addWidget(self.search_input)
        search_bar_layout.addWidget(search_btn)
        search_bar_layout.addWidget(clear_btn)
        search_bar_layout.addWidget(next_btn)

        self.scroll_area = QScrollArea()
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.results_container)
        self.scroll_area.setStyleSheet("""
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


        layout.addLayout(search_bar_layout)
        layout.addWidget(self.scroll_area)

        main_widget.setLayout(layout)


    def display_results(self, video_list):
        for i in reversed(range(self.results_layout.count())):
            widget_to_remove = self.results_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.deleteLater()

        for snippet in video_list:
            QApplication.processEvents()
            video_widget = VideoWidget(snippet)
            self.results_layout.addWidget(video_widget)

        self.loading_overlay.hide()

    def search_videos(self):
        query = self.search_input.text().strip()

        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search term!")
            return

        self.loading_overlay.show()
        QApplication.processEvents()

        self.worker = SearchWorker(query, YOUTUBE_API_KEY)
        self.worker.search_completed.connect(self.display_results)
        self.worker.start()


    def add_to_selected(self, video_widget):
        if video_widget not in self.selected_videos:
            self.selected_videos.append(video_widget)

    def remove_from_selected(self, video_widget):
        if video_widget in self.selected_videos:
            self.selected_videos.remove(video_widget)

    def analyze_comments(self, parent_window):
        for video_widget in self.selected_videos:
            video_data = video_widget.video_data
            video_id = video_data.get('videoId')
            if not video_id:
                continue
            try:
                comments = get_top_comments(video_id, top_n=100)
                func.func_openchat_chat.video_title = video_data.get('title', 'No Title')
                file_path = output_by_txt(video_id, comments, video_data.get('title', 'No Title'))
                summary_comments(file_path)
            except Exception as e:
                print(f'yt_gui의 analyze_comments 디버깅 에러 발생: {e}')

    def clear_selected_videos(self):
        for widget in self.selected_videos:

            widget.selected = False  # 상태 초기화
            widget.img_label.setStyleSheet("""
                border-radius: 6px;
                border: 1px solid #222;
                padding: 7px;
            """)

        self.selected_videos.clear()

    def show_selected_videos(self):
        if not self.selected_videos:
            QMessageBox.warning(self, "Warning", "No videos selected!")
            return

        selected_window = QDialog(self)
        selected_window.setWindowTitle("Selected Videos")
        selected_window.resize(500, 500)

        dialog_layout = QVBoxLayout(selected_window)

        for video_widget in self.selected_videos:
            video_data = video_widget.video_data

            thumbnail_url = video_data.get('thumbnails', {}).get('medium', {}).get('url', '')
            pixmap = QPixmap()
            if thumbnail_url:
                try:
                    image_data = requests.get(thumbnail_url).content
                    pixmap.loadFromData(image_data)
                except Exception as e:
                    print(f"썸네일 로드 실패: {e}")
                    pixmap = QPixmap("placeholder.jpg")
            else:
                pixmap = QPixmap("placeholder.jpg")

            item_layout = QHBoxLayout()
            img_label = QLabel()
            img_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio))
            title_label = QLabel(video_data.get('title', 'No Title'))
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")

            item_layout.addWidget(img_label)
            item_layout.addWidget(title_label)

            container_widget = QWidget()
            container_widget.setLayout(item_layout)
            dialog_layout.addWidget(container_widget)

        analyze_button = QPushButton("Analyze")

        selected_loading = LoadingOverlay(selected_window)
        selected_loading.setGeometry(0, 0, selected_window.width(), selected_window.height())

        def start_analysis():
            selected_loading.show()
            self.analysis_worker = AnalyzeWorker(self.selected_videos)

            def on_finished(result_data):
                selected_loading.hide()
                selected_window.accept()
                execute(result_data)

            self.analysis_worker.finished.connect(on_finished)
            self.analysis_worker.error.connect(lambda msg: print(f"Error: {msg}"))
            self.analysis_worker.start()

        analyze_button.clicked.connect(start_analysis)
        dialog_layout.addWidget(analyze_button)

        selected_window.setLayout(dialog_layout)
        selected_window.exec_()

    def on_analysis_finished(self, result_data):
        self.loading_overlay.hide()
        execute(result_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeSearchApp()
    ex.show()
    sys.exit(app.exec_())

