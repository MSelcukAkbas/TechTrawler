import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from TechCrawler import PageFetcher, Config

config = Config()
pageFetcher = PageFetcher(config=config)


result = pageFetcher.fetch("https://www.teknosa.com/ekran-karti-c-116001004")

max_page_element = result.select_one("#site-main > div > div > div.col-12.section-1 > div > div > div.plp-grid > div.plp-body > div.plp-paging > div.plp-paging-button > button > span")
max_page = 1 

if max_page_element and max_page_element.text:
    split_text = max_page_element.text.split("/")
    if len(split_text) > 1:
        max_page = split_text[1].strip().replace(")", "")

product_list = result.select("#product-item")
products = [] 

for product in product_list:
    name_link_element = product.select_one("a")
    price = product.select_one("input").get('value', "isim bulunamadı")

    product_name = name_link_element.get('title', "isim bulunamadı")
    link = name_link_element['href'] if name_link_element['href'].startswith("http") else "https://www.teknosa.com" + name_link_element['href']
    manufacturer = product_name.split()[0] if product_name != "isim bulunamadı" else "bulunamadı"
    
    products.append({
        "product_name": product_name,
        "price": price,
        "link": link,
        "manufacturer": manufacturer
    })
    
    print(product_name, price)

df = pd.DataFrame(products)
print(df)