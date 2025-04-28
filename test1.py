import requests
import json
import re

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
            print('\nitesm not in data')
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
            print('\nplace_scoe equals food_score')
            return "불명"
    except:
        print('\nException Error')
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

test_place = ['이재모 피자', '톤쇼우', '대저생태공원', '태종대', '황령산벚꽃길', '옥계관']
place_category = {}

for place in test_place:
    if place not in place_category:
        category = classify_place_google(place, REGION, API_KEY, CSE_ID)
        place_category[place] = category

print("\n\n[장소별 분류 결과]")
for place, category in place_category.items():
    print(f"{place}: {category}")