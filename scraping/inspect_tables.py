from bs4 import BeautifulSoup

with open("scraping/detail_sample.html", "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")

print("Toplam tablo sayısı:", len(tables))

for index, table in enumerate(tables):
    text = table.get_text(" ", strip=True)

    if "Astra" in text or "Vectra" in text or "Omega" in text or "Uyumlu" in text or "Marka" in text:
        print("\n" + "=" * 80)
        print("TABLO NO:", index)
        print("=" * 80)
        print(text[:2000])