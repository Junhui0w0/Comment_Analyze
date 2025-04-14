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

    comment_chunks = chunk_comments(comments, 20)

    results = []

    for i, chunk in enumerate(comment_chunks, 1):
        combined_comments = "\n".join([f"- {c['text']}" for c in chunk])

        prompt = f"""
            당신은 유튜브 여행 영상 댓글을 분석하여 유용한 정보를 정리하는 AI입니다.
            아래 댓글들을 참고하여 다음 세 가지 항목을 한국어로 자연스럽게 요약해 주세요:

            1. **맛집 추천** (가게명 중심, 메뉴 포함 가능)
            2. **명소/관광지** (실제 장소 이름)
            3. **여행 팁** (유용한 팁, 주의사항, 추천 일정 등)

            반드시 댓글에 실제로 언급된 정보만 기반으로 작성하고, 내용이 없으면 "없음"이라고 명시하세요.
            맛집을 작성할 때 '가게명-대표메뉴명' 형식으로 작성하세요.
            대표메뉴명은 댓글이 아닌, 인터넷에서 '가게명' 을 검색한 뒤, 최상단 메뉴 하나를 작성해주세요.
            여행 팁 부분에는 여행과 관련된 내용만 작성하세요.
            여행 팁 부분에는 해당 지역을 방문하면서 얻은 사람들의 경험을 요약해서 작성하세요.
            여행 팁 부분에 의상이나 패션과 관련된 내용은 작성하지 마세요.
            
            ---
             댓글 목록:
            {combined_comments}

            ---
            요약 형식 예시:
            맛집: XXX가 인기 많았고, XXX도 추천됨.
            명소: XXX, XXX 같은 관광지가 언급됨.
            팁: 사람들이 말한 팁은 XXX와 XXX이 있음.
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



# # 실행 예시
# file_path = "2025410_SLlN7ZgVT_w.txt"
# summaries = analyze_comments_lmstudio_text(file_path)


# # 최종 전체 출력
# print("\n\n [전체 요약 결과]")
# for idx, summary in enumerate(summaries, 1):
#     print(f"\n--- 묶음 {idx} ---\n{summary}")























