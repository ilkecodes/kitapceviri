"""Kitabın ilerleme durumu.

Aşamalar ve sayfa durumları (her aşama bir önceki durumdaki sayfaları alır):
  okuma          bekliyor        -> okundu              (sayfa-okuyucu)
  denetim        okundu          -> denetlendi          (sayfa-denetci)
  edisyon        denetlendi      -> edisyonlandi        (edisyoncu)
  alinti         edisyonlandi    -> alintilandi         (alinti-tespit + alinti.py dogrula)
  ceviri         alintilandi     -> cevrildi            (sayfa-cevirmen)
  ceviri_denetim cevrildi        -> ceviri_denetlendi   (ceviri-denetci)
  redaksiyon     ceviri_denetlendi (redaksiyon alanı yoksa)   (redaktor)

Kullanım:
  python durum.py kitaplar
  python durum.py ozet <kitap>
  python durum.py siradaki <kitap> <asama> [--adet 8]
  python durum.py guncelle <kitap>        # ajanların yazdıklarını doğrular, durumları ilerletir
  python durum.py kontrol <kitap>         # insan kontrolü gereken sayfalar ve nedenleri
  python durum.py kirpilacak <kitap>      # yüksek çözünürlükte yeniden okunması gereken sayfalar
  python durum.py metin-dok <kitap> [--sayfa-basi 40]   # terim taraması için edisyon metnini dosyalara döker
  python durum.py tarama-bitti <kitap>    # terim taraması tamamlandı işareti
  python durum.py sifirla <kitap> <sayfa> <asama>       # bir aşamayı (ve sonrakileri) yeniden yaptırmak için
  python durum.py duzen <kitap>           # düzeni kitabın tarifinden farklı olan sayfalar
  python durum.py takip <kitap>           # yazmalarda takip kelimesi kontrolü (eksik/karışık varak)
"""
from __future__ import annotations

import argparse
from collections import Counter

from ortak import ATLANDI, kitap_dizini, kitaplar, oku, sayfalar, utf8_cikti, yaz

ASAMALAR = ["okuma", "denetim", "edisyon", "alinti", "ceviri", "ceviri_denetim"]
GIRIS = {"okuma": "bekliyor", "denetim": "okundu", "edisyon": "denetlendi", "alinti": "edisyonlandi",
         "ceviri": "alintilandi", "ceviri_denetim": "cevrildi"}
CIKIS = {"okuma": "okundu", "denetim": "denetlendi", "edisyon": "edisyonlandi", "alinti": "alintilandi",
         "ceviri": "cevrildi", "ceviri_denetim": "ceviri_denetlendi"}
ALAN = {"okuma": "okuma", "denetim": "denetim", "edisyon": "edisyon", "alinti": "alintilar",
        "ceviri": "ceviri", "ceviri_denetim": "ceviri_denetim"}
VARSAYILAN_ESIK = 0.80


def bloklar_gecerli(b) -> bool:
    return isinstance(b, list) and all(isinstance(x, dict) and "tur" in x and "metin" in x for x in b)


def asama_gecerli(asama: str, s: dict) -> str | None:
    """Aşamanın çıktısı geçerliyse None, değilse hata açıklaması."""
    v = s.get(ALAN[asama])
    if asama == "okuma":
        if not isinstance(v, dict):
            return "okuma alanı yok ya da bozuk"
        if v.get("atla"):
            return None
        return None if bloklar_gecerli(v.get("bloklar")) else "okuma.bloklar hatalı"
    if asama == "denetim":
        if not isinstance(v, dict) or not isinstance(v.get("guven"), (int, float)) or not isinstance(v.get("sorunlar"), list):
            return "denetim.guven/sorunlar hatalı"
        if v.get("duzeltilmis_bloklar") is not None and not bloklar_gecerli(v["duzeltilmis_bloklar"]):
            return "denetim.duzeltilmis_bloklar hatalı"
        return None
    if asama == "edisyon":
        if not isinstance(v, dict) or not bloklar_gecerli(v.get("bloklar")) or not isinstance(v.get("tashihler"), list):
            return "edisyon.bloklar/tashihler hatalı"
        return None
    if asama == "alinti":
        if not isinstance(v, list):
            return "alintilar listesi yok"
        for x in v:
            if not isinstance(x, dict) or "metin" not in x or "id" not in x:
                return "alinti kaydı hatalı"
            if "eslesme" not in x:
                return "alinti.py dogrula henüz çalışmadı"
        return None
    if asama == "ceviri":
        return None if isinstance(v, dict) and bloklar_gecerli(v.get("bloklar")) else "ceviri.bloklar hatalı"
    if asama == "ceviri_denetim":
        if not isinstance(v, dict) or not isinstance(v.get("sorunlar"), list):
            return "ceviri_denetim.sorunlar hatalı"
        return None
    return "bilinmeyen aşama"


