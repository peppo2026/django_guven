import json
import re
from pathlib import Path


SCRAPING_DIR = Path("scraping")
EXISTING_PRODUCTS_FILE = SCRAPING_DIR / "scraped_products.json"
OUTPUT_FILE = SCRAPING_DIR / "missing_product_links.json"

BASE_URL = "https://guvenotoyedek.com/"

FILES_TO_SCAN = [
    "sitemap.html",
    "sitemap2.html",
    "site map 1.xml",
    "site map 3.aspx",
]


def read_text_safely(path):
    encodings = ["utf-8", "windows-1254", "iso-8859-9"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding, errors="replace")
        except Exception:
            pass

    return path.read_text(errors="replace")


def extract_product_ids(text):
    """
    Büyük dosyalarda donmasın diye komple URL yakalamıyoruz.
    Sadece urun.aspx?u=1234 içindeki ürün ID'sini alıyoruz.
    """
    ids = set()

    patterns = [
        r"urun\.aspx\?u=([0-9]+)",
        r"urun\.aspx&amp;u=([0-9]+)",
        r"urun\.aspx[^0-9]+u=([0-9]+)",
    ]

    for pattern in patterns:
        for product_id in re.findall(pattern, text, flags=re.IGNORECASE):
            ids.add(product_id)

    return ids


with open(EXISTING_PRODUCTS_FILE, "r", encoding="utf-8") as f:
    existing_products = json.load(f)

existing_ids = {
    str(product.get("source_product_id", "")).strip()
    for product in existing_products
    if product.get("source_product_id")
}

print("Bizde mevcut ürün sayısı:", len(existing_ids))

all_found_ids = set()

for file_name in FILES_TO_SCAN:
    path = SCRAPING_DIR / file_name

    if not path.exists():
        print("Dosya bulunamadı, geçiliyor:", file_name)
        continue

    print("Taranıyor:", file_name)

    text = read_text_safely(path)
    ids = extract_product_ids(text)

    print("  bulunan tekil ürün ID:", len(ids))

    all_found_ids.update(ids)

missing_ids = sorted(all_found_ids - existing_ids, key=lambda x: int(x))

missing_links = []

for product_id in missing_ids:
    missing_links.append({
        "source_product_id": product_id,
        "name_from_list": "",
        "url": f"{BASE_URL}urun.aspx?u={product_id}",
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(missing_links, f, ensure_ascii=False, indent=2)

print("\nBitti.")
print("Sitemaplerden bulunan tekil ürün:", len(all_found_ids))
print("Bizde zaten olan:", len(all_found_ids & existing_ids))
print("Eksik ürün:", len(missing_links))
print("Kaydedildi:", OUTPUT_FILE)

if missing_links:
    print("\nİlk 20 eksik ürün ID:")
    for item in missing_links[:20]:
        print(item["source_product_id"], item["url"])