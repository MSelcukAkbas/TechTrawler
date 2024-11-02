import requests as req
from bs4 import BeautifulSoup as bea
import pandas as pd

url = "https://www.cimri.com/ekran-kartlari"
respons = req.get(url=url)
sonuc = bea(respons.content, "html.parser")
parser_result = sonuc.select("#productListContainer > div")

site_names = []
site_prices = []
product_names = []
links = []

parser_result2= sonuc.select_one("#opacityLoadingWrapper > div.Head_head__EOVv7.Head_withBorder__ld2fz > div.Head_titleContainer__ZLRC5 > div.Head_subTitle__9GV_l > span.Head_numFound__mVmsR")
max_page=int(parser_result2.text.split()[1])

for i in range(1,(max_page // 32)):

    if i ==1:
        url = "https://www.cimri.com/ekran-kartlari"
    else:
        url = f"https://www.cimri.com/ekran-kartlari?page={i}"
        
    respons = req.get(url=url)
    sonuc = bea(respons.content, "html.parser")
    parser_result = sonuc.select("#productListContainer > div")

    for result in parser_result:
        ürün_adı_main = result.select("article > a > div > h3")
        for ürün_adı in ürün_adı_main:
            if ürün_adı:
                ürün_adı_text = ürün_adı.text.strip()  
                href = ürün_adı.find_parent('a')['href']


                product_names.append(ürün_adı_text) 
                links.append(href)


    for result in parser_result:
        siteler_div = result.select("article > div > div")
        for site in siteler_div:
            site_img = site.select_one("div > div > div > img")
            site_price = site.select_one("div > div > p")

            site_name = site_img.get('alt') if site_img else 'N/A'
            site_fiyat = site_price.text.strip() if site_price else 'N/A'


            site_names.append(site_name)
            site_prices.append(site_fiyat)


    df = pd.DataFrame({
        "site_name": site_names,
        "price": site_prices,
        "product_name": product_names,
        "link": links
    })

    df.to_csv("ekran_kartlari.csv", index=False)
