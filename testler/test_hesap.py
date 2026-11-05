import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "betikler"))
import hesap  # noqa: E402


# ---------- ızgara hücresi ----------

def test_mesafe_bilinen():
    # 1 derece enlem ≈ 111,2 km
    assert hesap.mesafe_km(40, 30, 41, 30) == pytest.approx(111.2, abs=0.2)
    # 41° enleminde 1 derece boylam ≈ 83,9 km
    assert hesap.mesafe_km(41, 29, 41, 30) == pytest.approx(83.9, abs=0.3)


def _izgara():
    enlemler = np.array([40.125, 40.375, 40.625])
    boylamlar = np.array([28.125, 28.375, 28.625, 28.875])
    deniz = np.array([
        [False, False, True, True],
        [False, False, False, True],
        [True, False, False, False],
    ])
    return enlemler, boylamlar, deniz


def test_kara_hucresi_atlanir():
    la, lo, deniz = _izgara()
    # nokta tam (40.375, 28.375) kara hücresinde; en yakın deniz komşusu
    i, j, km = hesap.en_yakin_deniz_hucresi(40.375, 28.375, la, lo, deniz)
    assert deniz[i, j]
    # adaylar: (0,2) ~ (40.125, 28.625), (2,0) ~ (40.625, 28.125): ikisi de çapraz komşu.
    # boylam derecesi enlem derecesinden kısa olduğundan mesafeler eşit değil; hangisi yakınsa o.
    d02 = hesap.mesafe_km(40.375, 28.375, 40.125, 28.625)
    d20 = hesap.mesafe_km(40.375, 28.375, 40.625, 28.125)
    beklenen = (0, 2) if d02 < d20 else (2, 0)
    assert (i, j) == beklenen
    assert km == pytest.approx(min(d02, d20))


def test_deniz_hucresinin_icindeyse_kendisi():
    la, lo, deniz = _izgara()
    i, j, km = hesap.en_yakin_deniz_hucresi(40.13, 28.88, la, lo, deniz)
    assert (i, j) == (0, 3)
    assert km < 2


def test_azami_mesafe():
    la, lo, deniz = _izgara()
    with pytest.raises(ValueError):
        hesap.en_yakin_deniz_hucresi(38.0, 28.0, la, lo, deniz, azami_km=60)


def test_maske_boyutu_denetlenir():
    la, lo, deniz = _izgara()
    with pytest.raises(ValueError):
        hesap.en_yakin_deniz_hucresi(40.3, 28.3, la, lo, deniz[:, :3])


# ---------- takvim ----------

def test_gun_indeksi_artik_yil():
    assert hesap.gun_indeksi(dt.date(2023, 1, 1)) == 0
    assert hesap.gun_indeksi(dt.date(2023, 12, 31)) == 364
    assert hesap.gun_indeksi(dt.date(2024, 12, 31)) == 364
    assert hesap.gun_indeksi(dt.date(2024, 2, 29)) == 58
    assert hesap.gun_indeksi(dt.date(2024, 3, 1)) == hesap.gun_indeksi(dt.date(2023, 3, 1)) == 59
    assert hesap.gun_indeksi(dt.date(2000, 8, 15)) == hesap.gun_indeksi(dt.date(2001, 8, 15))
    assert hesap.gun_indeksi(dt.date(1900, 3, 1)) == 59  # 1900 artık değil


def test_dairesel_fark():
    assert hesap.dairesel_fark(0, 364) == 1
    assert hesap.dairesel_fark(10, 3) == 7


# ---------- iklim, anomali ----------

def _sentetik(bas=1982, son=2025, isinma_10yil=0.0, gurultu=0.0, tohum=0):
    rng = np.random.default_rng(tohum)
    t = dt.date(bas, 1, 1)
    tarih, deger = [], []
    while t <= dt.date(son, 12, 31):
        g = hesap.gun_indeksi(t)
        v = 18 + 6 * np.sin(2 * np.pi * (g - 120) / 365) + isinma_10yil * (t.year - 2000) / 10
        v += gurultu * rng.standard_normal()
        tarih.append(t)
        deger.append(v)
        t += dt.timedelta(days=1)
    return tarih, np.array(deger)


def test_iklim_normali_mevsim_dongusunu_verir():
    tarih, deger = _sentetik()
    gun = [hesap.gun_indeksi(t) for t in tarih]
    yil = [t.year for t in tarih]
    ort, p10, p90 = hesap.iklim_normali(gun, yil, deger, pencere=0)
    for g in (0, 100, 211, 364):
        assert ort[g] == pytest.approx(18 + 6 * np.sin(2 * np.pi * (g - 120) / 365), abs=1e-9)
    assert np.all(p10 <= ort + 1e-9) and np.all(ort <= p90 + 1e-9)


