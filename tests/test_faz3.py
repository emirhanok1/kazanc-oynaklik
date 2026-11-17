"""Faz 3 (keşifsel analiz) testleri: notebook çıktıları bağımsız yeniden hesaplamayla karşılaştırılır,
istatistik fonksiyonları bilinen sonuçlu yapay veriyle sınanır, sızıntı kuralları kontrol edilir.

Çalıştırma (proje kökünden, 01–03 notebook'ları çalıştırıldıktan sonra):  python -m pytest tests -q
"""
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from src import ozellik, temizle, veri  # noqa: E402
from src.istatistik import kismi, kw, metin_komsulari, sirket_ornekleri  # noqa: E402

ISL, CIK, SEK = KOK / "veri" / "islenmis", KOK / "cikti", KOK / "sekiller"


@pytest.fixture(scope="module")
def eda():
    return pd.read_parquet(ISL / "eda_tablosu.parquet")


@pytest.fixture(scope="module")
def temiz():
    return pd.read_parquet(ISL / "temiz_cagrilar.parquet").set_index("klasor")


@pytest.fixture(scope="module")
def pencere():
    return pd.read_parquet(ISL / "fiyat_pencereleri.parquet")


# ---------------------------------------------------------------- veri ve sızıntı
def test_yalniz_egitim_donemi(eda):
    assert eda.tarih.max() <= pd.Timestamp("2016-12-31")
    assert len(eda) == 1866
    assert eda.sinif.value_counts().to_dict() == {0: 622, 1: 622, 2: 622}


def test_ozellikler_hedef_penceresine_dokunmuyor(pencere):
    """Gün 0..+10 verisi bozulsa bile model girdisi (60 x 3) ve özet fiyat özellikleri değişmemeli."""
    ornek = pencere[pencere.klasor.isin(pencere.klasor.unique()[:200])]
    X1, _ = temizle.seri_girdisi(ornek)
    bozuk = ornek.copy()
    gelecek = bozuk.gun >= 0
    for s in ["adj close", "close", "high", "low", "volume", "getiri"]:
        bozuk.loc[gelecek, s] = bozuk.loc[gelecek, s] * 7.0
    X2, _ = temizle.seri_girdisi(bozuk)
    assert np.array_equal(X1, X2)
    pd.testing.assert_frame_equal(ozellik.fiyat_ozet(X1), ozellik.fiyat_ozet(X2))


def test_piyasa_once_cagri_gunu_haric():
    """piyasa_once = SPY'nin t0'dan önceki 20 işlem günü; elle hesaplanan değerle aynı olmalı."""
    spy = veri.fiyat_oku(veri.fiyat_dosyalari()["SPY"]).sort_values("date")
    r = np.log(spy.set_index("date")["adj close"]).diff()
    for t0 in pd.to_datetime(["2015-04-21", "2016-02-11", "2016-11-09"]):
        elle = np.log(r[r.index < t0].tail(20).std(ddof=0))
        assert ozellik.piyasa_oynakligi(spy, [t0], -20, -1)[0] == pytest.approx(elle, abs=1e-9)
        icerir = np.log(r[r.index <= t0].tail(20).std(ddof=0))
        assert not np.isclose(elle, icerir)


# ---------------------------------------------------------------- özelliklerin bağımsız yeniden hesabı
def test_gecmis_oynaklik_ham_fiyattan(eda, pencere):
    p = pencere[pencere.klasor.isin(eda.klasor) & pencere.gun.between(-61, -1)].sort_values(["klasor", "gun"])
    elle = p.groupby("klasor")["adj close"].apply(lambda s: np.log(np.log(s.to_numpy()[1:] / s.to_numpy()[:-1]).std()))
    aralik = p[p.gun >= -60].groupby("klasor").apply(lambda g: np.log(np.log(g.high / g.low).mean()))
    t = eda.set_index("klasor")
    assert np.allclose(t.loc[elle.index, "gecmis_oyn_60"], elle, atol=1e-4)
    assert np.allclose(t.loc[aralik.index, "aralik_ort"], aralik, atol=1e-4)


def test_sozluk_sayimi_bagimsiz(eda, temiz):
    sozluk = ozellik.lm_sozluk()
    t = eda.set_index("klasor")
    for k in t.index[[0, 500, 1000, 1500, 1865]]:
        kelimeler = re.findall(r"[a-z]+", " ".join(temiz.loc[k, "cumleler_temiz"]).lower().replace("[name]", " ").replace("[url]", " "))
        say = Counter(kelimeler)
        for kat in ["belirsizlik", "olumsuz", "olumlu"]:
            beklenen = 1000 * sum(n for w, n in say.items() if w in sozluk[kat]) / len(kelimeler)
            assert t.loc[k, kat] == pytest.approx(beklenen, abs=1e-9), (k, kat)


def test_sozluk_kategorileri():
    s = ozellik.lm_sozluk()
    assert {"uncertain", "uncertainty"} <= s["belirsizlik"]
    assert {"loss", "decline"} <= s["olumsuz"]
    assert "growth" not in s["olumsuz"]


