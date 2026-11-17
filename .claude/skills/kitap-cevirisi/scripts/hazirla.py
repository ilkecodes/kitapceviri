"""PDF'i sayfa görüntülerine böler ve her sayfa için bir durum dosyası açar.

Kullanım:
  python hazirla.py "kaynak/Kitabın Adı.pdf" [--dpi 300] [--kitap kisa-ad] [--sayfalar 12-31] [--varak-bas 24a]
  python hazirla.py --yenile <kitap>            # eksik sayfa görüntülerini kaynaktan yeniden üretir (bulut oturumu)
  python hazirla.py "kaynak/goruntu_klasoru"   # tek tek sayfa görüntüleri (Gallica, Princeton vb.), ada göre sıralanır

  --sayfalar   Sadece bu PDF sayfalarını al (mecmua içindeki tek bir risale için)
  --varak-bas  Yazmalarda ilk sayfanın varak numarası; sonrakiler 24a, 24b, 25a... diye numaralanır

Aynı kitaba ikinci bir PDF (ör. ikinci cilt) eklenirse sayfalar kaldığı numaradan devam eder.

Maliyet için iki ön eleme yapılır, ikisi de Claude'a gitmeden:
  - Boş sayfalar (mürekkep oranı çok düşük) doğrudan "atlandi" işaretlenir.
  - PDF'te metin katmanı varsa çıkarılır ve okuyucu ajana yardımcı metin olarak verilir.
"""
from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

import pymupdf

from ortak import ATLANDI, CALISMA, hata, kitap_kisaltma, oku, sayfalar, utf8_cikti, yaz

UZUN_KENAR = 2400          # piksel; Claude'un okuması için yeterli, dosyalar şişmesin
BOS_ESIK = 0.0015          # mürekkep oranı bunun altındaysa sayfa boş sayılır
KATMAN_AZAMI = 8000        # durum dosyasına yazılacak metin katmanının üst sınırı (karakter)

ARAP_BLOK = (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)
SUNUM_BICIMI = (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)  # PDF'lerde sık görülen "şekillendirilmiş" Arap harfleri


def _aralikta(c: str, araliklar) -> bool:
    o = ord(c)
    return any(a <= o <= b for a, b in araliklar)


def murekkep_orani(page) -> float:
    """Sayfanın küçük gri tonlu bir kopyasında koyu piksellerin oranı."""
    zoom = 150 / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY)
    veri = pix.samples
    koyu = sum(1 for b in veri if b < 140)
    return koyu / max(len(veri), 1)


def metin_katmani(page) -> dict | None:
    ham = page.get_text("text").strip()
    if len(ham) < 20:
        return None
    sunum = sum(1 for c in ham if _aralikta(c, SUNUM_BICIMI))
    # Sunum biçimlerini temel harflere indir (ﺑ → ب gibi)
    metin = unicodedata.normalize("NFKC", ham)
    harfler = [c for c in metin if c.isalpha()]
    arap = sum(1 for c in harfler if _aralikta(c, ARAP_BLOK))
    bozuk = metin.count("�") + sum(1 for c in metin if unicodedata.category(c) in ("Co", "Cn"))
    oran_arap = arap / max(len(harfler), 1)
    oran_bozuk = bozuk / max(len(metin), 1)
    if oran_bozuk > 0.05 or len(harfler) < 20:
        kalite = "bozuk"
    elif sunum / max(len(ham), 1) > 0.2:
        kalite = "supheli"  # şekillendirilmiş harf: sıra ters ya da harfler kopuk olabilir
    else:
        kalite = "iyi"
    return {
        "metin": metin[:KATMAN_AZAMI],
        "karakter": len(metin),
        "arap_harf_orani": round(oran_arap, 2),
        "kalite": kalite,
    }


def goruntuleri_yenile(kitap: str, dpi: int) -> None:
    """Bulut oturumunda sayfa görüntüleri depoya kaydedilmez; eksik olanları kaynaktan yeniden üretir."""
    from ortak import KAYNAK
    d = CALISMA / kitap
    if not d.exists():
        hata(f"Kitap yok: {kitap}")
    (d / "sayfalar").mkdir(exist_ok=True)
    acik = {}
    n = 0
    for p in sayfalar(d):
        s = oku(p)
        hedef = d / "sayfalar" / f"{s['sayfa']}.png"
        if hedef.exists():
            continue
        kaynak = KAYNAK / s["kaynak_pdf"]
        if kaynak not in acik:
            if kaynak.is_dir():
                g = pymupdf.open()
                for x in sorted(y for y in kaynak.iterdir() if y.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".jp2")):
                    with pymupdf.open(x) as im:
                        g.insert_pdf(pymupdf.open("pdf", im.convert_to_pdf()))
                acik[kaynak] = g
            else:
                acik[kaynak] = pymupdf.open(kaynak)
        page = acik[kaynak][s["kaynak_sayfa"] - 1]
        zoom = min(dpi / 72, UZUN_KENAR / max(page.rect.width, page.rect.height))
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB).save(hedef)
        n += 1
    print(f"YENILENEN_GORUNTU {n}")


