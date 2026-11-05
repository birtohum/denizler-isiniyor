import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "betikler"))
import kaynak  # noqa: E402
import veri_deposu as vd  # noqa: E402


def test_psl_ascii_ayristirma():
    ny, nx = 33, 69
    satirlar = ["Dataset {", "} x;", "-" * 10, f"sst.sst[2][{ny}][{nx}]"]
    for t in range(2):
        for i in range(ny):
            vals = [-9.96921e36 if j == 0 else 10 + t + i * 0.01 + j * 0.001 for j in range(nx)]
            satirlar.append(f"[{t}][{i}], " + ", ".join(f"{v:g}" for v in vals))
    satirlar += ["", "sst.time[2]", "1.0, 2.0"]
    s = kaynak.psl_ascii_oku("\n".join(satirlar), 2)
    assert s.shape == (2, ny, nx)
    assert np.isnan(s[0, 0, 0])
    assert s[1, 5, 7] == np.float64(float(f"{11 + 0.05 + 0.007:g}"))


def test_kutudan_noktalar_hucreyi_degerle_bulur():
    import datetime as dt
    lat = np.array([40.125, 40.375])
    lon = np.array([28.125, 28.375, 28.625])
    sst = np.arange(6, dtype=float).reshape(1, 2, 3)
    sst[0, 0, 0] = np.nan
    h = [{"kimlik": "a", "hucre_enlem": 40.375, "hucre_boylam": 28.625},
         {"kimlik": "b", "hucre_enlem": 40.125, "hucre_boylam": 28.125}]
    d = vd.kutudan_noktalar([dt.date(2020, 1, 1)], lat, lon, sst, h)
    assert d[dt.date(2020, 1, 1)] == {"a": 5.0, "b": None}
