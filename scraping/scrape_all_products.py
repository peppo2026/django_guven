import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


LINKS_FILE = Path("scraping/product_links.json")
OUTPUT_FILE = Path("scraping/scraped_products.json")
FAILED_FILE = Path("scraping/failed_products.json")


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

    path = path.strip()
    path = path.replace("\\", "/")

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
    has_image_extension = any(path_lower.endswith(ext) for ext in image_extensions)

    if not has_image_extension:
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

    if "_files" in path_lower:
        return True

    return False


def parse_product_detail(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    lines = normalize_lines(soup)
    page_text = clean_text(soup.get_text(" "))

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
    }

    # Ürün adı
    name_tag = soup.find(id="MainContent_LblUrunadi0")

    if name_tag:
        data["name"] = clean_text(name_tag.get_text(" "))
    else:
        title = soup.find("title")
        if title:
            data["name"] = clean_text(title.get_text())

    # Fiyat
    price_match = re.search(r"([0-9\.\,]+)\s*TL", page_text)
    if price_match:
        data["price"] = price_match.group(1)

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

    # Uyumlu araç listesi
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
                compatible_cars.append({
                    "brand": brand,
                    "model": model,
                    "years": years,
                })

    unique_compatible_cars = []
    seen_cars = set()

    for car in compatible_cars:
        key = (car["brand"], car["model"], car["years"])

        if key not in seen_cars:
            seen_cars.add(key)
            unique_compatible_cars.append(car)

    data["compatible_cars"] = unique_compatible_cars

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

    if images:
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


def load_json_list(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"UYARI: {path} bozuk veya boş. Boş liste kullanılacak.")
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


with open(LINKS_FILE, "r", encoding="utf-8") as f:
    product_links = json.load(f)


scraped_products = load_json_list(OUTPUT_FILE)
failed_products = load_json_list(FAILED_FILE)

scraped_ids = {
    item.get("source_product_id")
    for item in scraped_products
    if item.get("source_product_id")
}

print("Toplam ürün linki:", len(product_links))
print("Daha önce çekilmiş ürün:", len(scraped_ids))
print("Daha önce hatalı ürün:", len(failed_products))
print("=" * 80)


for index, item in enumerate(product_links, start=1):
    source_product_id = item.get("source_product_id", "")

    if source_product_id in scraped_ids:
        print(f"{index}/{len(product_links)} zaten çekilmiş, geçiliyor: {source_product_id}")
        continue

    print("\n" + "=" * 80)
    print(f"{index}/{len(product_links)} ürün çekiliyor")
    print("ID:", source_product_id)
    print(item.get("name_from_list", ""))
    print(item.get("url", ""))

    try:
        html = fetch_html(item["url"])
        product_data = parse_product_detail(html, item["url"])

        scraped_products.append(product_data)
        scraped_ids.add(source_product_id)

        # Başarılı olan ürün varsa failed listesinden çıkar
        failed_products = [
            failed for failed in failed_products
            if failed.get("source_product_id") != source_product_id
        ]

        save_json(OUTPUT_FILE, scraped_products)
        save_json(FAILED_FILE, failed_products)

        print("Ürün adı:", product_data["name"])
        print("Fiyat:", product_data["price"])
        print("Stok kodu:", product_data["stock_code"])
        print("Ürün kodu:", product_data["product_code"])
        print("Marka:", product_data["brand"])
        print("Açıklama var mı:", "Evet" if product_data["description"] else "Hayır")
        print("Resim sayısı:", len(product_data["gallery_images"]))
        print("Uyumlu araç sayısı:", len(product_data["compatible_cars"]))
        print("Başarılı toplam:", len(scraped_products))
        print("Hatalı toplam:", len(failed_products))

    except Exception as e:
        error_message = str(e)
        print("HATA:", error_message)

        already_failed = any(
            failed.get("source_product_id") == source_product_id
            for failed in failed_products
        )

        if not already_failed:
            failed_products.append({
                "source_product_id": source_product_id,
                "name_from_list": item.get("name_from_list", ""),
                "url": item.get("url", ""),
                "error": error_message,
            })

        save_json(OUTPUT_FILE, scraped_products)
        save_json(FAILED_FILE, failed_products)

        print("Hatalı ürün kaydedildi.")
        print("Başarılı toplam:", len(scraped_products))
        print("Hatalı toplam:", len(failed_products))

    time.sleep(1)


print("\nBitti.")
print("Başarılı ürün dosyası:", OUTPUT_FILE)
print("Hatalı ürün dosyası:", FAILED_FILE)
print("Toplam başarılı ürün:", len(scraped_products))
print("Toplam hatalı ürün:", len(failed_products))
