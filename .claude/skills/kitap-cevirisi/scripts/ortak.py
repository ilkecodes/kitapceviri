"""Betiklerin ortak yardımcıları. Proje kökünden çalıştırılır (KitapCevirisi klasörü)."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

KOK = Path.cwd()
CALISMA = KOK / "calisma"
KAYNAK = KOK / "kaynak"
CIKTI = KOK / "cikti"
YAZARLAR = KOK / "yazarlar"

# Sayfa durumları, sırasıyla. Her aşama bir öncekinin çıktısını alır.
DURUMLAR = ["bekliyor", "okundu", "denetlendi", "edisyonlandi", "alintilandi", "cevrildi", "ceviri_denetlendi"]
ATLANDI = "atlandi"


def yazar_dizini(slug: str) -> Path:
    d = YAZARLAR / slug
    if not d.exists():
        hata(f"'{slug}' adlı yazar profili yok. Mevcut: {', '.join(p.name for p in YAZARLAR.glob('*') if p.is_dir()) or 'yok'}")
    return d


def kitap_yazari(kitap_dir: Path) -> str | None:
    return oku(kitap_dir / "kitap.json").get("yazar")


def kitap_kisaltma(ad: str) -> str:
    s = unicodedata.normalize("NFKD", ad).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "kitap"


def kitap_dizini(kitap: str) -> Path:
    d = CALISMA / kitap
    if not d.exists():
        hata(f"'{kitap}' adlı kitap bulunamadı. Mevcut kitaplar: {', '.join(kitaplar()) or 'yok'}")
    return d


def kitaplar() -> list[str]:
    if not CALISMA.exists():
        return []
    return sorted(p.name for p in CALISMA.iterdir() if (p / "kitap.json").exists())


def oku(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def yaz(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def sayfalar(kitap_dir: Path) -> list[Path]:
    return sorted((kitap_dir / "durum").glob("*.json"))


def hata(mesaj: str) -> None:
    print(f"HATA: {mesaj}", file=sys.stderr)
    sys.exit(1)


def utf8_cikti() -> None:
    # Windows konsolunda Türkçe/Arapça karakterler bozulmasın
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
