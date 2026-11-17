"""Kitabın Word dosyalarını üretir: Arapça asıl metin ve Türkçe çeviri, ayrı ayrı.

Kullanım:
  python birlestir.py <kitap> --asil      # Arapça edisyon metni (tashih dipnotlarıyla)
  python birlestir.py <kitap> --turkce    # Türkçe çeviri (ayet/hadis ve çevirmen dipnotlarıyla)
  python birlestir.py <kitap> --asil --turkce [--temiz] [--taslak]

  --temiz   "kontrol bekliyor" uyarılarını basmaz (son sürüm için)
  --taslak  henüz hazır olmayan sayfaların yerine yer tutucu koyar

Türkçe metindeki işaretler (çevirmen ajan koyar, burada dipnota dönüşür):
  ⟦A1⟧       alıntı A1'in kaynak dipnotu
  ⟦MEAL:A1⟧  alıntı A1 tam bir ayetse: meal metni tırnak içinde buraya konur + dipnot
  ⟦N1⟧       çevirmen notu N1
"""
from __future__ import annotations

import argparse
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from dipnot import Dipnotlar
from ortak import ATLANDI, CIKTI, YAZARLAR, kitap_dizini, kitap_kisaltma, oku, sayfalar, utf8_cikti

GRI = RGBColor(0x80, 0x80, 0x80)
AR_FONT = "Traditional Arabic"
TR_FONT = "Times New Roman"
ATLA = {"sayfa_no", "ust_bilgi"}
ATLA_KATMAN = {"takip", "kayit", "tercume", "ust_bilgi"}


def atlanir(b):
    return b.get("tur") in ATLA or b.get("katman") in ATLA_KATMAN or not b.get("metin", "").strip()

ISARET = re.compile(r"⟦(MEAL:)?([AN]\d+)⟧")
ARAPCA_RAKAM = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


# ---------------- yardımcılar ----------------
def rtl_yap(p, font=AR_FONT, boyut=16):
    pPr = p._p.get_or_add_pPr()
    pPr.insert(0, OxmlElement("w:bidi"))
    for r in p.runs:
        rtl_run(r, font, boyut)


def rtl_run(r, font=AR_FONT, boyut=16):
    rPr = r._r.get_or_add_rPr()
    if rPr.find(qn("w:rtl")) is None:
        rPr.append(OxmlElement("w:rtl"))
    f = rPr.find(qn("w:rFonts"))
    if f is None:
        f = OxmlElement("w:rFonts")
        rPr.insert(0, f)
    for k in ("w:ascii", "w:hAnsi", "w:cs"):
        f.set(qn(k), font)
    r.font.size = Pt(boyut)
    szcs = OxmlElement("w:szCs")
    szcs.set(qn("w:val"), str(int(boyut * 2)))
    rPr.append(szcs)


def sayfa_ayari(doc, rtl: bool):
    s = doc.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21)
    s.left_margin = s.right_margin = Cm(2.5)
    s.top_margin = s.bottom_margin = Cm(2.2)
    if rtl:
        s._sectPr.append(OxmlElement("w:bidi"))


