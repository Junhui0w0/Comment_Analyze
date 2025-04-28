# import requests
# import json
# import re

# def chunk_comments(comments, chunk_size=20):
#     return [comments[i:i + chunk_size] for i in range(0, len(comments), chunk_size)]

# def analyze_comments_lmstudio_text(file_path: str) -> list:
#     url = "http://localhost:1234/v1/chat/completions"

#     # 파일에서 댓글 읽기
#     comments = []
#     with open(file_path, "r", encoding="utf-8") as f:
#         for line in f:
#             if "|" in line:
#                 comment, likes = line.strip().rsplit("|", 1)
#                 comments.append({
#                     "text": comment.strip(),
#                     "likes": int(likes.strip())
#                 })

#     # 좋아요 수 기준 정렬 후 상위 60개 (20개씩 3묶음 예시)
#     comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:60]

#     comment_chunks = chunk_comments(comments, 10)

#     results = []

#     for i, chunk in enumerate(comment_chunks, 1):
#         combined_comments = "\n".join([f"- {c['text']}" for c in chunk])

#         prompt = f"""
#         당신은 유튜브 여행 영상의 댓글을 분석해서 유용한 여행 정보를 요약하는 AI입니다.

#         아래 댓글들을 읽고, 댓글에 나온 정보만 바탕으로 다음 세 가지 항목을 한국어로 간결하게 요약해 주세요.

#         1. 맛집 추천 (가게명과 언급된 메뉴 위주로)
#         2. 명소/관광지 (실제 장소명 위주)
#         3. 여행 팁 (여행에 도움이 되는 정보나 주의사항)

#         ※ 댓글에 해당 정보가 없으면 '없음'이라고 적어주세요.

#         ---
#         댓글 목록:
#         {combined_comments}

#         ---
#         요약:
#         맛집:
#         명소:
#         팁:
#         """


#         payload = {
#             "messages": [
#                 {"role": "system", "content": "당신은 여행 정보를 요약해주는 한국어 AI입니다."},
#                 {"role": "user", "content": prompt.strip()}
#             ],
#             "temperature": 0.4,
#             "max_tokens": 800
#         }

#         headers = {
#             "Content-Type": "application/json"
#         }

#         try:
#             print(f"\n [묶음 {i}] 요청 중...")

#             response = requests.post(url, headers=headers, data=json.dumps(payload))
#             response.raise_for_status()
#             result_text = response.json()["choices"][0]["message"]["content"].strip()

#             print(f"\n [요약 결과 - 묶음 {i}]:\n{result_text}\n")

#             results.append(result_text)

#         except Exception as e:
#             print(f"[!] 에러 발생: {e}")
#             continue

#     return results



# # 실행 예시
# file_path = "2025410_SLlN7ZgVT_w.txt"
# summaries = analyze_comments_lmstudio_text(file_path)


# # 최종 전체 출력
# print("\n\n [전체 요약 결과]")
# for idx, summary in enumerate(summaries, 1):
#     print(f"\n--- 묶음 {idx} ---\n{summary}")















import requests
import json
import re


#초기 값 설정
video_title = ''
region = ''
#음... 영상제목에서 대부분 장소를 명시해줄텐데..
#1. 영상 제목에서 추출
#2. 댓글에서 추출

#-> 영상 제목을 최우선으로 추출함 (title=영상제목)
#-> 영상 제목에 없을 경우(if title==None), 댓글에서 장소를 추출(title = 댓글제목)
#-> 댓글에 따라 장소를 동적으로 변경

# Google Custom Search API KEY
with open("api_search_place_info.txt", "r") as f:
    API_KEY = f.read()

with open("api_search_engine_key.txt", "r") as f:
    CSE_ID = f.read()

region_keywords = [
    # 국내
    "부산", "제주", "서울", "강릉", "여수", "속초", "인천", "경주", "전주",
    "강원도", "광주", "대구", "대전", "울산", "포항", "통영", "거제도", "목포",
    "남해", "평창", "태안", "안동", "청주", "충주", "삼척", "양양", "부여",
    # 일본
    "오사카", "도쿄", "후쿠오카", "교토", "나고야", "삿포로", "오키나와", "홋카이도",
    # 동남아
    "세부", "보라카이", "마닐라", "방콕", "푸켓", "치앙마이", "싱가포르", "발리",
    # 미국
    "뉴욕", "로스앤젤레스", "라스베이거스", "샌프란시스코", "시카고",
    # 유럽
    "런던", "파리", "로마", "바르셀로나", "베를린", "프라하", "암스테르담"
]

