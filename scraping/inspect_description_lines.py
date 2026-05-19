from bs4 import BeautifulSoup
import re


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


with open("scraping/detail_sample.html", "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

lines = []

for line in soup.get_text("\n").splitlines():
    line = clean_text(line)
    if line:
        lines.append(line)

for i, line in enumerate(lines):
    if line == "Paketleme":
        start = max(0, i - 25)
        end = min(len(lines), i + 10)

        print("Paketleme öncesi / sonrası satırlar:")
        print("=" * 80)

        for no in range(start, end):
            print(no, "=>", lines[no])

        break