def ust_bilgi_satiri(doc, metin, rtl=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(metin)
    r.font.size = Pt(9)
    r.font.color.rgb = GRI
    if rtl:
        rtl_run(r, AR_FONT, 11)
        r.font.color.rgb = GRI
    return p


def uyari(doc, metin):
    p = doc.add_paragraph()
    r = p.add_run("⚠ " + metin)
    r.font.size = Pt(8)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def sayfa_no_ar(s):
    ks = s.get("kitap_sayfa")
    return str(ks).translate(ARAPCA_RAKAM) if ks else f"PDF {s['kaynak_sayfa']}"


def sayfa_no_tr(s):
    ks = s.get("kitap_sayfa")
    return str(ks) if ks else f"PDF {s['kaynak_sayfa']}"


# ---------------- Arapça asıl ----------------
def tashih_yerlestir(p, metin, notlar, dn):
    """metin içinde notların 'edisyon' ifadelerinin ilk geçtiği yere dipnot koyar."""
    yerler = []
    for n in notlar:
        hedef = n.get("edisyon") or ""
        i = metin.find(hedef) if hedef else -1
        yerler.append((i + len(hedef) if i >= 0 else len(metin), n))
    yerler.sort(key=lambda x: x[0])
    bas = 0
    for konum, n in yerler:
        if konum > bas:
            rtl_run(p.add_run(metin[bas:konum]))
        dn.ekle(p, n["not"])
        bas = konum
    if bas < len(metin):
        rtl_run(p.add_run(metin[bas:]))


def asil_uret(kd, meta, yazar, temiz, taslak):
    doc = Document()
    sayfa_ayari(doc, rtl=True)
    st = doc.styles["Normal"]
    st.font.name = AR_FONT
    dn = Dipnotlar(doc, font=TR_FONT, boyut_pt=9, rtl=False)

    for metin, boy in ((meta.get("baslik_ar") or meta.get("baslik", ""), 26), (yazar.get("ad_ar", ""), 16), ("النص العربي", 14)):
        if metin:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(metin)
            r.bold = boy > 20
            rtl_yap(p, AR_FONT, boy)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(meta.get("edisyon_notu") or
                  "Baskıdan transkripsiyon. İmla, yazım standardına göre uyarlanmıştır (hemze, şedde, noktalama). "
                  "Baskıdaki yazımdan farklı okunan her kelime dipnotta \"Baskıda: ...\" şeklinde gösterilmiştir. "
                  "Sayfa numaraları [ص ...] baskının sayfalarıdır.")
    r.font.size = Pt(9)
    r.italic = True
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    yazilan = eksik = 0
    for path in sayfalar(kd):
        s = oku(path)
        if s.get("durum") == ATLANDI:
            continue
        ed = s.get("edisyon")
        if not ed or s.get("durum") in ("bekliyor", "okundu", "denetlendi"):
            eksik += 1
            if taslak:
                ust_bilgi_satiri(doc, f"[PDF s. {s['kaynak_sayfa']} — henüz hazır değil]")
            continue
        ust_bilgi_satiri(doc, f"[ص {sayfa_no_ar(s)}]", rtl=True)
        if not temiz and s.get("kontrol_gerekli"):
            uyari(doc, "Bu sayfa uzman kontrolü bekliyor: " + "; ".join(s["kontrol_gerekli"]))
        tashih = ed.get("tashihler", []) + [dict(x, supheli=True) for x in ed.get("supheli", [])]
        alintilar = {x["blok"]: [] for x in s.get("alintilar", []) if "blok" in x}
        for x in s.get("alintilar", []):
            e = x.get("eslesme") or {}
            if e.get("durum") in ("dogrulandi", "yakin") and "blok" in x:
                on = "Krş. " if (e.get("durum") == "yakin" or x.get("bicim") in ("iktibas", "isaret")) else ""
                alintilar[x["blok"]].append({"edisyon": x["metin"], "not": on + e["referans"] + "."})
        serhli = "serh" in (meta.get("katmanlar") or [])
        for i, b in enumerate(ed["bloklar"]):
            if atlanir(b):
                continue
            p = doc.add_paragraph()
            if b["tur"] == "baslik":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(4)
            pPr = p._p.get_or_add_pPr()
            pPr.insert(0, OxmlElement("w:bidi"))
            notlar = []
            for n in [x for x in tashih if x.get("blok") == i]:
                if n.get("supheli"):
                    metin_not = n.get("aciklama") or "Baskıda bu kısım bozuk görünüyor."
                else:
                    metin_not = f"Baskıda: {n.get('baski', '?')}" + (f"; {n['gerekce']}" if n.get("gerekce") else "")
                notlar.append({"edisyon": n.get("edisyon", ""), "not": metin_not})
            notlar += alintilar.get(i, [])
            kucuk = b["tur"] in ("dipnot", "kenar_notu") or b.get("katman") in ("hasiye", "tashih")
            boyut = 18 if b["tur"] == "baslik" else (12 if kucuk else 16)
            if notlar:
                tashih_yerlestir(p, b["metin"], notlar, dn)
                for r in p.runs:
                    if r.text:
                        rtl_run(r, AR_FONT, boyut)
            else:
                rtl_run(p.add_run(b["metin"]), AR_FONT, boyut)
            if b["tur"] == "baslik" or (serhli and b.get("katman") == "matn"):
                for r in p.runs:
                    r.bold = True
        yazilan += 1
    dn.kaydet()
    return doc, yazilan, eksik


# ---------------- Türkçe çeviri ----------------
def isaretli_paragraf(p, metin, s, dn, temiz):
    alintilar = {x["id"]: x for x in s.get("alintilar", [])}
    notlar = {}
    for n in (s.get("ceviri") or {}).get("notlar", []):
        if isinstance(n, dict) and n.get("id"):
            notlar[n["id"]] = n["metin"]
    bas = 0
    for m in ISARET.finditer(metin):
        if m.start() > bas:
            p.add_run(metin[bas:m.start()])
        meal_mi, kimlik = m.group(1), m.group(2)
        if kimlik.startswith("N"):
            if kimlik in notlar:
                dn.ekle(p, notlar.pop(kimlik))
        else:
            x = alintilar.get(kimlik, {})
            e = x.get("eslesme") or {}
            if meal_mi and e.get("tur") == "ayet" and e.get("durum") == "dogrulandi":
                p.add_run("“" + e["meal"].strip() + "”")
            if e.get("durum") in ("dogrulandi", "yakin"):
                on = "Krş. " if (e.get("durum") == "yakin" or x.get("bicim") in ("iktibas", "isaret")) else ""
                metin_not = on + e["referans"] + "."
                if e.get("tur") == "ayet" and meal_mi:
                    metin_not += " Meal: Diyanet İşleri."
                ayrica = e.get("ayrica") or []
                if ayrica and e.get("tur") == "hadis":
                    metin_not += " Ayrıca bk. " + "; ".join(ayrica[:3]) + "."
                dn.ekle(p, metin_not)
                if e.get("durum") == "yakin" and not temiz:
                    r = p.add_run(" [lafız kaynakla birebir tutmuyor]")
                    r.font.size = Pt(8)
                    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            elif not temiz and x:
                r = p.add_run(" [kaynağı bulunamadı]")
                r.font.size = Pt(8)
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        bas = m.end()
    if bas < len(metin):
        p.add_run(metin[bas:])
    return notlar  # işaretsiz kalan notlar


def turkce_uret(kd, meta, yazar, temiz, taslak):
    doc = Document()
    sayfa_ayari(doc, rtl=False)
    st = doc.styles["Normal"]
    st.font.name = TR_FONT
    st.font.size = Pt(12)
    dn = Dipnotlar(doc, font=TR_FONT, boyut_pt=9)

    for metin, boy, kalin, ital in ((meta.get("baslik_tr") or meta.get("baslik", ""), 22, True, False),
                                    (meta.get("baslik_ar") or "", 16, False, False),
                                    (yazar.get("ad", ""), 14, False, False),
                                    ("Arapça aslından Türkçe çeviri", 11, False, True)):
        if metin:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(metin)
            r.bold, r.italic = kalin, ital
            r.font.size = Pt(boy)
            if metin == meta.get("baslik_ar"):
                rtl_run(r, AR_FONT, boy)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Ayet mealleri Diyanet İşleri mealinden alınmıştır. Hadis referansları standart numaralarla verilmiştir "
                  "(Müslim için Fuad Abdülbâkî numarası). \"Krş.\" ile verilen referanslarda yazar ifadeyi aynen değil, "
                  "yakın bir lafızla ya da mana olarak aktarmıştır. Köşeli parantez içindeki sayfa numaraları [s. ...] "
                  "Arapça baskının sayfalarıdır.")
    r.font.size = Pt(9)
    r.italic = True
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    yazilan = eksik = 0
    for path in sayfalar(kd):
        s = oku(path)
        if s.get("durum") == ATLANDI:
            continue
        c = s.get("ceviri")
        if not c or s.get("durum") not in ("cevrildi", "ceviri_denetlendi"):
            eksik += 1
            if taslak:
                ust_bilgi_satiri(doc, f"[PDF s. {s['kaynak_sayfa']} — henüz çevrilmedi]")
            continue
        ust_bilgi_satiri(doc, f"[s. {sayfa_no_tr(s)}]")
        if not temiz and s.get("kontrol_gerekli"):
            uyari(doc, "Bu sayfa uzman kontrolü bekliyor: " + "; ".join(s["kontrol_gerekli"]))
        son_p = None
        kalan = {}
        kaynak_b = (s.get("edisyon") or {}).get("bloklar") or []
        serhli = "serh" in (meta.get("katmanlar") or [])
        for i, b in enumerate(c["bloklar"]):
            if i < len(kaynak_b) and "katman" not in b and kaynak_b[i].get("katman"):
                b = dict(b, katman=kaynak_b[i]["katman"])
            if atlanir(b):
                continue
            if b["tur"] == "baslik":
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                kalan = isaretli_paragraf(p, b["metin"], s, dn, temiz)
                for r in p.runs:
                    r.bold = True
                    r.font.size = Pt(13)
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.first_line_indent = Cm(0.6)
                if b.get("katman") == "hasiye":
                    p.add_run("[Hâşiye] ").italic = True
                kalan = isaretli_paragraf(p, b["metin"], s, dn, temiz)
                if b["tur"] in ("dipnot", "kenar_notu") or b.get("katman") in ("hasiye", "tashih"):
                    for r in p.runs:
                        r.font.size = Pt(10)
                if serhli and b.get("katman") == "matn":
                    for r in p.runs:
                        r.bold = True
            son_p = p
        # İşaretsiz çevirmen notları (eski biçim: düz metin listesi) sayfanın son paragrafına dipnot olur
        for n in c.get("notlar", []):
            metin = n if isinstance(n, str) else (n.get("metin") if n.get("id") in kalan else None)
            if metin and son_p is not None:
                dn.ekle(son_p, metin)
        yazilan += 1
    dn.kaydet()
    return doc, yazilan, eksik


