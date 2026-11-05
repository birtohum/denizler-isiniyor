# Denizler ısınıyor mu?

Türkiye'nin 41 kıyı noktasında bugünkü deniz yüzeyi sıcaklığı, 1981'den bu yana aynı takvim günüyle karşılaştırma ve uzun dönem eğilim.

Site: https://birtohum.github.io/denizler-isiniyor/

## Veri

- **NOAA OISST v2.1**, günlük, 0,25° ızgara (Huang vd., 2021, *J. Climate*). Hesap gerekmez.
  - Nihai seri: [NOAA CoastWatch ERDDAP `ncdcOisst21Agg`](https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg.html) (yaklaşık 2 hafta gecikmeli).
  - Ön seri (son ~2 hafta): ERDDAP `ncdcOisst21NrtAgg`. Nihai gelince üzerine yazılır.
  - ERDDAP birleşik kümesinde bazı günler eksik (ör. 1992–1998 arası yüzlerce gün). Bunlar aynı ürünün [NOAA PSL THREDDS](https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html) yıllık dosyalarından OPeNDAP ile tamamlanır; ortak günlerde iki kaynak birebir aynıdır.
- Yalnız Türkiye çevresindeki 33 × 69 hücrelik kutu indirilir.
- Kıyı çizgisi: Natural Earth 1:10m (kamu malı).

## Yöntem

- **Hücre seçimi** (`betikler/hucre_sec.py`, `hesap.en_yakin_deniz_hucresi`): her noktaya, her gün değeri olan en yakın deniz hücresi (büyük daire mesafesi). Uzaklıklar 0,7–26,7 km.
- **Normal**: 1991–2020, aynı takvim gününün ±5 gün penceresi (29 Şubat = 28 Şubat).
- **Anomali**: bugünkü değer − normal.
- **En sıcak / en soğuk yıl**: yalnız o takvim günündeki tek günlük değerler.
- **Eğilim**: 1982'den son tam yıla yıllık ortalamalara en küçük kareler. %95 güven aralığı, artıkların birinci derece öz ilintisine göre etkin örnek sayısıyla genişletilir (Santer vd., 2000).

## Çalıştırma

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cd betikler
python geri_doldur.py          # bir kerelik, kaynak_ham/ (git dışı, ~150 MB)
python hucre_sec.py 1981       # veri/hucreler.json
python guncelle.py --yerel     # veri/gunluk/YYYY.csv
python bosluk_doldur.py        # eksik günler PSL'den
python hesapla.py              # site/veri/
python -m pytest -q ../testler
```

Günlük iş (`.github/workflows/guncelle.yml`): son 40 gün nihai + ön seri, son 60 günde boşluk doldurma, hesap, commit; ardından Pages yayını.

## Sınırlar

Uydu ölçümü kumsaldaki suyu değil ~25 km'lik karenin ortalamasını verir; bulutlu günler istatistiksel olarak doldurulmuştur; kıyı kareleri ve dar körfezler (İzmir, İzmit, Marmara'nın bir kısmı) iyi temsil edilmez; son günler ön veridir.

Lisans: Apache-2.0. Veri NOAA'nındır (kamu malı).
