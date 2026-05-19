import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PRODUCTS_FILE = Path("scraping/scraped_products.json")
FAILED_FILE = Path("scraping/failed_options.json")


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_json_list(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_html(url, max_retries=3):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Deneme: {attempt}/{max_retries}")

            response = requests.get(url, timeout=60)

            print("Status:", response.status_code)

            if response.status_code != 200:
                last_error = f"HTTP hata kodu: {response.status_code}"
                time.sleep(2)
                continue

            response.encoding = "iso-8859-9"
            return response.text

        except Exception as e:
            last_error = str(e)
            print("Çekme hatası:", last_error)
            time.sleep(3)

    raise Exception(last_error)


def parse_options(html):
    soup = BeautifulSoup(html, "html.parser")

    option_title = ""
    option_values = []

    title_tag = soup.find(id="MainContent_Lbl_Secenek_turu")

    if title_tag:
        option_title = clean_text(title_tag.get_text(" "))

    select = soup.find(id="MainContent_DrpSecenek")

    if select:
        for option in select.find_all("option"):
            text = clean_text(option.get_text(" "))

            if not text:
                continue

            # "Seçiniz" gibi boş yönlendirme değerleri gelirse alma
            if "seç" in text.lower() and len(text) < 15:
                continue

            if text not in option_values:
                option_values.append(text)

    return {
        "has_options": bool(option_values),
        "option_title": option_title,
        "option_values": option_values,
    }


products = load_json_list(PRODUCTS_FILE)
failed_options = load_json_list(FAILED_FILE)

print("Toplam ürün:", len(products))
print("=" * 80)

option_count = 0

for index, product in enumerate(products, start=1):
    source_product_id = product.get("source_product_id", "")
    source_url = product.get("source_url", "")

    # Daha önce eklenmişse geç
    if "has_options" in product and "option_values" in product:
        if product.get("has_options"):
            option_count += 1

        print(f"{index}/{len(products)} zaten kontrol edilmiş, geçiliyor: {source_product_id}")
        continue

    print("\n" + "=" * 80)
    print(f"{index}/{len(products)} seçenek kontrol ediliyor")
    print("ID:", source_product_id)
    print("Ürün:", product.get("name", ""))
    print("URL:", source_url)

    try:
        html = fetch_html(source_url)
        option_data = parse_options(html)

        product["has_options"] = option_data["has_options"]
        product["option_title"] = option_data["option_title"]
        product["option_values"] = option_data["option_values"]

        if product["has_options"]:
            option_count += 1
            print("SEÇENEK VAR:", product["option_title"], product["option_values"])
        else:
            print("Seçenek yok")

        # Başarılıysa failed listesinden çıkar
        failed_options = [
            item for item in failed_options
            if item.get("source_product_id") != source_product_id
        ]

        save_json(PRODUCTS_FILE, products)
        save_json(FAILED_FILE, failed_options)

    except Exception as e:
        error_message = str(e)
        print("HATA:", error_message)

        already_failed = any(
            item.get("source_product_id") == source_product_id
            for item in failed_options
        )

        if not already_failed:
            failed_options.append({
                "source_product_id": source_product_id,
                "name": product.get("name", ""),
                "source_url": source_url,
                "error": error_message,
            })

        save_json(PRODUCTS_FILE, products)
        save_json(FAILED_FILE, failed_options)

    time.sleep(0.2)


print("\nBitti.")
print("Seçenekli ürün sayısı:", option_count)
print("Hatalı seçenek kontrolü:", len(failed_options))
print("Güncellenen dosya:", PRODUCTS_FILE)
print("Hatalı dosya:", FAILED_FILE)