"""Gerekli Python paketlerini kontrol eder. Eksik varsa kurulum komutunu yazar."""
import importlib.util
import sys

GEREKLI = {"pymupdf": "pymupdf", "docx": "python-docx"}

eksik = [paket for modul, paket in GEREKLI.items() if importlib.util.find_spec(modul) is None]
if sys.version_info < (3, 9):
    print(f"PYTHON_ESKI {sys.version.split()[0]} (en az 3.9 gerekli)")
    sys.exit(1)
if eksik:
    print("EKSIK " + " ".join(eksik))
    print(f"KUR: {sys.executable} -m pip install --user " + " ".join(eksik))
    print(f"KUR_2: {sys.executable} -m pip install --break-system-packages " + " ".join(eksik) + "   # KUR başarısız olursa (bulut oturumu)")
    sys.exit(1)
print("HAZIR")
