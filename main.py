# main.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

# 요청 body 스키마 정의
class MovieRequest(BaseModel):
    title: str
    director: str
    year: int

@app.post("/movie/locations")
async def get_movie_locations(request: MovieRequest):
    # 예시 결과 (실제로는 여기서 크롤링 + 분석)
    result_table = {
        "movie": {
            "title": request.title,
            "director": request.director,
            "year": request.year,
            "locations": [
                {
                    "장소명": "자하문 터널 계단",
                    "설명": "기택 가족이 폭우 속에서 집으로 내려가는 상징적인 장면",
                    "주소": "서울 종로구 자하문로 219",
                    "언급 블로그 수": 6,
                    "위도": 37.5945,
                    "경도": 126.9623,
                    "키워드": ["포토스팟", "관광", "문화"]
                }
                # 여기에 다른 장소들도 추가됨
            ]
        }
    }
    return result_table
