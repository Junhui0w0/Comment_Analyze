import re
import regex  # 정규식 처리용 모듈 (pip install regex)
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

try:
    # 로컬 캐시에서 먼저 시도
    print("local 파일 사용")
    model = AutoModelForCausalLM.from_pretrained(
        "tiiuae/falcon-7b-instruct",
        local_files_only=True,  # 로컬 파일만 사용
        device_map="auto",
        max_memory=max_memory,
        quantization_config=quant_config
    )
except OSError:
    print("모델이 로컬에 존재하지 않습니다. 다운로드를 시작합니다...")
    model = AutoModelForCausalLM.from_pretrained(
        "tiiuae/falcon-7b-instruct",
        device_map="auto",
        max_memory=max_memory,
        quantization_config=quant_config
    )

# 파이프라인 초기화 (메모리 최적화)
analyzer = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    torch_dtype=torch.float16
)

def clean_raw_text(raw_text):
    """
    raw_text에서 깨진 문자와 특수 문자를 제거하는 함수
    """
    try:
        # UTF-8로 디코딩 후 다시 인코딩 (깨진 문자 처리)
        cleaned_text = raw_text.encode("utf-8", "replace").decode("utf-8")

        # 정규식을 사용해 허용되지 않는 문자 제거 (ASCII 및 한글만 허용)
        cleaned_text = re.sub(r'[^\x00-\x7F가-힣{}:,"\[\]]+', '', cleaned_text)

        return cleaned_text
    except Exception as e:
        print(f"텍스트 정리 중 오류 발생: {str(e)}")
        return raw_text  # 오류 발생 시 원본 반환


def analyze_comments(file_path: str) -> dict:
    """
    댓글 파일을 분석하여 JSON 데이터로 변환
    """
    try:
        comments = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    comment, likes = line.strip().rsplit("|", 1)
                    comments.append({
                        "text": comment.strip(),
                        "likes": int(likes.strip())
                    })

        # 상위 50개로 필터링 (좋아요 순서대로 정렬)
        comments = sorted(comments, key=lambda x: x["likes"], reverse=True)[:50]

        # 최적화된 프롬프트 템플릿
        prompt_template = """[INST] <<SYS>>
        **반드시 지켜야 할 규칙**: 무조건 JSON만 생성! HTML/JS 코드 금지!
        {{
            "맛집": [{{"지역":"...", "가게":"...", "메뉴":"..."}}, ...],
            "명소": [{{"장소":"...", "특징":"..."}}, ...],
            "팁": ["..."]
        }}
        <</SYS>>
        {comments}
        [/INST]"""

        results = []
        
        # 배치 처리 (2개씩)
        for i in range(0, len(comments), 2):
            batch = comments[i:i+2]
            clean_comments = "\n".join([c['text'] for c in batch])
            formatted_prompt = prompt_template.format(comments=clean_comments)

            output = analyzer(
                formatted_prompt,
                max_new_tokens=512,
                temperature=0.7,  # 무작위성 조정
                top_k=50,         # 후보 제한
                top_p=0.9,        # 확률 기반 샘플링
                repetition_penalty=1.5,  # 반복 억제
                pad_token_id=tokenizer.eos_token_id,
                return_full_text=False
            )

            print(f'output \n {output}')
            raw_text = output[0]['generated_text']
            
            # raw_text 정리
            cleaned_raw_text = clean_raw_text(raw_text)

            # JSON 추출 및 필터링
            result = extract_json(cleaned_raw_text)

            if result:
                results.append(result)
            else:
                print("유효하지 않은 결과를 건너뜁니다.")

        return merge_results(results)

    except Exception as e:
        print(f"치명적 오류: {str(e)}")
        return {"error": str(e)}

def extract_json(raw_text):
    """
    모델 출력에서 JSON 데이터만 추출
    """
    try:
        # JSON 구조를 추출하는 정규식 (중첩된 중괄호 지원)
        json_pattern = r'\{(?:[^{}]|(?R))*\}'
        json_match = regex.search(json_pattern, raw_text, regex.DOTALL | regex.VERSION1)

        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)  # JSON 파싱

        else:
            print("JSON 패턴을 찾을 수 없습니다.")
            return None

    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return None


def merge_results(results: list) -> dict:
    """
    부분 결과 통합 함수
    """
    merged = {"맛집": [], "명소": [], "팁": []}
    for res in results:
        for key in merged.keys():
            if key in res and res[key]:
                merged[key].extend(res[key])
    return merged

# 실행 예시 (메모리 정리 추가)
with torch.no_grad():
    result = analyze_comments("2025318_us85YTsz5hw")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    torch.cuda.empty_cache()
