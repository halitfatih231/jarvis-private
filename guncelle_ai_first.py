# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil
import re

jarvis = Path(__file__).with_name("jarvis.py")
metin = jarvis.read_text(encoding="utf-8")

if "def komutu_isle_ai_first(komut):" in metin:
    print("AI-first sistemi zaten eklenmis.")
    raise SystemExit

if "def ai_dogal_dil_fallback(komut):" not in metin:
    print("HATA: ai_dogal_dil_fallback() bulunamadi.")
    raise SystemExit

if "def komutu_isle(komut):" not in metin:
    print("HATA: komutu_isle() bulunamadi.")
    raise SystemExit


# ============================================================
# AI-FIRST KOMUT KATMANI
# ============================================================

ai_first_kodu = r'''
def komutu_isle_ai_first(komut):
    """
    Sesli Jarvis icin ana karar katmani.

    Kullanici dogal Turkce konusur.
    Claude niyeti yorumlar.
    Gercek Windows islemlerini Jarvis yapar.

    Eski regex sistemi silinmez; ancak ana sesli akista
    karar verici olarak kullanilmaz.
    """

    k = norm(komut)

    if not k:
        return True

    # Cikis komutlarini Claude'a gonderme.
    if k in {
        "cik",
        "kapat",
        "jarvis kapat",
        "jarvisi kapat",
        "jarvis cik",
        "exit",
        "quit",
    }:
        print(
            "Jarvis: Görüşürüz."
        )

        konus(
            "Görüşürüz."
        )

        return False

    print(
        "Jarvis: İsteğini anlıyorum..."
    )

    return ai_dogal_dil_fallback(
        komut
    )


'''


# Eski komut fonksiyonundan hemen once ekle
yeni = metin.replace(
    "def komutu_isle(komut):",
    ai_first_kodu + "\ndef komutu_isle(komut):",
    1
)


# ============================================================
# ANA DONGUYU AI-FIRST'E BAGLA
# ============================================================

eski = '''            devam = komutu_isle(
                komut
            )
'''

yeni_cagri = '''            devam = komutu_isle_ai_first(
                komut
            )
'''

if eski in yeni:
    yeni = yeni.replace(
        eski,
        yeni_cagri,
        1
    )
else:
    # Bicim farkliysa regex ile yalnizca main icindeki cagriyi degistir
    desen = (
        r'devam\s*=\s*komutu_isle\(\s*'
        r'komut\s*'
        r'\)'
    )

    yeni, adet = re.subn(
        desen,
        "devam = komutu_isle_ai_first(komut)",
        yeni,
        count=1
    )

    if adet != 1:
        print(
            "HATA: Ana dongudeki komutu_isle() cagrisi bulunamadi."
        )
        raise SystemExit


# ============================================================
# BASLANGIC MESAJINI GUNCELLE
# ============================================================

yeni = yeni.replace(
    '"Sesli komut modu aktif. "',
    '"Sesli AI-first doğal dil modu aktif. "',
    1
)


# ============================================================
# SYNTAX TESTI
# ============================================================

compile(
    yeni,
    str(jarvis),
    "exec"
)


# ============================================================
# YEDEK
# ============================================================

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_ai_first_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)


# ============================================================
# KAYDET
# ============================================================

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Jarvis AI-first mimariye gecirildi.")
print("DOGAL KONUSMA -> CLAUDE -> GUVENLI JARVIS EYLEMI")
print("ESKI KOMUT SISTEMI: silinmedi, dosyada duruyor")
print("SILME ONAYI: korunuyor")
print("HIGGSFIELD KREDI ONAYI: korunuyor")
print("JARVIS KAPAT: yerel ve hizli")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")