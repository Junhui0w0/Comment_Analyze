import requests

with open('api\\api_kakao.txt', 'r', encoding='utf-8') as f:
    KAKAO_API_KEY = f.readline()

def classify_place_kakao(place_name, region):
    query = f"{region} {place_name}"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "query": query
    }
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

        if "documents" not in data or not data["documents"]:
            return "불명"

        doc = data["documents"][0]  # 가장 일치도가 높은 결과
        category_name = doc.get("category_name", "")

        # 카카오 장소 카테고리 필터링
        if any(keyword in category_name for keyword in ["맛집", "식당", "카페", "메뉴", "음식", "리뷰"]):
            return "맛집"
        elif any(keyword in category_name for keyword in ["공원", "관광지", "전망대", "해변", "입장료", "포토존"]):
            return "명소"
        else:
            return "불명"

    except Exception as e:
        print(f"[Kakao API 오류] {e}")
        return "불명"

# lst = ['돈가스', ' 양곱창', '신발원', ' 새우교자', '백탄', ' 양곱창집', '광안리 센트럴 베이 호텔', ' 톤쇼우', ' 해운대', '나가하마만게츠', ' 반여동', '광안리']
# for i in lst:
#     r = classify_place_kakao(i, '부산')
#     print(f'{i} = {r}')