"""Keşifsel analizde kullanılan istatistik yardımcıları (tests/ altında test edilir)."""
import numpy as np
from scipy import stats
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


def kw(df, sutun, grup="sinif"):
    """Kruskal–Wallis testi: (H, p, ε²). Etki büyüklüğü ε² = H / (n − 1); 0 = sınıflar arasında fark yok."""
    gruplar = [g[sutun].to_numpy() for _, g in df.groupby(grup)]
    H, p = stats.kruskal(*gruplar)
    return H, p, H / (len(df) - 1)


def kismi(df, x, y, kontrol):
    """Kısmi Spearman korelasyonu: değişkenler sıraya çevrilir, x ve y kontrol değişkenlerine
    doğrusal regresyonla arındırılır, artıkların Pearson korelasyonu döner."""
    R = lambda s: stats.rankdata(s)
    Z = np.column_stack([np.ones(len(df))] + [R(df[c]) for c in kontrol])
    rx = R(df[x]) - Z @ np.linalg.lstsq(Z, R(df[x]), rcond=None)[0]
    ry = R(df[y]) - Z @ np.linalg.lstsq(Z, R(df[y]), rcond=None)[0]
    return np.corrcoef(rx, ry)[0, 1]


def sirket_ornekleri(tickerlar, B=1000, tohum=0):
    """Şirket düzeyinde önyükleme örnekleri: şirketler iadeli çekilir, her şirketin bütün çağrıları birlikte gelir."""
    tickerlar = np.asarray(tickerlar)
    sirketler = np.array(list(dict.fromkeys(tickerlar)))   # ilk görünme sırası (sonuçlar sırayla tekrarlanabilir)
    indeks = {s: np.where(tickerlar == s)[0] for s in sirketler}
    rng = np.random.default_rng(tohum)
    return [np.concatenate([indeks[s] for s in rng.choice(sirketler, len(sirketler))]) for _ in range(B)]


def metin_komsulari(metinler, tickerlar, K=10, ngram=(1, 1), min_df=5, sublinear=True, haric_grup=None):
    """TF-IDF (bu metinlerden öğrenilir) + kosinüs benzerliği. Her metin için, aynı şirket hariç,
    her şirketten yalnız en benzer tek çağrı alınarak en benzer K çağrının sırası döner.
    haric_grup verilirse (ör. sektör), grubu bilinen ve aynı olan çağrılar da komşu olamaz ("bilinmiyor" hariç).
    Dönüş: (komşu indeks dizisi [n, K], benzerlik matrisi, TF-IDF nesnesi, TF-IDF matrisi)."""
    dur = list(ENGLISH_STOP_WORDS | {"name", "url"})
    tf = TfidfVectorizer(stop_words=dur, min_df=min_df, max_df=0.8, sublinear_tf=sublinear, ngram_range=ngram,
                         token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
    A = tf.fit_transform(metinler)
    B = (A @ A.T).toarray()
    kod = np.asarray(tickerlar)
    B[kod[:, None] == kod[None, :]] = -np.inf
    if haric_grup is not None:
        g = np.asarray(haric_grup)
        B[(g[:, None] == g[None, :]) & (g[:, None] != "bilinmiyor")] = -np.inf
    sira = np.argsort(-B, axis=1)
    komsu = []
    for i in range(len(kod)):
        secilen, gorulen = [], set()
        for j in sira[i]:
            if kod[j] not in gorulen:
                secilen.append(j)
                gorulen.add(kod[j])
                if len(secilen) == K:
                    break
        komsu.append(secilen)
    return np.array(komsu), B, tf, A
