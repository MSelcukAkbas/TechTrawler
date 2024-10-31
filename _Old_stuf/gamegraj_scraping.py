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

def scrape_products(url, category_name):
    all_products = []

    soup = fetch_page(url)
    if not soup:
        print(f"Sayfa alınamadı: {url}. İşlem durduruluyor.")
        return

    page_number_element = soup.select_one("body > div.edgtf-wrapper > div > div.edgtf-content > div > div.edgtf-container > div > div > div.edgtf-page-content-holder.edgtf-grid-col-9.edgtf-grid-col-push-3 > nav > ul > li:nth-child(2) > a")
    total_pages = int(page_number_element.text.strip()) if page_number_element else 1

    for page in range(1, total_pages + 1):
        page_url = f"{url}page/{page}/" if page > 1 else url

        soup = fetch_page(page_url)
        if not soup:
            print(f"Sayfa alınamadı: {page_url}. Atlanıyor.")
            continue

        products = soup.select("li.product")
        for product in products:
            price_element = product.select_one(".price ins .woocommerce-Price-amount")
            price = price_element.text.strip() if price_element else "Fiyat yok"

            title = product.select_one(".edgtf-product-list-title a").text.strip()
            product_link = product.select_one(".edgtf-product-list-title a")["href"]
            
            manufacturer = get_manufacturer(title)

            all_products.append({
                "İsim": title,
                "Fiyat": price,
                "Üretici": manufacturer,
                "Link": product_link
            })

    df = pd.DataFrame(all_products)

    directory = f"GameGaraj_{formatli_tarih_saat}"
    os.makedirs(directory, exist_ok=True)
    csv_filename = f"GameGaraj_{category_name}.csv"
    df.to_csv(os.path.join(directory, csv_filename), index=False, encoding='utf-8-sig')

    print(f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi.")

categories = {
    "https://www.gamegaraj.com/grup/pc-bilesenleri/ekran-karti-oem-urunler/": "gpu",
    "https://www.gamegaraj.com/grup/pc-bilesenleri/anakart-oem-urunler/": "motherboard",
    "https://www.gamegaraj.com/grup/pc-bilesenleri/guc-kaynagi-oem-urunler/": "psu"
}

with ThreadPoolExecutor() as executor:
    executor.map(lambda item: scrape_products(item[0], item[1]), categories.items())
