import requests as req
from bs4 import BeautifulSoup as bea
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
import json
import random
import time
from cachetools import TTLCache

cofig_dir_path = "json_data/"

class Config:
    def __init__(self):
        """
        Config sınıfını başlatır ve ayar dosyalarını yükler.
        """
        self.user_agents = self.load_json(f'{cofig_dir_path}user_agents.json')
        self.links = self.load_json(f'{cofig_dir_path}links.json')
        self.manufacturers = self.load_json(f'{cofig_dir_path}manufacturers.json')

    def load_json(self, path: str) -> dict:
        """
        Belirtilen dosya yolundan JSON verilerini yükler.

        Args:
            path (str): Yüklenilecek JSON dosyasının yolu.

        Returns:
            dict: JSON verileri.
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Hata: {path} dosyası bulunamadı.")
            return {}
        except json.JSONDecodeError:
            print(f"Hata: {path} dosyası okunurken bir hata oluştu.")
            return {}

class PageFetcher:
    def __init__(self, config: Config, retries: int = 5, delay: int = 2):
        """
        PageFetcher sınıfını başlatır.

        Args:
            config (Config): Config nesnesi.
            retries (int): Yeniden deneme sayısı.
            delay (int): Denemeler arasındaki gecikme süresi.
        """
        self.config = config
        self.retries = retries
        self.delay = delay
        self.cache = TTLCache(maxsize=100, ttl=300)

    def fetch(self, url: str, timeout: int = 15) -> bea:
        """
        Belirtilen URL'den sayfayı alır.

        Args:
            url (str): Alınacak sayfanın URL'si.
            timeout (int): Zaman aşımı süresi.

        Returns:
            BeautifulSoup: Alınan sayfanın BeautifulSoup nesnesi.
        """
        if url in self.cache:
            return self.cache[url]

        for attempt in range(self.retries):
            if not self.config.user_agents:
                print("Hata: Kullanıcı ajanı bulunamadı.")
                return None
            
            header = random.choice(self.config.user_agents.get('user_agents', [])) 
            try:
                if attempt != 0:
                    print(f"{attempt + 1}. deneme: {url}")
                response = req.get(url, headers=header, timeout=timeout)
                response.raise_for_status()
                soup = bea(response.text, "html.parser")
                self.cache[url] = soup  # O anki sayfayı önbelleğe al
                return soup
            
            except req.exceptions.HTTPError as http_err:
                print(f"HTTP hatası oluştu: {http_err} (URL: {url})")
            except req.exceptions.ConnectionError as conn_err:
                print(f"Bağlantı hatası oluştu: {conn_err} (URL: {url})")
            except req.exceptions.Timeout as timeout_err:
                print(f"Zaman aşımı hatası oluştu: {timeout_err} (URL: {url})")
            except req.exceptions.RequestException as req_err:
                print(f"Bir hata oluştu: {req_err} (URL: {url})")

            time.sleep(self.delay)
        return None

class WebScraper:
    def __init__(self, config: Config  , PageFetcher:PageFetcher):
        """
        WebScraper sınıfını başlatır ve gerekli dizinleri oluşturur.

        Args:
            config (Config): Config nesnesi.
        """
        now = datetime.now()
        self.formatli_tarih_saat = now.strftime("%m-%d_%H")
        self.main_directory = f"Site_Data_{self.formatli_tarih_saat}"
        os.makedirs(self.main_directory, exist_ok=True)
        self.config =config
        self.page_fetcher = PageFetcher
        
    def get_manufacturer(self, product_name: str) -> str:
        """
        Ürün adından üreticiyi alır.

        Args:
            product_name (str): Ürün adı.

        Returns:
            str: Üretici adı.
        """
        for key in self.config.manufacturers:
            if key in product_name:
                return self.config.manufacturers[key]
        return product_name.split(" ")[0]

    def get_total_pages(self, soup: bea, site_name: str) -> int:
        """
        Verilen BeautifulSoup nesnesinden toplam sayfa sayısını alır.

        Args:
            soup (BeautifulSoup): Sayfanın BeautifulSoup nesnesi.
            site_name (str): Site adı.

        Returns:
            int: Toplam sayfa sayısı.
        """
        if site_name == "GameGaraj":
            page_number_element = soup.select_one("body > div.edgtf-wrapper > div > div.edgtf-content > div > div.edgtf-container > div > div > div.edgtf-page-content-holder.edgtf-grid-col-9.edgtf-grid-col-push-3 > nav > ul > li:nth-child(2) > a")
            return int(page_number_element.text.strip()) if page_number_element else 1
        elif site_name == "Itopya":
            return int(soup.select_one('body > section.container-fluid > div > div.col-12.col-md-9.col-lg-9.col-xl-10 > div:nth-child(5) > div.actions > span > strong').get_text().strip().split('/')[1]) if soup else 1
        elif site_name == "Sinerji":
            page_links = soup.select("a[href*='?px=']")
            return max(int(link.text) for link in page_links if link.text.isdigit())
        elif site_name == "incehesap":
            page_links = soup.select("body > main > div.container.space-y-5.pb-5 > div.flex.flex-col.xl\\:flex-row.gap-5 > div > div.card.flex.items-center.justify-betweensm\\:px-6 > nav > a")

            if page_links:
                return max(
                    int(link.get('href', '').split('/sayfa-')[-1].strip('/'))
                    for link in page_links
                    if '/sayfa-' in link.get('href', '')
                )
            else:

                return 1

    def extract_products(self, soup: bea, site_name: str) -> list:
        """
        BeautifulSoup nesnesinden ürünleri çıkarır.

        Args:
            soup (BeautifulSoup): Sayfanın BeautifulSoup nesnesi.
            site_name (str): Site adı.

        Returns:
            list: Ürün bilgilerini içeren sözlükler.
        """
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

        elif site_name == "Sinerji":
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
        
        elif site_name == "incehesap":
            products = soup.select('body > main > div.container.space-y-5.pb-5 > div.flex.flex-col.xl\\:flex-row.gap-5 > div > div:nth-child(4) > div.grid.grid-cols-2.md\\:grid-cols-3.gap-1 > a')
            for product in products:
                title_element = product.find('div', class_='line-clamp-2 h-11 text-center leading-tight px-1 lg:px-4 md:space-x-3')
                title = title_element.text.strip() if title_element else "İsim yok"
                product_link = product['href'] if product else "Link yok"
                price_element = product.find('span', class_='mx-auto whitespace-nowrap text-lg font-bold leading-none tracking-tight text-orange-500 md:text-2xl mb-2')
                price = price_element.text.strip() if price_element else "Fiyat yok"
                manufacturer = self.get_manufacturer(title)
                all_products.append({"İsim": title, "Fiyat": price, "Üretici": manufacturer, "Link": product_link})

        return all_products

    def save_to_csv(self, all_products: list, site_name: str, category_name: str) -> None:
        """
        Ürün bilgilerini CSV dosyasına kaydeder.

        Args:
            all_products (list): Ürün bilgilerini içeren sözlükler.
            site_name (str): Site adı.
            category_name (str): Kategori adı.
        """
        df = pd.DataFrame(all_products)
        timestamp_directory = f"{site_name}_{self.formatli_tarih_saat}"
        full_directory = os.path.join(self.main_directory, timestamp_directory)
        os.makedirs(full_directory, exist_ok=True)

        csv_filename = f"{site_name}_{category_name}.csv"
        df.to_csv(os.path.join(full_directory, csv_filename), index=False, encoding='utf-8-sig')
        print(f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi.")

    def scrape_products(self, url: str, category_name: str, site_name: str) -> None:
        """
        Belirtilen URL'den ürünleri çekerek CSV dosyasına kaydeder.

        Args:
            url (str): Ürünlerin çekileceği ana URL.
            category_name (str): Ürünlerin ait olduğu kategori adı.
            site_name (str): Web sitesinin adı.

        Returns:
            None: Bu fonksiyon, çekilen ürünleri CSV dosyasına kaydeder ve geri dönüş değeri yoktur.
        """
        all_products = []
        
        soup = self.page_fetcher.fetch(url)
        if not soup:
            print(f"Sayfa alınamadı: {url}. İşlem durduruluyor.")
            return

        total_pages = self.get_total_pages(soup, site_name)

        for page_num in range(1, total_pages + 1):
            page_url = f"{url}?pg={page_num}"
            soup = self.page_fetcher.fetch(page_url)
            if not soup:
                print(f"Sayfa alınamadı: {page_url}. Atlanıyor.")
                continue
            
            all_products.extend(self.extract_products(soup, site_name))

        self.save_to_csv(all_products, site_name, category_name)

    def run(self):
        with ThreadPoolExecutor() as executor:
            for site_name, site_categories in self.config.links.items():
                executor.map(lambda item: self.scrape_products(item[0], item[1], site_name), site_categories.items())

if __name__ == "__main__":
    config = Config()
    pageFetcher =PageFetcher(config=config)
    scraper = WebScraper(config=config,
                        PageFetcher=pageFetcher)
    scraper.run()
