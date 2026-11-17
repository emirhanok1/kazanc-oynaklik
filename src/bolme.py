"""Faz 4: veri bölme. Test dönemi ayrılır, geliştirme dönemi içinde iki doğrulama düzeni kurulur.

- Geliştirme (D): çağrı tarihi <= 2016-12-31. Model seçimi yalnız burada yapılır.
- Test (T): 2017-01-01 ve sonrası. Finalde bir kez açılır; hedefleri yalnız sayılır.
- Şirket katları: D içinde sınıf oranı korunan, şirkete göre gruplu 5 kat (StratifiedGroupKFold).
  Bir şirketin bütün çağrıları aynı kattadır -> doğrulama "yeni şirket" genellemesini ölçer.
- İleri (zaman) katları: D içinde genişleyen pencere; her adımda bir sonraki çeyrek doğrulanır.
  Eğitimden, hedef penceresi doğrulama başlangıcına taşan çağrılar atılır (arındırma).
Etiket eşikleri her katta YALNIZ o katın eğitim kısmından hesaplanır (src.etiket.esikler).
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from src import etiket

GELISTIRME_SONU = pd.Timestamp("2016-12-31")
KAT_SAYISI = 5
TOHUM = 0


def hedef_bitisleri(pencere):
    """Her çağrı için hedef penceresinin son günü (gün +6) tarihi: klasor -> tarih."""
    return pencere[pencere.gun == 6].set_index("klasor")["date"]


def bolme_tablosu(cagrilar, pencere):
    """cagrilar: klasor, tarih, t0, ticker, v, sinif sütunlu tablo (Faz 2 çıktısı).
    Dönüş: her çağrı için bolum ('gelistirme'/'test'/'arindirildi'), kat (0..4, yalnız D), ileri_kat (0..3 doğrulama
    çeyreği, D içinde), hedef_bitis."""
    b = cagrilar[["klasor", "tarih", "t0", "ticker", "v"]].copy().reset_index(drop=True)
    b["hedef_bitis"] = b.klasor.map(hedef_bitisleri(pencere))
    test_bas = b.loc[b.tarih > GELISTIRME_SONU, "t0"].min()
    b["bolum"] = np.where(b.tarih > GELISTIRME_SONU, "test", "gelistirme")
    # Arındırma: hedef penceresi test döneminin ilk çağrı gününe ulaşan geliştirme çağrıları
    b.loc[(b.bolum == "gelistirme") & (b.hedef_bitis >= test_bas), "bolum"] = "arindirildi"
    D = b.bolum == "gelistirme"
    # Şirket katları: sınıf oranı D'nin kendi eşikleriyle korunur (katlar içindeki asıl eşikler ayrıca hesaplanır)
    sinif_D = etiket.siniflandir(b.loc[D, "v"], etiket.esikler(b.loc[D, "v"])).astype(int)
    b["kat"] = -1
    skf = StratifiedGroupKFold(n_splits=KAT_SAYISI, shuffle=True, random_state=TOHUM)
    idx = np.where(D)[0]
    for k, (_, dogrulama) in enumerate(skf.split(idx, sinif_D, groups=b.loc[D, "ticker"])):
        b.loc[idx[dogrulama], "kat"] = k
    # İleri katlar: 2016'nın her çeyreği bir kez doğrulama olur; eğitim = ondan önceki her şey
    b["ceyrek"] = b.tarih.dt.to_period("Q").astype(str)
    b["ileri_kat"] = -1
    for k, q in enumerate(["2016Q1", "2016Q2", "2016Q3", "2016Q4"]):
        b.loc[D & (b.ceyrek == q), "ileri_kat"] = k
    return b


def sirket_kati(b, k):
    """k. şirket katı için (eğitim maskesi, doğrulama maskesi); yalnız geliştirme çağrıları."""
    D = b.bolum == "gelistirme"
    return D & (b.kat != k), D & (b.kat == k)


def ileri_kat(b, k):
    """k. ileri kat için (eğitim maskesi, doğrulama maskesi). Eğitim: doğrulama çeyreğinden önceki çağrılar;
    hedef penceresi doğrulamanın ilk gününe ulaşanlar eğitimden atılır (arındırma)."""
    D = b.bolum == "gelistirme"
    dog = D & (b.ileri_kat == k)
    assert dog.any(), f"ileri kat {k} boş"
    bas = b.loc[dog, "t0"].min()
    egit = D & (b.t0 < bas) & (b.hedef_bitis < bas)
    return egit, dog


def kat_etiketleri(b, egit, maske):
    """Eşikler yalnız eğitim maskesindeki v'lerden; maske içindeki çağrıların sınıfı döner."""
    assert not b.loc[egit | maske, "v"].isna().any(), "hedefi tanımsız çağrı var"
    esik = etiket.esikler(b.loc[egit, "v"])
    return etiket.siniflandir(b.loc[maske, "v"], esik).astype(int), esik
