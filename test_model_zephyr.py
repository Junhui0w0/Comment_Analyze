import requests
import json
import re

# 초기 값 설정
video_title = ''
region = ''

# API 키 불러오기
with open("api_search_place_info.txt", "r") as f:
    API_KEY = f.read()

with open("api_search_engine_key.txt", "r") as f:
    CSE_ID = f.read()

region_keywords = [
    "부산", "제주", "서울", "강릉", "여수", "속초", "인천", "경주", "전주",
    "강원도", "광주", "대구", "대전", "울산", "포항", "통영", "거제도", "목포",
    "남해", "평창", "태안", "안동", "청주", "충주", "삼척", "양양", "부여",
    "오사카", "도쿄", "후쿠오카", "교토", "나고야", "삿포로", "오키나와", "홋카이도",
    "세부", "보라카이", "마닐라", "방콕", "푸켓", "치앙마이", "싱가포르", "발리",
    "뉴욕", "로스앤젤레스", "라스베이거스", "샌프란시스코", "시카고",
    "런던", "파리", "로마", "바르셀로나", "베를린", "프라하", "암스테르담"
]

def get_region(title):
    for reg in region_keywords:
        if reg in title:
            return reg
    return ''

def clean_summary_output(summary_text):
    # Explanation:, Response: 같은 추가 텍스트 삭제
    summary_text = re.sub(r'###.*', '', summary_text, flags=re.DOTALL)
    summary_text = re.sub(r'Explanation:.*', '', summary_text, flags=re.DOTALL)
    summary_text = summary_text.strip()
    return summary_text


def chunk_comments(comments, chunk_size=10):
    return [comments[i:i + chunk_size] for i in range(0, len(comments), chunk_size)]

def analyze_comments_lmstudio_text(file_path: str) -> list:
    url = "http://localhost:1234/v1/chat/completions"
    comments = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                comment, likes = line.strip().rsplit("|", 1)
                comments.append({
                    "text": comment.strip(),
                    "likes": int(likes.strip())
                })

    comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:60]
    comment_chunks = chunk_comments(comments, 10)
    results = []

    for i, chunk in enumerate(comment_chunks, 1):
        combined_comments = "\n".join([f"- {c['text']}" for c in chunk])

        prompt = f"""
당신은 유튜브 여행 영상의 댓글을 분석하여 요약하는 한국어 AI입니다.

규칙:
- 반드시 댓글에 나온 정보만 요약하세요.
- 설명, 분석, 추가 설명, 이유를 작성하지 마세요.
- 감정 표현(예: 이쁘다, 결혼해주세요)과 무관한 내용은 제거하세요.
- 출력은 아래 포맷만 사용하세요.

출력 포맷:
맛집: (댓글에 등장한 가게명만 쉼표로 구분, 없으면 '없음')
명소: (댓글에 등장한 장소명만 쉼표로 구분, 없으면 '없음')
팁: (여행에 도움이 되는 실질적 팁만 최대 3줄 이내 작성, 없으면 '없음')

---
댓글 목록:
{combined_comments}
---
요약 시작:
맛집:
명소:
팁:
"""

        payload = {
            "messages": [
                {"role": "system", "content": "당신은 여행 정보를 요약하는 한국어 AI입니다."},
                {"role": "user", "content": prompt.strip()}
            ],
            "temperature": 0.2,
            "max_tokens": 800
        }

        headers = {"Content-Type": "application/json"}

        try:
            print(f"\n [묶음 {i}] 요청 중...")
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result_text = response.json()["choices"][0]["message"]["content"].strip()
            result_text = clean_summary_output(result_text)
            print(f"\n [요약 결과 - 묶음 {i}]:\n{result_text}\n")
            results.append(result_text)

        except Exception as e:
            print(f"[!] 에러 발생: {e}")
            continue

    return results

