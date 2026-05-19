import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")
django.setup()

from shop.models import Product, ProductImage

BASE_DIR = "site_kopya"


def clean_image_path(path):
    path = path.replace("\\", "/")
    return path.split("?")[0]


def find_html_files():
    html_files = []

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    return html_files


def main():

    html_files = find_html_files()

    print("Bulunan html dosyası:", len(html_files))

    total_images = 0

    for i, file_path in enumerate(html_files, 1):

        print(f"İşleniyor: {i} / {len(html_files)}")

        try:

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()

            name_match = re.search(
                r'id="MainContent_DtlMalzemeDok_urun_adi_\d+"[^>]*>(.*?)</span>',
                html,
                re.DOTALL
            )

            if not name_match:
                continue

            name = re.sub(r"<.*?>", "", name_match.group(1)).strip()

            try:
                product = Product.objects.get(name=name)
            except Product.DoesNotExist:
                continue

            img_matches = re.findall(
                r'<img[^>]+src="([^"]+)"',
                html,
                re.IGNORECASE
            )

            for img in img_matches:

                image = clean_image_path(img)

                ProductImage.objects.get_or_create(
                    product=product,
                    image=image
                )

                total_images += 1

        except:
            pass

    print("----- BİTTİ -----")
    print("Toplam resim:", total_images)


if __name__ == "__main__":
    main()