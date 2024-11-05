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
    page_param = "?px="
    all_products = []

    soup = fetch_page(url)
    if not soup:
        print(f"Sayfa alınamadı: {url}. İşlem durduruluyor.")
        return
    # body > div.container-fluid > div.row > div.col > section > div:nth-child(1) > article > div.row > div.col > span
    # body > div.container-fluid > div.row > div.col > section > div:nth-child(1) > article > div.title > ak
    page_links = soup.select("a[href*='?px=']")
    total_pages = max(int(link.text) for link in page_links if link.text.isdigit())

    for page_num in range(1, total_pages + 1):
        page_url = url + page_param + str(page_num)
        soup = fetch_page(page_url)
        if not soup:
            print(f"Sayfa alınamadı: {page_url}. Atlanıyor.")
            continue

        products = soup.select("section article")
        for product in products:
            title_element = product.select_one("div.title a")
            product_name = title_element.text.strip() if title_element else "İsim yok"
            product_link = title_element["href"] if title_element else "Link yok"
            
            specs = product.find_all("li")
            specs_dict = {}
            for spec in specs:
                spec_text = spec.text.strip()
                if ':' in spec_text:
                    key, value = spec_text.split(':', 1)
                    specs_dict[key.strip()] = value.strip()
            price = product.select_one("div.row > div.col > span")
            price = price.text.replace('"', "").replace("₺","")
            manufacturer = get_manufacturer(product_name)

            product_info = {
                "İsim": product_name,
                "fiayt": price.strip(),
                "Üretici": manufacturer if manufacturer else "Bilinmiyor",
                "Link":"https://www.sinerji.gen.tr" + product_link
            }
            product_info.update(specs_dict) 

            all_products.append(product_info)

    df = pd.DataFrame(all_products)

    directory = f"sinerji_{formatli_tarih_saat}"
    os.makedirs(directory, exist_ok=True)
    csv_filename = f"sinerji_{category_name}.csv"
    df.to_csv(os.path.join(directory, csv_filename), index=False, encoding='utf-8-sig')

    print(f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi.")

categories = {
    "https://www.sinerji.gen.tr/islemci-c-1": "cpu",
    "https://www.sinerji.gen.tr/anakart-c-2009": "motherboard",
    "https://www.sinerji.gen.tr/bellek-ram-c-2010": "memory",
    "https://www.sinerji.gen.tr/ekran-karti-c-2023": "gpu",
    "https://www.sinerji.gen.tr/guc-kaynagi-c-2030": "psu"
}

with ThreadPoolExecutor() as executor:
    executor.map(lambda item: scrape_products(item[0], item[1]), categories.items())
