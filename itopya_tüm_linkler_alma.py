import requests
from bs4 import BeautifulSoup
import json
import os

url = "https://www.tebilon.com/bilgisayar-parcalari/"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
data = {}
cofig_dir_path = "json_data/"

categories = soup.select('#filterMobile > div:nth-child(3) > div')

for categori in categories:
    name_and_links = categori.select("div > strong > div")
    for items in name_and_links:
        link_item = items.select_one("a")
        if link_item:
            site_link = link_item.get('href', "Link bulunamadı")
            site_name = link_item.text.strip()
            data[site_name] = site_link 


with open(f'{cofig_dir_path}tebilon_tüm_linkler.json', 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

print("JSON dosyasına kaydedildi.")
