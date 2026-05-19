import os
import django
from bs4 import BeautifulSoup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")
django.setup()

from shop.models import Product

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_SITE_FOLDER = os.path.join(BASE_DIR, "site_kopya", "guvenotoyedek.com")

def norm(text):
    if not text:
        return ""
    text = text.lower()
    for a, b in {"ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u"}.items():
        text = text.replace(a, b)
    return " ".join(text.split())

products = list(Product.objects.all())
updated = 0
processed = 0

for file_name in os.listdir(OLD_SITE_FOLDER):
    if not (file_name.startswith("urun") and file_name.endswith(".html")):
        continue

    processed += 1

    if processed % 100 == 0:
        print("İşlenen:", processed, "Güncellenen:", updated)

    file_path = os.path.join(OLD_SITE_FOLDER, file_name)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        if "MainContent_DrpSecenek" not in html:
         continue

        soup = BeautifulSoup(html, "html.parser")
        
        title_tag = soup.find("title")
        if not title_tag:
            continue

        title = norm(title_tag.get_text(" ", strip=True))

        for product in products:
            pname = norm(product.name)

            if pname[:15] in title or title[:15] in pname:
                product.has_direction = True
                product.save(update_fields=["has_direction"])
                updated += 1
                print("Yön eklendi:", product.id, product.name)
                break

    except Exception as e:
        print("Hata:", file_name, e)

print("Bitti. İşlenen:", processed, "Güncellenen:", updated)