"""Çağrıyı aynı şirketin fiyat serisine bağlar.

Anahtar: ticker (MAEC klasör adı = FNSPID dosya adı) + çağrı tarihi -> olay günü t0.
Her eşleşen çağrı için t0'a göre hizalı bir fiyat penceresi kesilir (gün = t0'a göre işlem günü sırası):
  girdi : gün -60 .. -1 getirileri (60 getiri için gün -61 .. -1 fiyatları gerekir)
  hedef : gün 0 .. +6 getirileri (çağrı günü dahil 7 işlem günü)
Girdi gün -1 kapanışında biter, hedef gün 0'dan başlar: aynı gün iki tarafta birden yer almaz.
Çağrı açılıştan önce (BMO) ise tepki gün 0'da, kapanıştan sonra (AMC) ise gün +1'de görülür; ikisi de hedefe girer.
Sınırlılık: AMC çağrılarında gün 0 getirisi çağrıdan önceki saatleri de içerir.
"""
import numpy as np
import pandas as pd

from src.veri import fiyat_oku

GECMIS = 60          # girdi: t0'dan önceki işlem günü sayısı
HEDEF_SON = 6        # hedef: gün 0 .. +6
GOSTERIM_SON = 10    # olay grafiği için pencere +10'a kadar kesilir (varsa); eşleşme şartı değildir
MAKS_ARA = 5         # çağrı tarihi ile t0 arasında izin verilen en fazla takvim günü


def t0_bul(tarihler, cagri_tarihi):
    """Çağrı tarihine eşit ya da ondan sonraki ilk işlem gününün sırası; 5 takvim gününden uzaksa None."""
    i = int(tarihler.searchsorted(cagri_tarihi))
    if i >= len(tarihler) or (tarihler[i] - cagri_tarihi).days > MAKS_ARA:
        return None
    return i


def cagri_eslestir(klasor, ticker, tarih, fiyat_yollari):
    """Bir çağrıyı eşleştirir. (durum, pencere, onceki_gun) döner.

    durum: 'eslesti' ya da düşme nedeni; onceki_gun: fiyat dosyasında t0'dan önceki işlem günü sayısı.
    """
    if ticker not in fiyat_yollari:
        return "ticker fiyat verisinde yok", None, None
    p = fiyat_oku(fiyat_yollari[ticker])
    if p is None or p.empty:
        return "fiyat dosyası boş", None, None
    p = p.dropna(subset=["adj close"])
    p = p[p["adj close"] > 0].reset_index(drop=True)
    if not p["date"].iloc[0] <= tarih <= p["date"].iloc[-1]:
        return "fiyat serisi çağrı tarihini kapsamıyor", None, None
    i = t0_bul(pd.DatetimeIndex(p["date"]), pd.Timestamp(tarih))
    if i is None:
        return "çağrıdan sonra 5 gün içinde işlem günü yok", None, None
    if i - (GECMIS + 1) < 0:
        return "60 günlük geçmiş yetersiz", None, i
    if i + HEDEF_SON >= len(p):
        return "7 günlük gelecek yetersiz", None, i
    son = min(i + GOSTERIM_SON, len(p) - 1)
    w = p.iloc[i - (GECMIS + 1): son + 1].copy()
    w.insert(0, "gun", np.arange(-(GECMIS + 1), son - i + 1))
    w.insert(0, "klasor", klasor)
    w["getiri"] = np.log(w["adj close"]).diff()   # log getiri; gün -61'de tanımsız (NaN)
    return "eslesti", w, i


def tumunu_eslestir(cagrilar, fiyat_yollari):
    """Tüm çağrılar için durum tablosu ve uzun biçimde (her satır bir gün) pencere tablosu döndürür."""
    durumlar, pencereler = [], []
    for c in cagrilar.itertuples():
        durum, w, onceki = cagri_eslestir(c.klasor, c.ticker, c.tarih, fiyat_yollari)
        satir = {"klasor": c.klasor, "durum": durum, "t0_oncesi_gun": onceki}
        if w is not None:
            satir["t0"] = w.loc[w.gun == 0, "date"].iloc[0]
            pencereler.append(w)
        durumlar.append(satir)
    return pd.DataFrame(durumlar), pd.concat(pencereler, ignore_index=True)
