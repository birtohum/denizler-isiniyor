"""Nokta serilerini günceller → veri/gunluk/YYYY.csv

  python guncelle.py --yerel   : kaynak_ham/nihai_*.nc dosyalarından (geri doldurma sonrası)
  python guncelle.py           : ERDDAP'tan son 40 gün nihai + sonrası ön (NRT) seri (günlük iş)
"""
import datetime as dt
import sys

import kaynak
import veri_deposu as vd

hucreler = vd.hucreleri_oku()
kimlikler = [h["kimlik"] for h in hucreler]

if "--yerel" in sys.argv:
    for yol in sorted(kaynak.HAM.glob("nihai_*.nc")):
        t, la, lo, s = kaynak.nc_oku(yol.read_bytes())
        vd.birlestir(vd.kutudan_noktalar(t, la, lo, s, hucreler), "nihai", kimlikler)
        print(yol.name, len(t), "gün", flush=True)
else:
    son_n = kaynak.bitis_tarihi(kaynak.NIHAI)
    bas = son_n - dt.timedelta(days=40)
    t, la, lo, s = kaynak.kutu_indir(kaynak.NIHAI, bas, son_n)
    vd.birlestir(vd.kutudan_noktalar(t, la, lo, s, hucreler), "nihai", kimlikler)
    print("nihai", t[0], "→", t[-1], flush=True)
    son_o = kaynak.bitis_tarihi(kaynak.ON)
    if son_o > son_n:
        t, la, lo, s = kaynak.kutu_indir(kaynak.ON, son_n + dt.timedelta(days=1), son_o)
        vd.birlestir(vd.kutudan_noktalar(t, la, lo, s, hucreler), "on", kimlikler)
        print("ön", t[0], "→", t[-1], flush=True)
