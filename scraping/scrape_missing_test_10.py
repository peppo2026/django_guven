import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


LINKS_FILE = Path("scraping/missing_product_links.json")
OUTPUT_FILE = Path("scraping/missing_scraped_test_10.json")
FAILED_FILE = Path("scraping/failed_missing_test_10.json")


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_lines(soup):
    lines = []

    for line in soup.get_text("\n").splitlines():
        line = clean_text(line)
        if line:
            lines.append(line)

    return lines


def get_value_after_label(lines, label):
    for i, line in enumerate(lines):
        if clean_text(line).lower() == label.lower():
            for next_line in lines[i + 1:i + 8]:
                if next_line == ":":
                    continue
                return clean_text(next_line)

    return ""


def normalize_image_path(path):
    if not path:
        return ""

    path = path.strip().replace("\\", "/")

    if path.startswith("./"):
        path = path[2:]

    if path.startswith("../"):
        path = path.replace("../", "")

    if path.startswith("/"):
        path = path[1:]

    return path


def is_product_image(path):
    if not path:
        return False

    path_lower = path.lower()

    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

    if not any(path_lower.endswith(ext) for ext in image_extensions):
        return False

    excluded_names = [
        "baslik.gif",
        "opel_arma.gif",
        "opel_arma_k.gif",
        "chevroletl_arma.gif",
        "chevroletl_arma_k.gif",
        "loading.gif",
        "sepet_bos.png",
        "ara.png",
        "tekyildiz_sari.png",
        "icon_madde_isareti.gif",
        "super-hizli-gonderi.gif",
        "iade190x150.png",
        "para-iade.jpg",
        "vakifbank.gif",
    ]

    for excluded in excluded_names:
        if excluded in path_lower:
            return False

    if re.search(r"foto[0-9]", path_lower):
        return True

    if "urunler" in path_lower:
        return True

    return False


def parse_product_detail(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    lines = normalize_lines(soup)

    parsed_url = urlparse(source_url)
    query = parse_qs(parsed_url.query)
    source_product_id = query.get("u", [""])[0]

    data = {
        "source_product_id": source_product_id,
        "source_url": source_url,
        "name": "",
        "price": "",
        "stock_code": "",
        "product_code": "",
        "brand": "",
        "condition": "",
        "product_group": "",
        "description": "",
        "main_image": "",
        "gallery_images": [],
        "compatible_cars": [],
        "has_options": False,
        "option_title": "",
        "option_values": [],
    }

    # Ürün adı
    name_tag = soup.find(id="MainContent_LblUrunadi0")
    if name_tag:
        data["name"] = clean_text(name_tag.get_text(" "))
    else:
        title = soup.find("title")
        if title:
            data["name"] = clean_text(title.get_text(" "))

    # Fiyat - doğru ID
    price_tag = soup.find(id="MainContent_lbl_liste_fiyati_noktali_gost_icin")
    if price_tag:
        data["price"] = clean_text(price_tag.get_text(" "))

    # Ürün detay alanları
    data["stock_code"] = get_value_after_label(lines, "Stok Kodu")
    data["product_code"] = get_value_after_label(lines, "Ürün Kodu")
    data["brand"] = get_value_after_label(lines, "Markası")
    data["condition"] = get_value_after_label(lines, "Ürün Durumu")
    data["product_group"] = get_value_after_label(lines, "Ürün Grubu")

    # Açıklama
    description_tag = soup.find(id="MainContent_Lblaciklama2")
    if description_tag:
        data["description"] = clean_text(description_tag.get_text(" "))

    # Seçenek / yön
    option_title_tag = soup.find(id="MainContent_Lbl_Secenek_turu")
    if option_title_tag:
        data["option_title"] = clean_text(option_title_tag.get_text(" ")).replace(":", "")

    select = soup.find(id="MainContent_DrpSecenek")
    option_values = []

    if select:
        for option in select.find_all("option"):
            text = clean_text(option.get_text(" "))
            if text and text not in option_values:
                option_values.append(text)

    data["option_values"] = option_values
    data["has_options"] = bool(option_values)

    # Uyumlu araçlar
    compatible_cars = []

    for table in soup.find_all("table"):
        table_text = table.get_text(" ", strip=True)

        if "BU ÜRÜNÜN TAKILABİLECEĞİ" not in table_text:
            continue

        for tr in table.find_all("tr"):
            cells = [clean_text(td.get_text(" ")) for td in tr.find_all("td")]
            cells = [c for c in cells if c]

            if len(cells) < 2:
                continue

            row_text = " ".join(cells)

            if "BU ÜRÜNÜN TAKILABİLECEĞİ" in row_text:
                continue

            brand = cells[0]
            model = cells[1] if len(cells) >= 2 else ""
            years = cells[2] if len(cells) >= 3 else ""

            if brand in ["Opel", "Chevrolet"] and model and model != ":":
                item = {
                    "brand": brand,
                    "model": model,
                    "years": years,
                }

                if item not in compatible_cars:
                    compatible_cars.append(item)

    data["compatible_cars"] = compatible_cars

    # Resimler
    images = []
    seen_image_numbers = set()

    def add_image(path):
        if not is_product_image(path):
            return

        path = normalize_image_path(path)

        match = re.search(r"foto([0-9])", path.lower())

        if match:
            photo_number = match.group(1)

            if photo_number in seen_image_numbers:
                return

            seen_image_numbers.add(photo_number)

        if path and path not in images:
            images.append(path)

    for img in soup.find_all("img", src=True):
        add_image(img.get("src"))

    for input_tag in soup.find_all("input", src=True):
        add_image(input_tag.get("src"))

    for a in soup.find_all("a", href=True):
        add_image(a.get("href"))

    data["gallery_images"] = images

    orj_images = [img for img in images if "/orj/" in img]
    if orj_images:
        data["main_image"] = orj_images[0]
    elif images:
        data["main_image"] = images[0]

    return data


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


with open(LINKS_FILE, "r", encoding="utf-8") as f:
    missing_links = json.load(f)


test_links = missing_links[:10]

results = []
failed = []

for index, item in enumerate(test_links, start=1):
    print("\n" + "=" * 80)
    print(f"{index}/10 eksik ürün çekiliyor")
    print("ID:", item["source_product_id"])
    print(item["url"])

    try:
        html = fetch_html(item["url"])
        product_data = parse_product_detail(html, item["url"])

        if not product_data["name"]:
            raise Exception("Ürün adı boş geldi")

        results.append(product_data)

        print("Ürün adı:", product_data["name"])
        print("Fiyat:", product_data["price"])
        print("Stok kodu:", product_data["stock_code"])
        print("Ürün kodu:", product_data["product_code"])
        print("Marka:", product_data["brand"])
        print("Resim sayısı:", len(product_data["gallery_images"]))
        print("Uyumlu araç sayısı:", len(product_data["compatible_cars"]))
        print("Seçenek var mı:", product_data["has_options"])

    except Exception as e:
        print("HATA:", e)

        failed.append({
            "source_product_id": item["source_product_id"],
            "url": item["url"],
            "error": str(e),
        })

    time.sleep(0.7)


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open(FAILED_FILE, "w", encoding="utf-8") as f:
    json.dump(failed, f, ensure_ascii=False, indent=2)

print("\nBitti.")
print("Başarılı:", len(results))
print("Hatalı:", len(failed))
print("Kaydedildi:", OUTPUT_FILE)
print("Hatalı dosya:", FAILED_FILE)