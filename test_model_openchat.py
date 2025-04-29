import requests
import json
import re

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
        당신은 유튜브 여행 영상의 댓글을 분석해서 유용한 여행 정보를 요약하는 AI입니다.

        아래 댓글들을 읽고, 댓글에 나온 정보만 바탕으로 다음 세 가지 항목을 한국어로 간결하게 요약해 주세요.

        1. 맛집 추천 (가게명과 언급된 메뉴 위주로)
        2. 명소/관광지 (실제 장소명 위주)
        3. 여행 팁 (여행에 도움이 되는 정보나 주의사항)

        ※ 댓글에 해당 정보가 없으면 '없음'이라고 적어주세요.

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
            # print(f"\n [묶음 {i}] 요청 중...")

            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result_text = response.json()["choices"][0]["message"]["content"].strip()

            # print(f"\n [요약 결과 - 묶음 {i}]:\n{result_text}\n")

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
    places = set()
    for section in ["맛집", "명소"]:
        match = re.search(f"{section}:\s*(.*?)(?=(\n[A-Za-z가-힣]+:|$))", summary_text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            lines = re.findall(r"[-*•]?\s*([가-힣A-Za-z0-9\s]+)", content)
            for line in lines:
                clean = line.strip().split()[0]  # '백탄 고기집' → '백탄'
                if len(clean) > 1:
                    places.add(clean)
    return list(places)


REGION = "부산" 

# Google Custom Search API KEY
with open("api_search_place_info.txt", "r") as f:
    API_KEY = f.read()

with open("api_search_engine_key.txt", "r") as f:
    CSE_ID = f.read()

place_category = {}

# 실행 예시
file_path = "2025410_SLlN7ZgVT_w.txt"
summaries = analyze_comments_lmstudio_text(file_path)

place_category = {}
for summary in summaries:
    places = extract_places_from_summary(summary)
    for place in places:
        if place not in place_category:
            place_category[place] = classify_place_google(place, REGION, API_KEY, CSE_ID)

# ⬇ 요약 결과 교정하기
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
