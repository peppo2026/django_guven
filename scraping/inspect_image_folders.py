import json
import os
from collections import Counter


with open("scraping/scraped_products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

paths = []

for product in products:
    paths.extend(product.get("gallery_images", []))

normalized_paths = []

for path in paths:
    normalized_paths.append(path.replace("\\", "/"))

folders = Counter(os.path.dirname(path) for path in normalized_paths)
extensions = Counter(os.path.splitext(path)[1].lower() for path in normalized_paths)

print("Toplam ürün:", len(products))
print("Toplam resim yolu:", len(paths))
print("Tekil resim yolu:", len(set(normalized_paths)))

print("\nKlasörler:")
print("=" * 80)

for folder, count in folders.most_common(50):
    print(folder, "=>", count)

print("\nUzantılar:")
print("=" * 80)

for ext, count in extensions.most_common():
    print(ext, "=>", count)