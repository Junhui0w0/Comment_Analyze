import sys
import requests

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from func_GetComments import get_top_comments
from func_emotion import analyze_sentiments, extract_topics, analyze_video_comments
from func_output_txt import extract_from_txt, output_by_txt
from ai_openchat_chat import summary_comments
import ai_openchat_chat

file_path = ''

# YouTube API Key
with open("api_key.txt", "r") as f:
    YOUTUBE_API_KEY = f.read()

def get_filename():
    return file_path

class ClickableLabel(QLabel):
    clicked = pyqtSignal()  # 클릭 시 신호 발생

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        self.clicked.emit()  # 클릭 이벤트 발생


class VideoWidget(QWidget):
    def __init__(self, video_data, parent=None):
        super().__init__(parent)
        self.video_data = video_data or {}
        self.selected = False  # 선택 상태 저장
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()  # 썸네일과 콘텐츠를 가로로 배치

        # 썸네일 이미지 로드
        thumbnails = self.video_data.get('thumbnails', {})
        medium_thumb = thumbnails.get('medium', {})
        thumbnail_url = medium_thumb.get('url', '')

        self.img_label = ClickableLabel()
        pixmap = QPixmap()
        if thumbnail_url:
            try:
                image_data = requests.get(thumbnail_url).content
                pixmap.loadFromData(image_data)
            except Exception as e:
                print(f"썸네일 로드 실패: {e}")
                pixmap = QPixmap("placeholder.jpg")  # 기본 이미지 사용
        else:
            pixmap = QPixmap("placeholder.jpg")

        self.img_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio))
        self.img_label.setStyleSheet("border: 2px solid transparent;")  # 기본 테두리 없음
        self.img_label.clicked.connect(self.toggle_selection)  # 클릭 이벤트 연결

        # 콘텐츠 정보 표시
        content_layout = QVBoxLayout()

        self.title_label = QLabel(self.video_data.get('title', 'No Title'))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        channel = QLabel(f"Channel: {self.video_data.get('channelTitle', 'Unknown')}")
        channel.setStyleSheet("color: #606060; font-size: 12px;")

        description = QLabel(self.video_data.get('description', 'No Description')[:100] + "...")
        description.setWordWrap(True)
        description.setStyleSheet("color: #404040; font-size: 12px;")

        content_layout.addWidget(self.title_label)
        content_layout.addWidget(channel)
        content_layout.addWidget(description)

        # 전체 레이아웃 구성
        layout.addWidget(self.img_label)  # 썸네일 추가
        layout.addLayout(content_layout)  # 콘텐츠 추가

        self.setLayout(layout)

    def toggle_selection(self):
        parent_app = self.window()  # YouTubeSearchApp 참조
        if not isinstance(parent_app, YouTubeSearchApp):
            return

        if not self.selected:
            self.img_label.setStyleSheet("border: 2px solid red;")  # 빨간색 테두리 추가
            self.selected = True
            parent_app.add_to_selected(self)  # 부모 위젯에 선택 추가
        else:
            self.img_label.setStyleSheet("border: 2px solid transparent;")  # 테두리 제거
            self.selected = False
            parent_app.remove_from_selected(self)  # 부모 위젯에서 선택 제거



class YouTubeSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_videos = []  # 선택된 동영상 저장 리스트
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YouTube Search')
        self.setGeometry(300, 300, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()

        # 검색 바
        search_bar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search YouTube...")

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_videos)  # 검색 버튼 클릭 시 search_videos 호출

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_selected_videos)

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.show_selected_videos)  # Next 버튼 클릭 시 선택된 동영상 표시

        search_bar_layout.addWidget(self.search_input)
        search_bar_layout.addWidget(search_btn)
        search_bar_layout.addWidget(clear_btn)
        search_bar_layout.addWidget(next_btn)

        # 결과 표시 영역 (스크롤 가능)
        self.scroll_area = QScrollArea()
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)  # 세로 정렬

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.results_container)

        layout.addLayout(search_bar_layout)
        layout.addWidget(self.scroll_area)

        main_widget.setLayout(layout)

    def search_videos(self):
        query = self.search_input.text().strip()
        
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search term!")
            return
        
        # 기존 결과 삭제
        for i in reversed(range(self.results_layout.count())):
            widget_to_remove = self.results_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.deleteLater()
        
        # YouTube API 호출
        url = "https://www.googleapis.com/youtube/v3/search"
        
        params = {
            'part': 'snippet',
            'q': query,
            'key': YOUTUBE_API_KEY,
            'type': 'video',
            'maxResults': 10 #검색할 동영상 수
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # HTTP 오류 발생 시 예외 처리
            
            data = response.json()
            
            if 'items' not in data or not data['items']:
                QMessageBox.warning(self, "Warning", "No results found!")
                return
            
            for item in data['items']:
                snippet = item.get('snippet', {})
                video_id = item.get('id', {}).get('videoId')  # videoId 추출

                if not snippet or not video_id:
                    continue

                snippet['videoId'] = video_id  # videoId를 snippet에 추가
                video_widget = VideoWidget(snippet)  # VideoWidget 생성
                self.results_layout.addWidget(video_widget)
        
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch data: {str(e)}")


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
                # 댓글 수집 (좋아요 순위 TOP 10)
                comments = get_top_comments(video_id, top_n=100)  # 상위 100개 댓글 수집
                print(f'\n[디버깅-yt_gui.py] get_top_comments에서 추출된 댓글\n {comments}')
                print('\n[디버깅-yt_gui.py] analyze_comments에서 추출된 제목: ', video_data.get('title', 'No Title'))
                ai_openchat_chat.video_title = video_data.get('title', 'No Title')
                print(f'\n[디버깅-yt_gui.py] analyze_comments에서 추출된 video_id: {video_id}')

                file_path = output_by_txt(video_id, comments, video_data.get('title', 'No Title'))
                summary_comments(file_path)
            
            except Exception as e:
                print(f'yt_gui의 analyze_comments 디버깅 에러 발생: {e}')

    # def analyze_comments(self, parent_window):
    #     analysis_window = QDialog(parent_window)
    #     analysis_window.setWindowTitle("Comment Analysis")
    #     analysis_window.resize(600, 800)

    #     # 스크롤 영역 생성
    #     scroll_area = QScrollArea(analysis_window)
    #     scroll_area.setWidgetResizable(True)

    #     # 스크롤 콘텐츠 위젯
    #     scroll_content = QWidget()
    #     scroll_layout = QVBoxLayout(scroll_content)

    #     for video_widget in self.selected_videos:
    #         video_data = video_widget.video_data
    #         video_id = video_data.get('videoId')
    #         if not video_id:
    #             continue

    #         try:
    #             # 댓글 수집 (좋아요 순위 TOP 10)
    #             comments = get_top_comments(video_id, top_n=100)  # 상위 100개 댓글 수집
    #             print(f'\n[디버깅-yt_gui.py] get_top_comments에서 추출된 댓글\n {comments}')
    #             print('\n[디버깅-yt_gui.py] analyze_comments에서 추출된 제목: ', video_data.get('title', 'No Title'))
    #             ai_openchat_chat.video_title = video_data.get('title', 'No Title')
    #             print(f'\n[디버깅-yt_gui.py] analyze_comments에서 추출된 video_id: {video_id}')

    #             file_path = output_by_txt(video_id, comments, video_data.get('title', 'No Title'))
    #             summary_comments(file_path)

    #             #아래 감정 분석 파트는 없어도 될듯?

    #             # 감정 분석 및 토픽 모델링 수행
    #             sentiment_results, topics = analyze_video_comments(comments)

    #             # 동영상 제목 및 썸네일 표시
    #             thumbnail_url = video_data.get('thumbnails', {}).get('medium', {}).get('url', '')
    #             pixmap = QPixmap()
    #             if thumbnail_url:
    #                 try:
    #                     image_data = requests.get(thumbnail_url).content
    #                     pixmap.loadFromData(image_data)
    #                 except Exception as e:
    #                     print(f"썸네일 로드 실패: {e}")
    #                     pixmap = QPixmap("placeholder.jpg")  # 기본 이미지 사용
    #             else:
    #                 pixmap = QPixmap("placeholder.jpg")

    #             header_layout = QHBoxLayout()
    #             img_label = QLabel()
    #             img_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio))

    #             title_label = QLabel(video_data.get('title', 'No Title'))
    #             title_label.setWordWrap(True)
    #             title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-left: 10px;")

    #             header_layout.addWidget(img_label)
    #             header_layout.addWidget(title_label)

    #             header_widget = QWidget()
    #             header_widget.setLayout(header_layout)
    #             scroll_layout.addWidget(header_widget)

    #             # 감정 분석 결과 표시
    #             sentiment_label = QLabel(f"Sentiments - Positive: {sentiment_results['positive']}%, "
    #                                     f"Neutral: {sentiment_results['neutral']}%, "
    #                                     f"Negative: {sentiment_results['negative']}%")
    #             sentiment_label.setStyleSheet("font-size: 14px; color: #404040; margin-left: 15px; margin-top: 10px;")
    #             scroll_layout.addWidget(sentiment_label)

    #             # 토픽 모델링 결과 표시
    #             topic_label = QLabel("Topics:")
    #             topic_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
    #             scroll_layout.addWidget(topic_label)

    #             for topic, words in topics.items():
    #                 topic_line = QLabel(f"{topic}: {', '.join(words)}")
    #                 topic_line.setStyleSheet("font-size: 12px; color: #606060; margin-left: 15px;")
    #                 scroll_layout.addWidget(topic_line)

    #             layout_separator = QFrame()
    #             layout_separator.setFrameShape(QFrame.HLine)
    #             layout_separator.setStyleSheet("margin-top: 10px; margin-bottom: 10px; border: 1px solid #CCCCCC;")
    #             scroll_layout.addWidget(layout_separator)

    #             # 댓글 TOP 10 표시
    #             comment_title = QLabel("Top Comments (by Likes):")
    #             comment_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px;")
    #             scroll_layout.addWidget(comment_title)

    #             for idx, comment in enumerate(comments[:10], start=1):  # 상위 10개만 표시
    #                 comment_box = QGroupBox(f"{idx}.")
    #                 comment_layout = QVBoxLayout()

    #                 content_label = QLabel(comment.split("|")[0].strip())  # 댓글 내용
    #                 content_label.setWordWrap(True)
    #                 content_label.setStyleSheet("font-size: 14px; color: #404040;")

    #                 likes_count = '좋아요 수: ' + comment.split("|")[1].strip()
    #                 likes_label = QLabel(likes_count)  # 좋아요 수
    #                 likes_label.setStyleSheet("font-size: 12px; color: #606060; margin-top: 5px;")

    #                 comment_layout.addWidget(content_label)
    #                 comment_layout.addWidget(likes_label)

    #                 comment_box.setLayout(comment_layout)
    #                 scroll_layout.addWidget(comment_box)

    #         except Exception as e:
    #             error_label = QLabel(f"Failed to fetch comments for {video_data.get('title', 'No Title')}: {str(e)}")
    #             print(f'[디버깅-Erorr]: {str(e)}')
    #             error_label.setStyleSheet("color: red;")
    #             scroll_layout.addWidget(error_label)

    #     # 스크롤 영역에 콘텐츠 설정
    #     scroll_content.setLayout(scroll_layout)
    #     scroll_area.setWidget(scroll_content)

    #     main_layout = QVBoxLayout(analysis_window)
    #     main_layout.addWidget(scroll_area)
    #     analysis_window.setLayout(main_layout)

    #     analysis_window.exec_()

    def clear_selected_videos(self):
        self.selected_videos.clear()

    def show_selected_videos(self):
        """Next 버튼 클릭 시 선택된 동영상 정보를 표시"""
        # 선택된 동영상이 없을 경우 경고 메시지 표시
        if not self.selected_videos:
            QMessageBox.warning(self, "Warning", "No videos selected!")
            return

        # 새 창 생성
        selected_window = QDialog(self)
        selected_window.setWindowTitle("Selected Videos")
        selected_window.resize(500, 500)

        # 레이아웃 설정
        dialog_layout = QVBoxLayout(selected_window)

        # 선택된 동영상 정보 표시
        for video_widget in self.selected_videos:
            video_data = video_widget.video_data

            # 썸네일 로드
            thumbnail_url = video_data.get('thumbnails', {}).get('medium', {}).get('url', '')
            pixmap = QPixmap()
            if thumbnail_url:
                try:
                    image_data = requests.get(thumbnail_url).content
                    pixmap.loadFromData(image_data)
                except Exception as e:
                    print(f"썸네일 로드 실패: {e}")
                    pixmap = QPixmap("placeholder.jpg")  # 기본 이미지 사용
            else:
                pixmap = QPixmap("placeholder.jpg")

            # 썸네일과 제목을 가로로 배치
            item_layout = QHBoxLayout()

            img_label = QLabel()
            img_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio))

            title_label = QLabel(video_data.get('title', 'No Title'))
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")

            item_layout.addWidget(img_label)
            item_layout.addWidget(title_label)

            # 레이아웃에 추가
            container_widget = QWidget()
            container_widget.setLayout(item_layout)
            dialog_layout.addWidget(container_widget)

        # Analyze 버튼 추가
        analyze_button = QPushButton("Analyze")
        analyze_button.clicked.connect(lambda: self.analyze_comments(selected_window))
        dialog_layout.addWidget(analyze_button)

        # 창 실행
        selected_window.setLayout(dialog_layout)
        selected_window.exec_()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeSearchApp()
    ex.show()
    sys.exit(app.exec_())