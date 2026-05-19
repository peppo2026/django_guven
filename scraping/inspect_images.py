from bs4 import BeautifulSoup

with open("scraping/detayli.html", "r", encoding="windows-1254", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("Bulunan img etiketleri:")
print("=" * 80)

for img in soup.find_all("img", src=True):
    src = img.get("src", "")
    alt = img.get("alt", "")
    width = img.get("width", "")
    height = img.get("height", "")

    print("SRC:", src)
    print("ALT:", alt)
    print("WIDTH:", width, "HEIGHT:", height)
    print("-" * 80)