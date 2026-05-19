import os
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from shop.models import Product


def normalize_text(text):
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


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def get_text_by_id(soup, element_id):
    tag = soup.find(id=element_id)
    if tag:
        return tag.get_text(" ", strip=True)
    return ""


def get_html_by_id(soup, element_id):
    tag = soup.find(id=element_id)
    if tag:
        return tag.decode_contents()
    return ""


class Command(BaseCommand):
    help = "Eski ürün HTML sayfalarından detay bilgilerini Product modeline aktarır"

    def handle(self, *args, **kwargs):
        folder_path = "site_kopya/guvenotoyedek.com"

        updated_count = 0
        skipped_count = 0

        products = list(Product.objects.all())

        for file_name in os.listdir(folder_path):
            if not (file_name.startswith("urun") and file_name.endswith(".html")):
                continue

            file_path = os.path.join(folder_path, file_name)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    html = f.read()
            except Exception as e:
                print("Dosya okunamadı:", file_name, e)
                skipped_count += 1
                continue

            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("title")
            if not title_tag:
                skipped_count += 1
                continue

            html_product_name = title_tag.get_text(" ", strip=True)
            normalized_html_name = normalize_text(html_product_name)

            best_product = None
            best_score = 0

            for product in products:
                normalized_db_name = normalize_text(product.name)

                score = similarity(normalized_html_name, normalized_db_name)

                if normalized_html_name[:15] in normalized_db_name:
                    score += 0.20

                if normalized_db_name[:15] in normalized_html_name:
                    score += 0.20

                if score > best_score:
                    best_score = score
                    best_product = product

            if not best_product or best_score < 0.55:
                print("Eşleşmedi:", html_product_name, " skor:", round(best_score, 2))
                skipped_count += 1
                continue

            description_html = get_html_by_id(soup, "MainContent_Lblaciklama1")
            stock_code = get_text_by_id(soup, "MainContent_LblStokKodu")
            product_code = get_text_by_id(soup, "MainContent_LblUrunKodu")
            brand = get_text_by_id(soup, "MainContent_LblMarka")
            condition = get_text_by_id(soup, "MainContent_LblUrunDurumu")
            group1 = get_text_by_id(soup, "MainContent_LblUrunGrubu")
            group2 = get_text_by_id(soup, "MainContent_LblUrunGrubu_1")

            if description_html:
                best_product.description = description_html

            if stock_code:
                best_product.stock_code = stock_code

            if product_code:
                best_product.product_code = product_code

            if brand:
                best_product.brand = brand

            if condition:
                best_product.condition = condition

            product_group = " / ".join([x for x in [group1, group2] if x])
            if product_group:
                best_product.product_group = product_group

            best_product.save()
            updated_count += 1

            print(
                "Güncellendi:",
                best_product.name,
                "| HTML:",
                html_product_name,
                "| skor:",
                round(best_score, 2),
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamamlandı. Güncellenen: {updated_count}, Atlanan: {skipped_count}"
            )
        )