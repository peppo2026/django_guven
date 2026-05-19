import json
from pathlib import Path


PRODUCTS_FILE = Path("scraping/scraped_products.json")


CANONICAL_ORDER = [
    "Sol (Şoför Tarafı)",
    "Sağ (Yolcu Tarafı)",
    "Ön Sol (Şoför Tarafı)",
    "Ön Sağ (Yolcu Tarafı)",
    "Arka Sol (Şoför Tarafı)",
    "Arka Sağ (Yolcu Tarafı)",
]


KNOWN_OPTIONS = [
    "Ön Sağ (Yolcu Tarafı)",
    "Ön Sol (Şoför Tarafı)",
    "Arka Sağ (Yolcu Tarafı)",
    "Arka Sol (Şoför Tarafı)",
    "Sağ (Yolcu Tarafı)",
    "Sol (Şoför Tarafı)",
]


def clean_option_title(title):
    if not title:
        return ""

    title = title.strip()

    if title == "Yön Seçiniz:":
        return "Yön Seçiniz"

    return title


def extract_known_options(text):
    if not text:
        return []

    text = text.strip()
    found = []

    for option in KNOWN_OPTIONS:
        if option in text:
            found.append(option)
            text = text.replace(option, " ")

    if found:
        return found

    return [text]


def clean_option_values(values):
    found = []

    for value in values:
        parts = extract_known_options(value)

        for part in parts:
            if part not in found:
                found.append(part)

    has_front_or_back = any(
        option.startswith("Ön ") or option.startswith("Arka ")
        for option in found
    )

    # Eğer Ön/Arka seçenekleri varsa, önceki hatalı temizlikten gelen genel Sağ/Sol seçeneklerini at.
    if has_front_or_back:
        found = [
            option for option in found
            if option not in [
                "Sağ (Yolcu Tarafı)",
                "Sol (Şoför Tarafı)",
            ]
        ]

    ordered = []

    for option in CANONICAL_ORDER:
        if option in found:
            ordered.append(option)

    for option in found:
        if option not in ordered:
            ordered.append(option)

    return ordered


with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
    products = json.load(f)


changed_count = 0

for product in products:
    if not product.get("has_options"):
        product["has_options"] = False
        product["option_title"] = ""
        product["option_values"] = []
        continue

    old_title = product.get("option_title", "")
    old_values = product.get("option_values", [])

    new_title = clean_option_title(old_title)
    new_values = clean_option_values(old_values)

    if old_title != new_title or old_values != new_values:
        changed_count += 1

    product["option_title"] = new_title
    product["option_values"] = new_values
    product["has_options"] = bool(new_values)


with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)


print("Bitti.")
print("Temizlenen ürün sayısı:", changed_count)
print("Güncellenen dosya:", PRODUCTS_FILE)