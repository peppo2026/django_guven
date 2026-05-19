from bs4 import BeautifulSoup

with open("scraping/detail_sample.html", "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
text = soup.get_text("\n")

keywords = [
    "Stok",
    "Ürün Kodu",
    "Markası",
    "Ürün Durumu",
    "Ürün Grubu",
]

for keyword in keywords:
    index = text.find(keyword)

    print("\n" + "=" * 80)
    print("ARANAN:", keyword)
    print("=" * 80)

    if index == -1:
        print("Bulunamadı")
    else:
        start = max(0, index - 300)
        end = index + 700
        print(text[start:end])