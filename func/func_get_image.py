from bs4 import BeautifulSoup
import requests
import os

def download_images(query, num_images, output_name):
    base_url = 'https://www.google.co.in'
    url = base_url + '/search?q=' + query + '&source=lnms&tbm=isch'
    headers={'User-Agent' : 'Mozilla/5.0'}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    images = soup.find_all(('img'))

    for i, img in enumerate(images[1:num_images+1]):
        img_url = img['src']

        if not img_url.startswith('http'):
            img_url = base_url + img_url

        response = requests.get(img_url)
        if output_name == '가게':
            with open(f'downloaded_images\\{query}.jpg', 'wb') as file:
                file.write(response.content)

        elif output_name == '음식':
            with open(f'downloaded_images\\{query}_{i}.jpg', 'wb') as file:
                file.write(response.content)

# # 테스트
# download_images('부산 신발원 가게 외부사진', 1, '가게')