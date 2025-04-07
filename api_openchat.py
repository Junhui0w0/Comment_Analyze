import requests
import json
from collections import defaultdict
import re

def extract_json(text):
    matches = re.findall(r'\{[\s\S]*?\}', text)
    best = ""
    for m in matches:
        try:
            json.loads(m)
            if len(m) > len(best):
                best = m
        except json.JSONDecodeError:
            continue
    if best:
        return best
    else:
        return "{}" # 빈 json 객체 return


def analyze_comments_lmstudio(file_path: str) -> dict:
    url = "http://localhost:1234/v1/completions"

    comments = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                comment, likes = line.strip().rsplit("|", 1)
                comments.append({
                    "text": comment.strip(),
                    "likes": int(likes.strip())
                })

    comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:20]

    results = {"맛집": [], "명소": [], "팁": []}
    seen_entries = defaultdict(set)  # 중복 제거용

    for idx, comment in enumerate(comments, 1):
        prompt = f"""
            당신은 여행 정보를 정리해주는 AI입니다. 아래 댓글을 참고하여 다음 항목들을 JSON 형식으로 정확하게 추출하세요:

            요청사항:
            1. 반드시 JSON 형식으로만 출력하세요. 설명, 주석 등은 절대 포함하지 마세요.
            2. 문자열은 반드시 큰따옴표(")로 감싸주세요.
            3. 추출 항목은 "맛집", "명소", "팁" 입니다.
            4. 하나의 JSON 블럭만 출력하세요. 두 번 이상 반복해서 출력하지 마세요.
            5. 출력은 다음 형식으로 정확히 한 번만 출력해야 합니다.
            6. 일반 단어(감성, 감정, 홍시, 영상 등)는 가게이름으로 사용하지 마세요.
            7. 반드시 댓글에 명시적으로 언급된 정보만 추출해야 합니다. 댓글에 없는 정보는 절대 생성하지 마세요.
            8. 존재하지 않는 가게/장소 이름을 생성하지 마세요.
            9. "~같다", "~추천" 등 추측 표현이 포함된 경우 N/A 처리
            10. 메뉴 추천은 댓글에 정확한 메뉴명이 있을 때만 허용
            11. 댓글에 맛집, 명소, 팁에 해당하는 정보가 없을경우 반드시 "N/A"를 출력하세요.

            맛집:
            - 댓글에 명확하게 언급된 정보만 추출합니다.
            - 근거 없는 유추나 상상은 하지 않습니다.
            - 형식: [{{"가게이름": "OOO"}}]

            명소:
            - 댓글에 명확하게 언급된 정보만 추출합니다.
            - 근거 없는 유추나 상상은 하지 않습니다.
            - 유적지, 관광지, 특별히 방문할 만한 장소만 포함하세요. 단순한 역, 도시 이름, 평범한 거리 등은 제외하세요.
            - 명소에 관한 내용이 없으면 "N/A"를 작성하세요.
            - 형식: [{{"장소": "OOO"}}]

            팁:
            - 댓글에 명확하게 언급된 정보만 추출합니다.
            - 근거 없는 유추나 상상은 하지 않습니다.
            - 맛집이나 명소에 대한 방문 팁, 이용 시간, 추천 계절, 평균 비용 등 유용한 정보가 있다면 작성하세요.
            - 팁이 없으면 "N/A"를 작성하세요.
            - 형식: ["팁 내용"]

            댓글:
            {comment['text']}

            예시 출력:
            {{
                "맛집": [{{"가게이름": "예시가게"}}],
                "명소": [{{"장소": "예시장소"}}],
                "팁": ["예시팁"]
            }}
            """

        payload = {
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1,
            "stop": None
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            print(f"\n[{idx}/{len(comments)}] 댓글:\n{comment['text']}\n")

            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result_text = response.json()["choices"][0]["text"].strip()
            print(f"[모델 응답]:\n{result_text}\n")

            cleaned_text = extract_json(result_text)
            parsed = json.loads(cleaned_text)

            # 중복 제거 후 저장
            for key in results:
                if key in parsed and parsed[key] != "N/A":
                    for item in parsed[key]:
                        item_str = json.dumps(item, ensure_ascii=False)
                        if item_str not in seen_entries[key]:
                            results[key].append(item)
                            seen_entries[key].add(item_str)

            # 댓글별 결과 요약 로그
            print(f"[요약 결과]\n맛집: {parsed.get('맛집', 'N/A')}\n명소: {parsed.get('명소', 'N/A')}\n팁: {parsed.get('팁', 'N/A')}\n")

        except Exception as e:
            print(f"[!] 에러 발생: {e}")
            continue

    return results

file_path = "2025318_us85YTsz5hw.txt"
data = analyze_comments_lmstudio(file_path)

print(json.dumps(data, indent=2, ensure_ascii=False))