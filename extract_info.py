import re
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from extract_content import extract_body_text, extract_image_urls
from urlcrawling import get_blog_urls_with_selenium

# ✅ Tesseract 경로 지정
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ NER 모델 로딩
model_name = "Leo97/KoELECTRA-small-v3-modu-ner"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)
ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

# ✅ OCR 텍스트 추출
def extract_text_from_images(image_urls):
    texts = []
    for url in image_urls:
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            text = pytesseract.image_to_string(img, lang="kor")
            if text.strip():
                texts.append(text.strip())
        except Exception as e:
            continue
    return "\n".join(texts)

# ✅ 본문 + OCR 텍스트 전처리 (주소 정제 + 통합)
def preprocess_text(main_text, ocr_text):
    text = main_text + "\n" + ocr_text
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ✅ 장소/주소/장면 설명 추출
def extract_location_info(text):
    entities = ner(text)
    location_names = [e['word'] for e in entities if e['entity_group'] == 'LOC']
    address_pattern = r'(서울|부산|대전|광주|대구|인천|수원|제주|경기|강원|충북|충남|전북|전남|경북|경남)[^, \n]{2,}'
    addresses = re.findall(address_pattern, text)
    return list(set(location_names)), list(set(addresses))

# ✅ 전체 실행 파이프라인
def extract_all_info_from_movie(movie_title, max_results=30):
    results = []
    urls = get_blog_urls_with_selenium(movie_title, max_results=max_results)

    # ✅ WebDriver 준비
    options = options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service("C:/Users/keiro/moviecrawling/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    for url in urls:
        try:
            print(f"[🔗] {url}")
            # ✅ 여기 수정: driver 같이 넘겨줘야 함!
            body = extract_body_text(driver, url)
            images = extract_image_urls(driver)
            ocr_text = extract_text_from_images(images)
            full_text = preprocess_text(body, ocr_text)
            locs, addrs = extract_location_info(full_text)

            results.append({
                "url": url,
                "본문 요약": body[:80],
                "이미지 OCR": ocr_text[:80],
                "장소명": locs,
                "주소": addrs
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
        print(f"   📖 본문 요약: {info['본문 요약']}")
        print(f"   🖼️ OCR 텍스트: {info['이미지 OCR']}")
        print(f"   🗺️ 장소명: {info['장소명']}")
        print(f"   📍 주소: {info['주소']}")
