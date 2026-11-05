"""Her kıyı noktası için en yakın OISST deniz hücresini seçer → veri/hucreler.json.

Deniz maskesi: verilen nihai yıl dosyasında her gün değeri olan hücreler
(OISST'nin kara maskesi sabittir).
"""
import json
import sys

import numpy as np

import hesap
import kaynak
from noktalar import NOKTALAR
from veri_deposu import HUCRELER

yil = int(sys.argv[1]) if len(sys.argv) > 1 else 2019
tarih, lat, lon, sst = kaynak.nc_oku((kaynak.HAM / f"nihai_{yil}.nc").read_bytes())
deniz = np.all(np.isfinite(sst), axis=0)
print("deniz hücresi:", int(deniz.sum()), "/", deniz.size)

out = []
for kimlik, ad, den, la, lo in NOKTALAR:
    i, j, km = hesap.en_yakin_deniz_hucresi(la, lo, lat, lon, deniz)
    out.append({
        "kimlik": kimlik, "ad": ad, "deniz": den, "enlem": la, "boylam": lo,
        "hucre_enlem": float(lat[i]), "hucre_boylam": float(lon[j]), "uzaklik_km": round(km, 1),
    })
    print(f"{ad:18s} {den:10s} → {lat[i]:.3f},{lon[j]:.3f}  {km:5.1f} km")

# aynı hücreye düşen noktalar
from collections import Counter
c = Counter((h["hucre_enlem"], h["hucre_boylam"]) for h in out)
for k, n in c.items():
    if n > 1:
        print("PAYLAŞILAN HÜCRE", k, [h["ad"] for h in out if (h["hucre_enlem"], h["hucre_boylam"]) == k])

# maske (harita için): deniz hücre merkezleri
HUCRELER.parent.mkdir(exist_ok=True)
HUCRELER.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
