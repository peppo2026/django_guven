from bs4 import BeautifulSoup
import re
import json


HTML_FILE = "scraping/detayli.html"


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_lines(soup):
    lines = []

    for line in soup.get_text("\n").splitlines():
        line = clean_text(line)
        if line:
            lines.append(line)

    return lines


def get_value_after_label(lines, label):
    """
    Örnek yapı:
    Stok Kodu
    :
    348

    Label'i bulur, altındaki ':' satırını atlar, ilk gerçek değeri alır.
    """
    for i, line in enumerate(lines):
        if clean_text(line).lower() == label.lower():
            for next_line in lines[i + 1:i + 8]:
                if next_line == ":":
                    continue
                return clean_text(next_line)

    return ""


def normalize_image_path(path):
    if not path:
        return ""

    path = path.strip()
    path = path.replace("\\", "/")

    if path.startswith("./"):
        path = path[2:]

    if path.startswith("../"):
        path = path.replace("../", "")

    if path.startswith("/"):
        path = path[1:]

    return path


def is_product_image(path):
    if not path:
        return False

    path_lower = path.lower()

    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

    has_image_extension = any(path_lower.endswith(ext) for ext in image_extensions)

    if not has_image_extension:
        return False

    excluded_names = [
        "baslik.gif",
        "opel_arma.gif",
        "opel_arma_k.gif",
        "chevroletl_arma.gif",
        "chevroletl_arma_k.gif",
        "loading.gif",
        "sepet_bos.png",
        "ara.png",
        "tekyildiz_sari.png",
        "icon_madde_isareti.gif",
        "super-hizli-gonderi.gif",
        "iade190x150.png",
        "para-iade.jpg",
        "vakifbank.gif",
    ]

    for excluded in excluded_names:
        if excluded in path_lower:
            return False

    # Gerçek ürün fotoğraflarında çoğunlukla foto1, foto2, foto3 geçiyor.
    if re.search(r"foto[0-9]", path_lower):
        return True

    # Canlı sitede ürün resimleri genelde urunler klasöründen gelir.
    if "urunler" in path_lower:
        return True

    # Kaydedilmiş HTML'de bazen ürün görselleri _files içine düşer.
    # Yukarıdaki gereksiz site görsellerini dışladık, geriye kalan görseller ürün olabilir.
    if "_files" in path_lower:
        return True

    return False


with open(HTML_FILE, "r", encoding="windows-1254", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
lines = normalize_lines(soup)
page_text = clean_text(soup.get_text(" "))


data = {
    "name": "",
    "price": "",
    "stock_code": "",
    "product_code": "",
    "brand": "",
    "condition": "",
    "product_group": "",
    "description": "",
    "main_image": "",
    "gallery_images": [],
    "compatible_cars": [],
}


# Ürün adı
name_tag = soup.find(id="MainContent_LblUrunadi0")

if name_tag:
    data["name"] = clean_text(name_tag.get_text(" "))
else:
    title = soup.find("title")
    if title:
        data["name"] = clean_text(title.get_text())


# Fiyat
price_match = re.search(r"([0-9\.\,]+)\s*TL", page_text)
if price_match:
    data["price"] = price_match.group(1)


# Ürün detay alanları
data["stock_code"] = get_value_after_label(lines, "Stok Kodu")
data["product_code"] = get_value_after_label(lines, "Ürün Kodu")
data["brand"] = get_value_after_label(lines, "Markası")
data["condition"] = get_value_after_label(lines, "Ürün Durumu")
data["product_group"] = get_value_after_label(lines, "Ürün Grubu")


# Açıklama
description_tag = soup.find(id="MainContent_Lblaciklama2")

if description_tag:
    data["description"] = clean_text(description_tag.get_text(" "))
else:
    data["description"] = ""


# Uyumlu araç listesi
compatible_cars = []

for table in soup.find_all("table"):
    table_text = table.get_text(" ", strip=True)

    if "BU ÜRÜNÜN TAKILABİLECEĞİ" not in table_text:
        continue

    for tr in table.find_all("tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.find_all("td")]
        cells = [c for c in cells if c]

        if len(cells) < 2:
            continue

        row_text = " ".join(cells)

        if "BU ÜRÜNÜN TAKILABİLECEĞİ" in row_text:
            continue

        brand = cells[0]
        model = cells[1] if len(cells) >= 2 else ""
        years = cells[2] if len(cells) >= 3 else ""

        if brand in ["Opel", "Chevrolet"] and model and model != ":":
            compatible_cars.append({
                "brand": brand,
                "model": model,
                "years": years
            })


# Tekrarlayan uyumlu araçları temizle
unique_compatible_cars = []
seen = set()

for car in compatible_cars:
    key = (
        car["brand"],
        car["model"],
        car["years"],
    )

    if key not in seen:
        seen.add(key)
        unique_compatible_cars.append(car)

data["compatible_cars"] = unique_compatible_cars


# Resimler
images = []
seen_image_numbers = set()


def add_image(path):
    if not is_product_image(path):
        return

    path = normalize_image_path(path)

    # Aynı foto1 / foto2 / foto3 tekrarlarını temizle
    match = re.search(r"foto([0-9])", path.lower())

    if match:
        photo_number = match.group(1)

        if photo_number in seen_image_numbers:
            return

        seen_image_numbers.add(photo_number)

    if path and path not in images:
        images.append(path)


# 1. img src içindeki resimler
for img in soup.find_all("img", src=True):
    add_image(img.get("src"))


# 2. input type=image src içindeki resimler
for input_tag in soup.find_all("input", src=True):
    add_image(input_tag.get("src"))


# 3. a href içindeki büyük galeri resimleri
for a in soup.find_all("a", href=True):
    add_image(a.get("href"))


data["gallery_images"] = images

if images:
    data["main_image"] = images[0]


print(json.dumps(data, ensure_ascii=False, indent=2))

with open("scraping/detail_sample_result.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\nKaydedildi: scraping/detail_sample_result.json")