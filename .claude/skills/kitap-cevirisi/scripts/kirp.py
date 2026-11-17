"""Okunması zor bir sayfayı PDF'ten yüksek çözünürlükte, üst üste binen parçalara böler.

Claude görüntüleri belli bir boyuta küçülterek okur. Küçük puntolu, yoğun sayfalarda bu
okuma hatalarını artırır. Sayfa parçalanınca her parça daha büyük ölçekte görülür.

Kullanım:
  python kirp.py <kitap> <sayfa> [--parca 2] [--dpi 400]

Çıktı: calisma/<kitap>/sayfalar/NNNN_p1.png, NNNN_p2.png ... ve durum dosyasına "parcalar" alanı.
"""
from __future__ import annotations

import argparse

import pymupdf

from ortak import KAYNAK, hata, kitap_dizini, oku, utf8_cikti, yaz

BINME = 0.06  # parçalar arasında sayfa yüksekliğinin %6'sı kadar örtüşme; satır kesilmesin


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    ap.add_argument("kitap")
    ap.add_argument("sayfa")
    ap.add_argument("--parca", type=int, default=2)
    ap.add_argument("--dpi", type=int, default=400)
    a = ap.parse_args()

    d = kitap_dizini(a.kitap)
    yol = d / "durum" / f"{a.sayfa}.json"
    s = oku(yol)
    pdf = KAYNAK / s["kaynak_pdf"]
    if not pdf.exists():
        hata(f"Kaynak PDF bulunamadı: {pdf.name}")

    parcalar = []
    with pymupdf.open(pdf) as doc:
        page = doc[s["kaynak_sayfa"] - 1]
        r = page.rect
        h = r.height / a.parca
        for i in range(a.parca):
            y0 = max(r.y0, r.y0 + i * h - BINME * r.height)
            y1 = min(r.y1, r.y0 + (i + 1) * h + BINME * r.height)
            clip = pymupdf.Rect(r.x0, y0, r.x1, y1)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(a.dpi / 72, a.dpi / 72), clip=clip, colorspace=pymupdf.csRGB)
            ad = f"{a.sayfa}_p{i + 1}.png"
            pix.save(d / "sayfalar" / ad)
            parcalar.append(f"calisma/{a.kitap}/sayfalar/{ad}")

    s["parcalar"] = parcalar
    yaz(yol, s)
    for p in parcalar:
        print(f"PARCA {p}")


if __name__ == "__main__":
    main()
