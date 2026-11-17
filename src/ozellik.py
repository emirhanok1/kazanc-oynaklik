"""Keşifsel analiz ve taban modeller için özet özellikler.

Bunlar modelin asıl girdisi DEĞİLDİR: final modelinde fiyat modalitesi 60 x 3 diziyi, metin modalitesi metnin kendisini
okur. Özet özellikler, iki modalitenin hedefle ve birbiriyle ilişkisini ölçmek için kullanılır.
Her özellik yalnız çağrı anında bilinen bilgiden hesaplanır; tek istisna piyasa_oynakligi_hedef'tir ve yalnız
karıştırıcı etki analizinde kullanılır (açıkça işaretli).
"""
import re

import numpy as np
import pandas as pd

from src.veri import KOK

LM_DOSYA = KOK / "veri" / "ham" / "lm_master.csv"
LM_KATEGORI = {"Negative": "olumsuz", "Positive": "olumlu", "Uncertainty": "belirsizlik", "Litigious": "hukuki",
               "Constraining": "kisitlayici", "Weak_Modal": "zayif_kip", "Strong_Modal": "guclu_kip"}
KELIME = re.compile(r"[a-z]+")
SAYI = re.compile(r"\$?\d[\d,.]*%?")


def lm_sozluk():
    """Loughran-McDonald kategorileri: kategori adı -> küçük harfli kelime kümesi.
    Sütun değeri kelimenin kategoriye eklendiği yıldır; yalnız pozitif değerliler alınır
    (negatif değerli 19 kelime, ör. GREAT = -2020, kategoride sayılmaz)."""
    d = pd.read_csv(LM_DOSYA, usecols=["Word"] + list(LM_KATEGORI), keep_default_na=False)
    return {ad: set(d.loc[d[k] > 0, "Word"].str.lower()) for k, ad in LM_KATEGORI.items()}


def metin_ozellikleri(cumle_listeleri, sozluk):
    """Her çağrı için: kelime ve cümle sayısı, LM kategorilerinin 1000 kelimedeki sıklığı,
    net ton = (olumlu - olumsuz) / (olumlu + olumsuz), 1000 kelimedeki sayısal ifade sayısı."""
    satirlar = []
    for cumleler in cumle_listeleri:
        metin = " ".join(cumleler)
        kelimeler = KELIME.findall(metin.lower().replace("[name]", " ").replace("[url]", " "))
        n = max(len(kelimeler), 1)
        r = {"n_kelime": len(kelimeler), "n_cumle": len(cumleler)}
        for ad, kume in sozluk.items():
            r[ad] = 1000 * sum(k in kume for k in kelimeler) / n
        toplam = r["olumlu"] + r["olumsuz"]
        r["net_ton"] = (r["olumlu"] - r["olumsuz"]) / toplam if toplam > 0 else 0.0
        r["sayisal"] = 1000 * len(SAYI.findall(metin)) / n
        satirlar.append(r)
    return pd.DataFrame(satirlar)


def fiyat_ozet(X):
    """60 x 3 girdi dizisinden (getiri, göreli log hacim, günlük aralık) özet özellikler; yalnız gün -60..-1."""
    r, hacim, aralik = X[:, :, 0], X[:, :, 1], X[:, :, 2]
    return pd.DataFrame({
        "gecmis_oyn_60": np.log(r.std(axis=1)),               # hedefle aynı dönüşüm: ln(std)
        "gecmis_oyn_5": np.log(r[:, -5:].std(axis=1) + 1e-6),  # son 5 gün (çok kısa pencere; sıfıra karşı küçük pay)
        "aralik_ort": np.log(aralik.mean(axis=1)),            # ortalama gün içi aralığın logu
        "hacim_son5": hacim[:, -5:].mean(axis=1),             # çağrı öncesi 5 günde olağandışı işlem
        "getiri_60": r.sum(axis=1),                           # 60 günlük toplam log getiri
    })


def piyasa_oynakligi(spy, t0_tarihleri, bas, son):
    """SPY günlük log getirilerinden, her çağrının t0'ına göre [bas, son] işlem günü penceresinde ln(std).
    bas/son t0'a göre gün sırasıdır (ör. -20, -1 = çağrıdan önceki 20 gün)."""
    s = spy.sort_values("date").reset_index(drop=True)
    r = np.log(s["adj close"]).diff().to_numpy()
    tarih = s["date"].to_numpy()
    sonuc = []
    for t0 in pd.to_datetime(t0_tarihleri).to_numpy():
        i = int(np.searchsorted(tarih, t0))
        sonuc.append(np.log(np.nanstd(r[i + bas: i + son + 1])))
    return np.array(sonuc)
