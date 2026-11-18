# Kazanç Çağrısı ve Fiyat Serisiyle Hisse Oynaklığı Tahmini

Şirketler her üç ayda bir sonuçlarını bir toplantıda (kazanç çağrısı) açıklar ve ardından hisse fiyatı dalgalanır.
Bu proje, bu dalgalanmanın **düşük, orta ya da yüksek** olacağını iki tür veriyle tahmin etmeye hazırlanıyor:

- **Metin:** toplantıda yöneticilerin söyledikleri (MAEC veri seti)
- **Fiyat serisi:** toplantıdan önceki 60 günün hisse fiyatı ve işlem hacmi (FNSPID veri seti)

Bu depo projenin **vize aşamasıdır**: veriyi toplama, eşleştirme, temizleme, inceleme ve modele hazırlama.
Model eğitimi final aşamasında yapılacak.

## Kısaca sonuç

- 3.443 toplantının 3.026'sı fiyat verisiyle eşleşti; temizlikten sonra **3.000 örnek** (1.050 şirket) kaldı.
- Sınıflar dengeli: düşük 1.074, orta 938, yüksek 988.
- Fiyat geçmişi tek başına güçlü bir ipucu; metin bunun üstüne ek bilgi taşıyor.

## Nasıl çalıştırılır

```
pip install -r requirements.txt
python src/indir.py
```

Proje klasöründe `.env` adlı bir dosya açıp şu satırı yaz (SEC sitesi bir iletişim bilgisi istiyor):

```
SEC_USER_AGENT=Ad Soyad eposta@ornek.com
```

Sonra `notebooks/` klasöründeki dört notebook'u sırayla çalıştır (01 → 04). Kontrol testleri: `python -m pytest tests -q`

## Klasörler

- `notebooks/` — 01 eşleştirme, 02 temizlik, 03 analiz, 04 veri bölme
- `src/` — notebook'ların ortak kodu
- `sekiller/`, `cikti/` — grafikler ve özet tablolar
- `tests/` — kontrol testleri

## Veri ve lisans

Veriler lisans gereği bu depoda yok; `src/indir.py` aynı sürümü indirir.

- MAEC: CC BY-SA 4.0
- FNSPID fiyatları: CC BY-NC 4.0 (kaynağı Yahoo Finance; yeniden dağıtılamaz)
