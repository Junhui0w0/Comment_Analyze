import requests
import json
import re
from func.func_kakao_navi import classify_place_kakao
from func.func_get_image import download_images
from func.func_kakao_search_info import fetch_place_info, show_res

# 초기 값 설정
video_title = ''
region = ''

matzip_lst = []
myeongso_lst = []
tip_lst = []

#제목에서 region 추출
region_keywords = [
    "부산", "제주", "서울", "강릉", "여수", "속초", "인천", "경주", "전주",
    "강원도", "광주", "대구", "대전", "울산", "포항", "통영", "거제도", "목포",
    "남해", "평창", "태안", "안동", "청주", "충주", "삼척", "양양", "부여",
    "오사카", "도쿄", "후쿠오카", "교토", "나고야", "삿포로", "오키나와", "홋카이도",
    "세부", "보라카이", "마닐라", "방콕", "푸켓", "치앙마이", "싱가포르", "발리",
    "뉴욕", "로스앤젤레스", "라스베이거스", "샌프란시스코", "시카고",
    "런던", "파리", "로마", "바르셀로나", "베를린", "프라하", "암스테르담"
]

#제목에서 region 추출 func
def get_region(title):
    for reg in region_keywords:
        if reg in title:
            return reg
    return ''

# API 키 불러오기
with open("api\\api_search_place_info.txt", "r") as f:
    API_KEY = f.read()

#google custom search API 키
with open("api\\api_search_engine_key.txt", "r") as f:
    CSE_ID = f.read()

#1회 묶음에 댓글 전달 func
def chunk_comments(comments, chunk_size=10):
    return [comments[i:i + chunk_size] for i in range(0, len(comments), chunk_size)]

