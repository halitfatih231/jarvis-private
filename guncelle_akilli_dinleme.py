# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")
metin = jarvis.read_text(encoding="utf-8")

baslangic = metin.find("def sesli_komut_al():")
bitis = metin.find("def norm(metin):")

if baslangic == -1:
    print("HATA: sesli_komut_al() bulunamadi.")
    raise SystemExit

if bitis == -1 or bitis <= baslangic:
    print("HATA: norm() bulunamadi.")
    raise SystemExit


yeni_fonksiyon = r'''def sesli_komut_al():
    """
    Turkce sesli komut alir.

    Sabit sure kullanmaz:
    - ortam sesini olcer
    - konusmanin baslamasini bekler
    - konusma surdukce kaydeder
    - sustuktan sonra otomatik durur
    """

    try:
        import sounddevice as sd
        import numpy as np
        import speech_recognition as sr
        from collections import deque

        MIKROFON_ID = 2

        BLOK_SURESI = 0.10
        ORTAM_OLCUM_SURESI = 0.7
        KONUSMA_BEKLEME = 10.0
        SESSIZLIK_BITIS = 1.3
        MAKSIMUM_KONUSMA = 30.0
        ON_KAYIT_BLOK = 4

        cihaz = sd.query_devices(
            MIKROFON_ID
        )

        ornekleme = int(
            cihaz["default_samplerate"]
        )

        blok_boyutu = int(
            ornekleme * BLOK_SURESI
        )

        print(
            "\nJarvis: Dinliyorum..."
        )

        kayit_parcalari = []
        on_kayit = deque(
            maxlen=ON_KAYIT_BLOK
        )

        with sd.InputStream(
            samplerate=ornekleme,
            channels=1,
            dtype="float32",
            device=MIKROFON_ID,
            blocksize=blok_boyutu
        ) as stream:

            # ----------------------------------------
            # Ortam gurultusunu olc
            # ----------------------------------------

            ortam_degerleri = []

            ortam_blok_sayisi = max(
                1,
                int(
                    ORTAM_OLCUM_SURESI
                    / BLOK_SURESI
                )
            )

            for _ in range(
                ortam_blok_sayisi
            ):
                veri, _ = stream.read(
                    blok_boyutu
                )

                rms = float(
                    np.sqrt(
                        np.mean(
                            np.square(veri)
                        )
                    )
                )

                ortam_degerleri.append(
                    rms
                )

            ortam = (
                float(
                    np.median(
                        ortam_degerleri
                    )
                )
                if ortam_degerleri
                else 0.0
            )

            # Ortam sesine gore dinamik esik.
            baslama_esigi = max(
                0.006,
                ortam * 2.8
            )

            devam_esigi = max(
                0.004,
                ortam * 1.8
            )

            # ----------------------------------------
            # Konusmanin baslamasini bekle
            # ----------------------------------------

            basladi = False
            bekleme_baslangici = time.time()
            konusma_baslangici = None
            sessizlik_baslangici = None

            while True:

                veri, _ = stream.read(
                    blok_boyutu
                )

                veri = veri.copy()

                rms = float(
                    np.sqrt(
                        np.mean(
                            np.square(veri)
                        )
                    )
                )

                if not basladi:

                    on_kayit.append(
                        veri
                    )

                    if rms >= baslama_esigi:

                        basladi = True
                        konusma_baslangici = time.time()

                        kayit_parcalari.extend(
                            list(on_kayit)
                        )

                        on_kayit.clear()

                    elif (
                        time.time()
                        - bekleme_baslangici
                        >= KONUSMA_BEKLEME
                    ):
                        print(
                            "Jarvis: Ses duyamadim."
                        )

                        return None

                    continue

                # ----------------------------------------
                # Konusma basladi
                # ----------------------------------------

                kayit_parcalari.append(
                    veri
                )

                if rms < devam_esigi:

                    if sessizlik_baslangici is None:
                        sessizlik_baslangici = time.time()

                    elif (
                        time.time()
                        - sessizlik_baslangici
                        >= SESSIZLIK_BITIS
                    ):
                        break

                else:
                    sessizlik_baslangici = None

                if (
                    time.time()
                    - konusma_baslangici
                    >= MAKSIMUM_KONUSMA
                ):
                    break

        if not kayit_parcalari:
            print(
                "Jarvis: Ses kaydi alinamadi."
            )
            return None

        kayit = np.concatenate(
            kayit_parcalari,
            axis=0
        )

        # Cok dusuk seviyeli kaydi reddet.
        tepe = float(
            np.max(
                np.abs(kayit)
            )
        )

        if tepe < 0.008:
            print(
                "Jarvis: Ses cok dusuk."
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


yeni = (
    metin[:baslangic]
    + yeni_fonksiyon
    + metin[bitis:]
)

# Yazmadan once syntax kontrolu
compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_akilli_dinleme_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Akilli dinleme sistemi eklendi.")
print("SABIT 6 SANIYE: kaldirildi")
print("KONUSMAYI BEKLEME: aktif")
print("SUSUNCA OTOMATIK DURMA: aktif")
print("MAKSIMUM KONUSMA: 30 saniye")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")