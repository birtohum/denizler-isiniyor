"""veri/gunluk/YYYY.csv okuma-yazma ve kutudan nokta çıkarma."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parents[1]
VERI = KOK / "veri"
GUNLUK = VERI / "gunluk"
HUCRELER = VERI / "hucreler.json"


def hucreleri_oku():
    return json.loads(HUCRELER.read_text(encoding="utf-8"))


def kutudan_noktalar(tarih, lat, lon, sst, hucreler):
    """{tarih: {kimlik: deger}} — hücreler enlem/boylam değeriyle bulunur (kutu farklı olabilir)."""
    sonuc = {t: {} for t in tarih}
    for h in hucreler:
        i = int(np.argmin(np.abs(lat - h["hucre_enlem"])))
        j = int(np.argmin(np.abs(lon - h["hucre_boylam"])))
        if abs(lat[i] - h["hucre_enlem"]) > 0.01 or abs(lon[j] - h["hucre_boylam"]) > 0.01:
            raise ValueError(f"{h['kimlik']} hücresi kutuda yok")
        for k, t in enumerate(tarih):
            v = sst[k, i, j]
            sonuc[t][h["kimlik"]] = None if not np.isfinite(v) else round(float(v), 2)
    return sonuc


def yil_oku(yil: int):
    """{tarih: (kaynak, {kimlik: deger})}"""
    yol = GUNLUK / f"{yil}.csv"
    if not yol.exists():
        return {}
    out = {}
    with yol.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for satir in r:
            t = dt.date.fromisoformat(satir.pop("tarih"))
            kay = satir.pop("kaynak")
            out[t] = (kay, {k: (float(v) if v != "" else None) for k, v in satir.items()})
    return out


def yil_yaz(yil: int, kayitlar, kimlikler):
    GUNLUK.mkdir(parents=True, exist_ok=True)
    yol = GUNLUK / f"{yil}.csv"
    with yol.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["tarih", "kaynak", *kimlikler])
        for t in sorted(kayitlar):
            kay, d = kayitlar[t]
            w.writerow([t.isoformat(), kay, *["" if d.get(k) is None else f"{d[k]:.2f}" for k in kimlikler]])


def birlestir(yeni, kaynak_adi, kimlikler):
    """yeni: {tarih: {kimlik: deger}} — ilgili yıl dosyalarına yazar (aynı tarih üzerine yazılır).

    'nihai' kayıt 'on' ile ezilmez.
    """
    yillar = sorted({t.year for t in yeni})
    for y in yillar:
        mevcut = yil_oku(y)
        for t, d in yeni.items():
            if t.year != y:
                continue
            if kaynak_adi == "on" and t in mevcut and mevcut[t][0] == "nihai":
                continue
            mevcut[t] = (kaynak_adi, d)
        yil_yaz(y, mevcut, kimlikler)


def hepsini_oku():
    """(tarihler listesi, kaynaklar listesi, {kimlik: np.array})"""
    kimlikler = [h["kimlik"] for h in hucreleri_oku()]
    tarih, kay, deger = [], [], {k: [] for k in kimlikler}
    for yol in sorted(GUNLUK.glob("*.csv")):
        for t, (ka, d) in sorted(yil_oku(int(yol.stem)).items()):
            tarih.append(t)
            kay.append(ka)
            for k in kimlikler:
                v = d.get(k)
                deger[k].append(np.nan if v is None else v)
    return tarih, kay, {k: np.array(v, float) for k, v in deger.items()}
