"""SEC EDGAR'dan ticker -> şirket adı ve sektör kodu (SIC).

SEC, otomatik isteklerde 'Ad Soyad e-posta' biçiminde bir User-Agent ister.
Bu bilgi koda yazılmaz; SEC_USER_AGENT ortam değişkeninden ya da proje kökündeki .env dosyasından okunur.
Yanıtların yalnız gereken alanları veri/ham/sec/ altına kaydedilir; ikinci çalıştırmada istek atılmaz.
Not: company_tickers.json GÜNCEL ticker listesidir; o tarihten beri borsadan çıkan şirketler bulunmaz.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

import pandas as pd

KLASOR = Path(__file__).resolve().parents[1] / "veri" / "ham" / "sec"

# SIC bölümleri (ilk iki hane): ABD standart sanayi sınıflaması
SIC_BOLUMLERI = [(1, 9, "Tarım"), (10, 14, "Madencilik ve enerji"), (15, 17, "İnşaat"), (20, 39, "İmalat"),
                 (40, 49, "Ulaştırma, iletişim, altyapı"), (50, 51, "Toptan ticaret"), (52, 59, "Perakende"),
                 (60, 67, "Finans, sigorta, gayrimenkul"), (70, 89, "Hizmetler"), (91, 99, "Kamu")]


def _kimlik():
    """SEC_USER_AGENT: önce ortam değişkeni, yoksa proje kökündeki .env dosyası (git'e girmez)."""
    if "SEC_USER_AGENT" in os.environ:
        return os.environ["SEC_USER_AGENT"]
    env = KLASOR.parents[2] / ".env"
    ham = env.read_bytes() if env.exists() else b""
    # PowerShell 'echo > dosya' UTF-16 ya da BOM'lu UTF-8 yazabilir; ikisi de okunur.
    metin = ham.decode("utf-16") if ham[:2] in (b"\xff\xfe", b"\xfe\xff") else ham.decode("utf-8-sig")
    for satir in metin.splitlines():
        satir = satir.strip()
        if satir.startswith("SEC_USER_AGENT="):
            return satir.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("SEC_USER_AGENT tanımlı değil: proje kökündeki .env dosyasına ekleyin.")


def _istek(url):
    istek = urllib.request.Request(url, headers={"User-Agent": _kimlik()})
    with urllib.request.urlopen(istek) as yanit:
        veri = json.loads(yanit.read())
    time.sleep(0.15)  # SEC sınırı: saniyede en fazla 10 istek
    return veri


def _onbellekli(dosya, url, alanlar=None):
    yol = KLASOR / dosya
    if not yol.exists():
        veri = _istek(url)
        if alanlar:
            veri = {k: veri.get(k) for k in alanlar}
        yol.write_text(json.dumps(veri), encoding="utf-8")
    return json.loads(yol.read_text(encoding="utf-8"))


def sic_bolumu(sic):
    if not sic:
        return None
    iki = int(str(sic)[:2]) if len(str(sic)) == 4 else int(str(sic)[:1])
    return next((ad for a, b, ad in SIC_BOLUMLERI if a <= iki <= b), "Diğer")


def sirket_bilgisi(tickerlar):
    """Her ticker için cik, ad, eski adlar, sic, sic açıklaması, SIC bölümü (sektor). SEC listesinde yoksa yalnız ticker."""
    KLASOR.mkdir(parents=True, exist_ok=True)
    liste = _onbellekli("company_tickers.json", "https://www.sec.gov/files/company_tickers.json")
    cik = {}
    for v in liste.values():
        cik.setdefault(v["ticker"].upper(), v["cik_str"])
    satirlar = []
    for t in sorted(set(tickerlar)):
        if t not in cik:
            satirlar.append({"ticker": t})
            continue
        k = f"CIK{cik[t]:010d}"
        s = _onbellekli(f"{k}.json", f"https://data.sec.gov/submissions/{k}.json",
                        ["name", "sic", "sicDescription", "formerNames", "tickers"])
        satirlar.append({"ticker": t, "cik": cik[t], "ad": s["name"],
                         "eski_adlar": [f["name"] for f in (s["formerNames"] or [])],
                         "sic": s["sic"], "sic_aciklama": s["sicDescription"], "sektor": sic_bolumu(s["sic"])})
    return pd.DataFrame(satirlar)
