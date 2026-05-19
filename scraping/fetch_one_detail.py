import json
import requests


with open("scraping/product_links.json", "r", encoding="utf-8") as f:
    products = json.load(f)

first_product = products[0]
url = first_product["url"]

print("Çekilecek ürün:")
print(first_product["name_from_list"])
print(url)

response = requests.get(url, timeout=20)

print("Status code:", response.status_code)
print("Encoding:", response.encoding)
print("Apparent encoding:", response.apparent_encoding)
print("HTML uzunluğu:", len(response.text))

# Türkçe karakter için en muhtemel doğru encoding
response.encoding = "windows-1254"

html = response.text

with open("scraping/detail_sample.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Kaydedildi: scraping/detail_sample.html")