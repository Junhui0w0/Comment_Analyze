from pathlib import Path
import datetime

dt = datetime.datetime.now()
current_date = f'{dt.year}{dt.month}{dt.day}_'
folder_path = Path.cwd() / "Comment_Extract"


def output_by_txt(file_name, file_contents, file_title): #파일명 / 파일 내용
    try:
        # 폴더 생성 (없을 경우)
        folder_path.mkdir(parents=True, exist_ok=True)

        # 파일 경로 지정
        file_name = current_date + file_name
        file_path = folder_path / file_name

        # 파일 생성 및 내용 작성
        with open(file_path, "a", encoding="utf-8") as file:  # 'a' 모드 사용
            file.write('='*150)
            file.write('\n')
            file.write(f"영상 제목: {file_title} \n")
            file.write('='*150)
            file.write('\n\n')

            for item in file_contents:
                txt = str(item).replace('\n', ' ') + '\n'
                file.write(txt)  # 줄바꿈 추가

        return True
    
    except Exception as e:
        print("[디버깅] out_by_txt 에러: ", e)
        return False


def extract_from_txt(file_name):
    all_items = list(folder_path.glob("*"))
    
    for i in all_items: # 디렉터리 내에 있는 아이템(파일)
        print(str(i).split('\Comment_Extract\\')[1])

        if file_name in str(i).split('\Comment_Extract\\')[1]:
            print(f'[디버깅] extract_from_txt: {file_name} 추출 성공')
            return True
        
    return False