def test_iklim_yalniz_referans_yillari():
    # 1991-2020 dışındaki yıllara +10 eklensin: normal değişmemeli
    tarih, deger = _sentetik()
    deger2 = deger.copy()
    for k, t in enumerate(tarih):
        if t.year < 1991 or t.year > 2020:
            deger2[k] += 10
    gun = [hesap.gun_indeksi(t) for t in tarih]
    yil = [t.year for t in tarih]
    a, _, _ = hesap.iklim_normali(gun, yil, deger, pencere=5)
    b, _, _ = hesap.iklim_normali(gun, yil, deger2, pencere=5)
    assert np.allclose(a, b)


def test_iklim_pencere_yil_sinirini_asar():
    # 1 Ocak'ın ±5 günlük penceresi Aralık sonunu da içermeli
    gun = np.array([362, 0, 3])
    yil = np.array([2000, 2000, 2000])
    deger = np.array([10.0, 20.0, 30.0])
    ort, _, _ = hesap.iklim_normali(gun, yil, deger, pencere=5)
    assert ort[0] == pytest.approx(20.0)


def test_anomali_isinan_seride_pozitif():
    tarih, deger = _sentetik(isinma_10yil=0.5)
    gun = [hesap.gun_indeksi(t) for t in tarih]
    yil = [t.year for t in tarih]
    ort, _, _ = hesap.iklim_normali(gun, yil, deger, pencere=0)
    # 1991-2020 ortası 2005.5 → 2025'te beklenen anomali 0,5 * (2025 - 2005.5) / 10
    k = tarih.index(dt.date(2025, 8, 15))
    assert hesap.anomali(deger[k], gun[k], ort) == pytest.approx(0.5 * 19.5 / 10, abs=1e-9)


def test_bu_tarih_ve_sira():
    tarih, deger = _sentetik(isinma_10yil=0.3)
    d = hesap.bu_tarih_yillara_gore(tarih, deger, dt.date(2025, 8, 15))
    assert sorted(d) == list(range(1982, 2026))
    assert max(d, key=d.get) == 2025 and min(d, key=d.get) == 1982
    assert hesap.sira(d[2025], [v for y, v in d.items() if y != 2025]) == 1
    assert hesap.sira(d[1982], [v for y, v in d.items() if y != 1982]) == 44


def test_yillik_aylik_eksikleri_atar():
    tarih, deger = _sentetik(bas=2000, son=2001)
    deger = deger.copy()
    deger[:10] = np.nan  # 2000'de 10 gün eksik → 356 gün < 360
    y = hesap.yillik_ortalamalar(tarih, deger)
    assert list(y) == [2001]
    a = hesap.aylik_ortalamalar(tarih, deger)
    assert (2000, 1) not in a  # Ocak'ta 31 - 10 = 21 gün < 28
    assert (2000, 2) in a


# ---------- eğilim ----------

def test_egilim_kusursuz_dogru():
    yil = np.arange(1982, 2026)
    e = hesap.egilim(yil, 20 + 0.04 * (yil - 1982))
    assert e["egim"] == pytest.approx(0.4)
    assert e["alt"] == pytest.approx(0.4) and e["ust"] == pytest.approx(0.4)


def test_egilim_gurultulu_aralik_gercek_degeri_kapsar():
    # 300 sentetik seride %95 aralığı gerçek eğimi yaklaşık %95 kapsamalı (AR(1) gürültü)
    rng = np.random.default_rng(1)
    yil = np.arange(1982, 2026)
    kapsar = 0
    for _ in range(300):
        e = np.zeros(yil.size)
        for k in range(yil.size):
            e[k] = (0.5 * e[k - 1] if k else 0) + 0.3 * rng.standard_normal()
        r = hesap.egilim(yil, 0.03 * yil + e)
        kapsar += r["alt"] <= 0.3 <= r["ust"]
    assert 0.88 <= kapsar / 300 <= 0.99


def test_egilim_oz_ilinti_araligi_genisletir():
    rng = np.random.default_rng(2)
    yil = np.arange(1982, 2026)
    e = np.cumsum(rng.standard_normal(yil.size)) * 0.1  # güçlü öz ilinti
    r = hesap.egilim(yil, e)
    assert r["r1"] > 0.3
    assert r["n_etkin"] < r["n"]
    xm = yil - yil.mean()
    b = (xm * (e - e.mean())).sum() / (xm ** 2).sum()
    art = e - (e.mean() + b * xm)
    se_saf = np.sqrt((art ** 2).sum() / (yil.size - 2) / (xm ** 2).sum()) * 10
    assert r["se"] > se_saf


def test_egilim_az_veri():
    with pytest.raises(ValueError):
        hesap.egilim([2000, 2001, 2002], [1, 2, 3])
