"""veri/gunluk → site/veri/ozet.json + site/veri/n/<kimlik>.json"""
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

import hesap
import veri_deposu as vd

SITE = vd.KOK / "site" / "veri"
YONLER = ["kuzey", "kuzeydoğu", "doğu", "güneydoğu", "güney", "güneybatı", "batı", "kuzeybatı"]


def yon(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dl = math.radians(lo2 - lo1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    b = (math.degrees(math.atan2(x, y)) + 360) % 360
    return YONLER[int((b + 22.5) // 45) % 8]


def r2(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 2)


def main():
    hucreler = vd.hucreleri_oku()
    tarih, kaynaklar, seriler = vd.hepsini_oku()
    tarih_dizi = np.array(tarih)
    gun = np.array([hesap.gun_indeksi(t) for t in tarih])
    yil = np.array([t.year for t in tarih])

    # "bugün": tüm noktalarda değeri olan son gün
    hepsi = np.all(np.vstack([np.isfinite(v) for v in seriler.values()]), axis=0)
    k_son = int(np.where(hepsi)[0][-1])
    son = tarih[k_son]
    g_son = gun[k_son]
    son_tam_yil = son.year - 1 if son < dt.date(son.year, 12, 31) else son.year

    (SITE / "n").mkdir(parents=True, exist_ok=True)
    ozet_noktalar = []
    yillik_hepsi = {}
    for h in hucreler:
        k = h["kimlik"]
        v = seriler[k]
        ort, p10, p90 = hesap.iklim_normali(gun, yil, v)
        bugun = float(v[k_son])
        yillar_bu_tarih = hesap.bu_tarih_yillara_gore(tarih, v, son)
        digerleri = [x for y, x in yillar_bu_tarih.items() if y != son.year]
        en_sicak = max(yillar_bu_tarih.items(), key=lambda kv: kv[1])
        en_soguk = min(yillar_bu_tarih.items(), key=lambda kv: kv[1])
        yillik = hesap.yillik_ortalamalar(tarih, v)
        yillik = {y: x for y, x in yillik.items() if 1982 <= y <= son_tam_yil}
        yillik_hepsi[k] = yillik
        eg = hesap.egilim(list(yillik), list(yillik.values()))
        aylik = hesap.aylik_ortalamalar(tarih, v)
        aylik_tablo = {}
        for (yy, aa), x in aylik.items():
            aylik_tablo.setdefault(str(yy), [None] * 12)[aa - 1] = r2(x)

        bu_yil = [r2(x) for t, x in zip(tarih, v) if t.year == son.year and t <= son]
        gecen = [r2(x) for t, x in zip(tarih, v) if t.year == son.year - 1]
        if len(gecen) == 366:  # artık yıl: 29 Şubat'ı at
            del gecen[59]
        if len(bu_yil) and son.year % 4 == 0 and len(bu_yil) > 59:
            del bu_yil[59]

        egilim_ozet = {
            "egim": r2(eg["egim"]), "alt": r2(eg["alt"]), "ust": r2(eg["ust"]),
            "n": eg["n"], "n_etkin": round(eg["n_etkin"], 1), "r1": r2(eg["r1"]),
            "bas": min(yillik), "son": max(yillik),
        }
        nokta = {
            **h,
            "hucre_yon": yon(h["enlem"], h["boylam"], h["hucre_enlem"], h["hucre_boylam"]),
            "bugun": r2(bugun),
            "normal": r2(ort[g_son]),
            "anomali": r2(bugun - ort[g_son]),
            "normal_p10": r2(p10[g_son]),
            "normal_p90": r2(p90[g_son]),
            "sira": hesap.sira(bugun, digerleri),
            "yil_sayisi": len(yillar_bu_tarih),
            "en_sicak": {"yil": en_sicak[0], "deger": r2(en_sicak[1])},
            "en_soguk": {"yil": en_soguk[0], "deger": r2(en_soguk[1])},
            "egilim": egilim_ozet,
        }
        ozet_noktalar.append(nokta)
        ayrinti = {
            "kimlik": k,
            "normal": [r2(x) for x in ort],
            "p10": [r2(x) for x in p10],
            "p90": [r2(x) for x in p90],
            "bu_yil": bu_yil,
            "gecen_yil": gecen,
            "bu_tarih": {str(y): r2(x) for y, x in sorted(yillar_bu_tarih.items())},
            "yillik": {str(y): r2(x) for y, x in yillik.items()},
            "aylik": aylik_tablo,
            "egilim": {**egilim_ozet, "x_ort": float(np.mean(list(yillik))), "y_ort": round(float(np.mean(list(yillik.values()))), 4), "egim_tam": eg["egim"]},
        }
        (SITE / "n" / f"{k}.json").write_text(
            json.dumps(ayrinti, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # denizler ve tüm kıyı
    def grup(noktalar):
        ks = [n["kimlik"] for n in noktalar]
        ortak = sorted(set.intersection(*[set(yillik_hepsi[k]) for k in ks]))
        seri = [float(np.mean([yillik_hepsi[k][y] for k in ks])) for y in ortak]
        eg = hesap.egilim(ortak, seri)
        return {
            "nokta_sayisi": len(ks),
            "anomali": r2(np.mean([n["anomali"] for n in noktalar])),
            "normalden_sicak": int(sum(n["anomali"] > 0 for n in noktalar)),
            "egilim": {"egim": r2(eg["egim"]), "alt": r2(eg["alt"]), "ust": r2(eg["ust"]),
                       "n": eg["n"], "n_etkin": round(eg["n_etkin"], 1),
                       "bas": ortak[0], "son": ortak[-1]},
            "yillik": {str(y): r2(x) for y, x in zip(ortak, seri)},
            "toplam_degisim": r2(eg["egim"] * (ortak[-1] - ortak[0]) / 10),
        }

    denizler = {}
    for d in ["Karadeniz", "Marmara", "Ege", "Akdeniz"]:
        denizler[d] = grup([n for n in ozet_noktalar if n["deniz"] == d])
    ozet = {
        "guncelleme": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "son_tarih": son.isoformat(),
        "son_kaynak": kaynaklar[k_son],
        "ilk_tarih": tarih[0].isoformat(),
        "normal_donemi": "1991–2020",
        "tum_kiyi": grup(ozet_noktalar),
        "denizler": denizler,
        "noktalar": ozet_noktalar,
    }
    (SITE / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=0), encoding="utf-8")
    print("son gün", son, kaynaklar[k_son], "| tüm kıyı anomali", ozet["tum_kiyi"]["anomali"],
          "| eğilim", ozet["tum_kiyi"]["egilim"])


if __name__ == "__main__":
    main()
