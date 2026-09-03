# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")
metin = jarvis.read_text(encoding="utf-8")

if "def dogal_ac_komutu(sorgu):" in metin:
    print("Dogal ac sistemi zaten eklenmis.")
    raise SystemExit


# ============================================================
# 1. DOGAL DOSYA / KLASOR ACMA FONKSIYONU
# ============================================================

hedef = "def dosya_ac_komutu(sorgu):"

if hedef not in metin:
    print("HATA: dosya_ac_komutu bulunamadi.")
    raise SystemExit


yardimci = r'''
def dogal_ac_komutu(sorgu):
    """
    'kisisel bilgi kayit formu ac'
    gibi dogal komutlarda dosya veya klasoru bulup acar.
    Belirsizlik varsa kendi kendine karar vermez.
    """

    q = norm(sorgu).strip()

    if not q:
        return False

    # Konusmada kullanilabilecek gereksiz kelimeleri temizle.
    q = re.sub(
        r"\s+(?:dosyami|dosyayi|dosyasini|dosya|"
        r"klasorumu|klasoru|klasorunu|klasor)$",
        "",
        q
    ).strip()

    if not q:
        return False

    dosyalar = dosya_bul(
        q,
        en_fazla=10
    )

    klasorler = klasor_bul(
        q,
        en_fazla=10
    )

    # Sadece dosya bulundu.
    if dosyalar and not klasorler:
        en_iyi = dosya_puani(
            dosyalar[0],
            q
        )

        ayni = [
            p for p in dosyalar
            if dosya_puani(p, q) == en_iyi
        ]

        if len(ayni) > 1:
            print(
                "Jarvis: Birden fazla dosya eslesmesi buldum. "
                "Hangisini istedigini belirt:"
            )

            for p in ayni[:10]:
                print(" -", p)

            return True

        dosyayi_ac(
            dosyalar[0]
        )

        print(
            "Jarvis: Acildi:",
            dosyalar[0]
        )

        return True

    # Sadece klasor bulundu.
    if klasorler and not dosyalar:
        if (
            len(klasorler) > 1
            and norm(klasorler[0].name)
            == norm(klasorler[1].name)
        ):
            print(
                "Jarvis: Ayni isimde birden fazla klasor buldum:"
            )

            for p in klasorler[:10]:
                print(" -", p)

            return True

        klasoru_ac(
            klasorler[0]
        )

        print(
            "Jarvis: Acildi:",
            klasorler[0]
        )

        return True

    # Hem dosya hem klasor bulunduysa otomatik tahmin yapma.
    if dosyalar and klasorler:
        print(
            "Jarvis: Hem dosya hem klasor eslesmesi buldum. "
            "Yanlis bir sey acmamak icin secim yapmiyorum."
        )

        print("Dosya:")
        for p in dosyalar[:3]:
            print(" -", p)

        print("Klasor:")
        for p in klasorler[:3]:
            print(" -", p)

        return True

    print(
        f"Jarvis: '{sorgu}' icin dosya veya klasor bulamadim."
    )

    return True


'''

yeni = metin.replace(
    hedef,
    yardimci + "\n" + hedef,
    1
)


# ============================================================
# 2. KOMUT YORUMLAYICIYA "X AC" KURALINI EKLE
# ============================================================

eski = '''    m = re.match(
        r"^(.+?) klasorunu ac$",
        k
    )

    if m:
        klasor_ac_komutu(
            m.group(1)
        )

        return True
'''

ekli = eski + r'''
    # --------------------------------------------------------
    # Dogal "X ac" komutu
    # Ornek: "kisisel bilgi kayit formu ac"
    # Program komutlari yukarida zaten kontrol edilmistir.
    # --------------------------------------------------------

    m = re.match(
        r"^(.+?) ac$",
        k
    )

    if m:
        dogal_ac_komutu(
            m.group(1)
        )

        return True
'''

if eski not in yeni:
    print("HATA: Klasor ac bolumu bulunamadi.")
    raise SystemExit

yeni = yeni.replace(
    eski,
    ekli,
    1
)


# ============================================================
# 3. SYNTAX TESTI + YEDEK + KAYIT
# ============================================================

compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_dogal_ac_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Dogal 'X ac' komutu Jarvis'e eklendi.")
print("ORNEK: kisisel bilgi kayit formu ac")
print("BELIRSIZLIK GUVENLIGI: aktif")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")