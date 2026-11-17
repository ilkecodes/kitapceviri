"""python-docx için gerçek Word dipnotu desteği (python-docx bunu kendisi sağlamıyor).

Kullanım:
    dn = Dipnotlar(doc, font="Times New Roman", rtl=False)
    p = doc.add_paragraph(); p.add_run("metin"); dn.ekle(p, "Dipnot metni")
    ...
    dn.kaydet()   # doc.save()'den ÖNCE çağrılmalı
"""
from __future__ import annotations

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from xml.sax.saxutils import escape

CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class Dipnotlar:
    def __init__(self, doc, font: str = "Times New Roman", boyut_pt: float = 9, rtl: bool = False):
        self.doc = doc
        self.font = font
        self.boyut = int(boyut_pt * 2)
        self.rtl = rtl
        self.notlar: list[tuple[int, str]] = []
        self.sayac = 0

    def _ref_run(self, p, footnote_id: int):
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        va = OxmlElement("w:vertAlign")
        va.set(qn("w:val"), "superscript")
        rpr.append(va)
        if self.rtl:
            rpr.append(OxmlElement("w:rtl"))
        r.append(rpr)
        ref = OxmlElement("w:footnoteReference")
        ref.set(qn("w:id"), str(footnote_id))
        r.append(ref)
        p._p.append(r)

    def ekle(self, paragraf, metin: str) -> int:
        self.sayac += 1
        self._ref_run(paragraf, self.sayac)
        self.notlar.append((self.sayac, metin))
        return self.sayac

    def _xml(self) -> bytes:
        bidi = "<w:bidi/>" if self.rtl else ""
        jc = '<w:jc w:val="right"/>' if self.rtl else ""
        rtl = "<w:rtl/>" if self.rtl else ""
        fnt = f'<w:rFonts w:ascii="{self.font}" w:hAnsi="{self.font}" w:cs="{self.font}"/>'
        sz = f'<w:sz w:val="{self.boyut}"/><w:szCs w:val="{self.boyut}"/>'
        parcalar = [
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<w:footnotes xmlns:w="{W}">',
            '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>',
            '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>',
        ]
        for i, metin in self.notlar:
            parcalar.append(
                f'<w:footnote w:id="{i}"><w:p><w:pPr>{bidi}{jc}<w:spacing w:after="0"/></w:pPr>'
                f'<w:r><w:rPr>{fnt}{sz}<w:vertAlign w:val="superscript"/>{rtl}</w:rPr><w:footnoteRef/></w:r>'
                f'<w:r><w:rPr>{fnt}{sz}{rtl}</w:rPr><w:t xml:space="preserve"> {escape(metin)}</w:t></w:r></w:p></w:footnote>'
            )
        parcalar.append("</w:footnotes>")
        return "".join(parcalar).encode("utf-8")

    def kaydet(self):
        if not self.notlar:
            return
        part = Part(PackURI("/word/footnotes.xml"), CT, self._xml(), self.doc.part.package)
        self.doc.part.relate_to(part, RT.FOOTNOTES)
