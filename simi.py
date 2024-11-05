import os
import pandas as pd
from rapidfuzz import process
from rapidfuzz import fuzz

dosya1 = "Site_Data_11-05_06/Sinerji_11-05_06/Sinerji_cpu.csv"
dosya2 = "Site_Data_11-05_06/Itopya_11-05_06/Itopya_cpu.csv"

df1 = pd.read_csv(dosya1)
df2 = pd.read_csv(dosya2)

d1_kolon = df1.keys().to_list()
d2_kolon = df2.keys().to_list()

print(d1_kolon)
print(d2_kolon)

d1_isim = d1_kolon[0]
d2_isim = d2_kolon[0]

for index, row in df1.iterrows():
    name1 = row[d1_isim]
    for index2, row2 in df2.iterrows():
        name2 = row2[d2_isim]
        deneme = fuzz.ratio(name1, name2)
        if deneme > 80:
            print(f"{name1} ile {name2} arasındaki benzerlik: {deneme}")
