# Comment_Analyze #

## 2025-02-20 ##
프로그램 내 GUI를 통해 유튜브 영상 검색 및 선택 가능 \
선택한 영상에 작성된 댓글의 감정(긍정, 부정, 중립)과 Topic 판별 \
영어는 Vader를, 한글은 KoBERT를 사용 (한글은 추가 조정이 필요해보임) 

----

## 2025-03-10 ##
캡스톤디자인2 프로젝트 주제로 선정 \
선택한 유튜브 동영상의 댓글 분석 \
가중치: 댓글의 좋아요 수, 대댓글 수, 특정 키워드 반복 수 \
ex 1-1: A기업과 관련된 영상의 댓글 분석 -> 키워드, 여론 파악 \
ex 1-1: 어떤 키워드(이유) 때문에 그와 같이 분석했는지 

1-1. 댓글 수집: Google API를 통해 동영상의 댓글 추출 \
1-2. 수정 사항: 기존에는 '좋아요 순' Top 10 댓글 추출 -> 전체 댓글 추출 \
1-3. 댓글 알바(여론조작)은 기존 '계정 생성일' 으로 필터링

2-1. 댓글 감정: 기존 KoBERT 유지 또는 Ko-Bert, DistilBERT 중 뛰어난 모델 선택 \
2-2. GPT API: GPT를 활용해 추출한 댓글의 감정 추가 분석

3-1. 데이터 시각화: matplotlib 또는 Seaborn을 이용해 시각적 자료 제공 

[❗] KoBERT, Ko-BERT, DistilBERT 각 성능 분석 및 비교 \
[❗] 댓글 추출 방식 수정 \
[❗] 가중치 업데이트 기능 개발 \
[❗] 키워드 추출 기능 개발 \
[❗] 데이터 시각화 기능 개발 \
[✔] 추출 댓글을 txt 파일로 변환 (2025-03-16)

----

## 2025-03-16: 댓글 추출 및 txt 변환 ##
기존 기능에서 top_n 값을 수정해 추출할 수 있는 댓글 수 조정 가능 \
추출한 댓글은 좋아요 순을 기준으로하여 txt 파일 형식으로 저장 가능

[❗] 기존 txt 파일이 존재하면 삭제 후 재작성 \
[❗] txt 파일로 변환 시 대댓글수 추가
