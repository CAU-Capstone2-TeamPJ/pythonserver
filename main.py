from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import logging
import re
import time
import json
import requests
import os
from dotenv import load_dotenv

from extract_movie import extract_all_info_from_movie
from analyze_with_gpt import run_pipeline

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ✅ 환경 변수 로딩
load_dotenv()

app = FastAPI()

# ✅ 요청 DTO
class MovieInfoRequestDto(BaseModel):
    id: int
    title: str
    director: str
    releaseDate: str

# ✅ 응답용 장소 정보 구조
class LocationInfo(BaseModel):
    name: str
    country: str
    description: str
    nearbyKeywords: List[str]
    recommendKeywords: List[str]
    address: str
    mentionRate: float
    mentionCount: int
    durationTime: float

# ✅ 문자열 또는 리스트를 리스트로 통일
def to_list(value):
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        return [x.strip() for x in value.split(',')]
    return []

# ✅ dict → LocationInfo 변환
def convert_to_location_info(raw_data: List[Dict]) -> List[LocationInfo]:
    result = []
    for item in raw_data:
        result.append(LocationInfo(
            name=item.get("장소명", ""),
            country=item.get("국가", ""),
            description=item.get("설명", ""),
            nearbyKeywords=to_list(item.get("추가정보", [])),
            recommendKeywords=to_list(item.get("키워드", [])),
            address=item.get("주소", ""),
            mentionRate=float(item.get("mentionRate", 0.0)),
            mentionCount=int(item.get("언급 블로그 수", 1)),
            durationTime=float(item.get("체류시간", 0.0))
        ))
    return result

# ✅ 응답 DTO
class FilmingLocationResponseDto(BaseModel):
    movieId: int
    locations: List[LocationInfo]

# ✅ 통합형 크롤링 + GPT 처리 엔드포인트
@app.post("/movies", response_model=FilmingLocationResponseDto)
def get_filming_locations(request: MovieInfoRequestDto):
    try:
        logger.info(f"🎬 영화 제목 수신: {request.title}")

        # 1. 로컬에서 직접 블로그 크롤링
        all_blogs = extract_all_info_from_movie(request.title, max_results=30)
        logger.info(f"✅ 받은 블로그 수: {len(all_blogs)}")

        # 2. GPT로 장소 정보 추출 및 정제
        raw_locations = run_pipeline(all_blogs, request.title, save_to_file=False)
        logger.info(f"📌 GPT 파이프라인 완료 - 장소 후보 수: {len(raw_locations)}")

        # 3. 변환 및 응답
        locations = convert_to_location_info(raw_locations)
        logger.info(f"📦 응답으로 보낼 장소 수: {len(locations)}")

        return FilmingLocationResponseDto(movieId=request.id, locations=locations)

    except Exception as e:
        logger.exception("🔥 영화 장소 추출 중 예외 발생!")
        return {"error": "서버 처리 중 오류가 발생했습니다."}

# ✅ 헬스 체크용 엔드포인트
@app.get("/healthz")
def health_check():
    return {"status": "ok"}
