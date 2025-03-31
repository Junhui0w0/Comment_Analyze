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
import regex

def extract_json_from_text(text: str) -> dict:
    """개선된 JSON 추출 함수"""
    try:
        # 1. 유니코드 복원 (깨진 문자열 처리)
        try:
            text = text.encode('latin1').decode('utf-8')
        except UnicodeDecodeError:
            print("유니코드 디코딩 실패, 원본 텍스트 사용")
        
        # 2. 싱글쿼터 -> 더블쿼터 변환
        text = text.replace("'", '"')

        # 3. 키에 따옴표가 없는 경우 수정 (정규식)
        text = regex.sub(
            r'(\s*)(\w+)(\s*:\s*)', 
            r'\1"\2"\3', 
            text
        )

        # 4. JSON 객체 추출 (중첩된 JSON 포함)
        json_pattern = r'\{(?:[^{}]|(?R))*\}'
        match = regex.search(json_pattern, text, regex.DOTALL | regex.VERSION1)
        if not match:
            print("JSON 패턴을 찾을 수 없습니다")
            return None

        json_str = match.group(0)

        # 5. JSON 파싱
        return json.loads(json_str)

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}")
        print(f"문제 문자열:\n{text[:200]}...")  # 처음 200자만 출력
        return None

    except Exception as e:
        print(f"기타 오류: {e}")
        return None
        
    # except JSONDecodeError as e:
    #     print(f"JSON 파싱 실패: {str(e)}")
    #     print(f"문제 문자열:\n{json_str[:200]}...")  # 처음 200자만 출력
    #     return None
    except Exception as e:
        print(f"기타 오류: {str(e)}")
        return None

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
    print('local 파일 사용')
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
    print(f"local에 존재X")
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
    torch_dtype=torch.float16,
    repetition_penalty=1.2  # ⇠ 반복 생성 방지
)

def analyze_comments(file_path: str) -> dict:
    """최적화된 댓글 분석 함수"""
    json_str = ""
    
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

    prompt_template = """[INST] <<SYS>>
    **반드시 지켜야 할 규칙**:
    1. 키와 문자열 값에 반드시 큰따옴표(") 사용
    2. JSON 형식만 출력
    3. 주석/추가 텍스트 금지
    <</SYS>>

    아래 댓글 분석:
    1. {comment1}
    2. {comment2}

    JSON 출력 예시:
    {{
        "맛집": [{{"이름": "예시가게", "이유": "맛있음"}}],
        "명소": [{{"장소": "예시장소", "특징": "아름다움"}}],
        "팁": ["예시팁"]
    }}[/INST]"""
    
    # 배치 처리 (2개씩)
    results = []
    for i in range(0, len(comments), 2): #0 ~ 99 (100회) -> 0 2 4 6 8 10 ... 98
        print(f'index = {i}')
        batch = comments[i:i+2]
        formatted_prompt = prompt_template.format(
            comment1=batch[0]['text'],
            comment2=batch[1]['text'] if len(batch) > 1 else ""
        )

        print("\n" + "="*50 + " PROMPT START " + "="*50)
        print(formatted_prompt)
        print("="*50 + " PROMPT END " + "="*50 + "\n")
        
        # 모델 실행
        output = analyzer(
            formatted_prompt,
            max_new_tokens=512,  # ⇠ 토큰 길이 증가
            temperature=0.3,     # ⇠ 창의성 감소
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id
        )

        print("\n" + "="*50 + " RAW OUTPUT START " + "="*50)
        # print(output[0]['generated_text'])
        raw_text = output[0]['generated_text']
        print(f'raw_text : {raw_text}')

        json_data = extract_json_from_text(raw_text)
        print(f'json_data : {json_data}')
        print("="*50 + " RAW OUTPUT END " + "="*50 + "\n")

        # JavaScript 키워드 제거
        # filtered_text = re.sub(
        #     r'\b(useState|React|=>|import)\b', 
        #     '[INVALID]', 
        #     raw_text
        # )
        

        if json_data:
            print("Extracted JSON Data:", json_data)

            # 맛집 정보 출력
            if "맛집" in json_data:
                for item in json_data["맛집"]:
                    print(f"맛집 이름: {item.get('이름', 'N/A')}, 이유: {item.get('이유', 'N/A')}")

            # 팁 정보 출력
            if "팁" in json_data:
                for tip in json_data["팁"]:
                    print(f"팁: {tip}")
        else:
            print("JSON 데이터가 없습니다.")






        filtered_text = str(raw_text)
        filtered_text = re.sub(
            r'[^\x00-\x7F가-힣]',  # 한글/영문/기본 ASCII만 허용
            '', 
            filtered_text
        )

        filtered_text = filtered_text.encode('utf-8', 'replace').decode('utf-8')

        # JSON 파싱
        data = json.loads(filtered_text)

        # 2D 배열 생성
        result = []

        # 맛집 처리
        for item in data["맛집"]:
            row = [
                item["이름"],
                item["이유"],
                "",  # 명소 칸 비움
                ""   # 팁 칸 비움
            ]
            result.append(row)

        # 명소 처리 
        for item in data["명소"]:
            row = [
                "",  # 맛집 칸 비움
                "",
                item["장소"],
                item["특징"]
            ]
            result.append(row)

        # 팁 처리
        for tip in data["팁"]:
            row = ["", "", "", tip]
            result.append(row)

        print(result)  




        # # 개선된 정규식 (regex 설치 필요: pip install regex)
        # json_pattern = r'(?<!: )\{(?:[^{}]|(?R))*\}'
        # json_match = regex.search(
        #     json_pattern, 
        #     filtered_text, 
        #     regex.DOTALL | regex.VERSION1
        # )
        
        # # 2. 확장된 유니코드 처리
        # if json_match:
        #     json_str = (
        #         json_match.group(1)
        #         .encode('utf-8')
        #         .decode('unicode_escape')
        #         .replace(r'\"', '"')
        #         .replace(r"\'", "'")
        #     )


        #     # JSON 처리 부분에 추가
        #     json_str = json_match.group(1)
        #     print("\n" + "="*50 + " JSON CANDIDATE START " + "="*50)
        #     print(f"Extracted JSON String:\n{json_str}")
        #     print("="*50 + " JSON CANDIDATE END " + "="*50 + "\n")

            
        #     # 3. JSON 구조 강제 정렬
        #     json_str = re.sub(r'//.*?\\n', '', json_str)  # 주석 제거
        #     json_str = json_str.replace('True', 'true').replace('False', 'false')  # 부울값 정규화
            
        
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


        result = json.loads(json_str)  # 정상 파싱


        # 결과 처리
        if result:
            results.append(result)
        else:
            print("유효하지 않은 결과 건너뜀")



    # 최종 결과 병합
    return merge_results(results)
    
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
    result = analyze_comments("2025318_us85YTsz5hw.txt")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    torch.cuda.empty_cache()
