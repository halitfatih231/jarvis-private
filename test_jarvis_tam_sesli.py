# -*- coding: utf-8 -*-

import json
import os
import re
import subprocess
import time
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
import speech_recognition as sr


# ============================================================
# AYARLAR
# ============================================================

JARVIS_KLASORU = Path.home() / "Jarvis"

AGY = (
    Path(os.environ["LOCALAPPDATA"])
    / "agy"
    / "bin"
    / "agy.exe"
)

# AMD Microphone Array
MIKROFON_ID = 2

# ElevenLabs - Alper
VOICE_ID = "HllA1j2zLOqUQ4kLjMmK"

# Hizli ElevenLabs modeli
TTS_MODEL = "eleven_flash_v2_5"

# ElevenLabs PCM cikisi
TTS_SAMPLE_RATE = 24000

# Uzun cevaplar bu uzunluga yakin parcalara ayrilir
SES_PARCA_UZUNLUGU = 240


if not AGY.exists():

    print("HATA: Antigravity bulunamadi:")
    print(AGY)

    raise SystemExit


# ============================================================
# SESI YAZIYA CEVIR
# ============================================================

def sesi_yaziya_cevir(kayit, ornekleme):

    if kayit is None or len(kayit) == 0:
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

    taniyici = sr.Recognizer()

    try:

        metin = taniyici.recognize_google(
            ses,
            language="tr-TR"
        )

        metin = str(metin).strip()

        if not metin:
            return None

        return metin

    except sr.UnknownValueError:

        print(
            "Jarvis: Ne dedigini anlayamadim."
        )

        return None

    except sr.RequestError as e:

        print(
            "Jarvis: Ses tanima servisi hatasi:",
            e
        )

        return None


# ============================================================
# AKILLI MIKROFON
# ============================================================

def sesli_komut_al():

    BLOK_SURESI = 0.10

    ORTAM_OLCUM_SURESI = 0.45

    KONUSMA_BEKLEME = 60.0

    # Cumle sonundaki sessizlik
    SESSIZLIK_BITIS = 1.20

    MAKSIMUM_KONUSMA = 45.0

    # Ilk heceyi kacirmamak icin
    ON_KAYIT_BLOK = 4

    try:

        cihaz = sd.query_devices(
            MIKROFON_ID
        )

        ornekleme = int(
            cihaz["default_samplerate"]
        )

        blok_boyutu = int(
            ornekleme * BLOK_SURESI
        )

        print()
        print("Jarvis: Dinliyorum...")

        parcalar = []

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

            # ------------------------------------------------
            # ORTAM SESINI OLC
            # ------------------------------------------------

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

            ortam = float(
                np.median(
                    ortam_degerleri
                )
            )

            baslama_esigi = max(
                0.006,
                ortam * 2.7
            )

            devam_esigi = max(
                0.004,
                ortam * 1.7
            )

            basladi = False

            bekleme_baslangici = (
                time.perf_counter()
            )

            konusma_baslangici = None
            sessizlik_baslangici = None

            # ------------------------------------------------
            # KONUSMAYI BEKLE
            # ------------------------------------------------

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

                        konusma_baslangici = (
                            time.perf_counter()
                        )

                        parcalar.extend(
                            list(on_kayit)
                        )

                        on_kayit.clear()

                    elif (
                        time.perf_counter()
                        - bekleme_baslangici
                        >= KONUSMA_BEKLEME
                    ):

                        return None

                    continue

                # ------------------------------------------------
                # KONUSMA BASLADI
                # ------------------------------------------------

                parcalar.append(
                    veri
                )

                if rms < devam_esigi:

                    if sessizlik_baslangici is None:

                        sessizlik_baslangici = (
                            time.perf_counter()
                        )

                    elif (
                        time.perf_counter()
                        - sessizlik_baslangici
                        >= SESSIZLIK_BITIS
                    ):

                        break

                else:

                    sessizlik_baslangici = None

                if (
                    time.perf_counter()
                    - konusma_baslangici
                    >= MAKSIMUM_KONUSMA
                ):

                    break

        if not parcalar:
            return None

        kayit = np.concatenate(
            parcalar,
            axis=0
        )

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

        print(
            "Jarvis: Anliyorum..."
        )

        metin = sesi_yaziya_cevir(
            kayit,
            ornekleme
        )

        if metin:

            print(
                "Sen:",
                metin
            )

        return metin

    except Exception as e:

        print(
            "Jarvis: Mikrofon hatasi:",
            e
        )

        return None


