import requests as req
from bs4 import BeautifulSoup as bea
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime

now = datetime.now()
formatli_tarih_saat = now.strftime("%Y-%m-%d_%H")

def fetch_page(url):
    try:
        response = req.get(url, timeout=10)
        response.raise_for_status()
        return bea(response.text, "html.parser")
    except req.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
def get_manufacturer(product_name):
    manufacturers = {
        "Asus": "Asus",
        "MSI": "MSI",
        "Gigabyte": "Gigabyte",
        "EVGA": "EVGA",
        "Palit": "Palit",
        "ZOTAC": "ZOTAC",
        "GeForce": "NVIDIA"
    }
    
    for key in manufacturers.keys():
        if key.lower() in product_name.lower():
            return manufacturers[key]
    
    return product_name.split(" ")[0]

def scrape_products(url, category_name, page_param="?pg="):
    all_products = []
    
    soup = fetch_page(url)
    if not soup:
        print(f"Sayfa alınamadı: {url}. İşlem durduruluyor.")
        return

    total_pages = int(soup.select_one('body > section.container-fluid > div > div.col-12.col-md-9.col-lg-9.col-xl-10 > div:nth-child(5) > div.actions > span > strong').get_text().strip().split('/')[1]) if soup else 1

    for page_num in range(1, total_pages + 1):
        page_url = url + page_param + str(page_num)
        soup = fetch_page(page_url)
        if not soup:
            print(f"Sayfa alınamadı: {page_url}. Atlanıyor.")
            continue

        for product in soup.select('#productList > div'):
            link_tag = product.select_one('div.product-body > h2 > a')
            if link_tag:
                link = link_tag['href'] if link_tag['href'].startswith("http") else "https://www.itopya.com" + link_tag['href']
                title = link_tag.get_text().strip()
                price_tag = product.select_one('div.product-footer > div.price > strong')
                price_text = price_tag.get_text().strip().replace('\xa0', '').replace('₺', '').strip() if price_tag else "nan"

                manufacturer = get_manufacturer(title) if price_text and price_text != "nan" else "Bilinmiyor"
                
                product_info = {
                    "isim": title,
                    "Fiyat": price_text, 
                    "Üretici": manufacturer,
                    "Link": link
                }
                all_products.append(product_info)

    df = pd.DataFrame(all_products)

    directory = f"Itopya_{formatli_tarih_saat}"
    os.makedirs(directory, exist_ok=True)

    csv_filename = f"Itopya_{category_name}.csv"
    df.to_csv(os.path.join(directory, csv_filename), index=False, encoding='utf-8-sig')

    print(f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi.")

categories = {
    "https://www.itopya.com/islemci_k8": "cpu",
    "https://www.itopya.com/anakart_k9": "motherboard",
    "https://www.itopya.com/ram_k10": "memory",
    "https://www.itopya.com/ekran-karti_k11": "gpu",
    "https://www.itopya.com/powersupply_k17": "psu"
}

with ThreadPoolExecutor() as executor:
    executor.map(lambda item: scrape_products(item[0], item[1]), categories.items())