def kaydet(doc, ad):
    CIKTI.mkdir(exist_ok=True)
    hedef = CIKTI / f"{ad}.docx"
    n = 2
    while hedef.exists():  # önceki sürümde elle düzeltme yapılmış olabilir; üzerine yazma
        hedef = CIKTI / f"{ad} ({n}).docx"
        n += 1
    doc.save(hedef)
    return hedef


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    ap.add_argument("kitap")
    ap.add_argument("--asil", action="store_true")
    ap.add_argument("--turkce", action="store_true")
    ap.add_argument("--temiz", action="store_true")
    ap.add_argument("--taslak", action="store_true")
    a = ap.parse_args()
    if not (a.asil or a.turkce):
        a.asil = a.turkce = True

    kd = kitap_dizini(a.kitap)
    meta = oku(kd / "kitap.json")
    yazar = oku(YAZARLAR / meta["yazar"] / "profil.json") if meta.get("yazar") and (YAZARLAR / meta["yazar"] / "profil.json").exists() else {}
    ad = meta.get("baslik_tr") or meta.get("baslik") or a.kitap
    ek = "" if a.temiz else " (taslak)"
    if a.asil:
        doc, y, e = asil_uret(kd, meta, yazar, a.temiz, a.taslak)
        h = kaydet(doc, f"{ad} - Arapça Asıl Metin{ek}")
        print(f"ASIL {h.relative_to(CIKTI.parent)}  sayfa={y} eksik={e}")
    if a.turkce:
        doc, y, e = turkce_uret(kd, meta, yazar, a.temiz, a.taslak)
        h = kaydet(doc, f"{ad} - Türkçe Çeviri{ek}")
        print(f"TURKCE {h.relative_to(CIKTI.parent)}  sayfa={y} eksik={e}")


if __name__ == "__main__":
    main()
