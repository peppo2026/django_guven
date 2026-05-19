import json
from pathlib import Path

import os
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proje.settings")
django.setup()


from shop.models import Product, ProductComment


BASE_DIR = Path(__file__).resolve().parent
COMMENTS_FILE = BASE_DIR / "scraping" / "scraped_comments.json"


def clean_value(value):
    if value is None:
        return ""
    return str(value).strip()


def main():
    print("Yorum import başladı.")
    print("Ürünlere, fiyatlara, resimlere dokunulmaz.")
    print("-" * 60)

    if not COMMENTS_FILE.exists():
        print(f"HATA: Dosya bulunamadı: {COMMENTS_FILE}")
        return

    with COMMENTS_FILE.open("r", encoding="utf-8-sig") as f:
        comments = json.load(f)

    print(f"JSON yorum sayısı: {len(comments)}")

    # Eski/test yorumları temizliyoruz.
    deleted_count, _ = ProductComment.objects.all().delete()
    print(f"Temizlenen eski yorum kaydı: {deleted_count}")

    # Ürünleri source_product_id ile hızlı bulmak için sözlük yapıyoruz.
    products_by_source_id = {
        str(product.source_product_id): product
        for product in Product.objects.exclude(source_product_id__isnull=True)
    }

    created_comments_by_key = {}

    created_main = 0
    created_replies = 0
    skipped_missing_product = 0
    skipped_missing_parent = 0
    skipped_invalid = 0

    # 1. TUR: Ana yorumları oluştur.
    for item in comments:
        source_product_id = clean_value(item.get("source_product_id"))
        source_comment_id = clean_value(item.get("source_comment_id"))
        parent_comment_id = item.get("parent_comment_id")

        author_name = clean_value(item.get("author_name")) or "Misafir"
        text = clean_value(item.get("text"))
        date_text = clean_value(item.get("date_text"))

        if not source_product_id or not source_comment_id or not text:
            skipped_invalid += 1
            continue

        # parent varsa bu cevap yorumudur, 2. turda oluşturacağız.
        if parent_comment_id:
            continue

        product = products_by_source_id.get(source_product_id)

        if not product:
            skipped_missing_product += 1
            continue

        comment = ProductComment.objects.create(
            product=product,
            source_product_id=source_product_id,
            source_comment_id=source_comment_id,
            parent=None,
            author_name=author_name,
            text=text,
            date_text=date_text,
            is_approved=True,
            is_imported=True,
        )

        key = (source_product_id, source_comment_id)
        created_comments_by_key[key] = comment
        created_main += 1

    # 2. TUR: Cevap yorumlarını oluştur.
    for item in comments:
        source_product_id = clean_value(item.get("source_product_id"))
        source_comment_id = clean_value(item.get("source_comment_id"))
        parent_comment_id = clean_value(item.get("parent_comment_id"))

        author_name = clean_value(item.get("author_name")) or "Guvenotoyedek"
        text = clean_value(item.get("text"))
        date_text = clean_value(item.get("date_text"))

        if not parent_comment_id:
            continue

        if not source_product_id or not source_comment_id or not text:
            skipped_invalid += 1
            continue

        product = products_by_source_id.get(source_product_id)

        if not product:
            skipped_missing_product += 1
            continue

        parent = created_comments_by_key.get((source_product_id, parent_comment_id))

        if not parent:
            skipped_missing_parent += 1
            continue

        reply = ProductComment.objects.create(
            product=product,
            source_product_id=source_product_id,
            source_comment_id=source_comment_id,
            parent=parent,
            author_name=author_name,
            text=text,
            date_text=date_text,
            is_approved=True,
            is_imported=True,
        )

        key = (source_product_id, source_comment_id)
        created_comments_by_key[key] = reply
        created_replies += 1

    total_created = created_main + created_replies

    print("-" * 60)
    print("Yorum import bitti.")
    print(f"Oluşturulan ana yorum: {created_main}")
    print(f"Oluşturulan cevap: {created_replies}")
    print(f"Toplam oluşturulan yorum: {total_created}")
    print(f"Ürünü bulunamayan atlandı: {skipped_missing_product}")
    print(f"Parent yorumu bulunamayan cevap atlandı: {skipped_missing_parent}")
    print(f"Geçersiz/eksik veri atlandı: {skipped_invalid}")
    print(f"DB toplam ProductComment: {ProductComment.objects.count()}")


if __name__ == "__main__":
    main()