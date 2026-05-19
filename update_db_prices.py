import os
import json
from decimal import Decimal, InvalidOperation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")

import django
django.setup()

from shop.models import Product


PRODUCTS_JSON = "scraping/scraped_products.json"


def parse_price(value):
    if value is None:
        return Decimal("0.00")

    text = str(value).strip()
    text = text.replace("TL", "").replace("₺", "").strip()

    if not text:
        return Decimal("0.00")

    # 1.250,50 → 1250.50
    if "." in text and "," in text:
        text = text.replace(".", "")
        text = text.replace(",", ".")

    # 1,250 veya 1250,50
    elif "," in text:
        parts = text.split(",")

        if len(parts[-1]) == 3:
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")

    # 1.250
    elif "." in text:
        parts = text.split(".")

        if len(parts[-1]) == 3:
            text = text.replace(".", "")

    try:
        return Decimal(text)
    except InvalidOperation:
        print("Fiyat çevrilemedi:", value)
        return Decimal("0.00")


with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
    products_data = json.load(f)


updated_count = 0
not_found_count = 0
same_count = 0


for item in products_data:
    source_product_id = str(item.get("source_product_id", "")).strip()
    new_price = parse_price(item.get("price", "0"))

    if not source_product_id:
        continue

    product = Product.objects.filter(source_product_id=source_product_id).first()

    if not product:
        not_found_count += 1
        print("DB'de bulunamadı:", source_product_id, item.get("name", ""))
        continue

    if product.price == new_price:
        same_count += 1
        continue

    old_price = product.price
    product.price = new_price
    product.save(update_fields=["price"])

    updated_count += 1
    print(f"Güncellendi ID {source_product_id}: {old_price} => {new_price}")


print("\nBitti.")
print("Güncellenen fiyat:", updated_count)
print("Zaten aynı olan:", same_count)
print("DB'de bulunamayan:", not_found_count)