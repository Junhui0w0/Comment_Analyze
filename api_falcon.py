import re
from pathlib import Path
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    pipeline
)
import torch
import json

# 4-bit 양자화 설정
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    llm_int8_enable_fp32_cpu_offload=True  # CPU 오프로딩 활성화
)

max_memory = {
    0: "10GiB",  # GPU 0에 10GB 할당
    "cpu": "20GiB"  # CPU에 20GB 할당
}

# 경량화된 모델 초기화
tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-7b-instruct")
# model = AutoModelForCausalLM.from_pretrained(
#     "tiiuae/falcon-7b-instruct",
#     trust_remote_code=True,
#     device_map="auto",
#     max_memory = max_memory,
#     quantization_config=quant_config  # 4-bit 양자화 적용
# )

try:
    # 로컬 캐시에서 먼저 시도
    model = AutoModelForCausalLM.from_pretrained(
        "tiiuae/falcon-7b-instruct",
        # trust_remote_code=True,
        local_files_only=True,
        device_map="auto",
        max_memory = max_memory,
        quantization_config=quant_config
    )
except OSError:
    # 캐시 없을 경우 다운로드
    model = AutoModelForCausalLM.from_pretrained(
        "tiiuae/falcon-7b-instruct",
        device_map="auto",
        # trust_remote_code=True,
        max_memory = max_memory,
        quantization_config=quant_config
    )


# 파이프라인 초기화 (메모리 최적화)
analyzer = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    torch_dtype=torch.float16
)

def analyze_comments(file_path: str) -> dict:
    """최적화된 댓글 분석 함수"""
    json_str = ""
    
    try:
        # 파일 처리 (배치 처리 추가)
        comments = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    comment, likes = line.strip().rsplit("|", 1)
                    comments.append({
                        "text": comment.strip(),
                        "likes": int(likes.strip())
                    })

        # 상위 50개로 필터링 (메모리 절약)
        comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:50]
        print(f'추출된 comments_list: {comments}')

        # 최적화된 프롬프트
        prompt = """[INST] <<SYS>>
        **반드시 지켜야 할 규칙**
        1. 출력 형식 (반드시 준수)
        {{ 
            "맛집": [{{"이름":"...", "이유":"..."}}], 
            "명소": [{{"장소":"...", "특징":"..."}}],
            "팁": ["..."]
        }}
        2. 가중치: 좋아요 10당 +★1개 (예: 25좋아요 → ★★)

        **금지 사항**
        - JSON 외 추가 설명 절대 금지
        - 영어/일본어 사용 금지
        - 마크다운 사용 금지

        <</SYS>>
        {comments}
        [/INST]""".format()
        
        # 배치 처리 (2개씩)
        results = []
        for i in range(0, len(comments), 2): #0 ~ 99 (100회) -> 0 2 4 6 8 10 ... 98
            print(f'index = {i}')
            batch = comments[i:i+2]
            BATCH_SIZE = 2  # 상수 정의
            formatted_prompt = prompt.format(
                comments="\n".join([c['text'] for c in batch]),  # Likes 정보 제거
                batch_size=BATCH_SIZE  # 명시적 전달
            )
            
            # 메모리 효율적 생성
            output = analyzer(
                formatted_prompt,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                return_full_text=False
            )
            
            # JSON 처리 부분 전체 교체
            import regex  # 표준 re 대신 regex 모듈 사용

            raw_text = output[0]['generated_text']

            # JavaScript 키워드 제거
            filtered_text = re.sub(
                r'\b(useState|React|=>|import)\b', 
                '[INVALID]', 
                raw_text
            )


            try:
                # 개선된 정규식 (regex 설치 필요: pip install regex)
                json_pattern = r'(?<!: )\{(?:[^{}]|(?R))*\}'
                json_match = regex.search(
                    json_pattern, 
                    filtered_text, 
                    regex.DOTALL | regex.VERSION1
                )
                
                # 2. 확장된 유니코드 처리
                if json_match:
                    json_str = (
                        json_match.group(1)
                        .encode('utf-8')
                        .decode('unicode_escape')
                        .replace(r'\"', '"')
                        .replace(r"\'", "'")
                    )
                    
                    # 3. JSON 구조 강제 정렬
                    json_str = re.sub(r'//.*?\\n', '', json_str)  # 주석 제거
                    json_str = json_str.replace('True', 'true').replace('False', 'false')  # 부울값 정규화
                
                # 4. 키 존재 여부 검증 강화
                # 키 검증 강화
                REQUIRED_STRUCTURE = {
                    "맛집": list,
                    "명소": list,
                    "팁": list
                }

                for key, dtype in REQUIRED_STRUCTURE.items():
                    if not isinstance(result.get(key), dtype):
                        raise TypeError(f"{key} 타입 불일치: {type(result[key])}")

                try:
                    result = json.loads(json_str, strict=False)
                        
                except json.JSONDecodeError as e:
                    print(f"JSON 문법 오류: {e.doc[e.pos-20:e.pos+20]}")  # 오류 위치 하이라이트

            except Exception as e:
                print(f"심층 오류: {str(e)}")
                print(f"문제 구간:\n{json_str[:200]}...")  # 처음 200자만 출력


        # 최종 결과 병합
        return merge_results(results)

    except Exception as e:
        print(f"치명적 오류: {str(e)}")
        return {"error": str(e)}

def merge_results(results: list) -> dict:
    """부분 결과 통합 함수"""
    merged = {"맛집": [], "명소": [], "팁": []}
    for res in results:
        for key in merged.keys():
            if key in res:
                merged[key].extend(res[key])
    return merged

# 실행 예시 (메모리 정리 추가)
with torch.no_grad():
    result = analyze_comments("2025318_us85YTsz5hw")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    torch.cuda.empty_cache()