def get_region(title):
    for reg in region_keywords:
        if reg in title:
            return reg
        
    return ''

def chunk_comments(comments, chunk_size=20):
    return [comments[i:i + chunk_size] for i in range(0, len(comments), chunk_size)]

def analyze_comments_lmstudio_text(file_path: str) -> list:
    url = "http://localhost:1234/v1/chat/completions"

    # 파일에서 댓글 읽기
    comments = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                comment, likes = line.strip().rsplit("|", 1)
                comments.append({
                    "text": comment.strip(),
                    "likes": int(likes.strip())
                })

    # 좋아요 수 기준 정렬 후 상위 60개 (20개씩 3묶음 예시)
    comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:60]

    comment_chunks = chunk_comments(comments, 10)

    results = []

    for i, chunk in enumerate(comment_chunks, 1):
        combined_comments = "\n".join([f"- {c['text']}" for c in chunk])

        prompt = f"""
        당신은 유튜브 여행 영상의 댓글을 분석하여 유용한 여행 정보를 요약하는 AI입니다.

        아래 댓글을 분석해, 반드시 다음과 같은 형식으로 출력하세요.

        **출력 형식**
        - 맛집: 장소명1, 장소명2, 장소명3 (가게명만, 쉼표(,)로 구분)
        - 명소: 장소명1, 장소명2, 장소명3 (지명만, 쉼표(,)로 구분)
        - 팁: 여행에 도움이 되는 문장 (복수 문장 가능)

        **지침**
        - 맛집과 명소는 반드시 "가게명/장소명"만 나열하고, 문장 작성 금지.
        - 문장 없이, 쉼표(,)로만 구분하세요.
        - 해당 정보가 없으면 '없음'이라고만 작성하세요.
        - 반드시 항목 이름(맛집:, 명소:, 팁:)을 포함하세요.

        ---
        댓글 목록:
        {combined_comments}
        ---
        요약:
        맛집:
        명소:
        팁:
        """



        payload = {
            "messages": [
                {"role": "system", "content": "당신은 여행 정보를 요약해주는 한국어 AI입니다."},
                {"role": "user", "content": prompt.strip()}
            ],
            "temperature": 0.4,
            "max_tokens": 800
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            print(f"\n [묶음 {i}] 요청 중...")

            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result_text = response.json()["choices"][0]["message"]["content"].strip()

            print(f"\n [요약 결과 - 묶음 {i}]:\n{result_text}\n")

            results.append(result_text)

        except Exception as e:
            print(f"[!] 에러 발생: {e}")
            continue

    return results


def classify_place_google(place_name, region, api_key, cse_id):
    query = f"{region} {place_name}"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query
    }

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
        match = re.search(f"{section}:\s*(.*?)(?=(\n[A-Za-z가-힣]+:|$))", summary_text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            lines = re.split(r"[,\n]", content)
            for line in lines:
                clean = line.strip().split()[0]
                if len(clean) > 1 and clean not in bad_words:
                    places.add(clean)
    return list(places)

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

    return True




# # 실행 예시
# file_path = "2025410_SLlN7ZgVT_w.txt"
# summaries = analyze_comments_lmstudio_text(file_path)

# place_category = {}
# for summary in summaries:
#     places = extract_places_from_summary(summary)
#     for place in places:
#         if place not in place_category:
#             place_category[place] = classify_place_google(place, REGION, API_KEY, CSE_ID)

# # ⬇ 요약 결과 교정하기
# corrected_summaries = []
# for summary in summaries:
#     for place, correct_type in place_category.items():
#         if correct_type == "맛집" and place in summary and "명소" in summary:
#             summary = re.sub(rf"(명소:.*?)(\b{re.escape(place)}\b)", r"맛집: \2", summary)
#         elif correct_type == "명소" and place in summary and "맛집" in summary:
#             summary = re.sub(rf"(맛집:.*?)(\b{re.escape(place)}\b)", r"명소: \2", summary)
#     corrected_summaries.append(summary)




# print("\n\n[장소 분류 결과]")
# for place, category in place_category.items():
#     print(f"{place}: {category}")

# print("\n\n[교정된 전체 요약 결과]")
# for idx, summary in enumerate(corrected_summaries, 1):
#     print(f"\n--- 묶음 {idx} ---\n{summary}")
