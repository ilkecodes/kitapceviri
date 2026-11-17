"""Yazar profili: sözlükçe, üslup kararları ve çeviri hafızası (onaylı Arapça-Türkçe sayfa çiftleri).

Klasör: yazarlar/<yazar>/
  profil.json      ad, Arapça adı, eserler
  sozlukce.json    ıstılah ve isimler (sozlukce.py ile yönetilir)
  uslup.md         yazara özel üslup kararları (serbest metin; çevirmen ve redaktör okur)
  edisyon.md       (isteğe bağlı) yazara özel edisyon kuralları
  hafiza.jsonl     onaylı çeviri çiftleri, satır başına bir sayfa

Kullanım:
  python yazar.py olustur <yazar> --ad "Şah Veliyyullah ed-Dihlevî" [--ad-ar "..."]
  python yazar.py hafiza-yukle <yazar> --asil asil.docx --ceviri ceviri.docx --eser "Eser adı"
  python yazar.py hafiza-ekle-kitap <kitap>          # bitmiş bir kitabın sayfalarını hafızaya ekler
  python yazar.py ornek <yazar> --sayfa-json <yol> [--adet 3]   # bu sayfaya en benzer geçmiş çeviri örnekleri
  python yazar.py bul <yazar> "<Arapça kelime>" [--adet 5]      # bu kelime geçmişte nasıl çevrilmiş
  python yazar.py dok <yazar> [--sayfa-basi 25]       # profil çıkarmak için hafızayı okunur dosyalara döker
  python yazar.py istatistik <yazar>
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from ortak import YAZARLAR, hata, kitap_dizini, oku, sayfalar, utf8_cikti, yaz

HAREKE = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
AR_RAKAM = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Mevcut Word dosyalarındaki sayfa işaretleri: ﴿ كتاب ص ١٦ ﴾ ve ﴿ s. 16 ﴾ (ve yeni biçim [ص ١٦] / [s. 16])
AR_ISARET = re.compile(r"(?:﴿\s*كتاب\s*ص\s*([0-9٠-٩]+)\s*﴾|\[\s*ص\s*([0-9٠-٩]+)\s*\])")
TR_ISARET = re.compile(r"(?:﴿\s*s\.\s*(\d+)\s*﴾|\[\s*s\.\s*(\d+)\s*\])")


def normal(s: str) -> str:
    s = HAREKE.sub("", s)
    s = re.sub("[إأآٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ی", "ي").replace("ة", "ه")
    s = re.sub(r"[^ء-ي\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ydir(slug: str) -> Path:
    d = YAZARLAR / slug
    if not d.exists():
        hata(f"Yazar profili yok: {slug}. Önce: yazar.py olustur {slug} --ad ...")
    return d


def hafiza(d: Path) -> list[dict]:
    p = d / "hafiza.jsonl"
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def hafiza_ekle(d: Path, kayitlar: list[dict]) -> int:
    mevcut = {(k["eser"], str(k["sayfa"])) for k in hafiza(d)}
    yeni = [k for k in kayitlar if (k["eser"], str(k["sayfa"])) not in mevcut]
    with open(d / "hafiza.jsonl", "a", encoding="utf-8") as f:
        for k in yeni:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    return len(yeni)


def docx_sayfalari(yol: Path, desen) -> dict:
    import docx
    sayfa, out = None, {}
    for p in docx.Document(yol).paragraphs:
        t = p.text.strip()
        if not t:
            continue
        m = desen.search(t)
        if m and len(t) < 40:
            no = next(g for g in m.groups() if g)
            sayfa = int(no.translate(AR_RAKAM))
            out.setdefault(sayfa, [])
            continue
        if sayfa is not None:
            out[sayfa].append(t)
    return {k: "\n".join(v) for k, v in out.items() if v}


class TfIdf:
    def __init__(self, belgeler: list[str]):
        self.tf = [Counter(w for w in normal(b).split() if len(w) > 2) for b in belgeler]
        df = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(belgeler)
        self.idf = {w: math.log((n + 1) / (c + 1)) + 1 for w, c in df.items()}
        self.norm = [math.sqrt(sum((c * self.idf[w]) ** 2 for w, c in t.items())) or 1 for t in self.tf]

    def benzer(self, sorgu: str, adet: int):
        q = Counter(w for w in normal(sorgu).split() if len(w) > 2)
        qn = math.sqrt(sum((c * self.idf.get(w, 0)) ** 2 for w, c in q.items())) or 1
        skor = []
        for i, t in enumerate(self.tf):
            s = sum(c * t.get(w, 0) * self.idf.get(w, 0) ** 2 for w, c in q.items())
            if s:
                skor.append((s / (qn * self.norm[i]), i))
        skor.sort(reverse=True)
        return skor[:adet]


def sayfa_metni(s: dict) -> str:
    b = (s.get("edisyon") or {}).get("bloklar") or (s.get("denetim") or {}).get("duzeltilmis_bloklar") \
        or (s.get("okuma") or {}).get("bloklar") or []
    return "\n".join(x["metin"] for x in b if x.get("tur") not in ("sayfa_no", "ust_bilgi"))


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    o = alt.add_parser("olustur")
    o.add_argument("yazar")
    o.add_argument("--ad", required=True)
    o.add_argument("--ad-ar", default="")
    h = alt.add_parser("hafiza-yukle")
    h.add_argument("yazar")
    h.add_argument("--asil", required=True)
    h.add_argument("--ceviri", required=True)
    h.add_argument("--eser", required=True)
    alt.add_parser("hafiza-ekle-kitap").add_argument("kitap")
    r = alt.add_parser("ornek")
    r.add_argument("yazar")
    r.add_argument("--sayfa-json", required=True)
    r.add_argument("--adet", type=int, default=3)
    b = alt.add_parser("bul")
    b.add_argument("yazar")
    b.add_argument("kelime")
    b.add_argument("--adet", type=int, default=5)
    dk = alt.add_parser("dok")
    dk.add_argument("yazar")
    dk.add_argument("--sayfa-basi", type=int, default=25)
    alt.add_parser("istatistik").add_argument("yazar")
    a = ap.parse_args()

    if a.komut == "olustur":
        d = YAZARLAR / a.yazar
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "profil.json").exists():
            yaz(d / "profil.json", {"ad": a.ad, "ad_ar": a.ad_ar, "eserler": []})
        if not (d / "sozlukce.json").exists():
            yaz(d / "sozlukce.json", {"terimler": {}})
        if not (d / "uslup.md").exists():
            (d / "uslup.md").write_text(f"# {a.ad} — üslup kararları\n\n(Henüz karar yok.)\n", encoding="utf-8")
        print(f"YAZAR yazarlar/{a.yazar}")
        return

    if a.komut == "hafiza-ekle-kitap":
        kd = kitap_dizini(a.kitap)
        meta = oku(kd / "kitap.json")
        d = ydir(meta["yazar"])
        kayit = []
        for p in sayfalar(kd):
            s = oku(p)
            if s.get("durum") != "ceviri_denetlendi" or s.get("kontrol_gerekli"):
                continue
            tr = "\n".join(x["metin"] for x in s["ceviri"]["bloklar"] if x.get("metin"))
            kayit.append({"eser": meta.get("baslik_tr") or meta["baslik"], "sayfa": s.get("kitap_sayfa") or s["sayfa"],
                          "ar": sayfa_metni(s), "tr": tr, "kaynak": "skill"})
        n = hafiza_ekle(d, kayit)
        pr = oku(d / "profil.json")
        eser = meta.get("baslik_tr") or meta["baslik"]
        if eser not in pr["eserler"]:
            pr["eserler"].append(eser)
            yaz(d / "profil.json", pr)
        print(f"EKLENEN {n}  (kontrol bekleyen sayfalar eklenmedi)")
        return

    d = ydir(a.yazar)

    if a.komut == "hafiza-yukle":
        ar = docx_sayfalari(Path(a.asil), AR_ISARET)
        tr = docx_sayfalari(Path(a.ceviri), TR_ISARET)
        ortak = sorted(set(ar) & set(tr))
        kayit = [{"eser": a.eser, "sayfa": n, "ar": ar[n], "tr": tr[n], "kaynak": "onceki_ceviri"} for n in ortak]
        eklenen = hafiza_ekle(d, kayit)
        pr = oku(d / "profil.json")
        if a.eser not in pr["eserler"]:
            pr["eserler"].append(a.eser)
            yaz(d / "profil.json", pr)
        print(f"ESER {a.eser}")
        print(f"ASIL_SAYFA {len(ar)}  CEVIRI_SAYFA {len(tr)}  ESLESEN {len(ortak)}  EKLENEN {eklenen}")
        if set(ar) ^ set(tr):
            print(f"ESLESMEYEN {sorted(set(ar) ^ set(tr))[:20]}")
        return

    hz = hafiza(d)

    if a.komut == "istatistik":
        say = Counter(k["eser"] for k in hz)
        pr = oku(d / "profil.json")
        sz = oku(d / "sozlukce.json")["terimler"] if (d / "sozlukce.json").exists() else {}
        print(f"YAZAR {pr['ad']}")
        print(f"HAFIZA_SAYFA {len(hz)}")
        for e, n in say.most_common():
            print(f"  {e}: {n}")
        print(f"SOZLUKCE onayli={sum(1 for t in sz.values() if t.get('durum', 'onayli') == 'onayli')} aday={sum(1 for t in sz.values() if t.get('durum') == 'aday')}")
        return

    if a.komut == "ornek":
        if not hz:
            print("(hafıza boş)")
            return
        s = oku(Path(a.sayfa_json))
        metin = sayfa_metni(s)
        ix = TfIdf([k["ar"] for k in hz])
        for skor, i in ix.benzer(metin, a.adet):
            k = hz[i]
            print(f"### {k['eser']}, s. {k['sayfa']} (benzerlik {skor:.2f})")
            print("[Arapça]\n" + k["ar"][:1800])
            print("[Türkçe]\n" + k["tr"][:2600])
            print()
        return

    if a.komut == "bul":
        w = normal(a.kelime)
        n = 0
        for k in hz:
            na = normal(k["ar"])
            if w in na:
                i = na.find(w)
                print(f"### {k['eser']}, s. {k['sayfa']}")
                print("[Arapça] …" + na[max(0, i - 80): i + 80] + "…")
                print("[Türkçe sayfası] " + k["tr"][:700])
                print()
                n += 1
                if n >= a.adet:
                    break
        if n == 0:
            print("YOK")
        return

    if a.komut == "dok":
        hedef = d / "dok"
        hedef.mkdir(exist_ok=True)
        for i in range(0, len(hz), a.sayfa_basi):
            g = hz[i:i + a.sayfa_basi]
            ad = f"{i // a.sayfa_basi + 1:03d}.txt"
            (hedef / ad).write_text("\n\n".join(
                f"=== {k['eser']}, s. {k['sayfa']} ===\n[AR]\n{k['ar']}\n[TR]\n{k['tr']}" for k in g), encoding="utf-8")
            print(f"DOSYA yazarlar/{a.yazar}/dok/{ad}")
        return


if __name__ == "__main__":
    main()
