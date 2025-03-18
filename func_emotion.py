#===============================================================================================================#
# 감정 분석 및 주요 키워드 추출 함수
from gensim import corpora
from gensim.models import LdaModel
import spacy
import torch
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

def extract_topics(comments, num_topics=3, num_words=5):
    nlp = spacy.load("en_core_web_sm")
    processed_comments = []

    # 전처리: 불용어 제거 및 명사 추출
    for comment in comments:
        doc = nlp(comment.lower())
        tokens = [token.text for token in doc if token.is_alpha and not token.is_stop]
        processed_comments.append(tokens)

    # Gensim LDA 모델 학습
    dictionary = corpora.Dictionary(processed_comments)
    corpus = [dictionary.doc2bow(text) for text in processed_comments]
    lda_model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=10)

    topics = {}
    for idx, topic in lda_model.print_topics(num_topics=num_topics, num_words=num_words):
        topics[f"Topic {idx+1}"] = [word.split("*")[1].strip('"') for word in topic.split(" + ")]

    return topics

def analyze_video_comments(comments):
    # 댓글 텍스트만 추출 (좋아요 수 제거)
    comment_texts = [c.split("(")[0].strip() for c in comments]

    # 감정 분석 수행 (한국어 + 영어)
    sentiment_results = analyze_sentiments(comment_texts)
    print(f'sentiment_results: {sentiment_results}')

    # 토픽 모델링 수행
    topics = extract_topics(comment_texts)

    return sentiment_results, topics




#==[Version. KR]==
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from ekonlpy.sentiment import KSA
from konlpy.tag import Okt

# KoBERT 모델 및 토크나이저 로드 (분류 헤드 포함)
tokenizer = AutoTokenizer.from_pretrained(
    "monologg/kobert", 
    trust_remote_code=True
)
model = AutoModelForSequenceClassification.from_pretrained(
    "monologg/kobert", 
    num_labels=3,  # 0: 부정, 1: 중립, 2: 긍정
    trust_remote_code=True
)

# 레이블 매핑 확인 및 조정 (모델에 맞게 수정)
label_map = {0: "negative", 1: "neutral", 2: "positive"}  # 예시 매핑

def analyze_sentiments(comments):
    """KoBERT(한국어) + VADER(영어) 통합 감정 분석"""
    analyzer = SentimentIntensityAnalyzer()
    sentiment_results = {"positive": 0, "neutral": 0, "negative": 0}

    for comment in comments:
        if is_korean(comment):
            inputs = tokenizer(comment, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                outputs = model(**inputs)
            
            # 확률 기반 분류 (임계값 조정)
            probs = torch.softmax(outputs.logits, dim=1)[0]
            negative_prob = probs[0].item()  # 부정 확률
            
            # 임계값 설정: 부정 확률 > 30% 시 부정으로 분류
            if negative_prob > 0.3:  
                sentiment_results["negative"] += 1
            else:
                predicted_class = torch.argmax(probs).item()
                sentiment_results[label_map[predicted_class]] += 1
        else:
            # VADER를 이용한 영어 감정 분석
            scores = analyzer.polarity_scores(comment)
            if scores['compound'] >= 0.05:
                sentiment_results["positive"] += 1
            elif scores['compound'] <= -0.05:
                sentiment_results["negative"] += 1
            else:
                sentiment_results["neutral"] += 1

    # 비율 계산
    total = sum(sentiment_results.values())
    if total > 0:
        for key in sentiment_results:
            sentiment_results[key] = round((sentiment_results[key] / total) * 100, 2)
    
    return sentiment_results

def is_korean(text):
    """한글 포함 여부 확인"""
    return any('가' <= char <= '힣' for char in text)