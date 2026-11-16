"""Ham veriyi indirir: MAEC (kazanç çağrısı metinleri) ve FNSPID (günlük fiyatlar).

Her iki kaynak sabit bir sürüme (commit) bağlıdır; böylece aynı dosyalar yeniden indirilebilir.
İndirilen her dosyanın SHA256 özeti yazdırılır ve README'deki değerle karşılaştırılabilir.

Çalıştırma (proje kökünden):  python src/indir.py
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "veri" / "ham"

MAEC_COMMIT = "65a109f5b1a8cb4c96e8337b749ce3db41f2c210"
FNSPID_REVIZYON = "bf9189c41527198897d1af3e17b1a0095279fc45"

KAYNAKLAR = {
    "maec.zip": "https://codeload.github.com/Earnings-Call-Dataset/"
                "MAEC-A-Multimodal-Aligned-Earnings-Conference-Call-Dataset-for-Financial-Risk-Prediction/"
                f"zip/{MAEC_COMMIT}",
    "fnspid_full_history.zip": f"https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/{FNSPID_REVIZYON}/"
                               "Stock_price/full_history.zip",
}


# 15 Kasım 2026'da indirilen dosyaların özetleri; farklı çıkarsa kaynak değişmiş demektir.
BEKLENEN_SHA256 = {
    "maec.zip": "3df6d7134b79f28b02c6161094837b71bb8101b9aa28d2874e18075731ff3f99",
    "fnspid_full_history.zip": "03da4fce7ebea90d5715ba3501773d410ae663b617027b338ef000a9955dab91",
}


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def indir(ad, url):
    hedef = HAM / ad
    if hedef.exists():
        print(f"{ad}: zaten var, atlandı")
    else:
        gecici = hedef.with_suffix(".indiriliyor")
        print(f"{ad}: indiriliyor <- {url}")
        with urllib.request.urlopen(url) as yanit, open(gecici, "wb") as f:
            while parca := yanit.read(1 << 20):
                f.write(parca)
        gecici.rename(hedef)  # yarım kalan indirme tam dosya sanılmasın
    ozet = sha256(hedef)
    durum = "AYNI" if ozet == BEKLENEN_SHA256[ad] else "FARKLI (kaynak değişmiş olabilir)"
    print(f"{ad}: {hedef.stat().st_size / 1e6:.1f} MB, sha256 {ozet} -> beklenenle {durum}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    HAM.mkdir(parents=True, exist_ok=True)
    for ad, url in KAYNAKLAR.items():
        indir(ad, url)