# ============================================================
# UZUN METNI SES PARCALARINA BOL
# ============================================================

def metni_ses_parcalarina_bol(
    metin,
    maksimum=SES_PARCA_UZUNLUGU
):

    metin = str(
        metin
    ).strip()

    if not metin:
        return []

    # Fazla satir bosluklarini duzelt
    metin = re.sub(
        r"\s+",
        " ",
        metin
    ).strip()

    # Once cumlelere ayir
    cumleler = re.split(
        r"(?<=[.!?])\s+",
        metin
    )

    parcalar = []

    mevcut = ""

    for cumle in cumleler:

        cumle = cumle.strip()

        if not cumle:
            continue

        # ----------------------------------------------------
        # TEK CUMLE ZATEN COK UZUNSA
        # ----------------------------------------------------

        if len(cumle) > maksimum:

            if mevcut:

                parcalar.append(
                    mevcut
                )

                mevcut = ""

            kelimeler = (
                cumle.split()
            )

            gecici = ""

            for kelime in kelimeler:

                aday = (
                    gecici
                    + " "
                    + kelime
                ).strip()

                if len(aday) <= maksimum:

                    gecici = aday

                else:

                    if gecici:

                        parcalar.append(
                            gecici
                        )

                    gecici = kelime

            if gecici:

                parcalar.append(
                    gecici
                )

            continue

        # ----------------------------------------------------
        # NORMAL CUMLELERI BIRLESTIR
        # ----------------------------------------------------

        aday = (
            mevcut
            + " "
            + cumle
        ).strip()

        if len(aday) <= maksimum:

            mevcut = aday

        else:

            if mevcut:

                parcalar.append(
                    mevcut
                )

            mevcut = cumle

    if mevcut:

        parcalar.append(
            mevcut
        )

    return parcalar


# ============================================================
# ELEVENLABS - ALPER STREAMING
# ============================================================

def alper_stream_konus(
    metin,
    tur_baslangici=None
):

    metin = str(
        metin
    ).strip()

    if not metin:
        return False

    komut = [
        "cmd",
        "/c",
        "elevenlabs",
        "text-to-speech",
        "convert",

        "--voice-id",
        VOICE_ID,

        "--model-id",
        TTS_MODEL,

        "--text",
        metin,

        "--output-format",
        "pcm_24000",

        "--output",
        "-",

        "--optimize-streaming-latency",
        "3",

        "--use-pvc-as-ivc",
        "true",

        "--voice-settings.speed",
        "0.95",

        "--voice-settings.stability",
        "0.80",

        "--voice-settings.similarity-boost",
        "0.60",

        "--voice-settings.style",
        "0",

        "--voice-settings.use-speaker-boost",
        "false",

        "--quiet",
    ]

    proc = subprocess.Popen(
        komut,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        )
    )

    ilk_ses_geldi = False

    try:

        if proc.stdout is None:

            print(
                "Jarvis: ElevenLabs ses akisi acilamadi."
            )

            return False

        tampon = b""

        with sd.RawOutputStream(
            samplerate=TTS_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=0
        ) as hoparlor:

            while True:

                parca = proc.stdout.read(
                    4096
                )

                if not parca:
                    break

                if not ilk_ses_geldi:

                    ilk_ses_geldi = True

                    if tur_baslangici is not None:

                        gecikme = (
                            time.perf_counter()
                            - tur_baslangici
                        )

                        print(
                            f"\n[Ilk ses: "
                            f"{gecikme:.2f} sn]"
                        )

                tampon += parca

                # PCM int16 = 2 byte
                yazilabilir = (
                    len(tampon) // 2
                ) * 2

                if yazilabilir > 0:

                    hoparlor.write(
                        tampon[
                            :yazilabilir
                        ]
                    )

                    tampon = tampon[
                        yazilabilir:
                    ]

        try:

            proc.wait(
                timeout=30
            )

        except subprocess.TimeoutExpired:

            proc.kill()

            print(
                "Jarvis: ElevenLabs zaman asimina ugradi."
            )

            return False

        if proc.returncode != 0:

            hata = ""

            if proc.stderr is not None:

                hata = (
                    proc.stderr
                    .read()
                    .decode(
                        "utf-8",
                        errors="replace"
                    )
                )

            print()
            print(
                "Jarvis: ElevenLabs hatasi:"
            )

            print(
                hata.strip()
                or f"Kod: {proc.returncode}"
            )

            return False

        if not ilk_ses_geldi:

            print(
                "Jarvis: ElevenLabs ses uretmedi."
            )

            return False

        return True

    except Exception as e:

        print(
            "Jarvis: Ses hatasi:",
            e
        )

        try:

            if proc.poll() is None:
                proc.kill()

        except Exception:
            pass

        return False


