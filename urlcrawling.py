from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import urllib.parse

def get_blog_urls_with_selenium(movie_title, max_results=50):
    query = f"{movie_title} 영화 명소"
    encoded_query = urllib.parse.quote(query)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    chrome_driver_path = "C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe"  # 너 드라이버 경로
    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    blog_links = []
    start = 1
    while len(blog_links) < max_results:
        url = f"https://search.naver.com/search.naver?where=view&query={encoded_query}&start={start}"
        print(f"[INFO] 검색 페이지: {url}")
        driver.get(url)
        time.sleep(3)

        elements = driver.find_elements(By.CSS_SELECTOR, "a.link_tit")
        if not elements:
            print("[WARN] 결과 없음, 종료")
            break

        before = len(blog_links)

        for e in elements:
            href = e.get_attribute("href")
            if href and href not in blog_links:
                blog_links.append(href)
            if len(blog_links) >= max_results:
                break

        after = len(blog_links)
        if after == before:
            print("[STOP] 새로운 링크 없음 → 종료")
            break

        start += 10

    driver.quit()
    return blog_links

# 테스트 실행
if __name__ == "__main__":
    movie_title = "기생충"
    urls = get_blog_urls_with_selenium(movie_title, max_results=50)

    print(f"\n🔗 수집된 블로그 URL 목록 ({movie_title} 관련):")
    for i, url in enumerate(urls, 1):
        print(f"{i:02d}: {url}")