# ---------------------------------------------------------------- metin komşuları
def test_komsular(eda, temiz):
    komsu = np.load(ISL / "eda_komsu.npy")
    tick = eda.ticker.to_numpy()
    assert komsu.shape == (1866, 10)
    assert not (tick[komsu] == tick[:, None]).any(), "kendi şirketi komşu olamaz"
    assert all(len(set(tick[k])) == 10 for k in komsu), "10 farklı şirket"
    assert np.allclose(eda.komsu_v, eda.v.to_numpy()[komsu].mean(axis=1))
    metinler = [" ".join(s) for s in temiz.loc[eda.klasor, "cumleler_temiz"]]
    k2, B, tf, A = metin_komsulari(metinler, tick, K=10)
    assert np.array_equal(k2, komsu), "aynı ayarla yeniden hesaplanan komşular aynı olmalı"
    assert A.shape[0] == 1866, "TF-IDF yalnız eğitim dönemi metinlerinden öğrenilir"
    for i in (0, 777, 1865):
        b = B[i, komsu[i]]
        assert np.all(np.diff(b) <= 1e-12), "komşular benzerliğe göre azalan sırada"


def test_farkli_sektor_secenegi(eda, temiz):
    metinler = [" ".join(s) for s in temiz.loc[eda.klasor[:300], "cumleler_temiz"]]
    g = eda.bolum.to_numpy()[:300]
    k, *_ = metin_komsulari(metinler, eda.ticker.to_numpy()[:300], K=5, haric_grup=g)
    ayni = (g[k] == g[:, None]) & (g[:, None] != "bilinmiyor")
    assert not ayni.any()


# ---------------------------------------------------------------- istatistik fonksiyonları (yapay veri)
def test_kismi_korelasyon_yapay():
    rng = np.random.default_rng(0)
    z = rng.normal(size=5000)
    ortak = pd.DataFrame({"x": z + rng.normal(size=5000), "y": z + rng.normal(size=5000), "z": z})
    assert abs(stats.spearmanr(ortak.x, ortak.y)[0]) > 0.4, "kontrolsüz korelasyon yüksek"
    assert abs(kismi(ortak, "x", "y", ["z"])) < 0.05, "ortak nedeni kontrol edince sıfıra iner"
    gercek = ortak.assign(y=ortak.y + 0.8 * ortak.x)
    assert kismi(gercek, "x", "y", ["z"]) > 0.3, "gerçek ilişki kontrol sonrası kalır"


def test_kruskal_epsilon_yapay():
    rng = np.random.default_rng(0)
    ayni = pd.DataFrame({"sinif": np.repeat([0, 1, 2], 400), "d": rng.normal(size=1200)})
    farkli = ayni.assign(d=ayni.d + 5 * ayni.sinif)
    assert abs(kw(ayni, "d")[2]) < 0.02
    assert kw(farkli, "d")[2] > 0.8


def test_sirket_bootstrap():
    t = np.array(["A", "A", "B", "C", "C", "C"])
    for s in sirket_ornekleri(t, B=50, tohum=3):
        secilen = t[s]
        for sirket in set(secilen):
            assert (secilen == sirket).sum() % (t == sirket).sum() == 0, "şirketin çağrıları birlikte gelir"
    a, b = sirket_ornekleri(t, B=5, tohum=1), sirket_ornekleri(t, B=5, tohum=1)
    assert all(np.array_equal(x, y) for x, y in zip(a, b)), "aynı tohum aynı örnekler"


# ---------------------------------------------------------------- kaydedilen tabloların yeniden üretimi
def test_korelasyon_tablosu(eda):
    C = pd.read_csv(CIK / "f3_korelasyon.csv", index_col=0)
    yeniden = eda[C.columns].corr(method="spearman")
    assert np.allclose(C.values, yeniden.values, atol=1e-9)


def test_kismi_tablo_nokta_tahminleri(eda):
    tab = pd.read_csv(CIK / "f3_kismi_korelasyon.csv")
    beklenen = [kismi(eda, "komsu_v", "v", []), kismi(eda, "komsu_v", "v", ["gecmis_oyn_60", "aralik_ort"]),
                kismi(eda, "komsu_v", "v", ["gecmis_oyn_60", "aralik_ort", "piyasa_once"])]
    assert np.allclose(tab["kısmi ρ"].iloc[:3], beklenen, atol=1e-9)
    assert (tab["%95 GA alt"] <= tab["kısmi ρ"]).all() and (tab["kısmi ρ"] <= tab["%95 GA üst"]).all()


def test_istatistik_tablosu(eda):
    ist = pd.read_csv(CIK / "f3_istatistik_ozeti.csv")
    adlar = ["düşük", "orta", "yüksek"]
    for k in ["gecmis_oyn_60", "belirsizlik", "v"]:
        for c, ad in enumerate(adlar):
            s = eda.loc[eda.sinif == c, k]
            satir = ist[(ist["özellik"] == k) & (ist["sınıf"] == ad)].iloc[0]
            assert satir["medyan"] == pytest.approx(s.median(), abs=1e-6)
            assert satir["Ç3"] == pytest.approx(s.quantile(0.75), abs=1e-6)


def test_tamamlayicilik_tablosu(eda):
    g = pd.qcut(eda.gecmis_oyn_60, 3, labels=False)
    m = pd.qcut(eda.komsu_v, 3, labels=False)
    tablo = pd.crosstab(m, g, values=(eda.sinif == 2), aggfunc="mean") * 100
    assert pd.crosstab(m, g).values.sum() == 1866
    assert tablo.loc[0, 0] == pytest.approx(8.1, abs=0.05) and tablo.loc[2, 2] == pytest.approx(58.7, abs=0.05)


def test_sekiller_var():
    for i in range(1, 12):
        dosyalar = list(SEK.glob(f"f3_{i:02d}_*.png"))
        assert len(dosyalar) == 1 and dosyalar[0].stat().st_size > 30_000, i