# ============================================================
# UZUN CEVABI TAMAMEN SESLENDIR
# ============================================================

def cevabi_seslendir(
    cevap,
    tur_baslangici
):

    ses_parcalari = (
        metni_ses_parcalarina_bol(
            cevap
        )
    )

    if not ses_parcalari:

        print(
            "Jarvis: Seslendirilecek metin yok."
        )

        return False

    print(
        f"[Ses parcasi: "
        f"{len(ses_parcalari)}]"
    )

    for sira, parca in enumerate(
        ses_parcalari,
        start=1
    ):

        print(
            f"[Okunuyor: "
            f"{sira}/"
            f"{len(ses_parcalari)}]"
        )

        if sira == 1:

            baslangic = (
                tur_baslangici
            )

        else:

            baslangic = None

        basarili = alper_stream_konus(
            parca,
            tur_baslangici=baslangic
        )

        if not basarili:

            print(
                f"Jarvis: "
                f"{sira}. ses parcasi okunamadi."
            )

            return False

    return True


# ============================================================
# GEMINI / ANTIGRAVITY SUREKLI OTURUM
# ============================================================

print(
    "Jarvis beyni baslatiliyor..."
)


gemini = subprocess.Popen(
    [
        str(AGY),

        "--input-format",
        "stream-json",

        "--output-format",
        "stream-json",

        "--effort",
        "low",
    ],

    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,

    text=True,
    encoding="utf-8",
    errors="replace",

    bufsize=1,

    cwd=str(
        JARVIS_KLASORU
    ),

    creationflags=getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0
    )
)


if (
    gemini.stdin is None
    or gemini.stdout is None
):

    print(
        "HATA: Gemini baslatilamadi."
    )

    raise SystemExit


# ============================================================
# GEMINI'YE MESAJ GONDER
# ============================================================

def mesaj_gonder(metin):

    olay = {
        "event": "user",
        "message": {
            "content": metin
        }
    }

    gemini.stdin.write(
        json.dumps(
            olay,
            ensure_ascii=False
        )
        + "\n"
    )

    gemini.stdin.flush()


# ============================================================
# STREAM DELTA BUL
# ============================================================

def text_delta_bul(obj):

    if isinstance(
        obj,
        dict
    ):

        deger = obj.get(
            "text_delta"
        )

        if isinstance(
            deger,
            str
        ):

            return deger

        for v in obj.values():

            sonuc = text_delta_bul(
                v
            )

            if sonuc:
                return sonuc

    elif isinstance(
        obj,
        list
    ):

        for v in obj:

            sonuc = text_delta_bul(
                v
            )

            if sonuc:
                return sonuc

    return None


# ============================================================
# GEMINI CEVABINI TAM OLARAK AL
# ============================================================

def gemini_cevap_al():

    delta_toplam = ""

    while True:

        satir = (
            gemini.stdout.readline()
        )

        if not satir:

            raise RuntimeError(
                "Gemini oturumu kapandi."
            )

        try:

            olay = json.loads(
                satir
            )

        except json.JSONDecodeError:

            continue

        parca = text_delta_bul(
            olay
        )

        if parca:

            delta_toplam += parca

        if olay.get(
            "event"
        ) == "result":

            sonuc = olay.get(
                "result",
                {}
            )

            if sonuc.get(
                "status"
            ) != "SUCCESS":

                hata = sonuc.get(
                    "error",
                    "Bilinmeyen Gemini hatasi"
                )

                print(
                    "Jarvis: Gemini hatasi:",
                    hata
                )

                return None

            cevap = str(
                sonuc.get(
                    "response",
                    ""
                )
            ).strip()

            if not cevap:

                cevap = (
                    delta_toplam
                    .strip()
                )

            return cevap or None


# ============================================================
# BIR SOHBET TURU
# ============================================================

