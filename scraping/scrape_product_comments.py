import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCTS_FILE = BASE_DIR / "scraping" / "scraped_products.json"
OUTPUT_FILE = BASE_DIR / "scraping" / "scraped_comments.json"
FAILED_FILE = BASE_DIR / "scraping" / "failed_comment_pages.json"
PROGRESS_FILE = BASE_DIR / "scraping" / "comment_scrape_progress.json"

BASE_URL = "https://guvenotoyedek.com/urun.aspx?u={product_id}"

# Artık bütün ürünleri geziyoruz.
# Belirli ürün test etmek istersen örnek: TARGET_PRODUCT_IDS = ["11"]
TARGET_PRODUCT_IDS = []

# None = bütün ürünler.
# Test için 10, 50 gibi sayı verebilirsin.
TEST_LIMIT = None

REQUEST_DELAY = 0.05
REQUEST_TIMEOUT = 20


def clean_text(value):
    if not value:
        return ""

    if hasattr(value, "get_text"):
        text = value.get_text(" ", strip=True)
    else:
        text = str(value)

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_bad_chars(text):
    bad_markers = ["�", "ï¿½", "Ã", "Â"]
    return sum(text.count(marker) for marker in bad_markers)


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_html(url, max_retries=2):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"    İstek denemesi: {attempt}/{max_retries}", flush=True)

            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            print(f"    HTTP status: {response.status_code}", flush=True)

            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}"
                time.sleep(1)
                continue

            raw_html = response.content

            candidates = []

            for enc in ["iso-8859-9", "windows-1254", "utf-8"]:
                html = raw_html.decode(enc, errors="replace")
                candidates.append((count_bad_chars(html), enc, html))

            candidates.sort(key=lambda x: x[0])

            best_bad_count, best_encoding, best_html = candidates[0]

            return best_html, best_encoding, best_bad_count

        except Exception as e:
            last_error = str(e)
            print(f"    İstek hatası: {last_error}", flush=True)
            time.sleep(1)

    raise Exception(last_error)


def parse_comments(html_text, source_product_id):
    soup = BeautifulSoup(html_text, "html.parser")
    comments = []

    # Ürün detayındaki ana yorumlar:
    # MainContent_DataList1_Hdnkimlik_0
    main_hidden_inputs = soup.find_all(
        "input",
        id=re.compile(r"^MainContent_DataList1_Hdnkimlik_\d+$")
    )

    for hidden in main_hidden_inputs:
        index_match = re.search(r"_(\d+)$", hidden.get("id", ""))
        if not index_match:
            continue

        index = index_match.group(1)
        source_comment_id = hidden.get("value", "").strip()

        author_el = soup.find(id=f"MainContent_DataList1_label17_{index}")
        text_el = soup.find(id=f"MainContent_DataList1_labelkuladi0_{index}")
        date_el = soup.find(id=f"MainContent_DataList1_label18_{index}")

        comment = {
            "source_product_id": str(source_product_id),
            "source_comment_id": source_comment_id,
            "parent_comment_id": None,
            "author_name": clean_text(author_el),
            "text": clean_text(text_el),
            "date_text": clean_text(date_el),
        }

        if comment["source_comment_id"] and comment["text"]:
            comments.append(comment)

        # Ana yorumun altındaki cevaplar:
        # MainContent_DataList1_DataList2_0_Hdnyavrukimlik_0
        reply_hidden_inputs = soup.find_all(
            "input",
            id=re.compile(
                rf"^MainContent_DataList1_DataList2_{index}_Hdnyavrukimlik_\d+$"
            )
        )

        for reply_hidden in reply_hidden_inputs:
            reply_index_match = re.search(r"_(\d+)$", reply_hidden.get("id", ""))
            if not reply_index_match:
                continue

            reply_index = reply_index_match.group(1)
            reply_source_comment_id = reply_hidden.get("value", "").strip()

            reply_text_el = soup.find(
                id=f"MainContent_DataList1_DataList2_{index}_labelkuladi2_{reply_index}"
            )
            reply_date_el = soup.find(
                id=f"MainContent_DataList1_DataList2_{index}_label19_{reply_index}"
            )

            full_reply_text = clean_text(reply_text_el)

            reply_author = ""
            reply_body = full_reply_text

            if full_reply_text:
                parts = full_reply_text.split(" ", 1)
                if len(parts) == 2:
                    reply_author = parts[0].strip()
                    reply_body = parts[1].strip()

            reply_comment = {
                "source_product_id": str(source_product_id),
                "source_comment_id": reply_source_comment_id,
                "parent_comment_id": source_comment_id,
                "author_name": reply_author,
                "text": reply_body,
                "date_text": clean_text(reply_date_el),
            }

            if reply_comment["source_comment_id"] and reply_comment["text"]:
                comments.append(reply_comment)

    return comments


def load_products():
    with PRODUCTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_product_id(product):
    source_product_id = product.get("source_product_id")

    if source_product_id:
        return str(source_product_id).strip()

    source_url = product.get("source_url", "")
    match = re.search(r"u=(\d+)", source_url)

    if match:
        return match.group(1)

    return None


