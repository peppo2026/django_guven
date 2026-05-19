from bs4 import BeautifulSoup
import re


HTML_FILE = "scraping/yon_detail.html"


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


with open(HTML_FILE, "r", encoding="windows-1254", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("Seçenek başlığı:")
print("=" * 80)

option_title = soup.find(id="MainContent_Lbl_Secenek_turu")

if option_title:
    print(clean_text(option_title.get_text(" ")))
else:
    print("Bulunamadı")


print("\nDropdown seçenekleri:")
print("=" * 80)

select = soup.find(id="MainContent_DrpSecenek")

if select:
    for option in select.find_all("option"):
        value = clean_text(option.get("value", ""))
        text = clean_text(option.get_text(" "))

        print("VALUE:", value, "| TEXT:", text)
else:
    print("Dropdown bulunamadı")