def jarvis_sor(
    kullanici_metni
):

    tur_baslangici = (
        time.perf_counter()
    )

    mesaj_gonder(
        kullanici_metni
    )

    cevap = gemini_cevap_al()

    if not cevap:
        return

    gemini_suresi = (
        time.perf_counter()
        - tur_baslangici
    )

    print()
    print(
        "Jarvis:",
        cevap
    )

    print(
        f"\n[Gemini cevap: "
        f"{gemini_suresi:.2f} sn]"
    )

    # --------------------------------------------------------
    # CEVABI PARCALARA BOL VE TAMAMINI OKU
    # --------------------------------------------------------

    basarili = cevabi_seslendir(
        cevap,
        tur_baslangici
    )

    if not basarili:

        print(
            "Jarvis: Cevap ekranda olustu "
            "ancak seslendirme tamamlanamadi."
        )

    # Son sesin mikrofona sizmamasi icin
    # cok kisa bekleme
    time.sleep(
        0.20
    )


# ============================================================
# GEMINI'YI ISIT / JARVIS KIMLIGI
# ============================================================

print(
    "Gemini oturumu isitiliyor..."
)


sistem_talimati = """
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullanicinin adi Fatih.

Fatih seni sadece bir sohbet botu olarak degil,
zamanla bilgisayarinda pek cok isi yapabilecek gercek bir
kisisel asistan olarak gelistiriyor.

SU ANKI TESTIN AMACI DOGAL SESLI SOHBETTIR.

Kurallar:

- Turkce konus.
- Dogal ve insani konus.
- Fatih'in onceki mesajlarini bu oturum boyunca baglamda tut.
- "Peki?", "neden?", "onu demiyorum", "az onceki konu",
  "devam et" gibi ifadeleri onceki sohbete bagla.
- Fatih'in cumlesi konusma dilindeyse anlamini baglamdan
  cikarmaya calis.
- Her soyledigini bilgisayar komutu sanma.
- Fatih soru sormadiginda da normal sohbet surdurebilirsin.
- Varsayilan cevaplarini kisa ve dogal tut.
- Fatih ayrinti isterse ayrintili anlat.
- Sesli okunmaya uygun cumleler kur.
- Gereksiz baslik, tablo ve markdown kullanma.
- Surekli soru sorma.
- Her cevabin sonunda soru sormak zorunda degilsin.
- Fatih dusuncesini anlatirken hemen buyuk varsayimlara atlama.
- Onceki baglama sadik kal.
- "Seni dinliyorum" gibi kaliplari gereksiz tekrar etme.
- Bu testte terminal, dosya, uygulama veya internet araci
  KULLANMA.
- Bu testte sadece sohbet et.

Bu talimati anladigini sadece HAZIR diyerek onayla.
"""


mesaj_gonder(
    sistem_talimati
)


# Isitma cevabini sessizce al
isitma = gemini_cevap_al()

if not isitma:

    print(
        "HATA: Gemini isitilamadi."
    )

    raise SystemExit


# ============================================================
# ANA SESLI DONGU
# ============================================================

print()
print("=" * 62)
print("JARVIS TAM SESLI V3 HAZIR")
print("Mikrofon: AMD Microphone Array")
print("Beyin: Gemini / Antigravity surekli oturum")
print("Ses: ElevenLabs Alper")
print("Uzun cevaplar: otomatik parcali streaming")
print("Cikis: 'Jarvis kapat'")
print("=" * 62)


try:

    while True:

        kullanici = (
            sesli_komut_al()
        )

        if not kullanici:
            continue

        cikis = (
            kullanici
            .casefold()
            .replace(
                "ı",
                "i"
            )
        )

        if cikis in {
            "jarvis kapat",
            "jarvisi kapat",
            "jarvis cik",
            "cik",
            "exit",
            "quit",
        }:

            print()
            print(
                "Jarvis: Görüşürüz Fatih."
            )

            alper_stream_konus(
                "Görüşürüz Fatih."
            )

            break

        jarvis_sor(
            kullanici
        )


except KeyboardInterrupt:

    print()
    print(
        "Jarvis kapatiliyor..."
    )


finally:

    try:

        if gemini.stdin:
            gemini.stdin.close()

    except Exception:
        pass

    if gemini.poll() is None:

        try:

            gemini.terminate()

        except Exception:
            pass