import os
import django
from bs4 import BeautifulSoup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")
django.setup()

from shop.models import Product

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_SITE_FOLDER = os.path.join(BASE_DIR, "site_kopya", "guvenotoyedek.com")


def normalize(text):
    if not text:
        return ""

    text = text.lower()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "i̇": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


# ÜRÜNLERİ BİR KERE HAZIRLA
product_map = {}

for product in Product.objects.all():
    key = normalize(product.name)[:20]
    if key:
        product_map[key] = product

updated = 0
skipped = 0
processed = 0

for file_name in os.listdir(OLD_SITE_FOLDER):
    if not (file_name.startswith("urun") and file_name.endswith(".html")):
        continue

    processed += 1

    if processed % 100 == 0:
        print("İşlenen dosya:", processed, "Güncellenen:", updated)

    file_path = os.path.join(OLD_SITE_FOLDER, file_name)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        if "Google yorumları" not in html:
            skipped += 1
            continue

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")

        if not title_tag:
            skipped += 1
            continue

        html_title = normalize(title_tag.get_text(" ", strip=True))

        matched_product = None

        # Hızlı eşleştirme: önce direkt 20 karakter anahtar
        for key, product in product_map.items():
            if key in html_title:
                matched_product = product
                break

        if not matched_product:
            skipped += 1
            continue

        start = html.find("Google yorumları")
        end = html.find("©", start)

        if end == -1:
            end = start + 8000

        matched_product.comments_html = html[start:end]
        matched_product.save(update_fields=["comments_html"])

        updated += 1
        print("OK:", matched_product.id)

    except Exception as e:
        skipped += 1
        print("HATA:", file_name, e)

print("Bitti. İşlenen:", processed, "Güncellenen:", updated, "Atlanan:", skipped)