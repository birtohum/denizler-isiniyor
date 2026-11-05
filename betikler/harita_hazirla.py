"""Bir kerelik: Natural Earth 1:10m ülke sınırlarından Türkiye çevresi kara şekli → site/veri/harita.json

Kullanım: python harita_hazirla.py <ne_10m_admin_0.geojson>
Natural Earth kamu malıdır (public domain).
"""
import json
import math
import sys

from shapely.geometry import box, shape
from shapely.ops import unary_union

import veri_deposu as vd

LON0, LON1, LAT0, LAT1 = 25.2, 42.0, 35.6, 42.4
KX = math.cos(math.radians(39.0))
GEN = 1000.0
OLCEK = GEN / ((LON1 - LON0) * KX)
YUK = (LAT1 - LAT0) * OLCEK


def xy(lon, lat):
    return (lon - LON0) * KX * OLCEK, (LAT1 - lat) * OLCEK


def yol(geom):
    parcalar = []
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        if p.geom_type != "Polygon" or p.area < 0.0005:
            continue
        for halka in [p.exterior, *p.interiors]:
            pts = [xy(x, y) for x, y in halka.coords]
            parcalar.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(parcalar)


veri = json.load(open(sys.argv[1], encoding="utf-8"))
kutu = box(LON0 - 0.5, LAT0 - 0.5, LON1 + 0.5, LAT1 + 0.5)
tr, diger = [], []
for f in veri["features"]:
    g = shape(f["geometry"])
    if not g.intersects(kutu):
        continue
    g = g.intersection(kutu).simplify(0.01, preserve_topology=True)
    (tr if f["properties"]["ADM0_A3"] == "TUR" else diger).append(g)

out = {
    "genislik": GEN, "yukseklik": round(YUK, 1),
    "lon0": LON0, "lat1": LAT1, "kx": KX, "olcek": OLCEK,
    "turkiye": yol(unary_union(tr)),
    "diger": yol(unary_union(diger)),
}
(vd.KOK / "site" / "veri").mkdir(parents=True, exist_ok=True)
(vd.KOK / "site" / "veri" / "harita.json").write_text(json.dumps(out), encoding="utf-8")
print(len(out["turkiye"]) + len(out["diger"]), "karakter")
