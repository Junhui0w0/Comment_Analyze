import tkinter as tk
import requests
from io import BytesIO
from tkinter import ttk
from PIL import Image, ImageTk
from func.func_get_image import download_images
import webbrowser

with open("api\\api_kakao.txt", 'r', encoding='utf-8') as f:
    API_KAKAO = f.readline()

# def fetch_place_info(place_name, front_img): #region matzip, img
#     # 예: Kakao API 호출
#     headers = {"Authorization": f'KakaoAK {API_KAKAO}'}
#     params = {"query": place_name}
#     res = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=headers, params=params)
#     data = res.json()

#     if data['documents']:
#         place = data['documents'][0]
#         return {
#             "name": place['place_name'],
#             "address": place['road_address_name'],
#             "url": place['place_url'],
#             "category": place['category_name'],
#             "image" : front_img
#             # "x": place['x'], "y": place['y']
#         }
    
#     return None

def fetch_place_info(place_name, region):
    headers = {"Authorization": f'KakaoAK {API_KAKAO}'}
    params = {"query": place_name}
    res = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=headers, params=params)
    data = res.json()

    if data['documents']:
        place = data['documents'][0]

        #가게명 추출 후 이미지 다운
        name = place['place_name']
        download_images(f'{region} {name} 가게 외부사진', 1, '가게')
        download_images(f'{region} {name} 음식사진', 3, '음식')


        return {
            "name": place['place_name'],
            "address": place['road_address_name'],
            "url": place['place_url'],
            "category": place['category_name'],
            "image" : f'downloaded_images\\{region} {name} 가게 외부사진.jpg'
            # "x": place['x'], "y": place['y']
        }
    
    return None


def show_res(place_lst):
    root = tk.Tk()
    root.title("맛집 정보 리스트")
    root.geometry("600x850")

    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    # 스크롤 프레임 설정
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # 항목별 UI 생성
    for place in place_lst:
        row_frame = tk.Frame(scrollable_frame, pady=10)

        # 이미지 로드 및 표시
        img = Image.open(place["image"]).resize((150, 150))
        photo = ImageTk.PhotoImage(img)
        img_label = tk.Label(row_frame, image=photo)
        img_label.image = photo  # 참조 유지
        img_label.pack(side="left", padx=10)



        # # 텍스트 정보
        # text_info = f"""가게이름: {place['name']} \n주소: {place['address']} \n카테고리: {place['category']}"""

        # text_label = tk.Label(row_frame, text=text_info, justify="left", anchor="w", font=("맑은 고딕", 11))
        # text_label.pack(side="left", padx=10)

        # # 지도 링크 하이퍼텍스트처럼 표시
        # url_label = tk.Label(row_frame, text="지도 바로가기", fg="blue", cursor="hand2", font=("맑은 고딕", 11, "underline"))
        # url_label.pack(side="left", padx=5)
        # url_label.bind("<Button-1>", lambda e, url=place['url']: webbrowser.open_new(url))



        # 텍스트 정보 (이름, 주소, 카테고리)
        text_info = f"""가게이름: {place['name']} \n주소: {place['address']} \n카테고리: {place['category']}"""

        text_label = tk.Label(row_frame, text=text_info, justify="left", anchor="w", font=("맑은 고딕", 11))
        text_label.pack(side="left", padx=10, anchor="n")

        # 지도 링크를 텍스트 아래에 추가
        url_label = tk.Label(row_frame, text="지도 바로가기", fg="blue", cursor="hand2", font=("맑은 고딕", 11, "underline"))
        url_label.pack(side="left", padx=10, anchor="n")
        url_label.bind("<Button-1>", lambda e, url=place['url']: webbrowser.open_new(url))


        row_frame.pack(fill="x")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    root.mainloop()

# # 테스트
# lst = ['돈가스', '양곱창','신발원','새우교자','백탄','양곱창집','톤쇼우', '나가하마만게츠','레인스트릿']
# place_json_data = []
# for text in lst:
#     place = fetch_place_info(f'부산 {text}')
#     place_json_data.append(place)
#     print(place)

