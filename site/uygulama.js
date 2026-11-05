"use strict";
(() => {
  const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  const AY_BAS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  const NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const sayi = (x, b = 1) => x.toLocaleString("tr-TR", { minimumFractionDigits: b, maximumFractionDigits: b });
  const derece = (x, b = 1) => sayi(x, b) + "°";
  const isaretli = (x, b = 1) => {
    const r = Math.round(x * 10 ** b) / 10 ** b;
    return (r > 0 ? "+" : r < 0 ? "−" : "") + sayi(Math.abs(r), b) + "°";
  };
  const tarihYaz = (s) => { const [y, a, g] = s.split("-").map(Number); return `${g} ${AYLAR[a - 1]} ${y}`; };
  const css = (ad) => getComputedStyle(document.documentElement).getPropertyValue(ad).trim();
  const el = (ad, ozel = {}, ebeveyn) => {
    const e = document.createElementNS(NS, ad);
    for (const [k, v] of Object.entries(ozel)) e.setAttribute(k, v);
    if (ebeveyn) ebeveyn.appendChild(e);
    return e;
  };

  // ---- renk: soğuk (mavi) ← gri → sıcak (kırmızı), ±3 °C'de doyar ----
  function hex2rgb(h) { h = h.replace("#", ""); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  function karistir(a, b, t) { const x = hex2rgb(a), y = hex2rgb(b); return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`; }
  function anomaliRengi(a) {
    const t = Math.max(-1, Math.min(1, a / 3));
    return t >= 0 ? karistir(css("--notr"), css("--sicak"), t) : karistir(css("--notr"), css("--soguk"), -t);
  }

  // ---- ipucu ----
  const ipucu = $("ipucu");
  function ipucuGoster(ev, html) {
    ipucu.innerHTML = html; ipucu.hidden = false;
    const x = Math.min(ev.clientX + 12, window.innerWidth - ipucu.offsetWidth - 8);
    ipucu.style.left = Math.max(8, x) + "px";
    ipucu.style.top = (ev.clientY - ipucu.offsetHeight - 12) + "px";
  }
  const ipucuGizle = () => { ipucu.hidden = true; };

  let OZET, HARITA, SECILI;
  const ayrintiOnbellek = {};
  const ayrintiAl = (k) => ayrintiOnbellek[k] || (ayrintiOnbellek[k] = fetch(`veri/n/${k}.json`).then((r) => r.json()));

  Promise.all([fetch("veri/ozet.json").then((r) => r.json()), fetch("veri/harita.json").then((r) => r.json())])
    .then(([o, h]) => { OZET = o; HARITA = h; baslat(); })
    .catch(() => { $("giris").textContent = "Veri yüklenemedi. Sayfayı yenileyin."; });

  function baslat() {
    const tk = OZET.tum_kiyi, eg = tk.egilim;
    $("giris").textContent = `Türkiye'nin ${OZET.noktalar.length} kıyı noktasında deniz yüzeyinin sıcaklığı, ${tarihYaz(OZET.ilk_tarih).replace(/^\d+ /, "")}'den bu yana her günüyle.`;
    const isindi = eg.alt > 0;
    $("kahraman").innerHTML = `
      <div class="buyuk ${eg.egim < 0 ? "soguk" : ""}">${isaretli(tk.toplam_degisim)}</div>
      <p>${isindi ? "Evet. " : ""}${eg.bas}–${eg.son} arasında Türkiye kıyılarında yıllık ortalama deniz sıcaklığı yaklaşık <b>${sayi(Math.abs(tk.toplam_degisim))} °C ${tk.toplam_degisim >= 0 ? "arttı" : "azaldı"}</b>. Bu, her 10 yılda ${isaretli(eg.egim, 2)} demek.</p>
      <p class="alt">%95 güven aralığı: 10 yılda ${isaretli(eg.alt, 2)} ile ${isaretli(eg.ust, 2)} arası. ${eg.n} yılın ortalaması, ${OZET.noktalar.length} noktanın ortalaması.</p>`;
    $("bugun-baslik").textContent = `Bugün: ${tarihYaz(OZET.son_tarih)}`;
    const sicakSay = tk.normalden_sicak, n = OZET.noktalar.length;
    $("bugun-ozet").innerHTML = `${n} noktanın <b>${sicakSay}</b>'${ekAl(sicakSay)} deniz, bu tarihin 1991–2020 ortalamasından sıcak. Ortalama fark <b>${isaretli(tk.anomali)}</b>.` +
      (OZET.son_kaynak === "on" ? ` <span class="kucuk">(Son günler NOAA ön verisi.)</span>` : "");
    $("guncelleme").textContent = `Son veri günü: ${tarihYaz(OZET.son_tarih)} · Sayfa güncellemesi: ${OZET.guncelleme.replace("T", " ").replace("Z", " UTC")}`;

    haritaCiz();
    const sec = $("nokta-sec");
    for (const d of ["Karadeniz", "Marmara", "Ege", "Akdeniz"]) {
      const g = document.createElement("optgroup"); g.label = d;
      OZET.noktalar.filter((p) => p.deniz === d).forEach((p) => { const o = document.createElement("option"); o.value = p.kimlik; o.textContent = p.ad; g.appendChild(o); });
      sec.appendChild(g);
    }
    sec.addEventListener("change", () => noktaSec(sec.value));
    denizTablosu();
    dogumKur();
    let ilk = "antalya";
    try { ilk = localStorage.getItem("deniz-nokta") || ilk; } catch (e) { /* yok */ }
    if (!OZET.noktalar.some((p) => p.kimlik === ilk)) ilk = OZET.noktalar[0].kimlik;
    noktaSec(ilk);
  }

  // Türkçe ünlü uyumu: "12'sinde", "3'ünde"... burada yalnız iyelik+bulunma: 'inde/'ında
  function ekAl(n) {
    const son = n % 10, onlar = n % 100;
    const s = { 0: "ında", 1: "inde", 2: "sinde", 3: "ünde", 4: "ünde", 5: "inde", 6: "sında", 7: "sinde", 8: "inde", 9: "unda" };
    if (son === 0) { const o = { 10: "unda", 20: "sinde", 30: "unda", 40: "ında", 50: "sinde", 60: "ında", 70: "inde", 80: "inde", 90: "ında" }; return o[onlar] || "ünde"; }
    return s[son];
  }

  // ---- harita ----
  function proj(lon, lat) {
    return [(lon - HARITA.lon0) * HARITA.kx * HARITA.olcek, (HARITA.lat1 - lat) * HARITA.olcek];
  }
  function haritaCiz() {
    const svg = $("harita");
    svg.setAttribute("viewBox", `0 0 ${HARITA.genislik} ${HARITA.yukseklik}`);
    el("path", { d: HARITA.diger, fill: "var(--kara-diger)", stroke: "var(--kara-kenar)", "stroke-width": 0.8 }, svg);
    el("path", { d: HARITA.turkiye, fill: "var(--kara-tr)", stroke: "var(--kara-kenar)", "stroke-width": 0.8 }, svg);
    const denizAd = [["Karadeniz", 34.5, 42.75 - 0.6], ["Ege", 25.55, 38.9], ["Akdeniz", 31.2, 35.95], ["Marmara", 27.9, 40.72]];
    for (const [ad, lo, la] of denizAd) {
      const [x, y] = proj(lo, la);
      const t = el("text", { x, y, fill: "var(--metin-3)", "font-size": ad === "Marmara" ? 13 : 18, "font-style": "italic" }, svg);
      t.textContent = ad;
    }
    const kat = el("g", {}, svg);
    for (const p of OZET.noktalar) {
      const [x, y] = proj(p.hucre_boylam, p.hucre_enlem);
      const g = el("g", { class: "nokta", "data-k": p.kimlik, tabindex: 0, role: "button", "aria-label": `${p.ad}: ${derece(p.bugun)}, normalden ${isaretli(p.anomali)}` }, kat);
      el("circle", { cx: x, cy: y, r: 18, fill: "transparent", stroke: "none" }, g);
      el("circle", { cx: x, cy: y, r: 9, fill: anomaliRengi(p.anomali) }, g);
      const goster = (ev) => ipucuGoster(ev, `<b>${p.ad}</b> ${derece(p.bugun)} · normalden ${isaretli(p.anomali)}`);
      g.addEventListener("mousemove", goster);
      g.addEventListener("mouseleave", ipucuGizle);
      g.addEventListener("click", () => { noktaSec(p.kimlik); $("kart").scrollIntoView({ behavior: "smooth", block: "nearest" }); });
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); noktaSec(p.kimlik); } });
    }
    $("lejant").innerHTML = `<span>−3° daha soğuk</span><span class="serit" style="background:linear-gradient(90deg,${anomaliRengi(-3)},${anomaliRengi(0)},${anomaliRengi(3)})"></span><span>+3° daha sıcak</span>`;
  }

  // ---- seçili nokta ----
  function noktaSec(k) {
    SECILI = OZET.noktalar.find((p) => p.kimlik === k);
    $("nokta-sec").value = k;
    try { localStorage.setItem("deniz-nokta", k); } catch (e) { /* yok */ }
    document.querySelectorAll(".harita .nokta").forEach((g) => g.classList.toggle("secili", g.dataset.k === k));
    const sel = document.querySelector(`.harita .nokta[data-k="${k}"]`);
    if (sel) sel.parentNode.appendChild(sel);
    kartCiz(SECILI);
    ayrintiAl(k).then((a) => { if (SECILI.kimlik !== k) return; grafikBuTarih(SECILI, a); grafikBuYil(SECILI, a); grafikYillik(SECILI, a); dogumCumle(); });
  }

  function kartCiz(p) {
    const fark = p.anomali, sinif = fark > 0 ? "sicak-m" : "soguk-m";
    const farkMetin = Math.abs(fark) < 0.05 ? "Bu tarihin normaliyle aynı." : `Normalden <span class="${sinif}">${sayi(Math.abs(fark))}° daha ${fark > 0 ? "sıcak" : "soğuk"}</span>.`;
    const eg = p.egilim;
    $("kart").innerHTML = `
      <p class="ad">${p.ad} · ${p.deniz} · ${tarihYaz(OZET.son_tarih)}</p>
      <div class="derece">${derece(p.bugun)}</div>
      <p class="fark">${farkMetin}</p>
      <dl>
        <div><dt>Bu tarihin normali (1991–2020)</dt><dd>${derece(p.normal)}</dd></div>
        <div><dt>${p.yil_sayisi} yıl içinde sırası</dt><dd>${p.sira === 1 ? "en sıcak" : p.sira + ". en sıcak"}</dd></div>
        <div><dt>Bu tarihin en sıcak yılı</dt><dd>${p.en_sicak.yil} · ${derece(p.en_sicak.deger)}</dd></div>
        <div><dt>Bu tarihin en soğuk yılı</dt><dd>${p.en_soguk.yil} · ${derece(p.en_soguk.deger)}</dd></div>
        <div><dt>Isınma hızı (${eg.bas}–${eg.son})</dt><dd>10 yılda ${isaretli(eg.egim, 2)}</dd></div>
        <div><dt>%95 aralık</dt><dd>${isaretli(eg.alt, 2)} … ${isaretli(eg.ust, 2)}</dd></div>
      </dl>
      <p class="not">Ölçüm karesinin merkezi kıyı noktasından ${sayi(p.uzaklik_km, 0)} km ${p.hucre_yon}da (${sayi(p.hucre_enlem, 3)}° K, ${sayi(p.hucre_boylam, 3)}° D). Kare yaklaşık 28 × 21 km.</p>`;
  }

  // ---- grafik yardımcıları ----
  function cerceve(kap, G, Y, sol = 36, alt = 24, ust = 10, sag = 8) {
    kap.innerHTML = "";
    const svg = el("svg", { viewBox: `0 0 ${G} ${Y}`, role: "img" }, kap);
    return { svg, sol, alt, ust, sag, G, Y, ic: { x0: sol, x1: G - sag, y0: ust, y1: Y - alt } };
  }
  function yEkseni(c, ymin, ymax, adim) {
    const y = (v) => c.ic.y1 - (v - ymin) / (ymax - ymin) * (c.ic.y1 - c.ic.y0);
    for (let v = Math.ceil(ymin / adim) * adim; v <= ymax + 1e-9; v += adim) {
      el("line", { x1: c.ic.x0, x2: c.ic.x1, y1: y(v), y2: y(v), class: "izgara" }, c.svg);
      const t = el("text", { x: c.ic.x0 - 6, y: y(v) + 4, "text-anchor": "end" }, c.svg); t.textContent = sayi(v, 0) + "°";
    }
    return y;
  }
  function sinirlar(dizi, pay = 0.5) {
    const v = dizi.filter((x) => x != null && isFinite(x));
    return [Math.floor(Math.min(...v) - pay), Math.ceil(Math.max(...v) + pay)];
  }
  const adimSec = (aralik) => (aralik > 12 ? 4 : aralik > 6 ? 2 : 1);
  const genislik = (kap) => Math.max(320, Math.min(760, kap.clientWidth || 640));

  // 1) bu tarih, her yıl
  function grafikBuTarih(p, a) {
    const kap = $("g1"), yillar = Object.keys(a.bu_tarih).map(Number), deg = yillar.map((y) => a.bu_tarih[y]);
    const sonYil = Number(OZET.son_tarih.slice(0, 4));
    const [g, , ] = OZET.son_tarih.split("-").slice(1).reverse().map(Number);
    const ay = Number(OZET.son_tarih.slice(5, 7));
    $("g1-aciklama").textContent = `${p.ad}'da her yılın ${g} ${AYLAR[ay - 1]} günü. Kesikli çizgi: 1991–2020 normali. Koyu nokta: ${sonYil}.`;
    const G = genislik(kap), Y = 220, c = cerceve(kap, G, Y);
    const [lo, hi] = sinirlar([...deg, p.normal]);
    const y = yEkseni(c, lo, hi, adimSec(hi - lo));
    const x0 = yillar[0], x1 = sonYil;
    const x = (v) => c.ic.x0 + 6 + (v - x0) / (x1 - x0) * (c.ic.x1 - c.ic.x0 - 12);
    for (let v = Math.ceil(x0 / 10) * 10; v <= x1; v += 10) { const t = el("text", { x: x(v), y: Y - 6, "text-anchor": "middle" }, c.svg); t.textContent = v; }
    el("line", { x1: c.ic.x0, x2: c.ic.x1, y1: y(p.normal), y2: y(p.normal), stroke: "var(--normal)", "stroke-dasharray": "4 4", "stroke-width": 1.5 }, c.svg);
    yillar.forEach((yy, i) => {
      const son = yy === sonYil, v = deg[i];
      const k = el("circle", { cx: x(yy), cy: y(v), r: son ? 6 : 4, fill: son ? "var(--metin)" : anomaliRengi(v - p.normal), stroke: "var(--zemin)", "stroke-width": 1.5 }, c.svg);
      const h = el("circle", { cx: x(yy), cy: y(v), r: 12, fill: "transparent" }, c.svg);
      h.addEventListener("mousemove", (ev) => ipucuGoster(ev, `<b>${yy}</b> ${derece(v)} · normalden ${isaretli(v - p.normal)}`));
      h.addEventListener("mouseleave", ipucuGizle);
      if (son) { const asagi = y(v) < c.ic.y0 + 30; const t = el("text", { x: x(yy) - 10, y: y(v) + (asagi ? 18 : -10), "text-anchor": "end", fill: "var(--metin)", "font-weight": 600 }, c.svg); t.textContent = `${yy}: ${derece(v)}`; }
    });
  }

  // 2) bu yıl gün gün
  function grafikBuYil(p, a) {
    const kap = $("g2"), G = genislik(kap), Y = 240, c = cerceve(kap, G, Y);
    const [lo, hi] = sinirlar([...a.p10, ...a.p90, ...a.bu_yil, ...a.gecen_yil], 0.3);
    const y = yEkseni(c, lo, hi, adimSec(hi - lo));
    const x = (d) => c.ic.x0 + d / 364 * (c.ic.x1 - c.ic.x0);
    AY_BAS.forEach((d, i) => { if (G < 480 && i % 2) return; const t = el("text", { x: x(d + 14), y: Y - 6, "text-anchor": "middle" }, c.svg); t.textContent = AYLAR[i].slice(0, 3); });
    let bant = "";
    for (let d = 0; d < 365; d++) bant += (d ? "L" : "M") + x(d).toFixed(1) + "," + y(a.p90[d]).toFixed(1);
    for (let d = 364; d >= 0; d--) bant += "L" + x(d).toFixed(1) + "," + y(a.p10[d]).toFixed(1);
    el("path", { d: bant + "Z", fill: "var(--bant)" }, c.svg);
    const cizgi = (dizi, ozel) => {
      let d = "", ac = false;
      dizi.forEach((v, i) => { if (v == null) { ac = false; return; } d += (ac ? "L" : "M") + x(i).toFixed(1) + "," + y(v).toFixed(1); ac = true; });
      return el("path", { d, fill: "none", ...ozel }, c.svg);
    };
    cizgi(a.normal, { stroke: "var(--normal)", "stroke-width": 1.2 });
    cizgi(a.bu_yil, { stroke: "var(--metin)", "stroke-width": 2, "stroke-linejoin": "round" });
    const n = a.bu_yil.length - 1;
    el("circle", { cx: x(n), cy: y(a.bu_yil[n]), r: 4, fill: "var(--metin)" }, c.svg);
    const sonYil = OZET.son_tarih.slice(0, 4);
    const t = el("text", { x: x(n) + (n > 300 ? -8 : 8), y: y(a.bu_yil[n]) - 8, "text-anchor": n > 300 ? "end" : "start", fill: "var(--metin)", "font-weight": 600 }, c.svg); t.textContent = sonYil;
    // artı imleç
    const imlec = el("line", { y1: c.ic.y0, y2: c.ic.y1, stroke: "var(--metin-3)", "stroke-width": 1, visibility: "hidden" }, c.svg);
    const alan = el("rect", { x: c.ic.x0, y: c.ic.y0, width: c.ic.x1 - c.ic.x0, height: c.ic.y1 - c.ic.y0, fill: "transparent" }, c.svg);
    alan.addEventListener("mousemove", (ev) => {
      const r = c.svg.getBoundingClientRect(), px = (ev.clientX - r.left) / r.width * G;
      const d = Math.max(0, Math.min(364, Math.round((px - c.ic.x0) / (c.ic.x1 - c.ic.x0) * 364)));
      imlec.setAttribute("x1", x(d)); imlec.setAttribute("x2", x(d)); imlec.setAttribute("visibility", "visible");
      let ay = 0; while (ay < 11 && AY_BAS[ay + 1] <= d) ay++;
      const bu = a.bu_yil[d];
      ipucuGoster(ev, `<b>${d - AY_BAS[ay] + 1} ${AYLAR[ay]}</b><br>${bu != null ? `${sonYil}: ${derece(bu)}<br>` : ""}normal: ${derece(a.normal[d])}`);
    });
    alan.addEventListener("mouseleave", () => { imlec.setAttribute("visibility", "hidden"); ipucuGizle(); });
  }

  // 3) yıllık ortalama + eğilim
  function grafikYillik(p, a) {
    const kap = $("g3"), yillar = Object.keys(a.yillik).map(Number), deg = yillar.map((y) => a.yillik[y]);
    const eg = a.egilim;
    const ilkT = eg.y_ort + eg.egim_tam / 10 * (yillar[0] - eg.x_ort), sonT = eg.y_ort + eg.egim_tam / 10 * (yillar[yillar.length - 1] - eg.x_ort);
    $("g3-aciklama").textContent = `${p.ad}'da her yılın ortalama deniz sıcaklığı. Düz çizgi eğilim: ${yillar[0]}'de ${derece(ilkT)}, ${yillar[yillar.length - 1]}'de ${derece(sonT)}.`;
    const G = genislik(kap), Y = 220, c = cerceve(kap, G, Y);
    const [lo, hi] = sinirlar(deg, 0.3);
    const y = yEkseni(c, lo, hi, adimSec(hi - lo) / (hi - lo <= 3 ? 2 : 1));
    const x0 = yillar[0], x1 = yillar[yillar.length - 1];
    const x = (v) => c.ic.x0 + 6 + (v - x0) / (x1 - x0) * (c.ic.x1 - c.ic.x0 - 12);
    for (let v = Math.ceil(x0 / 10) * 10; v <= x1; v += 10) { const t = el("text", { x: x(v), y: Y - 6, "text-anchor": "middle" }, c.svg); t.textContent = v; }
    el("line", { x1: x(x0), x2: x(x1), y1: y(ilkT), y2: y(sonT), stroke: "var(--vurgu)", "stroke-width": 2 }, c.svg);
    el("path", { d: yillar.map((yy, i) => (i ? "L" : "M") + x(yy).toFixed(1) + "," + y(deg[i]).toFixed(1)).join(""), fill: "none", stroke: "var(--metin-2)", "stroke-width": 1.5 }, c.svg);
    yillar.forEach((yy, i) => {
      el("circle", { cx: x(yy), cy: y(deg[i]), r: 3, fill: "var(--metin-2)" }, c.svg);
      const h = el("circle", { cx: x(yy), cy: y(deg[i]), r: 10, fill: "transparent" }, c.svg);
      h.addEventListener("mousemove", (ev) => ipucuGoster(ev, `<b>${yy}</b> yıllık ortalama ${derece(deg[i], 2)}`));
      h.addEventListener("mouseleave", ipucuGizle);
    });
  }

  // ---- doğduğun yıl ----
  function dogumKur() {
    const ys = $("dogum-yil"), as = $("dogum-ay");
    const sonYil = Number(OZET.son_tarih.slice(0, 4));
    for (let y = sonYil - 1; y >= 1982; y--) { const o = document.createElement("option"); o.value = y; o.textContent = y; ys.appendChild(o); }
    AYLAR.forEach((a, i) => { const o = document.createElement("option"); o.value = i; o.textContent = a; as.appendChild(o); });
    ys.value = 1995; as.value = 7;
    try { const k = JSON.parse(localStorage.getItem("deniz-dogum") || "null"); if (k) { ys.value = k[0]; as.value = k[1]; } } catch (e) { /* yok */ }
    const deg = () => { try { localStorage.setItem("deniz-dogum", JSON.stringify([ys.value, as.value])); } catch (e) { /* yok */ } dogumCumle(); };
    ys.addEventListener("change", deg); as.addEventListener("change", deg);
  }
  function dogumCumle() {
    if (!SECILI) return;
    ayrintiAl(SECILI.kimlik).then((a) => {
      const y = $("dogum-yil").value, ay = Number($("dogum-ay").value);
      const onceki = a.aylik[y] && a.aylik[y][ay];
      const yillar = Object.keys(a.aylik).map(Number).filter((yy) => a.aylik[yy][ay] != null).sort((p, q) => q - p);
      const sonY = yillar[0];
      if (onceki == null || sonY == null) { $("dogum-cumle").textContent = "Bu ay için veri yok."; return; }
      const simdi = a.aylik[sonY][ay], fark = simdi - onceki;
      const vals = yillar.map((yy) => a.aylik[yy][ay]);
      const sira = 1 + vals.filter((v) => v > simdi).length;
      $("dogum-cumle").innerHTML = `${y} ${AYLAR[ay]}'${ayEki(ay)} ${SECILI.ad} açıklarında deniz ortalama <b>${derece(onceki)}</b> idi. ` +
        `${sonY} ${AYLAR[ay]}'${ayEki(ay)} <b>${derece(simdi)}</b>` +
        (Math.abs(fark) < 0.05 ? ", yani aynı." : `, yani <b class="${fark > 0 ? "sicak-m" : "soguk-m"}">${sayi(Math.abs(fark))}° daha ${fark > 0 ? "sıcak" : "soğuk"}</b>.`) +
        ` <span class="kucuk" style="color:var(--metin-3)">${sonY} ${AYLAR[ay]}, ${vals.length} yılın ${sira === 1 ? "en sıcağı" : sira + ". en sıcağı"}. Tek bir ayın farkı hava durumunu da içerir; uzun eğilim için yukarıdaki grafiğe bakın.</span>`;
    });
  }
  function ayEki(ay) { return ["ında", "ında", "ında", "ında", "ında", "ında", "ında", "ında", "ünde", "ında", "ında", "ında"][ay]; }

  // ---- dört deniz ----
  function denizTablosu() {
    const t = $("denizler");
    let h = `<tr><th>Deniz</th><th class="sayi">Bugün, normalden</th><th class="sayi">10 yılda</th><th class="sayi">${OZET.tum_kiyi.egilim.bas}'den beri</th></tr>`;
    const satir = (ad, d) => `<tr><td>${ad} <span style="color:var(--metin-3)">(${d.nokta_sayisi})</span></td><td class="sayi">${isaretli(d.anomali)}</td><td class="sayi">${isaretli(d.egilim.egim, 2)} <span style="color:var(--metin-3)">(${sayi(d.egilim.alt, 2)}–${sayi(d.egilim.ust, 2)})</span></td><td class="sayi">${isaretli(d.toplam_degisim)}</td></tr>`;
    for (const [ad, d] of Object.entries(OZET.denizler)) h += satir(ad, d);
    h += satir("Tüm kıyılar", OZET.tum_kiyi);
    t.innerHTML = h;
  }

  let zam;
  window.addEventListener("resize", () => { clearTimeout(zam); zam = setTimeout(() => { if (SECILI) noktaSec(SECILI.kimlik); }, 200); });
})();
