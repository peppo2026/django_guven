from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import json


HTML_FILE = "scraping/urun_listesi.html"
BASE_URL = "https://guvenotoyedek.com/"


def fix_turkish(text):
    if not text:
        return text

    replacements = {
        "Ý": "İ",
        "ý": "ı",
        "Þ": "Ş",
        "þ": "ş",
        "Ð": "Ğ",
        "ð": "ğ",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return text


with open(HTML_FILE, "r", encoding="windows-1254", errors="replace") as f:
    html = f.read()

html = fix_turkish(html)

soup = BeautifulSoup(html, "html.parser")

product_links = {}

for a in soup.find_all("a", href=True):
    href = a["href"]

    if "urun.aspx" not in href:
        continue

    full_url = urljoin(BASE_URL, href)

    parsed = urlparse(full_url)
    query = parse_qs(parsed.query)

    product_id = query.get("u", [None])[0]

    if not product_id:
        continue

    product_name = fix_turkish(a.get_text(strip=True))

    if product_id not in product_links:
        product_links[product_id] = {
            "source_product_id": product_id,
            "name_from_list": product_name,
            "url": full_url,
        }

products = list(product_links.values())

print("Toplam tekil ürün linki:", len(products))

with open("scraping/product_links.json", "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("Kaydedildi: scraping/product_links.json")