import streamlit as st

def display_summary(summary_text):
    st.set_page_config(page_title="부산 여행 요약", layout="centered")
    st.title("📦 최종 요약 결과")
    st.markdown(summary_text)

# 테스트용 텍스트
sample_summary = """
🍽️ 주요 맛집:
1. 톤쇼우 - 히레카츠, 웨이팅 있음
2. 신발원 - 새우교자
❗AI추천: 개금밀면 - 밀면

📍 명소:
1. 해운대 - 바다뷰
❗AI추천: 감천문화마을

💡 팁:
- 웨이팅 길다
- 사전 예약 필요
"""

# 메인 실행
if __name__ == "__main__":
    display_summary(sample_summary)