def make_existing_comment_key(comment):
    return (
        str(comment.get("source_product_id")),
        str(comment.get("source_comment_id"))
    )


def main():
    print("Yorum scraper başladı.", flush=True)
    print("DB'ye dokunulmaz. Sadece JSON yazılır.", flush=True)
    print("İnternet kesilirse tekrar çalıştırınca kaldığı yerden devam eder.", flush=True)
    print("-" * 60, flush=True)

    products = load_products()

    if TARGET_PRODUCT_IDS:
        products_to_process = [
            product for product in products
            if get_product_id(product) in TARGET_PRODUCT_IDS
        ]
    elif TEST_LIMIT:
        products_to_process = products[:TEST_LIMIT]
    else:
        products_to_process = products

    all_comments = load_json(OUTPUT_FILE, [])
    failed_pages = load_json(FAILED_FILE, [])
    progress = load_json(PROGRESS_FILE, {
        "processed_product_ids": []
    })

    processed_product_ids = set(str(x) for x in progress.get("processed_product_ids", []))
    existing_comment_keys = set(make_existing_comment_key(c) for c in all_comments)

    total_products = len(products_to_process)

    print(f"Toplam ürün sayısı JSON'da: {len(products)}", flush=True)
    print(f"Bu çalıştırmada hedef ürün sayısı: {total_products}", flush=True)
    print(f"Daha önce işlenen ürün sayısı: {len(processed_product_ids)}", flush=True)
    print(f"Mevcut yorum sayısı: {len(all_comments)}", flush=True)
    print("-" * 60, flush=True)

    if total_products == 0:
        print("İşlenecek ürün bulunamadı.", flush=True)
        return

    for index, product in enumerate(products_to_process, start=1):
        source_product_id = get_product_id(product)
        product_name = product.get("name", "")

        if not source_product_id:
            failed_pages.append({
                "product_index": index,
                "reason": "source_product_id bulunamadı",
                "product_name": product_name,
            })

            save_json(FAILED_FILE, failed_pages)
            continue

        if source_product_id in processed_product_ids:
            print(
                f"[{index}/{total_products}] Ürün ID: {source_product_id} zaten işlenmiş, geçiliyor.",
                flush=True
            )
            continue

        url = BASE_URL.format(product_id=source_product_id)

        print(
            f"[{index}/{total_products}] Ürün ID: {source_product_id} çekiliyor...",
            flush=True
        )
        print(f"    Ürün adı: {product_name}", flush=True)
        print(f"    URL: {url}", flush=True)

        try:
            html_text, encoding_used, bad_score = fetch_html(url)
            comments = parse_comments(html_text, source_product_id)

            new_comment_count = 0

            for comment in comments:
                key = make_existing_comment_key(comment)

                if key in existing_comment_keys:
                    continue

                all_comments.append(comment)
                existing_comment_keys.add(key)
                new_comment_count += 1

            processed_product_ids.add(source_product_id)
            progress["processed_product_ids"] = sorted(
                processed_product_ids,
                key=lambda x: int(x) if x.isdigit() else x
            )

            save_json(OUTPUT_FILE, all_comments)
            save_json(FAILED_FILE, failed_pages)
            save_json(PROGRESS_FILE, progress)

            print(
                f"    SONUÇ: Sayfadaki yorum: {len(comments)} | "
                f"Yeni eklenen: {new_comment_count} | "
                f"Encoding: {encoding_used} | Skor: {bad_score}",
                flush=True
            )

        except Exception as e:
            failed_pages.append({
                "source_product_id": source_product_id,
                "product_name": product_name,
                "url": url,
                "error": str(e),
            })

            save_json(FAILED_FILE, failed_pages)

            print(
                f"    HATA: Ürün ID {source_product_id} çekilemedi | {e}",
                flush=True
            )

        print("-" * 60, flush=True)
        time.sleep(REQUEST_DELAY)

    print("Çalışma bitti.", flush=True)
    print(f"Toplam JSON yorum sayısı: {len(all_comments)}", flush=True)
    print(f"Hatalı sayfa sayısı: {len(failed_pages)}", flush=True)
    print(f"İşlenen ürün sayısı: {len(processed_product_ids)}", flush=True)
    print(f"Yorum JSON: {OUTPUT_FILE}", flush=True)
    print(f"Hata JSON: {FAILED_FILE}", flush=True)
    print(f"Progress JSON: {PROGRESS_FILE}", flush=True)

    print("\nİlk 5 yorum önizleme:", flush=True)

    for comment in all_comments[:5]:
        print("-" * 50, flush=True)
        print("Ürün ID:", comment["source_product_id"], flush=True)
        print("Yorum ID:", comment["source_comment_id"], flush=True)
        print("Parent:", comment["parent_comment_id"], flush=True)
        print("Yazar:", comment["author_name"], flush=True)
        print("Metin:", comment["text"], flush=True)
        print("Tarih:", comment["date_text"], flush=True)


if __name__ == "__main__":
    main()