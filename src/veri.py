"""Ham veriyi zip'ten açmadan okur: MAEC çağrı metinleri ve FNSPID günlük fiyatları."""
import io
import re
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
MAEC_ZIP = KOK / "veri" / "ham" / "maec.zip"
FIYAT_ZIP = KOK / "veri" / "ham" / "fnspid_full_history.zip"
FIYAT_SUTUNLARI = ["date", "open", "high", "low", "close", "adj close", "volume"]


@lru_cache(maxsize=None)
def _zip(yol):
    return zipfile.ZipFile(yol)


def maec_oku():
    """Her çağrı için bir satır döndürür.

    klasor: 'YYYYMMDD_TICKER' (MAEC'in örnek kimliği), tarih, ticker,
    cumleler: text.txt'deki boş olmayan satırlar (MAEC her satıra bir cümle koyar),
    konusmaci_etiketi: MAEC_Dataset_Person_Label altında bu çağrı için text.csv var mı,
    utf8_hatasi: metin UTF-8 olarak çözülemedi mi (bozuk karakterler '�' ile değiştirilir).
    """
    z = _zip(MAEC_ZIP)
    metin_deseni = re.compile(r"/MAEC_Dataset/(\d{8})_([^/]+)/text\.txt$")
    etiketli = {m.group(1) for ad in z.namelist()
                if (m := re.search(r"/MAEC_Dataset_Person_Label/(\d{8}_[^/]+)/text\.csv$", ad))}
    satirlar = []
    for ad in sorted(z.namelist()):
        m = metin_deseni.search(ad)
        if not m:
            continue
        ham = z.read(ad)
        try:
            metin, hata = ham.decode("utf-8"), False
        except UnicodeDecodeError:
            metin, hata = ham.decode("utf-8", "replace"), True
        klasor = f"{m.group(1)}_{m.group(2)}"
        satirlar.append({
            "klasor": klasor,
            "tarih": pd.Timestamp(m.group(1)),
            "ticker": m.group(2),
            "cumleler": [s.strip() for s in metin.splitlines() if s.strip()],
            "konusmaci_etiketi": klasor in etiketli,
            "utf8_hatasi": hata,
        })
    return pd.DataFrame(satirlar)


def fiyat_dosyalari():
    """Ticker (büyük harf) -> zip içindeki CSV yolu. '__MACOSX/._*' kopyaları dahil edilmez."""
    on = "full_history/"
    return {ad[len(on):-4].upper(): ad for ad in _zip(FIYAT_ZIP).namelist()
            if ad.startswith(on) and ad.endswith(".csv")}


def fiyat_oku(yol):
    """Bir hissenin günlük fiyatları, eskiden yeniye sıralı.

    Sütunlar ada göre seçilir çünkü sütun sırası dosyadan dosyaya değişiyor.
    Dosya boşsa ya da beklenen sütunlar yoksa None döner.
    """
    try:
        d = pd.read_csv(io.BytesIO(_zip(FIYAT_ZIP).read(yol)), usecols=FIYAT_SUTUNLARI, parse_dates=["date"])
    except (ValueError, pd.errors.EmptyDataError):
        return None
    return d.sort_values("date").reset_index(drop=True)
