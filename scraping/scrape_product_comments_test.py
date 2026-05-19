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

BASE_URL = "https://guvenotoyedek.com/urun.aspx?u={product_id}"

# Şimdilik sadece ilk 10 üründe test ediyoruz.
# Her şey düzgünse sonra bunu None yaparız veya kaldırırız.
TEST_LIMIT = 10

# Siteyi yormamak için küçük bekleme.
REQUEST_DELAY = 0.5


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


def fetch_html(url, max_retries=3):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                timeout=60,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}"
                time.sleep(2)
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
            time.sleep(3)

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

            # Cevap satırı genelde şöyle geliyor:
            # "GuvenOtoYedek Merhaba evet araçınız için uygundur"
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


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    # utf-8-sig Windows/VS Code tarafında Türkçe karakter görüntülemeyi kolaylaştırır.
    with path.open("w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    products = load_products()

    if TEST_LIMIT:
        products_to_process = products[:TEST_LIMIT]
    else:
        products_to_process = products

    all_comments = []
    failed_pages = []

    total_products = len(products_to_process)

    print(f"Toplam ürün sayısı JSON'da: {len(products)}")
    print(f"Bu çalıştırmada denenecek ürün sayısı: {total_products}")
    print("DB'ye dokunulmaz. Sadece JSON yazılır.")
    print("-" * 60)

    for index, product in enumerate(products_to_process, start=1):
        source_product_id = get_product_id(product)

        if not source_product_id:
            failed_pages.append({
                "product_index": index,
                "reason": "source_product_id bulunamadı",
                "product_name": product.get("name", ""),
            })
            print(f"[{index}/{total_products}] source_product_id bulunamadı")
            continue

        url = BASE_URL.format(product_id=source_product_id)

        try:
            html_text, encoding_used, bad_score = fetch_html(url)
            comments = parse_comments(html_text, source_product_id)

            all_comments.extend(comments)

            print(
                f"[{index}/{total_products}] "
                f"Ürün ID: {source_product_id} | "
                f"Yorum: {len(comments)} | "
                f"Encoding: {encoding_used} | "
                f"Skor: {bad_score}"
            )

        except Exception as e:
            failed_pages.append({
                "source_product_id": source_product_id,
                "url": url,
                "error": str(e),
            })

            print(
                f"[{index}/{total_products}] "
                f"Ürün ID: {source_product_id} | HATA: {e}"
            )

        time.sleep(REQUEST_DELAY)

    save_json(OUTPUT_FILE, all_comments)
    save_json(FAILED_FILE, failed_pages)

    print("-" * 60)
    print("Test bitti.")
    print(f"Toplam çekilen yorum: {len(all_comments)}")
    print(f"Hatalı sayfa: {len(failed_pages)}")
    print(f"Yorum JSON: {OUTPUT_FILE}")
    print(f"Hata JSON: {FAILED_FILE}")

    print("\nİlk 5 yorum önizleme:")
    for comment in all_comments[:5]:
        print("-" * 50)
        print("Ürün ID:", comment["source_product_id"])
        print("Yorum ID:", comment["source_comment_id"])
        print("Parent:", comment["parent_comment_id"])
        print("Yazar:", comment["author_name"])
        print("Metin:", comment["text"])
        print("Tarih:", comment["date_text"])


if __name__ == "__main__":
    main()


