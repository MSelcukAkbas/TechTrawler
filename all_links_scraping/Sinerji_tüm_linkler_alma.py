import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.sinerji.gen.tr/'

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
data = {}
cofig_dir_path = "json_data/"

categories = soup.select('#Header > div.container-fluid.mainBar > div > div.categories.col-auto > nav > ul > li')

for category in categories:
    main_link = category.find('a')
    if main_link:
        main_name = main_link.get_text(strip=True)
        main_href = main_link['href']
        main_full_url = f"https://www.sinerji.gen.tr{main_href}"
        data[main_full_url] = main_name  

        sub_divs = category.find_all('div')
        for sub_div in sub_divs:
            sub_categories = sub_div.find_all('a')
            for sub_category in sub_categories:
                sub_name = sub_category.get_text(strip=True)
                sub_href = sub_category['href'] 
                sub_full_url = f"https://www.sinerji.gen.tr{sub_href}"
                data[sub_full_url] = sub_name

with open(f'{cofig_dir_path}sinerji_tüm_linkler.json', 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

print("JSON dosyasına kaydedildi.")
