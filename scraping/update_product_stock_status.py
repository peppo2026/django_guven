import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")

import django
django.setup()

from shop.models import Product


RESULTS_FILE = Path(__file__).resolve().parent / "stock_status_results.json"


def main():
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    updated = 0
    not_found = 0
    skipped = 0

    for item in results:
        source_product_id = str(item.get("source_product_id"))
        is_in_stock = item.get("is_in_stock")

        if is_in_stock is None:
            skipped += 1
            continue

        product = Product.objects.filter(source_product_id=source_product_id).first()

        if not product:
            not_found += 1
            print(f"BULUNAMADI: source_product_id={source_product_id}")
            continue

        product.is_in_stock = is_in_stock
        product.save(update_fields=["is_in_stock"])

        updated += 1

    print("BİTTİ")
    print(f"DB güncellenen ürün: {updated}")
    print(f"Bulunamayan ürün: {not_found}")
    print(f"Atlanan ürün: {skipped}")


if __name__ == "__main__":
    main()