"""Nihai serideki eksik günleri NOAA PSL'den tamamlar.

  python bosluk_doldur.py            : tüm yıllar
  python bosluk_doldur.py --gun 60   : yalnız son 60 gün (günlük iş)
"""
import datetime as dt
import sys

import numpy as np

import kaynak
import veri_deposu as vd

hucreler = vd.hucreleri_oku()
kimlikler = [h["kimlik"] for h in hucreler]
son_n = kaynak.bitis_tarihi(kaynak.NIHAI)
bas = dt.date(1981, 9, 1)
if "--gun" in sys.argv:
    bas = son_n - dt.timedelta(days=int(sys.argv[sys.argv.index("--gun") + 1]))

eksik = []
for yil in range(bas.year, son_n.year + 1):
    var = vd.yil_oku(yil)
    t = max(bas, dt.date(yil, 1, 1))
    while t <= min(son_n, dt.date(yil, 12, 31)):
        if t not in var or var[t][0] != "nihai":
            eksik.append(t)
        t += dt.timedelta(days=1)
print("eksik gün:", len(eksik), flush=True)

# aynı aydaki eksikler tek istekte: ilk eksikten son eksiğe kadar
aylar = {}
for t in eksik:
    aylar.setdefault((t.year, t.month), []).append(t)
parcalar = [v for _, v in sorted(aylar.items())]
for p in parcalar:
    try:
        tt, la, lo, s = kaynak.psl_indir(p[0], p[-1])
    except RuntimeError as e:  # PSL'de henüz yok (ör. çok yeni gün)
        print("atlandı", p[0], p[-1], str(e)[:120], flush=True)
        continue
    vd.birlestir(vd.kutudan_noktalar(tt, la, lo, s, hucreler), "nihai", kimlikler)
    print(p[0], "→", p[-1], flush=True)

if "--dene" in sys.argv:  # PSL erişim denetimi (tek gün, ~30 KB)
    tt, la, lo, s = kaynak.psl_indir(son_n, son_n)
    print("PSL erişimi tamam:", tt[0], f"{float(np.nanmean(s)):.2f} °C ortalama")
