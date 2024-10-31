import requests as req
from bs4 import BeautifulSoup as bea
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
import json
import random
import time

cofig_dir_path = "json_data/"

class PageFetcher:
    def __init__(self, retries=3, delay=1):
        self.retries = retries
        self.delay = delay
        self.headers = self.load_user_agents()

    def load_user_agents(self):
        json_file = f'{cofig_dir_path}user_agents.json'
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('user_agents', [])
        except FileNotFoundError:
            print(f"Hata: {json_file} dosyası bulunamadı.")
            return []
        except json.JSONDecodeError:
            print(f"Hata: {json_file} dosyası okunurken bir hata oluştu.")
            return []

    def fetch(self, url, timeout=10):
        if not self.headers:
            print("Hata: Kullanıcı ajanı bulunamadı.")
            return None

        for attempt in range(self.retries):
            header = random.choice(self.headers)
            try:
                if attempt != 0:
                    print(f"{attempt + 1}. deneme: {url}")
                response = req.get(url, headers=header, timeout=timeout)
                response.raise_for_status()
                return bea(response.text, "html.parser")

            except req.exceptions.RequestException as req_err:
                print(f"Hata oluştu: {req_err} (URL: {url})")
                time.sleep(self.delay)
        return None

class WebScraper:
    def __init__(self):
        self.formatli_tarih_saat = datetime.now().strftime("%m-%d_%H")
        self.main_directory = f"Site_Data_{self.formatli_tarih_saat}"
        self.page_fetcher = PageFetcher()

        self.categories = self.load_json(f"{cofig_dir_path}links.json")
        self.manufacturers = self.load_json(f"{cofig_dir_path}manufacturers.json")["manufacturers"]

        os.makedirs(self.main_directory, exist_ok=True)

    def load_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Hata: {path} dosyası bulunamadı.")
            return {}
        except json.JSONDecodeError:
            print(f"Hata: {path} dosyası okunurken bir hata oluştu.")
            return {}

    def get_manufacturer(self, product_name):
        for key in self.manufacturers:
            if key in product_name:
                return self.manufacturers[key]
        return product_name.split(" ")[0]

    def get_total_pages(self, soup, site_name):
        if site_name == "GameGaraj":
            page_number_element = soup.select_one("body > div.edgtf-wrapper > div > div.edgtf-content > div > div.edgtf-container > div > div > div.edgtf-page-content-holder.edgtf-grid-col-9.edgtf-grid-col-push-3 > nav > ul > li:nth-child(2) > a")
            return int(page_number_element.text.strip()) if page_number_element else 1
        elif site_name == "Itopya":
            return int(soup.select_one('body > section.container-fluid > div > div.col-12.col-md-9.col-lg-9.col-xl-10 > div:nth-child(5) > div.actions > span > strong').get_text().strip().split('/')[1]) if soup else 1
        else:  # Sinerji
            page_links = soup.select("a[href*='?px=']")
            return max(int(link.text) for link in page_links if link.text.isdigit())

    def extract_products(self, soup, site_name):
        all_products = []
        if site_name == "GameGaraj":
            products = soup.select("li.product")
            for product in products:
                price_element = product.select_one(".price ins .woocommerce-Price-amount")
                price = price_element.text.strip() if price_element else "Fiyat yok"
                title = product.select_one(".edgtf-product-list-title a").text.strip()
                product_link = product.select_one(".edgtf-product-list-title a")["href"]
                manufacturer = self.get_manufacturer(title)
                all_products.append({"İsim": title, "Fiyat": price, "Üretici": manufacturer, "Link": product_link})

        elif site_name == "Itopya":
            for product in soup.select('#productList > div'):
                link_tag = product.select_one('div.product-body > h2 > a')
                if link_tag:
                    link = link_tag['href'] if link_tag['href'].startswith("http") else "https://www.itopya.com" + link_tag['href']
                    title = link_tag.get_text().strip()
                    price_tag = product.select_one('div.product-footer > div.price > strong')
                    price_text = price_tag.get_text().strip().replace('\xa0', '').replace('₺', '').strip() if price_tag else "nan"
                    manufacturer = self.get_manufacturer(title) if price_text and price_text != "nan" else "Bilinmiyor"
                    all_products.append({"İsim": title, "Fiyat": price_text, "Üretici": manufacturer, "Link": link})

        else:  # Sinerji
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
                manufacturer = self.get_manufacturer(product_name)
                product_info = {"İsim": product_name, "Üretici": manufacturer if manufacturer else "Bilinmiyor", "Link": "https://www.sinerji.gen.tr" + product_link}
                product_info.update(specs_dict)
                all_products.append(product_info)
        
        return all_products

    def save_to_csv(self, all_products, site_name, category_name):
        df = pd.DataFrame(all_products)
        timestamp_directory = f"{site_name}_{self.formatli_tarih_saat}"
        full_directory = os.path.join(self.main_directory, timestamp_directory)
        os.makedirs(full_directory, exist_ok=True)

        csv_filename = f"{site_name}_{category_name}.csv"
        df.to_csv(os.path.join(full_directory, csv_filename), index=False, encoding='utf-8-sig')
        print(f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi.")

    def scrape_products(self, url, category_name, site_name):
        all_products = []
        
        soup = self.page_fetcher.fetch(url)
        if not soup:
            print(f"Sayfa alınamadı: {url}. İşlem durduruluyor.")
            return

        total_pages = self.get_total_pages(soup, site_name)

        for page_num in range(1, total_pages + 1):
            page_url = f"{url}?pg={page_num}"
            soup = self.page_fetcher.fetch(page_url)  # Düzeltildi
            if not soup:
                print(f"Sayfa alınamadı: {page_url}. Atlanıyor.")
                continue
            
            all_products.extend(self.extract_products(soup, site_name))

        self.save_to_csv(all_products, site_name, category_name)

    def run(self):
        with ThreadPoolExecutor() as executor:
            for site_name, site_categories in self.categories.items():
                executor.map(lambda item: self.scrape_products(item[0], item[1], site_name), site_categories.items())

if __name__ == "__main__":
    scraper = WebScraper()
    scraper.run()
