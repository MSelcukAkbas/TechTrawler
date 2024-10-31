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
from multi_scraping import WebScraper
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
    def __init__(self, config: Config, retries: int = 3, delay: int = 1):
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

    def fetch(self, url: str, timeout: int = 10) -> bea:
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
    

config = Config()
pageFetcher =PageFetcher(config=config)
result = pageFetcher.fetch("https://www.incehesap.com/islemci-fiyatlari/")
sa=WebScraper(config=config , PageFetcher=pageFetcher)




product_elements = result.select('body > main > div.container.space-y-5.pb-5 > div.flex.flex-col.xl\\:flex-row.gap-5 > div > div:nth-child(4) > div.grid.grid-cols-2.md\\:grid-cols-3.gap-1 > a')
all_products = []
for product_element in product_elements:
    title = product_element.find('div', class_='line-clamp-2 h-11 text-center leading-tight px-1 lg:px-4 md:space-x-3').text.strip()
    product_link = product_element['href']
    
    price_element = product_element.find('span', class_='mx-auto whitespace-nowrap text-lg font-bold leading-none tracking-tight text-orange-500 md:text-2xl mb-2')
    price = price_element.text.strip() if price_element else 'Fiyat bulunamadı'
    manufacturer =sa.get_manufacturer(product_name=title)
    all_products.append({"İsim": title, "Fiyat": price, "Üretici": manufacturer, "Link": product_link})
print(all_products)