def classify_place_google(place_name, region, api_key, cse_id):
    query = f"{region} {place_name}"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query}

    try:
        res = requests.get(url, params=params)
        data = res.json()
        if "items" not in data:
            return "불명"

        content = " ".join(item["snippet"] for item in data["items"])
        food_keywords = ["맛집", "식당", "카페", "메뉴", "음식", "리뷰"]
        place_keywords = ["공원", "관광지", "전망대", "해변", "입장료", "포토존"]

        food_score = sum(kw in content for kw in food_keywords)
        place_score = sum(kw in content for kw in place_keywords)

        if food_score > place_score:
            return "맛집"
        elif place_score > food_score:
            return "명소"
        else:
            return "불명"
    except:
        return "불명"

def extract_places_from_summary(summary_text):
    bad_words = {"없음", "명소", "맛집", "여행", "5월", "귀중한", "행복", "컨텐츠", "브이로그", "추천"}
    places = set()

    for section in ["맛집", "명소"]:
        match = re.search(f"{section}:\s*(.*?)(?=\n[A-Za-z가-힣]+:|$)", summary_text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            lines = re.split(r"[,\n]", content)
            for line in lines:
                clean = line.strip().split()[0]
                if len(clean) > 1 and clean not in bad_words:
                    places.add(clean)
    return list(places)


def rewrite_summary(summary_text):
    url = "http://localhost:1234/v1/chat/completions"

    prompt = f"""
당신은 여행 정보를 친절하고 자연스럽게 **한국어**로 소개하는 작가입니다.

아래 정보를 참고하여 **한국어로 부드럽게** 풀어서 글을 작성해 주세요.
- 맛집과 명소는 추천하듯 자연스럽게 소개하세요.
- 팁은 여행자의 입장에서 유용하게 느껴질 수 있도록 부드럽게 조언해 주세요.
- 전체적으로 자연스러운 서술형 문장으로 연결해 주세요.
- 추가적인 창작은 하지 말고, 주어진 정보만 사용하세요.

---
주어진 요약:
{summary_text}
---
**한국어로 친절하게 작성한 소개글:**
"""

    payload = {
        "messages": [
            {"role": "system", "content": "당신은 여행 정보를 친절하고 자연스럽게 소개하는 한국어 작가입니다."},
            {"role": "user", "content": prompt.strip()}
        ],
        "temperature": 0.3,
        "max_tokens": 800
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"].strip()
        return result_text
    except Exception as e:
        print(f"[!] 에러 발생: {e}")
        return None

def summary_comments(filepath):
    place_category = {}
    print(f'전달받은 video_title : {video_title}')
    region = get_region(video_title)
    print(f'설정된 region: {region}')

    summaries = analyze_comments_lmstudio_text(filepath)

    for summary in summaries:
        places = extract_places_from_summary(summary)
        print(f'ai_open_chat - places 추출 : {places}')

        for place in places:
            if place not in place_category:
                place_category[place] = classify_place_google(place, region, API_KEY, CSE_ID)

    corrected_summaries = []

    for summary in summaries:
        for place, correct_type in place_category.items():
            if correct_type == "맛집" and place in summary and "명소" in summary:
                summary = re.sub(rf"(명소:.*?)(\b{re.escape(place)}\b)", r"맛집: \2", summary)
            elif correct_type == "명소" and place in summary and "맛집" in summary:
                summary = re.sub(rf"(맛집:.*?)(\b{re.escape(place)}\b)", r"명소: \2", summary)

        corrected_summaries.append(summary)

    print("\n\n[장소 분류 결과]")
    for place, category in place_category.items():
        print(f"{place}: {category}")

    print("\n\n[교정된 전체 요약 결과]")
    for idx, summary in enumerate(corrected_summaries, 1):
        print(f"\n--- 묶음 {idx} ---\n{summary}")

    print(f'\n\n\n================[rewriting]==================')
    print(rewrite_summary(corrected_summaries))

    return True
    


summary_comments('2025410_SLlN7ZgVT_w.txt')
