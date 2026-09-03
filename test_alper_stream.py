# -*- coding: utf-8 -*-

import subprocess
import time

import sounddevice as sd


# ============================================================
# AYARLAR
# ============================================================

VOICE_ID = "HllA1j2zLOqUQ4kLjMmK"
MODEL_ID = "eleven_flash_v2_5"

# ElevenLabs'ten ham PCM aliyoruz:
# 24 kHz / 16 bit / mono
SAMPLE_RATE = 24000

METIN = (
    "Merhaba Fatih. Ben Jarvis. "
    "Gerçek zamanlı ses bağlantısı çalışıyor."
)


# ============================================================
# ELEVENLABS KOMUTU
# ============================================================

komut = [
    "cmd",
    "/c",
    "elevenlabs",
    "text-to-speech",
    "convert",

    "--voice-id",
    VOICE_ID,

    "--model-id",
    MODEL_ID,

    "--text",
    METIN,

    "--output-format",
    "pcm_24000",

    # Dosya olusturmadan sesi stdout'a aktar
    "--output",
    "-",

    # Dusuk gecikme
    "--optimize-streaming-latency",
    "3",

    # PVC yerine daha hizli IVC yolunu kullan
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


# ============================================================
# TEST
# ============================================================

print("Alper streaming testi basliyor...")

baslangic = time.perf_counter()

ilk_ses = None
toplam_byte = 0

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


try:

    if proc.stdout is None:
        raise RuntimeError(
            "ElevenLabs stdout acilamadi."
        )

    # int16 PCM'de her ses ornegi 2 byte.
    # ElevenLabs bazen tek sayida byte parcasi verebildigi icin
    # artan byte'i bir sonraki parcaya tasiyoruz.
    tampon = b""

    with sd.RawOutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=0
    ) as hoparlor:

        while True:

            parca = proc.stdout.read(4096)

            if not parca:
                break

            if ilk_ses is None:
                ilk_ses = (
                    time.perf_counter()
                    - baslangic
                )

                print(
                    f"ILK SES: {ilk_ses:.2f} saniye"
                )

            toplam_byte += len(parca)

            tampon += parca

            # int16 icin yalnizca cift sayida byte oynat.
            yazilabilir_byte = (
                len(tampon) // 2
            ) * 2

            if yazilabilir_byte > 0:

                hoparlor.write(
                    tampon[:yazilabilir_byte]
                )

                tampon = tampon[
                    yazilabilir_byte:
                ]

    # ElevenLabs isleminin bitmesini bekle.
    proc.wait(
        timeout=30
    )

    # --------------------------------------------------------
    # HATA KONTROLU
    # --------------------------------------------------------

    if proc.returncode != 0:

        hata = ""

        if proc.stderr is not None:
            hata = proc.stderr.read().decode(
                "utf-8",
                errors="replace"
            )

        print()
        print("ELEVENLABS HATASI:")
        print(
            hata.strip()
            or f"Return code: {proc.returncode}"
        )

    else:

        toplam_sure = (
            time.perf_counter()
            - baslangic
        )

        print()
        print(
            f"TOPLAM: {toplam_sure:.2f} saniye"
        )

        print(
            f"SES VERISI: {toplam_byte} byte"
        )

        if ilk_ses is not None:

            print(
                "SONUC: Streaming basarili."
            )

            print(
                f"Alper {ilk_ses:.2f} saniyede "
                "konusmaya basladi."
            )

        else:

            print(
                "SONUC: Ses verisi gelmedi."
            )


except subprocess.TimeoutExpired:

    print(
        "HATA: ElevenLabs islemi zaman asimina ugradi."
    )

    proc.kill()


except Exception as e:

    print(
        "HATA:",
        type(e).__name__,
        "-",
        e
    )


finally:

    if proc.poll() is None:
        proc.terminate()