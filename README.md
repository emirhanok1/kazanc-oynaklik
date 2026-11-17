# Metin ve Zaman Serisi Füzyonu ile Hisse Senedi Oynaklık Sınıflandırması

Multimodal Derin Öğrenme dersi projesi. Kazanç çağrısı metni (MAEC) ile çağrıdan önceki 60 işlem gününün fiyat/hacim
serisini (FNSPID) aynı olay üzerinde birleştirerek, çağrı günü dahil 7 işlem gününün oynaklığını üç sınıfta
(düşük / orta / yüksek) tahmin etmeyi amaçlar.

Vize aşaması: veri edinme, eşleştirme, temizlik, keşifsel analiz ve veri bölme. Model eğitimi final aşamasındadır.

## Kurulum

Python 3.11 ile:

```
pip install -r requirements.txt
```

## Çalıştırma

1. Ham veriyi ve sözlüğü indir (~0,68 GB, SHA256 kontrollü):
   ```
   python src/indir.py
   ```
2. Şirket adı ve sektör bilgisi için SEC EDGAR, istek başlığında bir iletişim bilgisi ister. Proje kökünde `.env`
   dosyası oluşturup tek satır yaz (bu dosya git'e girmez):
   ```
   SEC_USER_AGENT=Ad Soyad eposta@ornek.com
   ```
3. Notebook'ları sırayla çalıştır (Jupyter ile ya da komut satırından):
   ```
   python -m nbconvert --to notebook --execute --inplace notebooks/01_veri_edinme_eslestirme.ipynb
   python -m nbconvert --to notebook --execute --inplace notebooks/02_temizlik_on_isleme.ipynb
   python -m nbconvert --to notebook --execute --inplace notebooks/03_kesifsel_analiz.ipynb
   ```
   İlk çalıştırma SEC verisini indirdiği için ~20 dk, sonrakiler toplam ~8 dk sürer.
4. Testleri çalıştır (notebook çıktılarını bağımsız yeniden hesaplamayla karşılaştırır, sızıntı kurallarını sınar):
   ```
   python -m pytest tests -q
   ```

## Klasörler

| Klasör | İçerik |
|---|---|
| `src/` | Ortak kod: `indir.py` (ham veri), `veri.py` (okuma), `eslestir.py` (çağrı–fiyat eşleştirme), `etiket.py` (oynaklık ve sınıflar), `sec.py` (şirket adı/sektör), `temizle.py` (metin temizliği, 60 × 3 fiyat girdisi), `ozellik.py` (analiz için özet özellikler), `istatistik.py` (kısmi korelasyon, önyükleme, metin komşuları) |
| `notebooks/` | Her faz için bir notebook |
| `tests/` | Doğrulama testleri (pytest) |
| `sekiller/` | Rapordaki şekiller |
| `cikti/` | Özet tablolar (veri kaybı dökümü, sınıf ve sektör dağılımı, veri özeti) |
| `veri/` | Ham ve işlenmiş veri; repoda yok, kodla yeniden üretilir |

## Veri kaynakları

| Modalite | Kaynak | Sürüm | Yayın | Lisans / kısıt |
|---|---|---|---|---|
| Metin | [MAEC](https://github.com/Earnings-Call-Dataset/MAEC-A-Multimodal-Aligned-Earnings-Conference-Call-Dataset-for-Financial-Risk-Prediction) | commit `65a109f` | Li vd. (2020), CIKM, doi:10.1145/3340531.3412879 | CC BY-SA 4.0 |
| Fiyat serisi | [FNSPID](https://huggingface.co/datasets/Zihan1004/FNSPID) `Stock_price/full_history.zip` | revizyon `bf9189c` | Dong vd. (2024), KDD, doi:10.1145/3637528.3671629 | CC BY-NC 4.0; fiyatların kökeni Yahoo Finance (yeniden dağıtılamaz) |
| Yardımcı (sözlük) | [Loughran–McDonald Master Dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) 1993–2025 | SHA256 kontrollü | Loughran ve McDonald (2011), doi:10.1111/j.1540-6261.2010.01625.x | Akademik araştırmada ücretsiz |
| Yardımcı | SEC EDGAR (`company_tickers.json`, `submissions`) | erişim tarihi Kasım 2026 | — | Kimlik bildiren User-Agent, saniyede ≤ 10 istek |

Ham veri bu repoda yeniden dağıtılmaz; yalnız indirme kodu paylaşılır. Çalışma ticari olmayan bir ders projesidir.

## Sızıntıyı önleyen temel kurallar

- Olay günü t0: çağrı tarihine eşit ya da sonraki ilk işlem günü.
- Girdi: gün −60..−1 getirileri (gün −1 kapanışında biter). Hedef: gün 0..+6 getirileri. Hiçbir gün iki tarafta birden yer almaz.
- Sınıf eşikleri, ölçekleme ve metin sözlüğü yalnız eğitim kısmından öğrenilir.
