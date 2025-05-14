from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from analyze_with_gpt import run_pipeline
from extract_movie import extract_all_info_from_movie

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

class FilmingLocationResponseDto(BaseModel):
    movieId: int
    locations: List[LocationInfo]

@app.post("/movies", response_model=FilmingLocationResponseDto)
def get_filming_locations(request: MovieInfoRequestDto):
    all_blogs = extract_all_info_from_movie(request.title, max_results=30)
    locations = run_pipeline(all_blogs, request.title, save_to_file=False)
    return FilmingLocationResponseDto(movieId=request.id, locations=locations)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}
