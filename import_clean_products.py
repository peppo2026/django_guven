import os
import json
from decimal import Decimal, InvalidOperation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")

import django
django.setup()

from django.db import transaction

from shop.models import (
    Product,
    ProductImage,
    CarBrand,
    CarModel,
    ProductCompatibility,
    CartItem,
    OrderItem,
)


PRODUCTS_JSON = "scraping/scraped_products.json"


def parse_price(value):
    """
    JSON'da fiyatlar bazen şöyle geliyor:
    1,200
    850
    2.500
    1.250,50

    Biz bunları Decimal formatına çeviriyoruz.
    """
    if value is None:
        return Decimal("0.00")

    text = str(value).strip()
    text = text.replace("TL", "").replace("₺", "").strip()

    if not text:
        return Decimal("0.00")

    # Hem nokta hem virgül varsa: 1.250,50 → 1250.50
    if "." in text and "," in text:
        text = text.replace(".", "")
        text = text.replace(",", ".")

    # Sadece virgül varsa
    elif "," in text:
        parts = text.split(",")

        # 1,200 gibi 3 haneli kısım varsa bunu binlik ayırıcı kabul ediyoruz
        if len(parts[-1]) == 3:
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")

    # Sadece nokta varsa
    elif "." in text:
        parts = text.split(".")

        # 1.200 gibi 3 haneli kısım varsa bunu binlik ayırıcı kabul ediyoruz
        if len(parts[-1]) == 3:
            text = text.replace(".", "")

    try:
        return Decimal(text)
    except InvalidOperation:
        print("Fiyat çevrilemedi:", value)
        return Decimal("0.00")


def option_values_to_text(values):
    """
    Listeyi DB'de tek metin olarak saklıyoruz:
    ["Sol", "Sağ"] → "Sol|Sağ"
    """
    if not values:
        return ""

    return "|".join(values)


def compatible_cars_to_text(cars):
    """
    Product.compatible_cars alanı için okunabilir özet metin oluşturur.
    Asıl filtreleme ProductCompatibility tablosundan yapılacak.
    """
    lines = []

    for car in cars:
        brand = car.get("brand", "")
        model = car.get("model", "")
        years = car.get("years", "")

        text = f"{brand} {model}".strip()

        if years:
            text = f"{text} {years}"

        if text:
            lines.append(text)

    return "\n".join(lines)


with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
    products_data = json.load(f)


print("JSON ürün sayısı:", len(products_data))
print("Import başlıyor...")


with transaction.atomic():
    print("Eski sepet kayıtları temizleniyor...")
    CartItem.objects.all().delete()

    print("Eski sipariş ürünleri temizleniyor...")
    OrderItem.objects.all().delete()

    print("Eski ürünler temizleniyor...")
    Product.objects.all().delete()

    print("Eski araç marka/model kayıtları temizleniyor...")
    CarModel.objects.all().delete()
    CarBrand.objects.all().delete()

    created_products = 0
    created_images = 0
    created_compatibilities = 0

    for index, item in enumerate(products_data, start=1):
        name = item.get("name", "").strip()
        price = parse_price(item.get("price", "0"))
        main_image = item.get("main_image", "").strip()

        description = item.get("description", "").strip()

        if not description:
            description = name

        option_values = item.get("option_values", [])

        product = Product.objects.create(
            name=name,
            price=price,
            image=main_image,
            stock=1,

            source_product_id=item.get("source_product_id", ""),
            source_url=item.get("source_url", ""),

            description=description,
            stock_code=item.get("stock_code", ""),
            product_code=item.get("product_code", ""),
            brand=item.get("brand", ""),
            condition=item.get("condition", ""),
            product_group=item.get("product_group", ""),

            compatible_cars=compatible_cars_to_text(item.get("compatible_cars", [])),
            comments_html="",

            has_direction=bool(item.get("has_options", False)),
            option_title=item.get("option_title", ""),
            option_values=option_values_to_text(option_values),
        )

        created_products += 1

        # Ürün görselleri
        gallery_images = item.get("gallery_images", [])

        seen_images = set()

        for image_path in gallery_images:
            image_path = image_path.strip()

            if not image_path:
                continue

            if image_path in seen_images:
                continue

            seen_images.add(image_path)

            ProductImage.objects.create(
                product=product,
                image=image_path,
            )

            created_images += 1

        # Uyumlu araçlar
        for car in item.get("compatible_cars", []):
            brand_name = car.get("brand", "").strip()
            model_name = car.get("model", "").strip()
            years = car.get("years", "").strip()

            if not brand_name or not model_name:
                continue

            brand_obj, _ = CarBrand.objects.get_or_create(name=brand_name)

            model_obj, _ = CarModel.objects.get_or_create(
                brand=brand_obj,
                name=model_name,
            )

            ProductCompatibility.objects.create(
                product=product,
                car_model=model_obj,
                years=years,
            )

            created_compatibilities += 1

        if index % 100 == 0:
            print(f"{index}/{len(products_data)} ürün işlendi...")

    print("\nImport tamamlandı.")
    print("Oluşturulan ürün:", created_products)
    print("Oluşturulan ürün resmi:", created_images)
    print("Oluşturulan uyumluluk:", created_compatibilities)
    print("Toplam marka:", CarBrand.objects.count())
    print("Toplam model:", CarModel.objects.count())