def main() -> None:
    utf8_cikti()
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--yenile":
        goruntuleri_yenile(sys.argv[2], 300)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--kitap", help="kısa ad; verilmezse PDF adından üretilir")
    ap.add_argument("--sayfalar", help="ör. 12-31")
    ap.add_argument("--varak-bas", help="ör. 24a")
    a = ap.parse_args()

    pdf = Path(a.pdf)
    if not pdf.exists():
        hata(f"PDF bulunamadı: {pdf}")
    kitap = a.kitap or kitap_kisaltma(pdf.stem)
    d = CALISMA / kitap
    (d / "sayfalar").mkdir(parents=True, exist_ok=True)
    (d / "durum").mkdir(parents=True, exist_ok=True)

    meta_yolu = d / "kitap.json"
    meta = oku(meta_yolu) if meta_yolu.exists() else {
        "kitap": kitap,
        "baslik": pdf.stem,
        "kaynak_pdfler": [],
        # Aşağıdakiler örnek tarama sonrası doldurulur
        "baslik_tr": None,
        "yazar": None,          # yazarlar/<yazar> klasörünün adı
        "dil": None,            # arapca | urduca | uygurca_modern | uygurca_eski
        "yon": "rtl",
        "uretim": None,         # matbu | tasbaski | el_yazmasi
        "kaynak_duzen": None,   # sayfa düzeninin tarifi (bkz. references/duzenler.md)
        "katmanlar": None,      # okunacak katmanlar, ör. ["matn"] ya da ["matn", "serh", "hasiye"]
        "yardimci_sutun": None, # okunmayan tercüme katmanının dili, ör. "urduca" — çevirmen gerekirse bakar
        "tur": None,            # dini_tasavvufi | tarih | edebi | siir | akademik
        "notlar": "",
    }
    if pdf.name in meta["kaynak_pdfler"]:
        hata(f"{pdf.name} bu kitaba zaten eklenmiş.")

    mevcut = sayfalar(d)
    no = int(mevcut[-1].stem) + 1 if mevcut else 1
    adet = bos = katmanli = 0
    varak = None
    if a.varak_bas:
        m = __import__("re").match(r"(\d+)([ab])", a.varak_bas)
        varak = [int(m.group(1)), m.group(2)]
    aralik = None
    if a.sayfalar:
        bas, son = (int(x) for x in a.sayfalar.split("-"))
        aralik = range(bas - 1, son)
    gecici = None
    if pdf.is_dir():
        # Görüntü klasörünü geçici bir PDF'e çevir (her görüntü bir sayfa)
        gorseller = sorted(x for x in pdf.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".jp2"))
        if not gorseller:
            hata("Klasörde görüntü dosyası yok.")
        gecici = pymupdf.open()
        for g in gorseller:
            with pymupdf.open(g) as im:
                gecici.insert_pdf(pymupdf.open("pdf", im.convert_to_pdf()))
    with (gecici if gecici is not None else pymupdf.open(pdf)) as doc:
        for i, page in enumerate(doc):
            if aralik is not None and i not in aralik:
                continue
            sid = f"{no:04d}"
            zoom = min(a.dpi / 72, UZUN_KENAR / max(page.rect.width, page.rect.height))
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB)
            pix.save(d / "sayfalar" / f"{sid}.png")

            durum = {
                "sayfa": sid,
                "gorsel": f"calisma/{kitap}/sayfalar/{sid}.png",
                "kaynak_pdf": pdf.name,
                "kaynak_sayfa": i + 1,
                "durum": "bekliyor",
                "murekkep": round(murekkep_orani(page), 4),
            }
            if varak:
                durum["kitap_sayfa"] = f"{varak[0]}{varak[1]}"
                varak = [varak[0], "b"] if varak[1] == "a" else [varak[0] + 1, "a"]
            katman = metin_katmani(page)
            if katman:
                durum["metin_katmani"] = katman
                katmanli += 1
            if durum["murekkep"] < BOS_ESIK and not katman:
                durum["durum"] = ATLANDI
                durum["okuma"] = {"atla": True, "rol": "bos", "bloklar": [], "otomatik": True}
                bos += 1
            yaz(d / "durum" / f"{sid}.json", durum)
            no += 1
            adet += 1

    meta["kaynak_pdfler"].append(pdf.name)
    yaz(meta_yolu, meta)
    print(f"KITAP {kitap}")
    print(f"EKLENEN_SAYFA {adet}")
    print(f"BOS_SAYFA {bos}")
    print(f"METIN_KATMANLI_SAYFA {katmanli}")
    print(f"TOPLAM_SAYFA {len(sayfalar(d))}")


if __name__ == "__main__":
    main()
