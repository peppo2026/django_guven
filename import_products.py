import os
import re
import django

# Django ayarı
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")
django.setup()

from shop.models import Product

BASE_DIR = "site_kopya"


def clean_text(text):
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.replace("&nbsp;", " ").strip()


def clean_image_path(path):
    path = path.replace("\\", "/")
    return path.split("?")[0]


def find_html_files():
    html_files = []

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".html"):
                full_path = os.path.join(root, file)
                html_files.append(full_path)

    return html_files


def extract_products(html):

    name_pattern = re.compile(
        r'id="MainContent_DtlMalzemeDok_urun_adi_(\d+)"[^>]*>(.*?)</span>',
        re.DOTALL
    )

    products = []

    for match in name_pattern.finditer(html):

        index = match.group(1)
        name = clean_text(match.group(2))

        price_match = re.search(
            rf'id="MainContent_DtlMalzemeDok_labellistefi_{index}"[^>]*>(.*?)</span>',
            html,
            re.DOTALL
        )

        if not price_match:
            continue

        price = clean_text(price_match.group(1))
        price = price.replace(",", ".")

        img_match = re.search(
            rf'id="MainContent_DtlMalzemeDok_Image1_{index}"[^>]*src="([^"]+)"',
            html,
            re.DOTALL
        )

        image = "dizayn/slayt1.png"

        if img_match:
            image = clean_image_path(img_match.group(1))

        products.append((name, price, image))

    return products


def main():

    html_files = find_html_files()

    print("Bulunan html dosyası:", len(html_files))

    created = 0
    updated = 0
    total = 0

    for i, file_path in enumerate(html_files, 1):

        print(f"İşleniyor: {i} / {len(html_files)}")

        try:

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()

            products = extract_products(html)

            for name, price, image in products:

                obj, is_created = Product.objects.update_or_create(
                    name=name,
                    defaults={
                        "price": price,
                        "image": image,
                        "stock": 0,
                    }
                )

                total += 1

                if is_created:
                    created += 1
                else:
                    updated += 1

        except Exception as e:
            print("Hata:", e)

    print("----- BİTTİ -----")
    print("Toplam bulunan ürün:", total)
    print("Yeni eklenen:", created)
    print("Güncellenen:", updated)


if __name__ == "__main__":
    main()