from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from extract_movie import extract_all_info_from_movie  # 같은 파일에 있으면 직접 호출 가능
import uvicorn

app = FastAPI()

class CrawlRequest(BaseModel):
    title: str
    max_results: int = 30  # 기본값 설정

@app.post("/crawl")
def crawl_movie_info(request: CrawlRequest):
    print(f"[📥] 요청 수신: {request.title} ({request.max_results})")
    results = extract_all_info_from_movie(request.title, max_results=request.max_results)
    print(f"[✅] 크롤링 완료, 총 {len(results)}건")
    return results

# 로컬 실행용
if __name__ == "__main__":
    uvicorn.run("movie_content_server:app", host="0.0.0.0", port=8000, reload=True)
