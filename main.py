from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from analyze_with_gpt import run_pipeline, get_blogs_from_local_crawler

app = FastAPI()

class MovieInfoRequestDto(BaseModel):
    id: int
    title: str
    director: str
    releaseDate: str

class LocationInfo(BaseModel):
    name: str
    country: str
    description: str
    nearbyKeywords: List[str]
    recommendKeywords: List[str]
    latitude: float
    longitude: float
    address: str
    mentionRate: float
    mentionCount: int
    durationTime: float

def to_list(value):
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        return [x.strip() for x in value.split(',')]
    return []

def convert_to_location_info(raw_data: List[dict]) -> List[LocationInfo]:
    result = []
    for item in raw_data:
        result.append(LocationInfo(
            name=item.get("장소명", ""),
            country="",
            description= item.get("설명", ""),
            nearbyKeywords= to_list(item.get("추가정보", [])),
            recommendKeywords= to_list(item.get("키워드", [])),
            latitude=float(item.get("latitude", 0.0)) if item.get("latitude") else 0.0,
            longitude=float(item.get("longitude", 0.0)) if item.get("longitude") else 0.0,
            address=item.get("주소", ""),
            mentionRate=float(item.get("mentionRate", 0.0)),
            mentionCount=int(item.get("언급 블로그 수", 1)),
            durationTime = float(item.get("체류시간", 0.0))
        ))
    return result

class FilmingLocationResponseDto(BaseModel):
    movieId: int
    locations: List[LocationInfo]

@app.post("/movies", response_model=FilmingLocationResponseDto)
def get_filming_locations(request: MovieInfoRequestDto):
    all_blogs = get_blogs_from_local_crawler(request.title, max_results=30)
    print(f"✅ 받은 블로그 수: {len(all_blogs)}")  # 여기 추가
    raw_locations = run_pipeline(all_blogs, request.title, save_to_file=False)
    locations = convert_to_location_info(raw_locations)
    return FilmingLocationResponseDto(movieId=request.id, locations=locations)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}
