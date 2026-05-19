from pathlib import Path
from bs4 import BeautifulSoup
import re


BASE_DIR = Path(__file__).resolve().parent.parent

# Sen hangi offline HTML dosyasını test ediyorsan adını buraya yaz.
HTML_FILE = BASE_DIR / "deyaycode.html"


def clean_text(el):
    if not el:
        return ""
    text = el.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


raw = HTML_FILE.read_bytes()

encodings = [
    "utf-8",
    "windows-1254",
    "iso-8859-9",
    "latin-1",
]

for enc in encodings:
    print("\n" + "=" * 60)
    print(f"ENCODING TEST: {enc}")
    print("=" * 60)

    html_text = raw.decode(enc, errors="replace")
    soup = BeautifulSoup(html_text, "html.parser")

    # İlk birkaç ürün yorumu metnini yakalayalım.
    comment_texts = soup.find_all(id=re.compile(r"^MainContent_DataList1_labelkuladi0_\d+$"))

    if not comment_texts:
        print("Ürün yorum metni bulunamadı.")
        continue

    for item in comment_texts[:5]:
        print(clean_text(item))