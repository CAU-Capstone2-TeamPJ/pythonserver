from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

from urlcrawling import get_blog_urls_with_selenium  # 절대 삭제 금지

# 📌 본문 정제 함수
def clean_text(text):
    # 기본 공백, 제로폭 문자 정리
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\u200b", "", text)

    # 전화번호 제거 (010-1234-5678, 02-123-4567 등)
    text = re.sub(r"\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b", "", text)

    # 이모티콘 제거 (기본적인 유니코드 이모지 범위)
    text = re.sub(
        r"[\U0001F600-\U0001F64F"  # emoticons
        r"\U0001F300-\U0001F5FF"  # symbols & pictographs
        r"\U0001F680-\U0001F6FF"  # transport & map symbols
        r"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        r"\u2600-\u26FF"          # misc symbols
        r"\u2700-\u27BF"          # dingbats
        r"]+", "", text, flags=re.UNICODE)

    # 기타 쓸데없는 문장들 제거
    patterns_to_remove = [
        r"이\s?글은\s?.{0,20}제공받았습니다",
        r"내\s?돈\s?내\s?산",
        r"블로그에서\s?더\s?보기",
        r"인스타그램\s?@[\w]+",
        r"좋아요\s?[~!꾹♥❤❣️]*",
        r"링크[:：]?\s?https?://[^\s]+",
        r"클릭해서\s?확인하세요",
        r"더\s?많은\s?사진은\s?블로그에서",
        r"광고\s?포함",
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()
# 📌 이미지 URL 필터링 함수 (광고 제거용)
def extract_image_urls(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    img_tags = soup.find_all("img")

    valid_images = []
    for img in img_tags:
        src = img.get("src")
        if not src:
            continue
        # 광고 이미지 제외 규칙
        if any(domain in src for domain in ["adimg", "doubleclick", "googlesyndication", "adsystem"]):
            continue
        if not src.startswith("http"):
            continue
        valid_images.append(src)
    return valid_images

# 📌 네이버 블로그 본문 추출
def extract_naver_blog_body(driver, url):
    driver.get(url)
    time.sleep(2)
    try:
        driver.switch_to.frame("mainFrame")
        time.sleep(1)
    except:
        return "[ERROR] iframe 접근 실패", []

    soup = BeautifulSoup(driver.page_source, "html.parser")
    content = soup.select_one("div.se-main-container") or soup.select_one("#postViewArea")
    text = content.get_text(strip=True) if content else "[본문 없음]"
    cleaned = clean_text(text)
    images = extract_image_urls(driver)
    return cleaned, images

# 📌 일반 사이트 본문 추출
def extract_general_body(driver, url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    selectors = [
        "div.article-body",
        "div.articleView",
        "div#article-view-content-div",
        "div.entry-content",
        "div#content",
        "article",
        "body"
    ]
    for sel in selectors:
        content = soup.select_one(sel)
        if content and content.get_text(strip=True):
            cleaned = clean_text(content.get_text(strip=True))
            images = extract_image_urls(driver)
            return cleaned, images
    return "[본문 없음]", []

# 📌 본문 추출 진입점
def extract_body_text(driver, url):
    if "blog.naver.com" in url:
        return extract_naver_blog_body(driver, url)
    else:
        return extract_general_body(driver, url)

# 📌 외부에서 호출용 (본문 + 이미지 URL)
def extract_text_and_images_from_url(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service("C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        text, images = extract_body_text(driver, url)
    finally:
        driver.quit()

    return text, images

# ✅ 직접 실행 테스트
if __name__ == "__main__":
    movie_title = "기생충"
    urls = get_blog_urls_with_selenium(movie_title, max_results=10)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service("C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    for i, url in enumerate(urls, 1):
        print(f"\n[{i:02d}] 🔗 {url}")
        try:
            text, images = extract_body_text(driver, url)
            print(f"본문: {text[:200]}...")
            print(f"이미지 {len(images)}개:")
            for img_url in images:
                print(f"  - {img_url}")
        except Exception as e:
            print(f"[ERROR] {e}")

    driver.quit()