def kontrol_nedenleri(s: dict, esik: float) -> list[str]:
    n = []
    den = s.get("denetim") or {}
    g = den.get("guven")
    if isinstance(g, (int, float)) and g < esik:
        n.append(f"okuma güveni düşük ({g:.2f})")
    yuksek = [x for x in den.get("sorunlar", []) if x.get("ciddiyet") == "yuksek" and not x.get("duzeltildi")]
    if yuksek:
        n.append(f"{len(yuksek)} çözülmemiş ciddi okuma sorunu")
    belirsiz = (s.get("okuma") or {}).get("belirsiz_sayisi", 0) or 0
    if belirsiz >= 5:
        n.append(f"{belirsiz} okunamayan/belirsiz yer")
    ed = s.get("edisyon") or {}
    if ed.get("supheli"):
        n.append(f"{len(ed['supheli'])} şüpheli/bozuk yer (edisyon)")
    for x in s.get("alintilar", []):
        d = (x.get("eslesme") or {}).get("durum")
        if d == "yakin":
            n.append(f"alıntı {x['id']} lafzen tutmuyor ({x['eslesme'].get('referans')})")
        elif d == "bulunamadi" and x.get("tur_tahmini") in ("ayet", "hadis"):
            n.append(f"alıntı {x['id']} kaynakta bulunamadı")
    cd = s.get("ceviri_denetim") or {}
    cy = [x for x in cd.get("sorunlar", []) if x.get("ciddiyet") == "yuksek" and not x.get("duzeltildi")]
    if cy:
        n.append(f"{len(cy)} çözülmemiş ciddi çeviri sorunu")
    return n


def guncelle(d, esik: float) -> dict:
    sayim, bozuk = Counter(), []
    for p in sayfalar(d):
        # Bir ajan bu sayfaya hâlâ yazıyor olabilir: okunamayan ya da okuduktan sonra değişen dosyayı ezme
        once = p.stat().st_mtime_ns
        try:
            s = oku(p)
        except ValueError:
            bozuk.append((p.stem, "MESGUL: dosya okunamadı (yazılıyor olabilir); sonra tekrar güncelleyin"))
            continue
        try:
            ilerledi = True
            while ilerledi and s.get("durum") != ATLANDI:
                ilerledi = False
                for asama in ASAMALAR:
                    if s.get("durum") == GIRIS[asama] and ALAN[asama] in s:
                        h = asama_gecerli(asama, s)
                        if h:
                            if not (asama == "alinti" and "dogrula" in h):
                                bozuk.append((s["sayfa"], h))
                            break
                        if asama == "okuma" and s["okuma"].get("atla"):
                            s["durum"] = ATLANDI
                        else:
                            s["durum"] = CIKIS[asama]
                        ilerledi = True
                        break
            s["kontrol_gerekli"] = kontrol_nedenleri(s, esik)
        except (KeyError, TypeError, AttributeError) as e:
            bozuk.append((s.get("sayfa", p.stem), f"beklenmeyen yapı: {e}"))
            continue
        if p.stat().st_mtime_ns != once:
            # Okuduktan sonra bir ajan yazdı: onun işini ezmemek için bu sayfayı bu turda bırak
            bozuk.append((s.get("sayfa", p.stem), "MESGUL: güncellerken değişti; sonra tekrar güncelleyin"))
            continue
        yaz(p, s)
        sayim[s["durum"]] += 1
    return {"sayim": sayim, "bozuk": bozuk}


