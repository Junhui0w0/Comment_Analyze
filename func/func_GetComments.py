from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone 

# api 키 추출
with open('api\\api_key.txt', 'r', encoding='UTF-8') as f:
    api_key = f.read() 


#youtube api 호출 -> 댓글 추출에 필요한 api
youtube = build('youtube', 'v3', developerKey=api_key)


# FUNC_계정 생성일 반환 -> 댓글 필터링
def parse_youtube_date(date_str):
    # 1. '+'로 끝나는 경우 제거 (예: '2021-07-11T10:02:32.66107+')
    if date_str.endswith('+'):
        date_str = date_str[:-1]
    
    # 2. 시간대 정보가 없는 경우 UTC로 강제 지정
    if 'Z' in date_str:
        date_str = date_str.replace('Z', '+00:00')
    elif '+' not in date_str:
        date_str += '+00:00'
    
    # 3. 마이크로초 보정
    if '.' in date_str:
        main_part, fractional = date_str.split('.')
        fractional = fractional.split('+')[0][:6].ljust(6, '0')  # 6자리로 정규화
        date_str = f"{main_part}.{fractional}+00:00"
    
    return datetime.fromisoformat(date_str).astimezone(timezone.utc)

# FUNC_6개월 이내 계정 생성 여부 -> 댓글 필터링
def filter_recent_accounts(comments):
    current_date = datetime.now(timezone.utc)
    cutoff_date = current_date - timedelta(days=180)
    
    # 채널 ID 추출
    channel_ids = list({c['author_id'] for c in comments if c['author_id']})
    
    # 채널 정보 일괄 조회
    channels = []
    for i in range(0, len(channel_ids), 50):  # 50개씩 분할 조회
        batch = channel_ids[i:i+50]
        response = youtube.channels().list(
            part='snippet',
            id=','.join(batch),
            maxResults=50
        ).execute()
        channels.extend(response.get('items', []))
    
    # 생성일 매핑 테이블
    creation_dates = {item['id']: item['snippet']['publishedAt'] for item in channels}
    
    # 필터링 적용
    return [
        comment for comment in comments
        if parse_youtube_date(
            creation_dates.get(comment['author_id'], '2000-01-01T00:00:00Z')
        ).date() < cutoff_date.date()
    ]

# 좋아요 갯수 top 10 리스트 추출
def get_top_comments(video_id, top_n=10):
    all_comments = []
    next_page_token = None

    while True:
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=50,
            order='relevance',
            textFormat='plainText',
            pageToken=next_page_token
        ).execute()

        batch = []
        for item in response['items']:
            # likes 값 추출 (dict 또는 int 처리)
            likes_data = item['snippet']['topLevelComment']['snippet'].get('likeCount', 0)
            if isinstance(likes_data, dict):
                likes = likes_data.get('value', 0)
            else:
                likes = int(likes_data)

            batch.append({
                'text': item['snippet']['topLevelComment']['snippet']['textDisplay'],
                'likes': likes,  # 숫자로 강제 변환
                'author_id': item['snippet']['topLevelComment']['snippet'].get('authorChannelId', {}).get('value')
            })

        all_comments.extend(batch)

        next_page_token = response.get('nextPageToken')
        if not next_page_token or len(all_comments) >= 500:
            break

    # 좋아요 순 정렬
    sorted_comments = sorted(all_comments, key=lambda x: x['likes'], reverse=True)
    print(f'[디버깅_Func] get_top_commtents: 좋아요 순으로 정렬된 댓글 lst \n {sorted_comments}')

    # 상위 N개 댓글 반환
    return [
        f"{c['text']} | {c['likes']}"
        for idx, c in enumerate(sorted_comments[:top_n])
    ]