#1차 댓글 요약 func
def analyze_comments_lmstudio_text(file_path: str) -> list:
    url = "http://192.168.75.162:1234/v1/chat/completions"
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
    comment_chunks = chunk_comments(comments, 20)
    results = []

    for i, chunk in enumerate(comment_chunks, 1):
        combined_comments = "\n".join([f"- {c['text']}" for c in chunk])

        prompt = f"""
        당신은 유튜브 여행 영상의 댓글을 분석하여 요약하는 한국어 AI입니다.

        규칙:
        - 반드시 댓글에 나온 정보만 요약하세요.
        - 설명, 분석, 추가 설명, 이유를 작성하지 마세요.
        - 팁 부분에는 반드시 이동수단 혹은 웨이팅과 관련된 내용만 작성하세요.
        - 감정 표현(예: 이쁘다, 결혼해주세요)과 무관한 내용은 제거하세요.
        - 출력은 아래 포맷만 사용하세요.
        - 출력 포멧에 특수문자는 쉼표(,)와 콜론(:)만 허용됩니다.
        - 맛집과 명소에는 장소에 해당하는 명사만 작성하세요.

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
            # result_text = clean_summary_output(result_text)

            # print(f'\n[Type] result_text: {type(result_text)}')
            print(f"\n [요약 결과 - 묶음 {i}]:\n{result_text}\n")
            results.append(result_text)

            combined_data = result_text.split('\n') #-> [맛집:..., 명소:..., 팁:...]
            print(combined_data)

            matzip_lst.extend(combined_data[0].split(':')[1].strip().split(','))
            myeongso_lst.extend(combined_data[1].split(':')[1].strip().split(','))
            tip_lst.extend(combined_data[2].split(':')[1].strip().split(','))

            print(f'----------- \n {matzip_lst} \n {myeongso_lst} \n {tip_lst} \n')


        except Exception as e:
            print(f"[!] 에러 발생: {e}")
            continue

    return results


#Google Custom Search -> 장소가 맛집인지, 명소인지 구분 func
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

#2차 작성 func
def rewrite_summary(summary_text):
    # next_sign = input('진행 (Y/N): ')
    url = "http://localhost:1234/v1/chat/completions"

    prompt = f"""
    당신은 여행 정보를 친절하고 자연스럽게 한국어로 소개하는 작가입니다.

    아래 정보를 참고하여 부드럽고 따뜻한 문체로 자연스럽게 글을 작성해 주세요.

    **지침:**
    - 맛집과 명소는 추천하듯 자연스럽게 문장으로 풀어 주세요.
    - 팁은 여행자의 입장에서 유용하게 느껴질 수 있도록 부드럽게 조언해 주세요.
    - 전체 글은 **자연스럽게 연결된 서술형 문장**으로 작성하세요.
    - **절대로 1., 2., 3. 처럼 번호를 매기거나 목록 형태로 나열하지 마세요.**
    - 추가적인 창작은 하지 말고, 주어진 정보만 사용하세요.
    - 문단 구성을 자연스럽게 하되, 필요하면 2~3문단 정도로 나누어도 됩니다.
    - 맛집, 명소, 팁은 서로 구분되게 문단을 크게 나눠서 읽기 편하게 해주세요.

    ---
    주어진 요약:
    {summary_text}
    ---
    한국어로 자연스럽고 부드럽게 작성한 소개글:

    """

    payload = {
        "messages": [
            {"role": "system", "content": "당신은 여행 정보를 친절하고 자연스럽게 소개하는 한국어 작가입니다."},
            {"role": "user", "content": prompt.strip()}
        ],
        "temperature": 0.4,
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

#2. KAKAO 지도 API 활용
#1차 -> 2차 -> return 파이프라인 func
def summary_comments(filepath):
    global matzip_lst, myeongso_lst, tip_lst

    # place_category = {}
    print(f'전달받은 video_title : {video_title}')
    region = get_region(video_title)
    print(f'설정된 region: {region}')

    analyze_comments_lmstudio_text(filepath)

    #matzip_lst // myeongso_lst 의 값을 병합해서 다시 구분 -> Google Custom Search 사용 -> 음.. kakao 지도 api도 괜찮을 거 같은데 ?

    #1. google custom search
    place_lst = []
    place_lst.extend(matzip_lst)
    place_lst.extend(myeongso_lst)

    matzip_lst = []
    myeongso_lst = []

    for place in place_lst:
        if place == '없음': continue

        guess_place = classify_place_kakao(place, region)
        
        if guess_place == '맛집':
            matzip_lst.append(place)
        elif guess_place == '명소':
            myeongso_lst.append(place)
        else:
            continue

    print('==============================')
    print('분석된 맛집:', matzip_lst)
    print(f'분석된 명소: {myeongso_lst}')
    print(f'분석된 팁: {tip_lst}')
    print('==============================')

    matzip_json_data = []

    # #대표 이미지 추출 (가게 정면 사진 1장, 메뉴 사진 3장)
    # for matzip in matzip_lst:
    #     download_images(f'{region} {matzip} 가게 외부사진', 1, '가게')
    #     download_images(f'{region} {matzip} 음식사진', 3, '음식')

    #     data = fetch_place_info(f'{region} {matzip}', f'downloaded_images\\{region} {matzip} 가게 외부사진.jpg')
    #     matzip_json_data.append(data)

    # show_res(matzip_json_data)

    url_set = set()
    for matzip in matzip_lst:
        data = fetch_place_info(f'{region} {matzip}', region)
        if data["url"] in url_set:
            continue
        
        url_set.add(data["url"])
        matzip_json_data.append(data)

    show_res(matzip_json_data)



    

    print(f'\n\n\n================[rewriting]==================')
    str_data = '최종 분석된 맛집 리스트는', *matzip_lst, '이고, 명소 리스트는', *myeongso_lst,'야. 댓글에서 알려준 여행관련 팁들은',*tip_lst,'이고, 팁 부분에서 웨이팅이나 이동수단 처럼 여행에 꼭 필요한 내용만 작성해줘'
    
    # print(rewrite_summary(str_data))


    #초기화
    matzip_lst.clear()
    myeongso_lst.clear()
    tip_lst.clear()
    url_set.clear()

    return True
    


if __name__ == '__main__':
# # 테스트
    summary_comments('2025410_SLlN7ZgVT_w.txt')