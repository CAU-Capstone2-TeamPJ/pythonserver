import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import re
from typing import List, Dict
import requests

# 환경변수 로딩
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
ngrok_base = os.getenv("NGROK_URL")
if not ngrok_base:
    raise RuntimeError("NGROK_URL 환경변수가 설정되지 않았습니다.")
ngrok_url = ngrok_base.rstrip("/") + "/crawl"


def get_blogs_from_local_crawler(movie_title: str, max_results: int = 50) -> list[dict]:
    """
    로컬 크롤링 서버(ngrok 통해 열림)에 요청하여 영화 블로그 본문들을 받아옴
    """

    payload = {
        "title": movie_title,
        "max_results": max_results
    }

    try:
        response = requests.post(ngrok_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] 크롤링 서버 요청 실패: {e}")
        return []

# 초기 프롬프트 불러오기
with open("초기_프롬프트.txt", "r", encoding="utf-8") as f:
    initial_prompt = f.read()

# 누적 장소정보 초기화
accumulated_result = ""

# 📌 OpenAI 기반 필터링 + JSON 변환
def clean_json_text(raw: str) -> str:
    """
    코드 블럭(```json ... ```) 제거
    """
    return re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.MULTILINE)

def filter_result_table_to_json(table_text: str) -> list:
    """
    OpenAI에게 마크다운 표를 전달하여:
    - 주소가 불분명하고 언급 블로그 수가 1회인 항목 제거
    - 위도/경도 칼럼을 빈 문자열로 추가
    - 결과를 JSON 리스트로 출력
    """

    prompt = f"""
다음은 마크다운 테이블 형식의 장소 정보입니다. 아래 조건을 만족하도록 작업해주세요:

1. 주소가 불분명한 항목은 제거합니다.
   - '주소가 불분명하다'의 기준은 다음과 같습니다:
     주소 문자열에 '로' 또는 '길'이라는 단어가 포함되지 않거나 숫자가 없는 경우입니다.
     예: '서울 성북구' → 불분명 / '서울 마포구 손기정로 32' → 명확함
2. 남은 항목들은 모두 위도(latitude), 경도(longitude) 필드를 추가하되, 현재는 빈 문자열("")로 설정합니다.
3. 결과는 JSON 리스트 형식으로 출력해주세요.
   - 반드시 JSON 포맷만 출력하고, 코드 블럭(```json) 없이 출력해주세요.

표:
{table_text}
"""

    messages = [
        {"role": "system", "content": "당신은 마크다운 테이블을 구조화된 JSON 데이터로 정확히 정제하는 전문가입니다."},
        {"role": "user", "content": prompt.strip()}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )

    raw_response = response.choices[0].message.content.strip()
    clean_text = clean_json_text(raw_response)

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print("❌ JSON 파싱 실패. 다음 내용을 확인하세요:\n", clean_text)
        return []

def compute_mention_rate(json_list: List[Dict], total_urls: int) -> List[Dict]:
    """
    mentionRate 필드를 추가
    """
    for item in json_list:
        count = int(item.get("언급 블로그 수", 1))
        item["mentionRate"] = round(count / total_urls, 4) if total_urls > 0 else 0.0
    return json_list

def process_single_blog(blog_text: str, accumulated_text: str, movie_title: str):
    messages = [
        {"role": "system", "content": f"너는 블로그 본문에서 {movie_title} 영화 촬영 장소 정보를 정리하고 유지하는 전문가야." + initial_prompt},
        {"role": "user", "content": f"""지금까지 정리된 결과는 다음과 같습니다:\n\n{accumulated_text}\n\n다음은 새로운 블로그 본문입니다:\n\n{blog_text}\n\n이 본문을 반영해서 결과를 **업데이트**하거나 **추가**해 주세요."""}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

def run_pipeline(all_blogs, movie_title, save_to_file=False):
    global accumulated_result
    accumulated_result = ""  # 중요: API 요청마다 초기화

    for i, blog_entry in enumerate(all_blogs, 1):
        updated_result = process_single_blog(blog_entry["본문"], accumulated_result, movie_title)
        accumulated_result = updated_result

    filtered_json = filter_result_table_to_json(accumulated_result)
    final_json = compute_mention_rate(filtered_json, total_urls=len(all_blogs))

    if save_to_file:
        output_path = f"{movie_title}_result.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered_json, f, ensure_ascii=False, indent=2)

    return filtered_json

# 테스트 실행 예시
if __name__ == "__main__":
    movie_title = input("🎬 영화 제목 입력: ")
    all_blogs = get_blogs_from_local_crawler(movie_title, max_results=50)
    final_output = run_pipeline(all_blogs, movie_title)
