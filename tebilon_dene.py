import requests as req
from bs4 import BeautifulSoup as bea
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.tebilon.com/bilgisayar-parcalari/anakart/'
#allProducts > div > div:nth-child(17)
#allProducts > div > div:nth-child(17) > div > div > div > div.showcase__image.text-center.col-md-12.no-padding
#allProducts > div > div:nth-child(17) > div > div > div > div.showcase__image.text-center.col-md-12.no-padding > a:nth-child(2)
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

result = soup
result = result.select("#allProducts > div > div")

# print(result)
for res in result:
    main_name = res.select_one("div > div > div > div > a").find('a')

    if main_name:
        print(main_name)