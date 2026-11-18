# Metin ve Zaman Serisi Füzyonu ile Hisse Senedi Oynaklık Sınıflandırması

Multimodal Derin Öğrenme dersi projesi. Bu depo **vize aşamasını (Aşama 1)** içerir: veri toplama, iki modalitenin
eşleştirilmesi, temizlik, keşifsel veri analizi ve veri bölme. Model eğitimi final aşamasındadır.

## Proje bir bakışta

| | |
|---|---|
| **Soru** | Bir şirketin kazanç çağrısı bittiğinde, hissenin sonraki günlerdeki oynaklığı düşük mü, orta mı, yüksek mi olacak? |
| **Modalite 1: metin** | Kazanç çağrısının yazılı metni (MAEC) |
| **Modalite 2: zaman serisi** | Çağrıdan önceki 60 işlem gününün fiyat ve hacim serisi (FNSPID) |
| **Hedef** | Çağrı günü dahil 7 işlem gününün (gün 0..+6) log getirilerinin standart sapmasının logaritması → 3 sınıf |
| **Veri** | 3.443 çağrı → 3.026'sı eşleşti (%87,9) → temizlik sonrası 3.000 çağrı, 1.050 şirket |
| **Sınıflar** | düşük 1.074 / orta 938 / yüksek 988 (eşikler yalnız eğitim verisinden) |
| **Bölme** | Geliştirme: çağrı tarihi ≤ 2016 (1.866) · Test: 2017 ve sonrası (1.134); geliştirmede şirkete göre 5 kat + 2016 çeyreklerinden ileri katlar |

## Notebook'lar

Sırayla çalıştırılır; her biri bir öncekinin kaydettiği ara dosyaları okur.

| Notebook | Ne yapar | Süre |
|---|---|---|
| `01_veri_edinme_eslestirme.ipynb` | Ham veriyi okur, çağrıyı fiyat serisiyle eşleştirir, hedefi ve sınıfları hesaplar, veri özeti ve kayıp dökümünü çıkarır | ~2 dk (ilk çalıştırmada SEC indirmesiyle ~20 dk) |
| `02_temizlik_on_isleme.ipynb` | Metin temizliği, 60 × 3 fiyat girdisi, üç öncesi–sonrası karşılaştırma | ~1 dk |
| `03_kesifsel_analiz.ipynb` | Metin ve fiyat EDA'sı, modaliteler arası analiz, örnek olaylar, sağlamlık analizi | ~3 dk |
| `04_bolme_sizinti.ipynb` | Test ayrımı, şirket ve ileri katlar, sızıntı denetimi, model girdi yapısı | ~1 dk |

## Kurulum ve çalıştırma

Python 3.11 ile:

1. Paketleri kur:
   ```
   pip install -r requirements.txt
   ```
2. Ham veriyi indir (~0,68 GB; her dosyanın SHA256 özeti kontrol edilir, uyuşmazsa indirme durur):
   ```
   python src/indir.py
   ```
3. Şirket adı ve sektör bilgisi SEC EDGAR'dan alınır; SEC istek başlığında bir iletişim bilgisi ister. Proje kökünde
   `.env` dosyası oluşturup tek satır yaz (bu dosya git'e girmez):
   ```
   SEC_USER_AGENT=Ad Soyad eposta@ornek.com
   ```
4. Notebook'ları sırayla çalıştır (Jupyter ile ya da komut satırından):
   ```
   python -m nbconvert --to notebook --execute --inplace notebooks/01_veri_edinme_eslestirme.ipynb
   python -m nbconvert --to notebook --execute --inplace notebooks/02_temizlik_on_isleme.ipynb
   python -m nbconvert --to notebook --execute --inplace notebooks/03_kesifsel_analiz.ipynb
   python -m nbconvert --to notebook --execute --inplace notebooks/04_bolme_sizinti.ipynb
   ```
5. Testleri çalıştır (24 test; notebook sonuçlarını bağımsız yeniden hesaplamayla karşılaştırır ve sızıntı kurallarını sınar):
   ```
   python -m pytest tests -q
   ```

## Klasörler

| Klasör | İçerik |
|---|---|
| `notebooks/` | Her faz için bir notebook (yukarıdaki tablo) |
| `src/` | Ortak kod: `indir.py` (indirme + SHA256), `veri.py` ve `eslestir.py` (okuma, çağrı–fiyat eşleştirme), `etiket.py` (hedef ve sınıf eşikleri), `sec.py` (şirket adı/sektör), `temizle.py` (metin temizliği, 60 × 3 fiyat girdisi), `ozellik.py` ve `istatistik.py` (analiz), `bolme.py` (test ayrımı, şirket ve ileri katlar) |
| `tests/` | Doğrulama testleri (pytest) |
| `sekiller/` | Notebook'ların ürettiği şekiller (Şekil 1–29) |
| `cikti/` | Özet tablolar: veri kaybı dökümü, sınıf ve sektör dağılımı, istatistik özetleri, bölme tabloları |
| `veri/` | Ham ve işlenmiş veri; repoda yok, kodla yeniden üretilir |

## Veri kaynakları

| Modalite | Kaynak | Sabit sürüm | Lisans / kısıt |
|---|---|---|---|
| Metin | [MAEC](https://github.com/Earnings-Call-Dataset/MAEC-A-Multimodal-Aligned-Earnings-Conference-Call-Dataset-for-Financial-Risk-Prediction) — Li vd. (2020), CIKM, doi:10.1145/3340531.3412879 | commit `65a109f` | CC BY-SA 4.0 |
| Fiyat serisi | [FNSPID](https://huggingface.co/datasets/Zihan1004/FNSPID), yalnız `Stock_price/full_history.zip` — Dong vd. (2024), KDD, doi:10.1145/3637528.3671629 | revizyon `bf9189c` | CC BY-NC 4.0 (FNSPID GitHub README'sindeki 24.07.2025 duyurusu bununla çelişiyor; tutucu olarak CC BY-NC 4.0 uygulanır). Fiyatların kökeni Yahoo Finance, yeniden dağıtılamaz |
| Yardımcı: sözlük | [Loughran–McDonald Master Dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) 1993–2025 — Loughran ve McDonald (2011), doi:10.1111/j.1540-6261.2010.01625.x | SHA256 kontrollü | Akademik kullanım ücretsiz |
| Yardımcı: ad, sektör | SEC EDGAR (`company_tickers.json`, `submissions`) | Kasım 2026 erişimi | Kimlik bildiren User-Agent, saniyede ≤ 10 istek |

Ham veri bu repoda yeniden dağıtılmaz; yalnız indirme kodu paylaşılır. Çalışma ticari olmayan bir ders projesidir.

## Sızıntıyı önleyen kurallar

- **Zaman:** girdi gün −1 kapanışında biter (gün −60..−1 getirileri), hedef gün 0'da başlar (gün 0..+6). Hiçbir gün iki tarafta birden yer almaz.
- **Öğrenilen her şey yalnız eğitimden:** sınıf eşikleri, ölçekleme ve metin sözlüğü yalnız eğitim kısmından hesaplanır.
- **Fiyat düzeyi kullanılmaz:** düzeltilmiş fiyat sonradan gelen temettü/bölünmelere göre değiştiği için yalnız getiri ve oranlar kullanılır.
- **Şirket:** şirket katlarında bir şirketin bütün çağrıları aynı kattadır.
- **Test:** 2017 ve sonrası zamanca ayrıdır; hedefe dayanan bütün analizler yalnız geliştirme döneminde yapıldı, test finalde bir kez açılır.
