import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.itopya.com/HazirSistemler'

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
data = {}
cofig_dir_path = "json_data/"

categories = soup.select('a[href^="/"]')
exclude_keywords = ['blog', 'HAKKIMIZDA', 'mağazalarımız', 'kendin topla']

for category in categories:
    span_tag = category.find('span', class_='text')
    if span_tag:
        product_name = span_tag.text.strip()
        product_link = category['href']

        if len(product_name.split()) > 2:
            continue

        if any(keyword.upper() in product_name.upper() for keyword in exclude_keywords):
            continue

        full_product_link = 'https://www.itopya.com' + product_link
        data[full_product_link] = product_name


with open(f'{cofig_dir_path}itopya_tüm_linkler.json', 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

print("JSON dosyasına kaydedildi.")
