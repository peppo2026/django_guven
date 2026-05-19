import json
from pathlib import Path


MAIN_FILE = Path("scraping/scraped_products.json")
MISSING_FILE = Path("scraping/missing_scraped_products.json")


with open(MAIN_FILE, "r", encoding="utf-8") as f:
    main_products = json.load(f)

with open(MISSING_FILE, "r", encoding="utf-8") as f:
    missing_products = json.load(f)


existing_ids = {
    str(product.get("source_product_id", "")).strip()
    for product in main_products
    if product.get("source_product_id")
}

added_count = 0
skipped_count = 0

for product in missing_products:
    source_product_id = str(product.get("source_product_id", "")).strip()

    if not source_product_id:
        skipped_count += 1
        continue

    if source_product_id in existing_ids:
        skipped_count += 1
        continue

    main_products.append(product)
    existing_ids.add(source_product_id)
    added_count += 1


with open(MAIN_FILE, "w", encoding="utf-8") as f:
    json.dump(main_products, f, ensure_ascii=False, indent=2)


print("Bitti.")
print("Eklenen ürün:", added_count)
print("Atlanan ürün:", skipped_count)
print("Toplam ürün:", len(main_products))
print("Güncellenen dosya:", MAIN_FILE)