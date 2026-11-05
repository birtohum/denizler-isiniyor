"""NOAA OISST v2.1 (günlük, 0,25°) Türkiye kutusu indirici.

Kaynak: NOAA CoastWatch West Coast ERDDAP (hesap gerekmez).
  - ncdcOisst21Agg     : nihai (final) seri, 1981-09-01'den, ~2 hafta gecikmeli
  - ncdcOisst21NrtAgg  : ön (preliminary / NRT) seri, 2020-05'ten, ~1-2 gün gecikmeli

Yalnız Türkiye çevresindeki küçük kutu indirilir (yaklaşık 33 x 69 hücre).
"""
from __future__ import annotations

import datetime as dt
import io
import re
import time
from pathlib import Path

import numpy as np
import requests
from scipy.io import netcdf_file

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
NIHAI = "ncdcOisst21Agg"
ON = "ncdcOisst21NrtAgg"

# Türkiye kıyılarını saran kutu
ENLEM = (35.0, 43.0)
BOYLAM = (25.0, 42.0)

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "kaynak_ham"

OTURUM = requests.Session()
OTURUM.headers["User-Agent"] = "denizler-isiniyor/1.0 (github.com/birtohum/denizler-isiniyor)"


def _al(url: str, deneme: int = 5, zaman: int = 300) -> bytes:
    son_hata = None
    for i in range(deneme):
        try:
            r = OTURUM.get(url, timeout=zaman)
            if r.status_code == 200:
                return r.content
            son_hata = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.RequestException as e:  # ağ hatası
            son_hata = repr(e)
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"İndirilemedi: {url}\n{son_hata}")


def bitis_tarihi(veri_kumesi: str) -> dt.date:
    """ERDDAP'taki son mevcut gün."""
    das = _al(f"{ERDDAP}/{veri_kumesi}.das", zaman=120).decode("utf-8", "replace")
    m = re.search(r'time_coverage_end "(\d{4}-\d{2}-\d{2})', das)
    if not m:
        raise RuntimeError("time_coverage_end bulunamadı")
    return dt.date.fromisoformat(m.group(1))


def kutu_url(veri_kumesi: str, bas: dt.date, son: dt.date) -> str:
    q = (
        f"sst[({bas}T12:00:00Z):1:({son}T12:00:00Z)][(0.0)]"
        f"[({ENLEM[0]}):1:({ENLEM[1]})][({BOYLAM[0]}):1:({BOYLAM[1]})]"
    )
    q = q.replace("[", "%5B").replace("]", "%5D")
    return f"{ERDDAP}/{veri_kumesi}.nc?{q}"


def nc_oku(icerik: bytes):
    """ERDDAP .nc (NetCDF-3) -> (tarihler, enlemler, boylamlar, sst[t, y, x])."""
    with netcdf_file(io.BytesIO(icerik), "r", mmap=False) as f:
        t = np.array(f.variables["time"][:], dtype=float)
        lat = np.array(f.variables["latitude"][:], dtype=float)
        lon = np.array(f.variables["longitude"][:], dtype=float)
        v = f.variables["sst"]
        sst = np.array(v[:], dtype=float)
        dolgu = getattr(v, "_FillValue", None)
        olcek = getattr(v, "scale_factor", 1.0)
        ofset = getattr(v, "add_offset", 0.0)
    if sst.ndim == 4:
        sst = sst[:, 0, :, :]
    if dolgu is not None:
        sst[sst == float(np.asarray(dolgu).ravel()[0])] = np.nan
    sst = sst * olcek + ofset
    sst[(sst < -5) | (sst > 45)] = np.nan
    tarih = [dt.datetime.fromtimestamp(s, dt.timezone.utc).date() for s in t]
    return tarih, lat, lon, sst


def kutu_indir(veri_kumesi: str, bas: dt.date, son: dt.date):
    return nc_oku(_al(kutu_url(veri_kumesi, bas, son)))


def yil_dosyasi(yil: int, son_nihai: dt.date, yenile: bool = False) -> Path:
    """Nihai seriden bir yılın kutusunu indirip kaynak_ham/'a yazar (varsa atlar)."""
    HAM.mkdir(exist_ok=True)
    yol = HAM / f"nihai_{yil}.nc"
    bas = max(dt.date(yil, 1, 1), dt.date(1981, 9, 1))
    son = min(dt.date(yil, 12, 31), son_nihai)
    tam_yil = son == dt.date(yil, 12, 31)
    if yol.exists() and tam_yil and not yenile:
        return yol
    yol.write_bytes(_al(kutu_url(NIHAI, bas, son)))
    return yol


# ---------- NOAA PSL THREDDS (aynı OISST v2.1, yıllık dosyalar) ----------
# CoastWatch ERDDAP birleşik kümesinde bazı günler eksik (ör. 1993'te 163 gün);
# eksikler PSL OPeNDAP'tan küçük kutu olarak (ASCII) tamamlanır.
PSL = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/sst.day.mean.{yil}.nc"
PSL_ENLEM_I = (500, 532)   # 35.125 … 43.125
PSL_BOYLAM_I = (100, 168)  # 25.125 … 42.125


def psl_ascii_oku(metin: str, n_t: int):
    ny = PSL_ENLEM_I[1] - PSL_ENLEM_I[0] + 1
    nx = PSL_BOYLAM_I[1] - PSL_BOYLAM_I[0] + 1
    sst = np.full((n_t, ny, nx), np.nan)
    veri_basladi = False
    for satir in metin.splitlines():
        if satir.startswith("sst.sst"):
            veri_basladi = True
            continue
        if not veri_basladi:
            continue
        if satir.startswith("sst.") or not satir.startswith("["):
            if satir.startswith("sst."):
                break
            continue
        bas, _, geri = satir.partition("],")
        t, i = (int(x) for x in bas.strip("[").split("]["))
        sst[t, i, :] = [float(x) for x in geri.split(",")]
    sst[(sst < -5) | (sst > 45)] = np.nan
    return sst


def psl_indir(bas: dt.date, son: dt.date):
    """Aynı yıl içinde [bas, son] → (tarihler, enlemler, boylamlar, sst)."""
    assert bas.year == son.year
    ilk = dt.date(1981, 9, 1) if bas.year == 1981 else dt.date(bas.year, 1, 1)
    t0, t1 = (bas - ilk).days, (son - ilk).days
    q = (f"sst[{t0}:1:{t1}][{PSL_ENLEM_I[0]}:1:{PSL_ENLEM_I[1]}]"
         f"[{PSL_BOYLAM_I[0]}:1:{PSL_BOYLAM_I[1]}]").replace("[", "%5B").replace("]", "%5D")
    metin = _al(PSL.format(yil=bas.year) + ".ascii?" + q).decode("ascii", "replace")
    n = t1 - t0 + 1
    sst = psl_ascii_oku(metin, n)
    lat = 35.125 + 0.25 * np.arange(sst.shape[1])
    lon = 25.125 + 0.25 * np.arange(sst.shape[2])
    tarih = [bas + dt.timedelta(days=k) for k in range(n)]
    return tarih, lat, lon, sst
