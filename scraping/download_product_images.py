import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


PRODUCTS_FILE = Path("scraping/scraped_products.json")
FAILED_FILE = Path("scraping/failed_images.json")

BASE_URL = "https://guvenotoyedek.com/"
STATIC_DIR = Path("static")


def load_json_list(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_path(path):
    path = path.strip().replace("\\", "/")

    if path.startswith("./"):
        path = path[2:]

    if path.startswith("../"):
        path = path.replace("../", "")

    if path.startswith("/"):
        path = path[1:]

    return path


def download_image(image_path, max_retries=3):
    image_path = normalize_path(image_path)

    image_url = urljoin(BASE_URL, image_path)
    save_path = STATIC_DIR / image_path

    if save_path.exists() and save_path.stat().st_size > 0:
        return "exists", image_url, save_path

    save_path.parent.mkdir(parents=True, exist_ok=True)

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Deneme {attempt}/{max_retries}: {image_url}")

            response = requests.get(image_url, timeout=60)

            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}"
                time.sleep(2)
                continue

            content_type = response.headers.get("Content-Type", "")

            if "image" not in content_type.lower():
                last_error = f"Resim değil: {content_type}"
                time.sleep(2)
                continue

            with open(save_path, "wb") as f:
                f.write(response.content)

            return "downloaded", image_url, save_path

        except Exception as e:
            last_error = str(e)
            print("Hata:", last_error)
            time.sleep(3)

    raise Exception(last_error)


with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
    products = json.load(f)

image_paths = []

for product in products:
    for image_path in product.get("gallery_images", []):
        normalized = normalize_path(image_path)

        if normalized not in image_paths:
            image_paths.append(normalized)

failed_images = load_json_list(FAILED_FILE)

print("Toplam ürün:", len(products))
print("Tekil resim:", len(image_paths))
print("=" * 80)

downloaded_count = 0
exists_count = 0

for index, image_path in enumerate(image_paths, start=1):
    print("\n" + "=" * 80)
    print(f"{index}/{len(image_paths)}")
    print("Resim yolu:", image_path)

    try:
        status, image_url, save_path = download_image(image_path)

        if status == "exists":
            exists_count += 1
            print("Zaten var:", save_path)

        elif status == "downloaded":
            downloaded_count += 1
            print("İndirildi:", save_path)

        failed_images = [
            item for item in failed_images
            if item.get("image_path") != image_path
        ]

        save_json(FAILED_FILE, failed_images)

    except Exception as e:
        error_message = str(e)
        print("RESİM HATASI:", error_message)

        already_failed = any(
            item.get("image_path") == image_path
            for item in failed_images
        )

        if not already_failed:
            failed_images.append({
                "image_path": image_path,
                "url": urljoin(BASE_URL, image_path),
                "error": error_message,
            })

        save_json(FAILED_FILE, failed_images)

    time.sleep(0.3)

print("\nBitti.")
print("İndirilen:", downloaded_count)
print("Zaten var:", exists_count)
print("Hatalı resim:", len(failed_images))
print("Hatalı dosya:", FAILED_FILE)