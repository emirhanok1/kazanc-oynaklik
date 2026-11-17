"""Faz 4 (bölme) testleri: test ayrımı, şirket ve ileri katlarda sızıntı olmaması, eşiklerin yalnız eğitimden
öğrenilmesi, modalitelerin hizası ve bölmenin tekrarlanabilirliği.

Çalıştırma (proje kökünden, 01–04 notebook'ları çalıştırıldıktan sonra):  python -m pytest tests -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from src import bolme, etiket  # noqa: E402

ISL = KOK / "veri" / "islenmis"


@pytest.fixture(scope="module")
def b():
    return pd.read_parquet(ISL / "bolme.parquet")


def test_test_ayrimi(b):
    assert (b.loc[b.bolum == "test", "tarih"] > bolme.GELISTIRME_SONU).all()
    assert (b.loc[b.bolum != "test", "tarih"] <= bolme.GELISTIRME_SONU).all()
    ilk_test = b.loc[b.bolum == "test", "t0"].min()
    assert (b.loc[b.bolum == "gelistirme", "hedef_bitis"] < ilk_test).all(), "geliştirme hedefi test dönemine taşmamalı"
    assert (b.loc[b.bolum == "test", "kat"] == -1).all() and (b.loc[b.bolum == "test", "ileri_kat"] == -1).all()


def test_sirket_katlari(b):
    D = b.bolum == "gelistirme"
    assert set(b.loc[D, "kat"]) == set(range(bolme.KAT_SAYISI)), "her geliştirme çağrısı tam bir katta"
    for k in range(bolme.KAT_SAYISI):
        egit, dog = bolme.sirket_kati(b, k)
        assert not (set(b.loc[egit, "ticker"]) & set(b.loc[dog, "ticker"])), f"kat {k}: ortak şirket"
        assert egit.sum() + dog.sum() == D.sum()
        y, _ = bolme.kat_etiketleri(b, egit, dog)
        payl = np.bincount(y, minlength=3) / len(y)
        assert np.all(np.abs(payl - 1 / 3) < 0.05), f"kat {k}: sınıf payları dengesiz {payl}"


def test_esikler_yalniz_egitimden(b):
    egit, dog = bolme.sirket_kati(b, 0)
    _, esik = bolme.kat_etiketleri(b, egit, dog)
    assert np.allclose(esik, etiket.esikler(b.loc[egit, "v"]))
    bozuk = b.copy()
    bozuk.loc[dog, "v"] = bozuk.loc[dog, "v"] + 10          # doğrulama hedefleri değişse bile eşik değişmemeli
    _, esik2 = bolme.kat_etiketleri(bozuk, egit, dog)
    assert np.allclose(esik, esik2)


def test_ileri_katlar(b):
    for k, q in enumerate(["2016Q1", "2016Q2", "2016Q3", "2016Q4"]):
        egit, dog = bolme.ileri_kat(b, k)
        assert egit.sum() > 0 and dog.sum() > 0, f"ileri kat {k} boş"
        assert dog.sum() == ((b.bolum == "gelistirme") & (b.ceyrek == q)).sum(), "çeyreğin bütün çağrıları doğrulamada"
        bas = b.loc[dog, "t0"].min()
        assert (b.loc[dog, "ceyrek"] == q).all()
        assert (b.loc[egit, "t0"] < bas).all(), "eğitim doğrulamadan önce"
        assert (b.loc[egit, "hedef_bitis"] < bas).all(), "eğitim hedefi doğrulamaya taşmamalı (arındırma)"
        assert (b.loc[egit | dog, "bolum"] == "gelistirme").all(), "ileri katlar yalnız geliştirme döneminde"


def test_modalite_hizasi(b):
    temiz = pd.read_parquet(ISL / "temiz_cagrilar.parquet")
    z = np.load(ISL / "seri_girdisi.npz", allow_pickle=True)
    assert (b.klasor.to_numpy() == temiz.klasor.to_numpy()).all()
    assert (b.klasor.to_numpy() == z["klasor"]).all()
    assert z["X"].shape == (len(b), 60, 3)


def test_hedef_ve_girdi_hizasi():
    """Kural 1–2 ham düzeltilmiş kapanıştan bağımsız hesapla sınanır: gün 0 = t0 (çağrı tarihi ya da sonraki ilk
    işlem günü, en çok 5 gün), gün −1 çağrıdan önce; v = ln(std(r0..r+6), ddof=0); girdi getirisi = r−60..r−1."""
    temiz = pd.read_parquet(ISL / "temiz_cagrilar.parquet").set_index("klasor")
    p = pd.read_parquet(ISL / "fiyat_pencereleri.parquet", columns=["klasor", "gun", "date", "adj close"])
    p = p[p.klasor.isin(temiz.index) & p.gun.between(-61, 6)]
    tarih = p.pivot(index="klasor", columns="gun", values="date").loc[temiz.index]
    assert (tarih[0] == temiz.t0).all()
    assert (temiz.t0 >= temiz.tarih).all() and ((temiz.t0 - temiz.tarih).dt.days <= 5).all()
    assert (tarih[-1] < temiz.tarih).all(), "girdinin son günü çağrıdan önce"
    P = p.pivot(index="klasor", columns="gun", values="adj close").loc[temiz.index].to_numpy()
    assert P.shape[1] == 68 and not np.isnan(P).any()
    r = np.diff(np.log(P), axis=1)                      # sütunlar: gün −60..+6
    assert np.allclose(np.log(r[:, 60:].std(axis=1)), temiz.v.to_numpy(), atol=1e-9)
    z = np.load(ISL / "seri_girdisi.npz", allow_pickle=True)
    assert (z["klasor"] == temiz.index.to_numpy()).all()
    assert np.allclose(z["X"][:, :, 0], r[:, :60], atol=1e-6)


def test_bolme_tekrarlanabilir(b):
    temiz = pd.read_parquet(ISL / "temiz_cagrilar.parquet")
    pencere = pd.read_parquet(ISL / "fiyat_pencereleri.parquet", columns=["klasor", "gun", "date"])
    yeniden = bolme.bolme_tablosu(temiz, pencere)
    for s in ["bolum", "kat", "ileri_kat"]:
        assert (yeniden[s].to_numpy() == b[s].to_numpy()).all(), s


def test_sekiller_var():
    for i in range(1, 5):
        dosyalar = list((KOK / "sekiller").glob(f"f4_{i:02d}_*.png"))
        assert len(dosyalar) == 1 and dosyalar[0].stat().st_size > 30_000, i
