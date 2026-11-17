"""Ajan şablonlarını derler: {{DAHIL:references/x.md}} yer tutucularını dosya içeriğiyle doldurup
.claude/agents/ altına yazar. Referans dosyalarını tek bir yerde tutup ajanlara gömmek içindir;
gömülü talimat her çağrıda aynı kaldığı için önbellekten okunur ve ajan dosya okumakla vakit harcamaz.

Bir referans dosyasını (ör. ceviri-uslubu.md) değiştirdikten sonra çalıştırın:
    python .claude/gelistirici/derle.py
"""
import re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent          # .claude
SKILL = KOK / "skills" / "kitap-cevirisi"
SABLON = KOK / "gelistirici" / "ajanlar"
HEDEF = KOK / "agents"
DESEN = re.compile(r"\{\{DAHIL:([^}]+)\}\}")


def dahil(m):
    yol = SKILL / m.group(1).strip()
    metin = yol.read_text(encoding="utf-8").strip()
    # Gömülen dosyanın ana başlıklarını bir seviye aşağı al ki ajan dosyasının yapısı bozulmasın
    return re.sub(r"^(#+) ", lambda h: "#" + h.group(1) + " ", metin, flags=re.M)


def main():
    HEDEF.mkdir(exist_ok=True)
    for s in sorted(SABLON.glob("*.md")):
        icerik = DESEN.sub(dahil, s.read_text(encoding="utf-8"))
        (HEDEF / s.name).write_text(icerik, encoding="utf-8")
        print(f"{s.name}: {len(icerik):,} karakter")


if __name__ == "__main__":
    main()
