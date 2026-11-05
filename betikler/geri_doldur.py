"""Bir kerelik: 1981-09'dan bugüne nihai seriyi yıl yıl indirir (kaynak_ham/, git dışı)."""
import sys
import time

import kaynak

son = kaynak.bitis_tarihi(kaynak.NIHAI)
print("nihai seri sonu:", son, flush=True)
for yil in range(1981, son.year + 1):
    t0 = time.time()
    yol = kaynak.yil_dosyasi(yil, son, yenile=(yil == son.year))
    print(yil, yol.stat().st_size, f"{time.time() - t0:.0f} sn", flush=True)
    time.sleep(1)
sys.exit(0)
