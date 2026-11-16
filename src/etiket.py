"""Hedef etiket: çağrı günü dahil 7 işlem gününün (gün 0..+6) oynaklığı ve 3 sınıf.

Oynaklık v = ln( std(r_0 .. r_+6) ), r = günlük log getiri, std paydası 7 (ddof=0).
Literatüre yakın ama birebir aynı değil: Qin ve Yang (2019) takvim günü ve basit getiri kullanır.
Sınıflar: eğitim kısmındaki v'nin 1/3 ve 2/3 kantilleri eşik; 0 = düşük, 1 = orta, 2 = yüksek.
"""
import numpy as np

SINIF_ADLARI = ["düşük", "orta", "yüksek"]


def oynaklik(getiriler):
    """Getirilerin standart sapmasının logaritması. Eksik getiri varsa ya da hepsi aynıysa NaN."""
    r = np.asarray(getiriler, dtype=float)
    if np.isnan(r).any():
        return np.nan
    s = r.std()
    return np.log(s) if s > 0 else np.nan


def hedef_oynaklik(pencereler):
    """Her çağrı için hedef oynaklık (gün 0..+6 getirileri). Sonuç: klasor -> v."""
    hedef = pencereler[pencereler.gun.between(0, 6)]
    return hedef.groupby("klasor")["getiri"].apply(oynaklik)


def esikler(v_egitim):
    """Yalnız eğitim örneklerinden 1/3 ve 2/3 kantilleri."""
    return np.nanquantile(v_egitim, [1 / 3, 2 / 3])


def siniflandir(v, esik):
    """v <= e1 -> 0, e1 < v <= e2 -> 1, v > e2 -> 2. Tanımsız v (NaN) için NaN."""
    v = np.asarray(v, dtype=float)
    s = np.where(v <= esik[0], 0.0, np.where(v <= esik[1], 1.0, 2.0))
    s[np.isnan(v)] = np.nan
    return s
