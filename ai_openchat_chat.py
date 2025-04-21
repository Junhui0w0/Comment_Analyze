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



# 실행 예시
file_path = "2025410_SLlN7ZgVT_w.txt"
summaries = analyze_comments_lmstudio_text(file_path)


# 최종 전체 출력
print("\n\n [전체 요약 결과]")
for idx, summary in enumerate(summaries, 1):
    print(f"\n--- 묶음 {idx} ---\n{summary}")

