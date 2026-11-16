"""Faz 2: metin temizliği ve fiyat serisinin model girdisine dönüştürülmesi.

Metin: yalnız biçim gürültüsü temizlenir (dökümcü notları, tipografik karakterler, URL, HTML varlıkları);
büyük/küçük harf, noktalama ve durak kelimeler KORUNUR, çünkü bu kararlar kullanılacak modele bağlıdır.
Fiyat: modele fiyat ya da hacim DÜZEYİ verilmez (düzeltilmiş fiyat sonradan gelen temettü/bölünmelere göre
geriye dönük değişir); yalnız gün -60..-1 penceresinden ölçekten bağımsız üç kanal üretilir.
"""
import html
import re

import numpy as np

MIN_KELIME = 20   # bu sayıya kadar (dahil) kelimeli metin içeriksiz sayılır: incelenen örneklerin hepsi selamlaşma/kapanış

NOTLAR = re.compile(r"[\[\(]\s*(?:indiscernible|inaudible|ph|sic|laughter|crosstalk|technical difficult(?:y|ies)|audio gap)"
                    r"[^\]\)]{0,30}[\]\)]", re.I)                      # [indiscernible], (ph), [laughter] ...
KOSELI = re.compile(r"\[(?!NAME\]|URL\])([^\]\[]{1,40})\]")              # [million] gibi dökümcü eklemeleri
URL = re.compile(r"(?:https?://|www\.)\S+", re.I)
UNK = re.compile(r"<UNK>")
TIPOGRAFIK_KARAKTER = re.compile("[’‘“”–—…•]")
HTML_VARLIGI = re.compile(r"&[a-z]+;")
TIPOGRAFIK = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "•": " "})

KALIPLAR = {
    "dökümcü notu ([indiscernible], (ph) …)": NOTLAR,
    "köşeli parantezli ekleme ([million] …)": KOSELI,
    "URL": URL,
    "<UNK> (gizlenmiş kişi adı)": UNK,
    "tipografik karakter (’ – … •)": TIPOGRAFIK_KARAKTER,
    "HTML varlığı (&amp; …)": HTML_VARLIGI,
}


def cumle_temizle(s):
    """Tek cümle: HTML varlığı ve tipografik karakter → düz karşılık; dökümcü notu silinir;
    [million] → million; URL → [URL]; <UNK> → [NAME]; fazla boşluk tekilleştirilir."""
    s = html.unescape(s).translate(TIPOGRAFIK)
    s = NOTLAR.sub(" ", s)
    s = KOSELI.sub(r"\1", s)
    s = URL.sub(" [URL] ", s)
    s = UNK.sub("[NAME]", s)
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)        # silinen nottan kalan "growth ." → "growth."
    return re.sub(r"\s+", " ", s).strip()


def metin_temizle(cumleler):
    """Cümle listesini temizler; temizlik sonrası boş kalan cümleler atılır."""
    return [c for c in (cumle_temizle(x) for x in cumleler) if c]


def kalip_say(metinler):
    """Her gürültü kalıbı için: kaç metinde geçtiği ve toplam kaç kez geçtiği."""
    sonuc = {}
    for ad, desen in KALIPLAR.items():
        sayilar = [len(desen.findall(t)) for t in metinler]
        sonuc[ad] = {"metin": sum(s > 0 for s in sayilar), "toplam": sum(sayilar)}
    return sonuc


KANALLAR = ["getiri", "goreli_log_hacim", "gunluk_aralik"]


def seri_girdisi(pencere):
    """Her çağrı için 60 x 3 girdi dizisi (yalnız gün -60..-1):
    getiri           = ln(P_t / P_t-1), P = düzeltilmiş kapanış
    goreli_log_hacim = ln(hacim_t) - aynı penceredeki ln(hacim) ortalaması
    gunluk_aralik    = ln(yüksek_t / düşük_t) (aynı günün oranı; düzeltmeden etkilenmez)
    Dönüş: (X [N, 60, 3], klasor sırası)."""
    g = pencere[pencere.gun.between(-60, -1)].sort_values(["klasor", "gun"])
    log_hacim = np.log(g["volume"].clip(lower=1))
    g = g.assign(goreli_log_hacim=log_hacim - log_hacim.groupby(g["klasor"]).transform("mean"),
                 gunluk_aralik=np.log(g["high"] / g["low"]))
    adlar = g["klasor"].unique()
    assert len(g) == 60 * len(adlar), "her çağrı için tam 60 gün olmalı"
    return g[KANALLAR].to_numpy().reshape(len(adlar), 60, len(KANALLAR)), adlar
