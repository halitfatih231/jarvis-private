# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")
metin = jarvis.read_text(encoding="utf-8")

if "def sesli_komut_al():" in metin:
    print("Mikrofon sistemi zaten eklenmis.")
    raise SystemExit


# ------------------------------------------------------------
# 1. Mikrofon fonksiyonunu norm() fonksiyonundan once ekle
# ------------------------------------------------------------

hedef = "def norm(metin):"

if hedef not in metin:
    print("HATA: norm() bulunamadi.")
    raise SystemExit


mikrofon_kodu = r'''
def sesli_komut_al():
    """AMD Microphone Array ile Turkce sesli komut alir."""

    try:
        import sounddevice as sd
        import numpy as np
        import speech_recognition as sr

        MIKROFON_ID = 2
        SURE = 6

        cihaz = sd.query_devices(
            MIKROFON_ID
        )

        ornekleme = int(
            cihaz["default_samplerate"]
        )

        print("\nJarvis: Dinliyorum...")

        kayit = sd.rec(
            int(SURE * ornekleme),
            samplerate=ornekleme,
            channels=1,
            dtype="float32",
            device=MIKROFON_ID
        )

        sd.wait()

        # Çok sessiz kayit ise bos kabul et.
        seviye = float(
            np.max(
                np.abs(kayit)
            )
        )

        if seviye < 0.008:
            print(
                "Jarvis: Ses duyamadim."
            )
            return None

        pcm = (
            np.clip(
                kayit[:, 0],
                -1,
                1
            )
            * 32767
        ).astype(
            np.int16
        ).tobytes()

        ses = sr.AudioData(
            pcm,
            ornekleme,
            2
        )

        tanima = sr.Recognizer()

        try:
            komut = tanima.recognize_google(
                ses,
                language="tr-TR"
            )

        except sr.UnknownValueError:
            print(
                "Jarvis: Ne dedigini anlayamadim."
            )
            return None

        except sr.RequestError as e:
            print(
                "Jarvis: Ses tanima servisine ulasilamadi:",
                e
            )
            return None

        komut = str(
            komut
        ).strip()

        if not komut:
            return None

        print(
            "Sen:",
            komut
        )

        return komut

    except Exception as e:
        print(
            "Jarvis: Mikrofon hatasi:",
            e
        )

        return None


'''


yeni = metin.replace(
    hedef,
    mikrofon_kodu + "\n" + hedef,
    1
)


# ------------------------------------------------------------
# 2. Ana dongudeki yazili input'u sesli sisteme cevir
# ------------------------------------------------------------

eski = '''            komut = input(
                "\\nSen: "
            ).strip()
'''

yeni_input = '''            komut = sesli_komut_al()

            if not komut:
                secim = input(
                    "Yazmak icin komutu gir veya tekrar dinlemek icin Enter: "
                ).strip()

                if not secim:
                    continue

                komut = secim
'''

if eski not in yeni:
    print(
        "HATA: Ana dongudeki input bolumu bulunamadi."
    )
    raise SystemExit

yeni = yeni.replace(
    eski,
    yeni_input,
    1
)


# ------------------------------------------------------------
# 3. Baslangic bilgisini guncelle
# ------------------------------------------------------------

yeni = yeni.replace(
    '"Yazılı komut modu aktif. "\n        "Mikrofon kullanılmıyor."',
    '"Sesli komut modu aktif. "\n        "Yazili komut yedegi de kullanilabilir."',
    1
)


# ------------------------------------------------------------
# 4. Yazmadan once syntax testi ve yedek
# ------------------------------------------------------------

compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_mikrofon_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Jarvis mikrofon sistemi eklendi.")
print("MIKROFON: AMD Microphone Array - ID 2")
print("DIL: tr-TR")
print("SES KAYDI: 6 saniye")
print("YAZILI YEDEK: aktif")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")