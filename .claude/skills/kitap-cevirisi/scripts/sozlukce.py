"""Yazar sözlükçesi: Bir yazarın ıstılahları, özel isimleri ve bunların onaylı Türkçe karşılıkları.

Sözlükçe kitap düzeyinde değil YAZAR düzeyindedir (yazarlar/<yazar>/sozlukce.json). Böylece yazarın her
yeni kitabı, öncekilerde verilmiş kararlarla başlar.

<hedef>: bir kitabın kısa adı (sözlükçe o kitabın yazarınınkidir) ya da "yazar:<yazar-kisa-adi>".

Kullanım:
  python sozlukce.py liste <hedef> [--hepsi]         # onaylı terimler (+ bu kitapta açıklanmış mı)
  python sozlukce.py adaylar <hedef>                 # onay bekleyen terimler
  python sozlukce.py topla <kitap>                   # çevirmenlerin önerdiği yeni terimler ve çakışmalar
  python sozlukce.py onayla <hedef> --kaynak X --turkce Y [--ilk-gecis "..."] [--tur ...] [--aciklama ...] [--aday]
  python sozlukce.py isaretle <kitap>                # toplanan önerileri işlendi say
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from ortak import YAZARLAR, hata, kitap_dizini, oku, sayfalar, utf8_cikti, yaz


def coz(hedef: str):
    """(sözlükçe yolu, kitap dizini ya da None)"""
    if hedef.startswith("yazar:"):
        d = YAZARLAR / hedef.split(":", 1)[1]
        if not d.exists():
            hata(f"Yazar profili yok: {d.name}")
        return d / "sozlukce.json", None
    kd = kitap_dizini(hedef)
    y = oku(kd / "kitap.json").get("yazar")
    if not y:
        hata("Kitabın yazarı belirlenmemiş (kitap.json: yazar). Önce yazar profilini oluşturun.")
    d = YAZARLAR / y
    if not d.exists():
        hata(f"Yazar profili yok: {y}")
    return d / "sozlukce.json", kd


def yukle(yol: Path) -> dict:
    return oku(yol) if yol.exists() else {"terimler": {}}


def aciklananlar(kd: Path) -> dict:
    """Bu kitapta ilk geçişte açıklaması yapılmış terimler -> sayfa"""
    r = {}
    for p in sayfalar(kd):
        s = oku(p)
        for t in (s.get("ceviri") or {}).get("aciklanan_terimler", []):
            r.setdefault(t, s.get("kitap_sayfa") or s["sayfa"])
    return r


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    l = alt.add_parser("liste")
    l.add_argument("hedef")
    l.add_argument("--hepsi", action="store_true")
    alt.add_parser("adaylar").add_argument("hedef")
    for k in ("topla", "isaretle"):
        alt.add_parser(k).add_argument("kitap")
    o = alt.add_parser("onayla")
    o.add_argument("hedef")
    o.add_argument("--kaynak", required=True)
    o.add_argument("--turkce", required=True)
    o.add_argument("--ilk-gecis", default="")
    o.add_argument("--tur", default="")
    o.add_argument("--aciklama", default="")
    o.add_argument("--aday", action="store_true", help="onaylı değil, aday olarak kaydet")
    a = ap.parse_args()

    if a.komut in ("liste", "adaylar", "onayla"):
        yol, kd = coz(a.hedef)
    else:
        yol, kd = coz(a.kitap)
    sz = yukle(yol)
    T = sz["terimler"]

    if a.komut == "liste":
        acik = aciklananlar(kd) if kd else {}
        onayli = {k: t for k, t in T.items() if a.hepsi or t.get("durum", "onayli") == "onayli"}
        if not onayli:
            print("(sözlükçe henüz boş)")
        for k, t in sorted(onayli.items(), key=lambda x: x[1]["turkce"]):
            satir = f"{k} => {t['turkce']}"
            if t.get("tur"):
                satir += f" ({t['tur']})"
            if t.get("ilk_gecis"):
                if k in acik:
                    satir += f" | bu kitapta s. {acik[k]}'de açıklandı, tekrar açıklama"
                else:
                    satir += f" | ilk geçişte açıkla: {t['ilk_gecis']}"
            if t.get("aciklama"):
                satir += f" | not: {t['aciklama']}"
            print(satir)
        return

    if a.komut == "adaylar":
        for k, t in sorted(T.items()):
            if t.get("durum") == "aday":
                print(f"{k}\t{t['turkce']}\t{t.get('tur', '')}\t{t.get('aciklama', '')}")
        return

    if a.komut == "onayla":
        eski = T.get(a.kaynak, {})
        T[a.kaynak] = {
            "turkce": a.turkce,
            "ilk_gecis": a.ilk_gecis or eski.get("ilk_gecis", ""),
            "tur": a.tur or eski.get("tur", ""),
            "aciklama": a.aciklama or eski.get("aciklama", ""),
            "durum": "aday" if a.aday else "onayli",
        }
        yol.parent.mkdir(parents=True, exist_ok=True)
        yaz(yol, sz)
        print(f"{'ADAY' if a.aday else 'ONAYLANDI'} {a.kaynak} => {a.turkce}")
        return

    oneriler = defaultdict(lambda: defaultdict(list))
    detay = {}
    for p in sayfalar(kd):
        s = oku(p)
        c = s.get("ceviri") or {}
        if c.get("terimler_islendi"):
            continue
        for t in c.get("yeni_terimler", []):
            k, tr = t.get("kaynak", "").strip(), t.get("turkce", "").strip()
            if k and tr:
                oneriler[k][tr].append(s["sayfa"])
                detay.setdefault(k, t)

    if a.komut == "topla":
        if not oneriler:
            print("YOK")
        for k, sec in sorted(oneriler.items()):
            onayli = T.get(k, {}).get("turkce") if T.get(k, {}).get("durum", "onayli") == "onayli" else None
            if onayli:
                for tr, sf in sec.items():
                    if tr != onayli:
                        print(f"CAKISMA\t{k}\tonayli={onayli}\tkullanilan={tr}\tsayfalar={','.join(sf)}")
                continue
            secenek = " | ".join(f"{tr} [{','.join(sf)}]" for tr, sf in sec.items())
            print(f"YENI\t{k}\t{secenek}\t{detay[k].get('tur', '')}\t{detay[k].get('aciklama', '')}")
        return

    if a.komut == "isaretle":
        n = 0
        for p in sayfalar(kd):
            s = oku(p)
            c = s.get("ceviri")
            if c and not c.get("terimler_islendi"):
                c["terimler_islendi"] = True
                yaz(p, s)
                n += 1
        print(f"ISARETLENDI {n}")


if __name__ == "__main__":
    main()
