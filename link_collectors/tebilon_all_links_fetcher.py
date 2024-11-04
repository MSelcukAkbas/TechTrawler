import requests
from bs4 import BeautifulSoup
import pandas as pd

url = 'https://www.tebilon.com/bilgisayar-parcalari/islemci/'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
all_products = []

max_page = soup.select_one("#mainPage > main > section.showcase > div > div > div.showcase__showcaseProducts.col-md-12.col-sm-12.col-xs-12.mobileShow > div.col-md-12.productSort__paginationBottom > div > a:nth-child(5)")

if max_page:
    print(max_page.text)


product_list = soup.select("#allProducts > div > div")
for product in product_list:
    name_link_manufacturer = product.select_one("div > div > div > div.showcase__shadow.col-md-12.no-padding > div.showcase__title.col-md-12.text-center.no-padding.mobileShow > a")
    price_tag = product.select_one("div > div > div > div.showcase__shadow.col-md-12.no-padding > div:nth-child(4) > div > div > div.new.newPrice.col-md-12.col-12.text-center")

    title = name_link_manufacturer.text if name_link_manufacturer else "isim bulunamadı"
    product_link = (name_link_manufacturer['href'] if name_link_manufacturer and name_link_manufacturer['href'].startswith("http") 
                    else f"https://www.tebilon.com{name_link_manufacturer['href']}" if name_link_manufacturer else "Link bulunamadı")
    price = price_tag.text.strip() if price_tag else "Fiyat bulunamadı"
    manufacturer = title.split()[0] if title != "isim bulunamadı" else "bulunamadı"
    
    all_products.append({
        "İsim": title,
        "Fiyat": price,
        "Üretici": manufacturer,
        "Link": product_link
    })

for product in all_products:
    print(product)
