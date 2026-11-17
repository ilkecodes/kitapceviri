"""Ayet ve hadis alıntılarını veri setlerine karşı doğrular. Hiçbir referans hafızadan yazılmaz.

Kullanım:
  python alinti.py ara "<Arapça metin>"            # tek bir alıntıyı ara (deneme için)
  python alinti.py dogrula <kitap>                  # sayfalardaki alıntı adaylarını doğrular, sonucu yazar
  python alinti.py tara <kitap>                     # emniyet ağı: ajanın kaçırmış olabileceği uzun alıntıları listeler
  python alinti.py ozet <kitap>                     # doğrulanan / bulunamayan alıntıların listesi

Eşleşme ölçütü (pilotta belirlendi):
  - Alıntı 6 kelime ya da daha uzunsa: en az 6 kelime art arda birebir aynı olmalı ve alıntının en az %75'ini kapsamalı.
  - Alıntı 3-5 kelimeyse: kelimelerin tamamı art arda birebir bulunmalı. Bu tür eşleşmeler "kisa" diye işaretlenir.
  - Karşılaştırma harekesiz ve imlası normalleştirilmiş metin üzerinde yapılır.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from ortak import kitap_dizini, oku, sayfalar, utf8_cikti, yaz

VERI = Path(__file__).resolve().parent.parent / "veri"
HADIS_SIRASI = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah", "malik", "dehlawi"]
HAREKE = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
KALIPLAR = ["صلى الله عليه وسلم", "عليه الصلوة والسلام", "عليه الصلاة والسلام", "عليه السلام",
            "رضي الله عنه", "رضي الله عنهم", "تبارك وتعالى", "جل وعز", "عز وجل", "سبحانه وتعالى",
            "بسم الله الرحمن الرحيم", "والحمد لله رب العالمين", "ولا حول ولا قوة الا بالله العلي العظيم",
            "حسبنا الله ونعم الوكيل"]


def normal(s: str) -> str:
    s = HAREKE.sub("", s)
    s = re.sub("[إأآٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ی", "ي").replace("ئ", "ي").replace("ؤ", "و")
    s = s.replace("ة", "ه").replace("ء", "").replace("ک", "ك").replace("ھ", "ه").replace("ہ", "ه")
    s = re.sub(r"[^ء-ي\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


KALIP_N = [normal(k) for k in KALIPLAR]


def en_uzun_ortak(a: list[str], b: list[str]) -> int:
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return max((m.size for m in sm.get_matching_blocks()), default=0)


class Dizin:
    def __init__(self):
        self.kayit = []
        self.uc = defaultdict(set)
        self.ayet_konum = {}  # (sure, ayet) -> kayıt indeksi
        self.sureler = {}

    def _ekle(self, kayit: dict):
        i = len(self.kayit)
        kayit["k"] = kayit["norm"].split()
        self.kayit.append(kayit)
        k = kayit["k"]
        for j in range(len(k) - 2):
            self.uc[" ".join(k[j:j + 3])].add(i)
        return i

    def yukle(self):
        with gzip.open(VERI / "kuran.json.gz", "rt", encoding="utf-8") as f:
            q = json.load(f)
        self.sureler = {int(k): v for k, v in q["sureler"].items()}
        self.meal_kaynak = q["kaynak"]["meal"]
        for a in q["ayetler"]:
            i = self._ekle({"tur": "ayet", "s": a["s"], "a": a["a"], "ar": a["ar"], "meal": a["meal"], "norm": normal(a["ar"])})
            self.ayet_konum[(a["s"], a["a"])] = i
        for kod in HADIS_SIRASI:
            yol = VERI / f"hadis-{kod}.json.gz"
            if not yol.exists():
                continue
            with gzip.open(yol, "rt", encoding="utf-8") as f:
                h = json.load(f)
            for x in h["hadisler"]:
                self._ekle({"tur": "hadis", "kod": kod, "kitap": h["kitap"], "n": x["n"], "an": x.get("an"),
                            "tr": x.get("tr", ""), "norm": x["ar"]})
        return self

    # ---- arama ----
    def _adaylar(self, k: list[str], tur: str | None):
        say = Counter()
        if len(k) >= 3:
            for j in range(len(k) - 2):
                for i in self.uc.get(" ".join(k[j:j + 3]), ()):
                    say[i] += 1
        for i, _ in say.most_common(60):
            if tur and self.kayit[i]["tur"] != tur:
                continue
            yield i

    def ara(self, metin: str, tur: str | None = None) -> dict:
        n = normal(metin)
        for kp in KALIP_N:
            n = n.replace(kp, " ")
        k = n.split()
        if len(k) < 3:
            return {"durum": "cok_kisa"}
        kisa = len(k) < 6
        bulunan = []
        for i in self._adaylar(k, tur):
            r = self.kayit[i]
            uz = en_uzun_ortak(k, r["k"])
            if kisa:
                if uz < len(k):
                    continue
            elif uz < 6 or uz / len(k) < 0.75:
                continue
            bulunan.append((uz / len(k), uz, i))
        if not bulunan:
            return self._yakin(k, tur)
        bulunan.sort(key=lambda x: (-x[0], self._oncelik(self.kayit[x[2]])))
        ayetler = [b for b in bulunan if self.kayit[b[2]]["tur"] == "ayet"]
        hadisler = [b for b in bulunan if self.kayit[b[2]]["tur"] == "hadis"]
        # Alıntı hem bir ayeti hem o ayeti içeren bir hadisi karşılıyorsa ayet önceliklidir
        if ayetler and (not hadisler or ayetler[0][0] >= hadisler[0][0] - 0.05):
            return self._ayet_sonuc(k, ayetler, kisa)
        return self._hadis_sonuc(k, hadisler, kisa)

    def _yakin(self, k, tur):
        """Yazar alıntıyı lafzen değil, biraz değiştirerek aktarmış olabilir. Sıralı kelime örtüşmesine bakar.
        Bu seviye kesin sayılmaz; insan kontrolüne düşer."""
        if len(k) < 4:
            return {"durum": "bulunamadi"}
        # 2'li kelime gruplarıyla aday topla (3'lüden daha gevşek)
        ikili = defaultdict(int)
        for j in range(len(k) - 1):
            ik = (k[j], k[j + 1])
            for i in self._ikili_ara(ik, tur):
                ikili[i] += 1
        en_iyi = None
        for i, _ in sorted(ikili.items(), key=lambda x: -x[1])[:40]:
            r = self.kayit[i]
            sm = SequenceMatcher(None, k, r["k"], autojunk=False)
            ortak = sum(m.size for m in sm.get_matching_blocks())
            oran = ortak / len(k)
            if oran >= 0.7 and (en_iyi is None or oran > en_iyi[0]):
                en_iyi = (oran, i)
        if not en_iyi:
            return {"durum": "bulunamadi"}
        r = self.kayit[en_iyi[1]]
        if r["tur"] == "ayet":
            ref = f"{self.sureler.get(r['s'], r['s'])} {r['s']}/{r['a']}"
            return {"durum": "yakin", "tur": "ayet", "referans": ref, "kapsama": round(en_iyi[0], 2),
                    "meal": r["meal"], "meal_kaynak": self.meal_kaynak,
                    "uyari": "Lafız birebir tutmuyor; yazar ayeti değiştirerek ya da mealen aktarmış olabilir. Kontrol edilmeli."}
        return {"durum": "yakin", "tur": "hadis", "referans": self._hadis_ref(r), "kapsama": round(en_iyi[0], 2),
                "turkce": r.get("tr", "")[:1200],
                "uyari": "Lafız birebir tutmuyor; yazar hadisi farklı bir rivayetten ya da mana ile aktarmış olabilir. Kontrol edilmeli."}

    def _ikili_ara(self, ik, tur):
        # 3'lü dizinden türetilmiş basit ikili arama: ilk iki kelimesi eşleşen üçlüleri dolaş
        if not hasattr(self, "_ikili"):
            self._ikili = defaultdict(set)
            for i, r in enumerate(self.kayit):
                kk = r["k"]
                for j in range(len(kk) - 1):
                    self._ikili[(kk[j], kk[j + 1])].add(i)
        for i in self._ikili.get(ik, ()):
            if tur and self.kayit[i]["tur"] != tur:
                continue
            yield i

    def _oncelik(self, r):
        if r["tur"] == "ayet":
            return 0
        return 1 + HADIS_SIRASI.index(r["kod"])

    def _ayet_sonuc(self, k, ayetler, kisa):
        kap, uz, i = ayetler[0]
        r = self.kayit[i]
        s, a = r["s"], r["a"]
        # Alıntı komşu ayetlere taşıyor mu? En iyi kapsayan kısa aralığı bul
        en_iyi = (kap, a, a)
        for bas in range(max(1, a - 2), a + 1):
            for son in range(a, a + 3):
                if (s, bas) not in self.ayet_konum or (s, son) not in self.ayet_konum:
                    continue
                birlesik = []
                for x in range(bas, son + 1):
                    birlesik += self.kayit[self.ayet_konum[(s, x)]]["k"]
                kk = en_uzun_ortak(k, birlesik) / len(k)
                if kk > en_iyi[0] + 0.05 or (abs(kk - en_iyi[0]) <= 0.05 and (son - bas) < (en_iyi[2] - en_iyi[1])):
                    en_iyi = (kk, bas, son)
        _, bas, son = en_iyi
        ayet_kelime = sum(len(self.kayit[self.ayet_konum[(s, x)]]["k"]) for x in range(bas, son + 1))
        meal = " ".join(self.kayit[self.ayet_konum[(s, x)]]["meal"] for x in range(bas, son + 1))
        aralik = f"{bas}" if bas == son else f"{bas}-{son}"
        tam = len(k) / max(ayet_kelime, 1) >= 0.85
        return {
            "durum": "dogrulandi", "tur": "ayet", "kisa": kisa,
            "sure": self.sureler.get(s, str(s)), "sure_no": s, "ayet": aralik,
            "referans": f"{self.sureler.get(s, s)} {s}/{aralik}",
            "kapsama": round(en_iyi[0], 2),
            "tam_ayet": tam,
            "meal": meal, "meal_kaynak": self.meal_kaynak,
        }

    def _hadis_sonuc(self, k, hadisler, kisa):
        ilk = self.kayit[hadisler[0][2]]
        ayrica = []
        gorulen = {(ilk["kod"], ilk["n"])}
        for _, _, i in hadisler[1:]:
            r = self.kayit[i]
            if (r["kod"], r["n"]) in gorulen:
                continue
            gorulen.add((r["kod"], r["n"]))
            ayrica.append(self._hadis_ref(r))
            if len(ayrica) >= 4:
                break
        return {
            "durum": "dogrulandi", "tur": "hadis", "kisa": kisa,
            "referans": self._hadis_ref(ilk), "kitap": ilk["kitap"], "no": ilk["n"], "abdulbaki_no": ilk.get("an"),
            "kapsama": round(hadisler[0][0], 2),
            "turkce": ilk.get("tr", "")[:1200],
            "ayrica": ayrica,
        }

    @staticmethod
    def _hadis_ref(r):
        if r["kod"] == "muslim" and r.get("an"):
            return f"Müslim, nr. {str(r['an']).split('.')[0]}"
        return f"{r['kitap']}, nr. {r['n']}"


def edisyon_metni(s: dict) -> list[dict]:
    e = s.get("edisyon") or {}
    if e.get("bloklar"):
        return e["bloklar"]
    d = s.get("denetim") or {}
    return d.get("duzeltilmis_bloklar") or (s.get("okuma") or {}).get("bloklar") or []


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    a1 = alt.add_parser("ara")
    a1.add_argument("metin")
    a1.add_argument("--tur", choices=["ayet", "hadis"])
    for k in ("dogrula", "tara", "ozet"):
        alt.add_parser(k).add_argument("kitap")
    a = ap.parse_args()

    if a.komut == "ozet":
        d = kitap_dizini(a.kitap)
        for p in sayfalar(d):
            s = oku(p)
            for x in s.get("alintilar", []):
                e = x.get("eslesme", {})
                print(f"{s['sayfa']}\t{x['id']}\t{e.get('durum', 'dogrulanmadi')}\t{e.get('referans', '-')}\t{x['metin'][:60]}")
        return

    dz = Dizin().yukle()

    if a.komut == "ara":
        print(json.dumps(dz.ara(a.metin, a.tur), ensure_ascii=False, indent=1))
        return

    d = kitap_dizini(a.kitap)
    if a.komut == "dogrula":
        say = Counter()
        for p in sayfalar(d):
            s = oku(p)
            degisti = False
            for x in s.get("alintilar", []):
                if "eslesme" in x:
                    continue
                tur = x.get("tur_tahmini") if x.get("tur_tahmini") in ("ayet", "hadis") else None
                e = dz.ara(x["metin"], tur)
                if e["durum"] != "dogrulandi" and tur:
                    e = dz.ara(x["metin"])  # tahmin yanlış olabilir; türsüz bir daha dene
                x["eslesme"] = e
                say[e["durum"]] += 1
                degisti = True
            if degisti:
                yaz(p, s)
        for k, v in sorted(say.items()):
            print(f"{k} {v}")
        return

    if a.komut == "tara":
        # Emniyet ağı: ajanın işaretlemediği uzun alıntılar (en az 8 kelime) — sadece listeler, yazmaz
        for p in sayfalar(d):
            s = oku(p)
            isaretli = " ".join(normal(x["metin"]) for x in s.get("alintilar", []))
            for b in edisyon_metni(s):
                n = normal(b.get("metin", ""))
                for kp in KALIP_N:
                    n = n.replace(kp, " | ")
                for parca in n.split("|"):
                    k = parca.split()
                    for i in range(0, max(len(k) - 7, 1), 3):
                        w = " ".join(k[i:i + 8])
                        if len(w.split()) < 8 or w in isaretli:
                            continue
                        e = dz.ara(w)
                        if e["durum"] == "dogrulandi" and e["kapsama"] >= 0.9:
                            print(f"{s['sayfa']}\t{e['referans']}\t{w}")
        return


if __name__ == "__main__":
    main()
