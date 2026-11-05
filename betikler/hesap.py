"""Saf hesaplar: ızgara hücresi seçimi, iklim normali, anomali, eğilim. (Testli.)"""
from __future__ import annotations

import datetime as dt
import math

import numpy as np
from scipy import stats

DUNYA_YARICAPI_KM = 6371.0088


# ---------- ızgara hücresi ----------

def mesafe_km(enlem1, boylam1, enlem2, boylam2):
    """Büyük daire (haversine) mesafesi, km. Dizi kabul eder."""
    p1, p2 = np.radians(enlem1), np.radians(enlem2)
    dp = p2 - p1
    dl = np.radians(np.asarray(boylam2) - np.asarray(boylam1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * DUNYA_YARICAPI_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def en_yakin_deniz_hucresi(enlem, boylam, enlemler, boylamlar, deniz, azami_km=60.0):
    """En yakın deniz hücresinin (i, j, km) değeri.

    enlemler: (ny,), boylamlar: (nx,) hücre merkezleri; deniz: (ny, nx) bool.
    Azami mesafede deniz hücresi yoksa ValueError.
    """
    enlemler = np.asarray(enlemler, float)
    boylamlar = np.asarray(boylamlar, float)
    deniz = np.asarray(deniz, bool)
    if deniz.shape != (enlemler.size, boylamlar.size):
        raise ValueError("maske boyutu enlem/boylam ile uyuşmuyor")
    LA, LO = np.meshgrid(enlemler, boylamlar, indexing="ij")
    d = mesafe_km(enlem, boylam, LA, LO)
    d = np.where(deniz, d, np.inf)
    k = int(np.argmin(d))
    i, j = np.unravel_index(k, d.shape)
    if not math.isfinite(d[i, j]) or d[i, j] > azami_km:
        raise ValueError(f"{azami_km} km içinde deniz hücresi yok")
    return int(i), int(j), float(d[i, j])


# ---------- takvim ----------

def gun_indeksi(tarih: dt.date) -> int:
    """365 günlük takvimde 0..364. 29 Şubat, 28 Şubat ile aynı güne (58) düşer."""
    if tarih.month == 2 and tarih.day == 29:
        return 58
    ilk = dt.date(tarih.year, 1, 1)
    n = (tarih - ilk).days
    artik = tarih.year % 4 == 0 and (tarih.year % 100 != 0 or tarih.year % 400 == 0)
    if artik and tarih.month > 2:
        n -= 1
    return n


def dairesel_fark(a, b, n=365):
    d = np.abs(np.asarray(a) - np.asarray(b)) % n
    return np.minimum(d, n - d)


# ---------- iklim normali ve anomali ----------

def iklim_normali(gunler, yillar, degerler, bas=1991, son=2020, pencere=5):
    """Her takvim günü için (ortalama, %10, %90), bas–son yıllarında ±pencere gün.

    gunler: gun_indeksi dizisi, yillar: yıl dizisi, degerler: °C (NaN olabilir).
    Dönüş: üç tane (365,) dizi.
    """
    gunler = np.asarray(gunler)
    yillar = np.asarray(yillar)
    degerler = np.asarray(degerler, float)
    ref = (yillar >= bas) & (yillar <= son) & np.isfinite(degerler)
    g, v = gunler[ref], degerler[ref]
    ort = np.full(365, np.nan)
    p10 = np.full(365, np.nan)
    p90 = np.full(365, np.nan)
    for d in range(365):
        s = v[dairesel_fark(g, d) <= pencere]
        if s.size:
            ort[d] = s.mean()
            p10[d], p90[d] = np.percentile(s, [10, 90])
    return ort, p10, p90


def anomali(deger, gun, normal):
    return float(deger) - float(normal[gun])


def bu_tarih_yillara_gore(tarihler, degerler, hedef: dt.date):
    """Her yıl için hedefle aynı takvim günündeki değer: {yil: deger}."""
    hg = gun_indeksi(hedef)
    sonuc = {}
    for t, v in zip(tarihler, degerler):
        if gun_indeksi(t) == hg and t.year not in sonuc and np.isfinite(v):
            sonuc[t.year] = float(v)
    return sonuc


def sira(deger, digerleri):
    """Değerin, digerleri içinde sıcaktan soğuğa kaçıncı olduğu (1 = en sıcak)."""
    return 1 + int(sum(1 for x in digerleri if x > deger))


# ---------- yıllık / aylık ortalamalar ----------

def yillik_ortalamalar(tarihler, degerler, asgari_gun=360):
    toplam, sayi = {}, {}
    for t, v in zip(tarihler, degerler):
        if np.isfinite(v):
            toplam[t.year] = toplam.get(t.year, 0.0) + v
            sayi[t.year] = sayi.get(t.year, 0) + 1
    return {y: toplam[y] / sayi[y] for y in sorted(toplam) if sayi[y] >= asgari_gun}


def aylik_ortalamalar(tarihler, degerler, asgari_gun=28):
    """{(yil, ay): ortalama}; eksik aylar (< asgari_gun) atlanır."""
    toplam, sayi = {}, {}
    for t, v in zip(tarihler, degerler):
        if np.isfinite(v):
            k = (t.year, t.month)
            toplam[k] = toplam.get(k, 0.0) + v
            sayi[k] = sayi.get(k, 0) + 1
    return {k: toplam[k] / sayi[k] for k in sorted(toplam) if sayi[k] >= asgari_gun}


# ---------- eğilim ----------

def egilim(yillar, degerler, guven=0.95):
    """En küçük kareler eğilimi, °C / 10 yıl, birinci derece öz ilinti düzeltmeli güven aralığı.

    Santer vd. (2000): artıkların gecikme-1 öz ilintisi r1 > 0 ise etkin örnek
    n_e = n (1 - r1) / (1 + r1); standart hata sqrt((n-2)/(n_e-2)) ile büyütülür,
    t dağılımı n_e - 2 serbestlik derecesiyle kullanılır.
    Dönüş: dict(egim, alt, ust, se, r1, n, n_etkin, p)
    """
    x = np.asarray(yillar, float)
    y = np.asarray(degerler, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = x.size
    if n < 5:
        raise ValueError("eğilim için en az 5 yıl gerekir")
    xm = x - x.mean()
    b = float((xm * (y - y.mean())).sum() / (xm ** 2).sum())
    a = float(y.mean() - b * x.mean())
    art = y - (a + b * x)
    se = math.sqrt((art ** 2).sum() / (n - 2) / (xm ** 2).sum())
    r1 = float(np.corrcoef(art[:-1], art[1:])[0, 1]) if n > 3 else 0.0
    if not math.isfinite(r1):
        r1 = 0.0
    ne = n * (1 - r1) / (1 + r1) if r1 > 0 else float(n)
    ne = max(ne, 3.0)
    se_d = se * math.sqrt((n - 2) / (ne - 2)) if ne > 2 else float("inf")
    tk = float(stats.t.ppf(0.5 + guven / 2, ne - 2))
    p = float(2 * stats.t.sf(abs(b) / se_d, ne - 2)) if se_d > 0 else 0.0
    return {
        "egim": b * 10,
        "alt": (b - tk * se_d) * 10,
        "ust": (b + tk * se_d) * 10,
        "se": se_d * 10,
        "r1": r1,
        "n": int(n),
        "n_etkin": float(ne),
        "p": p,
        "kesisim": a,
    }
