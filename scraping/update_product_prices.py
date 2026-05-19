import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PRODUCTS_FILE = Path("scraping/scraped_products.json")
FAILED_FILE = Path("scraping/failed_prices.json")


PRICE_ID = "MainContent_lbl_liste_fiyati_noktali_gost_icin"


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


def parse_price_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    price_tag = soup.find(id=PRICE_ID)

    if not price_tag:
        return ""

    return clean_text(price_tag.get_text(" "))


products = load_json_list(PRODUCTS_FILE)
failed_prices = load_json_list(FAILED_FILE)

print("Toplam ürün:", len(products))
print("=" * 80)

updated_count = 0

for index, product in enumerate(products, start=1):
    source_product_id = product.get("source_product_id", "")
    source_url = product.get("source_url", "")

    print("\n" + "=" * 80)
    print(f"{index}/{len(products)} fiyat kontrol ediliyor")
    print("ID:", source_product_id)
    print("Eski fiyat:", product.get("price"))
    print("URL:", source_url)

    try:
        html = fetch_html(source_url)
        new_price = parse_price_from_html(html)

        if not new_price:
            raise Exception("Fiyat ID bulundu ama fiyat boş geldi veya ID yok")

        old_price = product.get("price", "")

        product["price"] = new_price

        if old_price != new_price:
            updated_count += 1
            print("Fiyat güncellendi:", old_price, "=>", new_price)
        else:
            print("Fiyat aynı:", new_price)

        failed_prices = [
            item for item in failed_prices
            if item.get("source_product_id") != source_product_id
        ]

        save_json(PRODUCTS_FILE, products)
        save_json(FAILED_FILE, failed_prices)

    except Exception as e:
        error_message = str(e)
        print("HATA:", error_message)

        already_failed = any(
            item.get("source_product_id") == source_product_id
            for item in failed_prices
        )

        if not already_failed:
            failed_prices.append({
                "source_product_id": source_product_id,
                "name": product.get("name", ""),
                "source_url": source_url,
                "error": error_message,
            })

        save_json(PRODUCTS_FILE, products)
        save_json(FAILED_FILE, failed_prices)

    time.sleep(0.4)


print("\nBitti.")
print("Güncellenen fiyat sayısı:", updated_count)
print("Hatalı fiyat sayısı:", len(failed_prices))
print("Güncellenen dosya:", PRODUCTS_FILE)
print("Hatalı dosya:", FAILED_FILE)