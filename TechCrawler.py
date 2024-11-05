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
from functools import partial
import re
from tqdm import tqdm
import inspect

cofig_dir_path = "json_data/"

class Config:
    def __init__(self):
        """
        Config sınıfını başlatır ve ayar dosyalarını yükler.
        """
        self.user_agents = self.load_json(f'{cofig_dir_path}user_agents.json')
        self.links = self.load_json(f'{cofig_dir_path}links.json')
        self.manufacturers = self.load_json(f'{cofig_dir_path}manufacturers.json')
        self.error_log= f'{cofig_dir_path}error_log.json'

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
        except FileNotFoundError as e:
            self.save_error_to_json(e)
            return {}
        except json.JSONDecodeError as e :
            self.save_error_to_json(e)
            return {}
            
    def save_error_to_json(self, exception):
        error_info = {
            'error_name': type(exception).__name__,
            'error_message': str(exception),
            'function_name': inspect.currentframe().f_back.f_code.co_name,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(self.error_log, 'a+') as file:
                file.seek(0)  
                try:
                    error_data = json.load(file)
                except (json.JSONDecodeError, ValueError):  
                    error_data = []
                error_data.append(error_info)
                file.seek(0)    
                json.dump(error_data, file, indent=4)
        except Exception as e:
            print(f"Dosya hatası: {e}")

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
                if attempt >= 3:
                    print(f"{attempt + 1}. deneme: {url}")
                response = req.get(url, headers=header, timeout=timeout)
                response.raise_for_status()
                soup = bea(response.text, "html.parser")
                self.cache[url] = soup
                return soup
            
            except Exception as e:
                self.config.save_error_to_json(e)

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
        try:
            for key in self.config.manufacturers:
                if re.search(key, product_name, re.IGNORECASE):
                    return self.config.manufacturers[key]
            
            return product_name.split(" ")[0]
        except Exception as e:
            self.config.save_error_to_json(e)
            return None 
    
    def get_total_pages(self, soup: bea, site_name: str) -> int:
        """
        Verilen BeautifulSoup nesnesinden toplam sayfa sayısını alır.

        Args:
            soup (BeautifulSoup): Sayfanın BeautifulSoup nesnesi.
            site_name (str): Site adı.

        Returns:
            int: Toplam sayfa sayısı ya da 1 
        """
        try:
            if   site_name == "gameGaraj":
                page_number_element = soup.select_one("body > div.edgtf-wrapper > div > div.edgtf-content > div > div.edgtf-container > div > div > div.edgtf-page-content-holder.edgtf-grid-col-9.edgtf-grid-col-push-3 > nav > ul > li:nth-child(2) > a")
                if page_number_element:
                    total_pages = int(page_number_element.text.strip())
                else:
                    total_pages = 1

            elif site_name == "itopya":
                strong_element = soup.select_one('body > section.container-fluid > div > div.col-12.col-md-9.col-lg-9.col-xl-10 > div:nth-child(5) > div.actions > span > strong')
                if strong_element:
                    total_pages_text = strong_element.get_text().strip()
                    total_pages = int(total_pages_text.split('/')[1])
                else:
                    total_pages = 1

            elif site_name == "sinerji":
                page_links = soup.select("a[href*='?px=']")
                total_pages = max(int(link.text) for link in page_links if link.text.isdigit()) if page_links else 1
            
            elif site_name == "incehesap":
                page_links = soup.select("body > main > div.container.space-y-5.pb-5 > div.flex.flex-col.xl\\:flex-row.gap-5 > div > div.card.flex.items-center.justify-betweensm\\:px-6 > nav > a")
                if page_links:
                    total_pages = max(
                        int(link.get('href', '').split('/sayfa-')[-1].strip('/'))
                        for link in page_links
                        if '/sayfa-' in link.get('href', '')
                    )
                else:
                    total_pages = 1
                    
            elif site_name == "teknosa":
                page_links = soup.select_one("#site-main > div > div > div.col-12.section-1 > div > div > div.plp-grid > div.plp-body > div.plp-paging > div.plp-paging-button > button > span")
                if page_links and page_links.text:
                    split_text = page_links.text.split("/")
                    if len(split_text) > 1:
                        total_pages = int(split_text[1].strip().replace(")", "")) - 1
                    else:
                        total_pages = 1
            
            elif site_name == "tebilon":
                page_links =  soup.select_one("#mainPage > main > section.showcase > div > div > div.showcase__showcaseProducts.col-md-12.col-sm-12.col-xs-12.mobileShow > div.col-md-12.productSort__paginationBottom > div > a:nth-child(5)")
                if page_links and page_links.text:
                        total_pages = int(page_links.text)
                else:
                    total_pages = 1
            
            else:
                total_pages = 1
            last_try = total_pages * 3
        except (IndexError, ValueError) as e:
            self.config.save_error_to_json(e)
            total_pages = 1
        if isinstance(total_pages, int):
            return total_pages
        else:
            return 1

    def extract_products(self, soup: bea, site_name: str, tür: str =None) -> list:
        """
        BeautifulSoup nesnesinden ürünleri çıkarır.

        Args:
            soup (BeautifulSoup): Sayfanın BeautifulSoup nesnesi.
            site_name (str): Site adı.

        Returns:
            list: Ürün bilgilerini içeren sözlükler.
        """
        all_products = []
        if   site_name == "gameGaraj":
            products = soup.select("li.product")
            for product in products:
                price_element = product.select_one(".price ins .woocommerce-Price-amount")
                price = price_element.text.strip() if price_element else "Fiyat yok"
                title = product.select_one(".edgtf-product-list-title a").text
                product_link = product.select_one(".edgtf-product-list-title a")["href"]
                manufacturer = self.get_manufacturer(title)
                all_products.append({"isim": title.replace('"','').replace("₺","").strip(), 
                                    "Fiyat": price.replace('"','').replace("₺","").strip(), 
                                    "Üretici": manufacturer.replace('"', '').replace("₺","").strip(), 
                                    "Link": product_link.strip()})

        elif site_name == "itopya":
            for product in soup.select('#productList > div'):
                link_tag = product.select_one('div.product-body > h2 > a')
                if link_tag:
                    product_link = link_tag['href'] if link_tag['href'].startswith("http") else "https://www.itopya.com" + link_tag['href']
                    title = link_tag.get_text().strip()
                    price_tag = product.select_one('div.product-footer > div.price > strong')
                    price = price_tag.get_text().strip().replace('\xa0', '').replace('₺', '').strip() if price_tag else "nan"
                    manufacturer = self.get_manufacturer(title) if price != "nan" else "Bilinmiyor"
                    all_products.append({
                        "isim": title.replace('"','').replace("₺","").strip(), 
                        "Fiyat": price.strip(),
                        "Üretici": manufacturer.replace('"','').replace("₺","").strip(), 
                        "Link": product_link.strip()})

        elif site_name == "sinerji":
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
                price = product.select_one("div.row > div.col > span")
                price = price.text.replace('"', "").replace("₺","")
                product_info = {"isim": product_name.replace('"','').replace("₺","").strip(), 
                                "Fiyat" : price.strip(),
                                "Üretici": manufacturer.replace('"','').replace("₺","").strip() if manufacturer else "Bilinmiyor",
                                "Link": ("https://www.sinerji.gen.tr" + product_link).replace('"','').replace("₺","").strip()}
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
                all_products.append({
                    "isim": title.replace('"','').replace("₺","").strip(), 
                    "Fiyat": price.replace('"','').replace("₺","").strip(),
                    "Üretici": manufacturer.replace('"','').replace("₺","").strip(),
                    "Link": product_link.replace('"','').replace("₺","").strip()})
                
        elif site_name == "teknosa":
            product_list = soup.select("#product-item")
            for product in product_list:
                name_link_manufacturer = product.select_one("a")
                title = name_link_manufacturer.get('title', "isim bulunamadı") if name_link_manufacturer else "isim bulunamadı"
                product_link = name_link_manufacturer['href'] if name_link_manufacturer and name_link_manufacturer['href'].startswith("http") else "https://www.teknosa.com" + name_link_manufacturer['href'] if name_link_manufacturer else "Link bulunamadı"
                price = product.select_one("input").get('value', "Fiyat bulunamadı") if product.select_one("input") else "Fiyat bulunamadı"
                manufacturer = title.split()[0] if title != "isim bulunamadı" else "bulunamadı"
                all_products.append({
                    "isim": title.replace('"','').replace("₺","").strip(), 
                    "Fiyat": price.replace('"','').replace("₺","").strip(),
                    "Üretici": manufacturer.replace('"','').replace("₺","").strip(),
                    "Link": product_link.replace('"','').replace("₺","").strip()})
                
        elif site_name =="tebilon":
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
                    "isim": title.replace('"','').replace("₺","").strip(),
                    "Fiyat": price.replace('"','').replace("₺","").strip(),
                    "Üretici": manufacturer.replace('"','').replace("₺","").strip(),
                    "Link": product_link.replace('"','').replace("₺","").strip()
                })
                            
        return all_products

    def save_to_csv(self, all_products: list, site_name: str, category_name: str) -> None:
        """
        Ürün bilgilerini CSV dosyasına kaydeder.

        Args:
            all_products (list): Ürün bilgilerini içeren sözlükler.
            site_name (str): Site adı.
            category_name (str): Kategori adı.

        Returns:
            str: CSV dosyasına kaydedilen ürün sayısını belirten bir mesaj.
        """
        try:
            if not all_products:
                return f"{site_name}_{category_name}.csv için kaydedilecek ürün bulunamadı. Hiçbir veri yazılmadı."

            df = pd.DataFrame(all_products)
            timestamp_directory = f"{site_name}_{self.formatli_tarih_saat}"
            full_directory = os.path.join(self.main_directory, timestamp_directory)
            os.makedirs(full_directory, exist_ok=True)

            csv_filename = f"{site_name}_{category_name}.csv"
            df.to_csv(os.path.join(full_directory, csv_filename), index=False, encoding='utf-8-sig')
            message = f"{len(all_products)} {category_name} bilgisi '{csv_filename}' dosyasına kaydedildi."
            return message
        except Exception as e:
            self.config.save_error_to_json(e)

    def scrape_products(self, url: str, category_name: str, site_name: str) -> None:
        """
        Belirtilen URL'den ürünleri çekerek CSV dosyasına kaydeder.

        Args:
            url (str): Ürünlerin çekileceği ana URL.
            category_name (str): Ürünlerin ait olduğu kategori adı.
            site_name (str): Web sitesinin adı.

        Returns:
            tuple: Çekilen tüm ürünler, site adı ve kategori adı.
        """
        all_products = []

        try:
            soup = self.page_fetcher.fetch(url)
            if not soup:
                return
            
            total_pages =int( self.get_total_pages(soup, site_name) )

            for page_num in range(1, total_pages + 1):
                if page_num == 1:
                    page_url = f"{url}"
                else:
                    if site_name == "tebilon" or site_name == "teknosa":
                        page_url = f"{url}?page={page_num}"
                    elif site_name == "sinerji":
                        page_url = f"{url}?px={page_num}"
                    elif site_name == "itopta":
                        page_url = f"{url}?pg={page_num}"
                    elif site_name == "gamegaraj":
                        page_url = f"{url}/page/{page_num}/"
                        
                soup = self.page_fetcher.fetch(page_url)
                if not soup:
                    continue  

                all_products.extend(self.extract_products(soup, site_name))

            return all_products, site_name, category_name
        except Exception as e:
            self.config.save_error_to_json(e)

    def scrape_and_log(self, url_category_pair, site_name):
        """
        Verilen URL ve kategori çiftini kullanarak ürünleri çeker ve verileri CSV dosyasına kaydeder.

        Bu metod, belirtilen URL'den ürünleri almak için `scrape_products` fonksiyonunu çağırır
        ve elde edilen ürün verilerini belirtilen site ve kategori adıyla birlikte bir CSV dosyasına
        kaydeder. Hata durumunda, hata kaydedilir ve kullanıcıya bilgi verilir.

        Args:
            url_category_pair (tuple): URL ve kategori çiftini içeren bir tuple.
            site_name (str): Ürünlerin çekileceği site adı.
        """
        try:
            url, category = url_category_pair
            all_products, site_name, category_name = self.scrape_products(url, category, site_name)
            self.save_to_csv(all_products, site_name, category_name)
        except Exception as e:
            self.config.save_error_to_json(e)

    def run(self):
        """
        Çoklu iş parçacığı kullanarak web scraping işlemini gerçekleştirir. 

        Bu metod, tüm bağlantıları ve kategorileri içeren bir yapıdan yararlanarak
        verileri çekmek için bir iş parçacığı havuzu oluşturur. Her kategori için
        bir iş parçacığı başlatılır ve işlemin ilerleyişi bir çubuk ile gösterilir. 
        İşlem tamamlandığında toplam süre hesaplanır. 

        Hata durumunda, tüm hatalar tek bir try-except bloğunda yakalanarak
        kaydedilir ve kullanıcıya bilgi verilir.
        """
        try:
            start_time = time.time()
            max_workers = os.cpu_count() * 2
            total_tasks = sum(len(categories) for site, categories in self.config.links.items())
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                with tqdm(total=total_tasks, desc="İlerleme", unit="kategori") as pbar:
                    for site_name, site_categories in self.config.links.items():
                        for category_pair in site_categories.items():
                            future = executor.submit(self.scrape_and_log, category_pair, site_name.lower().strip())
                            future.add_done_callback(lambda _: pbar.update(1)) 
                            futures.append(future)

                    for future in futures:
                        future.result()

            print(f"Toplam süre: {((time.time()) - start_time):.2f} saniye")
            
        except Exception as e:
            self.config.save_error_to_json(e)

if __name__ == "__main__":
    config = Config()
    page_fetcher = PageFetcher(config=config)
    scraper = WebScraper(config=config, PageFetcher=page_fetcher)
    scraper.run()