def redaksiyon_bekliyor(s: dict) -> bool:
    return s.get("durum") == "ceviri_denetlendi" and "redaksiyon" not in (s.get("ceviri") or {})


def main() -> None:
    utf8_cikti()
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("kitaplar")
    for k in ("ozet", "guncelle", "kontrol", "kirpilacak", "tarama-bitti", "duzen", "takip"):
        alt.add_parser(k).add_argument("kitap")
    sp = alt.add_parser("siradaki")
    sp.add_argument("kitap")
    sp.add_argument("asama", choices=ASAMALAR + ["redaksiyon"])
    sp.add_argument("--adet", type=int, default=8)
    md = alt.add_parser("metin-dok")
    md.add_argument("kitap")
    md.add_argument("--sayfa-basi", type=int, default=40)
    sf = alt.add_parser("sifirla")
    sf.add_argument("kitap")
    sf.add_argument("sayfa")
    sf.add_argument("asama", choices=ASAMALAR)
    a = ap.parse_args()

    if a.komut == "kitaplar":
        for k in kitaplar():
            print(k)
        return

    d = kitap_dizini(a.kitap)
    meta = oku(d / "kitap.json")
    esik = meta.get("guven_esigi", VARSAYILAN_ESIK)

    if a.komut == "guncelle":
        r = guncelle(d, esik)
        for k, v in sorted(r["sayim"].items()):
            print(f"{k} {v}")
        for sid, neden in r["bozuk"]:
            print(f"BOZUK {sid} {neden}")
        return

    if a.komut == "ozet":
        say, kontrol, red = Counter(), 0, 0
        for p in sayfalar(d):
            s = oku(p)
            say[s.get("durum")] += 1
            kontrol += bool(s.get("kontrol_gerekli"))
            red += redaksiyon_bekliyor(s)
        toplam = sum(say.values())
        print(f"KITAP {a.kitap}")
        print(f"YAZAR {meta.get('yazar') or 'belirlenmedi'}")
        print(f"DIL {meta.get('dil') or 'belirlenmedi'}")
        print(f"TOPLAM {toplam}")
        for k in ["bekliyor", "okundu", "denetlendi", "edisyonlandi", "alintilandi", "cevrildi", "ceviri_denetlendi", ATLANDI]:
            print(f"{k} {say.get(k, 0)}")
        print(f"REDAKSIYON_BEKLEYEN {red}")
        print(f"KONTROL_GEREKLI {kontrol}")
        arapca_hazir = sum(say.get(k, 0) for k in ("alintilandi", "cevrildi", "ceviri_denetlendi", ATLANDI))
        print(f"ARAPCA_HAZIR {arapca_hazir}/{toplam}")
        print(f"TURKCE_HAZIR {say.get('ceviri_denetlendi', 0) + say.get(ATLANDI, 0)}/{toplam}")
        if meta.get("dil") is None:
            sir = "ornek_tarama"
        elif say.get("bekliyor"):
            sir = "okuma"
        elif say.get("okundu"):
            sir = "denetim"
        elif say.get("denetlendi"):
            sir = "edisyon"
        elif say.get("edisyonlandi"):
            sir = "alinti"
        elif say.get("alintilandi") and meta.get("terim_taramasi") != "tamam":
            sir = "terim_taramasi"
        elif say.get("alintilandi"):
            sir = "ceviri"
        elif say.get("cevrildi"):
            sir = "ceviri_denetim"
        elif red:
            sir = "redaksiyon"
        else:
            sir = "birlestir"
        print(f"SIRADAKI_IS {sir}")
        return

    if a.komut == "siradaki":
        n = 0
        for p in sayfalar(d):
            s = oku(p)
            hazir = redaksiyon_bekliyor(s) if a.asama == "redaksiyon" else s.get("durum") == GIRIS[a.asama]
            if hazir:
                parcalar = ",".join(s.get("parcalar", [])) or "-"
                print(f"{s['sayfa']}\t{s['gorsel']}\tcalisma/{a.kitap}/durum/{p.name}\t{parcalar}")
                n += 1
                if n >= a.adet:
                    break
        if n == 0:
            print("YOK")
        return

    if a.komut == "kontrol":
        for p in sayfalar(d):
            s = oku(p)
            if s.get("kontrol_gerekli"):
                ks = s.get("kitap_sayfa") or "?"
                print(f"{s['sayfa']}\tkitap s. {ks}\tPDF s. {s['kaynak_sayfa']}\t{'; '.join(s['kontrol_gerekli'])}")
        return

    if a.komut == "kirpilacak":
        for p in sayfalar(d):
            s = oku(p)
            if s.get("durum") == "denetlendi" and not s.get("parcalar"):
                n = kontrol_nedenleri(s, esik)
                if any(("okuma" in x or "okunamayan" in x) for x in n):
                    print(f"{s['sayfa']}\t{'; '.join(n)}")
        return

    if a.komut == "metin-dok":
        hedef = d / "tarama"
        hedef.mkdir(exist_ok=True)
        uygun = []
        for p in sayfalar(d):
            s = oku(p)
            b = (s.get("edisyon") or {}).get("bloklar")
            if not b:
                continue
            m = "\n".join(x["metin"] for x in b if x.get("tur") not in ("sayfa_no", "ust_bilgi"))
            if m.strip():
                uygun.append((s["sayfa"], s.get("kitap_sayfa") or s["kaynak_sayfa"], m))
        for i in range(0, len(uygun), a.sayfa_basi):
            g = uygun[i:i + a.sayfa_basi]
            ad = f"{g[0][0]}-{g[-1][0]}.txt"
            (hedef / ad).write_text("\n\n".join(f"=== Sayfa {sid} (kitap s. {ks}) ===\n{m}" for sid, ks, m in g), encoding="utf-8")
            print(f"DOSYA calisma/{a.kitap}/tarama/{ad}")
        if not uygun:
            print("YOK")
        return

    if a.komut == "tarama-bitti":
        meta["terim_taramasi"] = "tamam"
        yaz(d / "kitap.json", meta)
        print("TAMAM")
        return

    if a.komut == "duzen":
        for p in sayfalar(d):
            s = oku(p)
            f = (s.get("okuma") or {}).get("duzen_farki")
            if f:
                print(f"{s['sayfa']}\tkitap s. {s.get('kitap_sayfa') or '?'}\t{f}")
        return

    if a.komut == "takip":
        import re as _re
        def _n(t):
            t = _re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)
            t = _re.sub("[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
            return _re.sub(r"[^\u0621-\u064A\s]", " ", t).split()
        liste = [oku(p) for p in sayfalar(d)]
        liste = [s for s in liste if s.get("durum") != ATLANDI and s.get("okuma")]
        sorun = 0
        for s, sonraki in zip(liste, liste[1:]):
            b = (s.get("denetim") or {}).get("duzeltilmis_bloklar") or s["okuma"].get("bloklar") or []
            takip = [x["metin"] for x in b if x.get("katman") == "takip" and x.get("metin")]
            if not takip:
                continue
            nb = (sonraki.get("denetim") or {}).get("duzeltilmis_bloklar") or sonraki["okuma"].get("bloklar") or []
            ilk = next((x["metin"] for x in nb if x.get("katman") in (None, "matn", "serh") and x.get("tur") != "baslik" and x.get("metin")), "")
            t, i = _n(takip[0]), _n(ilk)
            if t and i[:len(t)] != t:
                sorun += 1
                print(f"UYUMSUZ\t{s.get('kitap_sayfa') or s['sayfa']} -> {sonraki.get('kitap_sayfa') or sonraki['sayfa']}\ttakip: {' '.join(t)}\tsonraki sayfa: {' '.join(i[:4])}")
        print(f"KONTROL_EDILEN {len(liste)}  UYUMSUZ {sorun}")
        return

    if a.komut == "sifirla":
        p = d / "durum" / f"{a.sayfa}.json"
        s = oku(p)
        i = ASAMALAR.index(a.asama)
        for asama in ASAMALAR[i:]:
            s.pop(ALAN[asama], None)
        s["durum"] = GIRIS[a.asama]
        s.pop("kontrol_gerekli", None)
        yaz(p, s)
        print(f"SIFIRLANDI {a.sayfa} -> {s['durum']}")


if __name__ == "__main__":
    main()
