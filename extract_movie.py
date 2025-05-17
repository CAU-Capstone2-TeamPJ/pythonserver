import re
import time
import pytesseract
import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import urllib.parse

# ✅ Tesseract 경로 설정
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

# ✅ NER 모델 로딩
model_name = "Leo97/KoELECTRA-small-v3-modu-ner"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)
ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")


# ✅ 스크롤 내리는 함수
def scroll_to_bottom(driver, pause_time=1.0):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # 스크롤 아래로
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)

        # 스크롤 후 높이 확인
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # 더 이상 안 내려감
        last_height = new_height
        
# ✅ 블로그 URL 크롤링 함수
def get_blog_urls_with_selenium(movie_title, max_results=50):
    query = f"{movie_title} 촬영지"
    encoded_query = urllib.parse.quote(query)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # ✅ 로컬용 크롬 드라이버 경로 설정
    chrome_driver_path = "C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe"
    service = Service(executable_path=chrome_driver_path)

    driver = webdriver.Chrome(service=service, options=options)
    
    blog_links = []
    start = 1
    while len(blog_links) < max_results:
        url = f"https://search.naver.com/search.naver?where=view&query={encoded_query}&start={start}"
        print(f"[INFO] 검색 페이지: {url}")
        driver.get(url)
        time.sleep(3)

        scroll_to_bottom(driver, pause_time=1.5)
        
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

# ✅ 정제 함수 (본문용)
def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\u200b", "", text)
    text = re.sub(r"\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b", "", text)
    text = re.sub(
        r"[\U0001F600-\U0001F64F"  # emoticons
        r"\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF"
        r"\u2600-\u26FF"
        r"\u2700-\u27BF]+", "", text, flags=re.UNICODE)
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

# ✅ 이미지 URL 추출 함수

def extract_image_urls(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    img_tags = soup.find_all("img")
    valid_images = []
    for img in img_tags:
        src = img.get("src")
        if not src:
            continue
        if any(domain in src for domain in ["adimg", "doubleclick", "googlesyndication", "adsystem"]):
            continue
        if "base64" in src or src.endswith(".gif"):
            continue
        valid_images.append(src)
    return valid_images

# ✅ 본문 추출 함수들

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
    return clean_text(text), extract_image_urls(driver)

def extract_general_body(driver, url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    selectors = [
        "div.article-body", "div.articleView", "div#article-view-content-div",
        "div.entry-content", "div#content", "article", "body"
    ]
    for sel in selectors:
        content = soup.select_one(sel)
        if content and content.get_text(strip=True):
            return clean_text(content.get_text(strip=True)), extract_image_urls(driver)
    return "[본문 없음]", []

def extract_body_text(driver, url):
    if "blog.naver.com" in url:
        return extract_naver_blog_body(driver, url)
    else:
        return extract_general_body(driver, url)

# ✅ OCR 텍스트 추출
def extract_text_from_images(image_urls):
    texts = []
    for url in image_urls:
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            if img.width < 100 or img.height < 100:
                continue
            text = pytesseract.image_to_string(img, lang="kor")
            if text.strip():
                texts.append(text.strip())
        except:
            continue
    return "\n".join(texts)

# ✅ 텍스트 통합 및 전처리
def preprocess_text(main_text, ocr_text):
    text = main_text + "\n" + ocr_text
    return re.sub(r"\s+", " ", text).strip()



# ✅ 메인 실행 파이프라인
def extract_all_info_from_movie(movie_title, max_results=50):
    results = []
    urls = get_blog_urls_with_selenium(movie_title, max_results=max_results)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service("C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    for url in urls:
        try:
            print(f"[🔗] {url}")
            body, images = extract_body_text(driver, url)
            ocr_text = extract_text_from_images(images)
            full_text = preprocess_text(body, ocr_text)

            results.append({
                "url": url,
                "본문": full_text
            })
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            continue

    driver.quit()
    return results

# ✅ 단독 실행
if __name__ == "__main__":
    movie_title = input("🎬 영화 제목 입력: ")
    infos = extract_all_info_from_movie(movie_title)

    print("\n📌 최종 추출 결과:")
    for i, info in enumerate(infos, 1):
        print(f"\n[{i}] 🔗 {info['url']}")
        print(f"   📖 본문: {info['본문']}")
