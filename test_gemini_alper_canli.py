# -*- coding: utf-8 -*-

import json
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

import sounddevice as sd


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

VOICE_ID = "HllA1j2zLOqUQ4kLjMmK"

# Hiz icin ElevenLabs Flash
TTS_MODEL = "eleven_flash_v2_5"

# Ham PCM
SAMPLE_RATE = 24000


if not AGY.exists():
    print("HATA: agy.exe bulunamadi:")
    print(AGY)
    raise SystemExit


# ============================================================
# ELEVENLABS CANLI SES
# ============================================================

ses_kuyrugu = queue.Queue()


def alper_stream_konus(metin, tur_baslangici=None, ilk_parca=False):
    """
    Metni ElevenLabs OAuth + Alper ile
    dosya olusturmadan canli olarak oynatir.
    """

    metin = str(metin).strip()

    if not metin:
        return

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

    try:

        if proc.stdout is None:
            return

        tampon = b""
        ilk_ses_geldi = False

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

                if not ilk_ses_geldi:
                    ilk_ses_geldi = True

                    if (
                        ilk_parca
                        and tur_baslangici is not None
                    ):
                        gecikme = (
                            time.perf_counter()
                            - tur_baslangici
                        )

                        print(
                            f"\n[Jarvis ilk ses: "
                            f"{gecikme:.2f} saniye]"
                        )

                tampon += parca

                # int16 = 2 byte
                yazilabilir = (
                    len(tampon) // 2
                ) * 2

                if yazilabilir:

                    hoparlor.write(
                        tampon[:yazilabilir]
                    )

                    tampon = tampon[
                        yazilabilir:
                    ]

        proc.wait(
            timeout=30
        )

        if proc.returncode != 0:

            hata = ""

            if proc.stderr:
                hata = proc.stderr.read().decode(
                    "utf-8",
                    errors="replace"
                )

            print(
                "\nElevenLabs hatasi:",
                hata.strip()
            )

    except Exception as e:

        print(
            "\nSes hatasi:",
            e
        )

        if proc.poll() is None:
            proc.kill()


def ses_worker():
    """
    Gemini cevap verirken gelen cumleleri
    sirayla Alper'e okut.
    """

    while True:

        is_ = ses_kuyrugu.get()

        if is_ is None:
            ses_kuyrugu.task_done()
            break

        metin, baslangic, ilk = is_

        try:
            alper_stream_konus(
                metin,
                tur_baslangici=baslangic,
                ilk_parca=ilk
            )

        finally:
            ses_kuyrugu.task_done()


ses_thread = threading.Thread(
    target=ses_worker,
    daemon=True
)

ses_thread.start()


# ============================================================
# GEMINI / ANTIGRAVITY SUREKLI OTURUM
# ============================================================

print("Jarvis beyni baslatiliyor...")


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

    cwd=str(JARVIS_KLASORU),

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
    print("HATA: Gemini oturumu baslatilamadi.")
    raise SystemExit


# ============================================================
# YARDIMCILAR
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


def text_delta_bul(obj):
    """
    Antigravity olay yapisi degisse bile
    text_delta alanini ic ice arar.
    """

    if isinstance(obj, dict):

        deger = obj.get(
            "text_delta"
        )

        if isinstance(
            deger,
            str
        ):
            return deger

        for v in obj.values():

            sonuc = text_delta_bul(v)

            if sonuc:
                return sonuc

    elif isinstance(obj, list):

        for v in obj:

            sonuc = text_delta_bul(v)

            if sonuc:
                return sonuc

    return None


def hazir_cumleleri_ayir(tampon):
    """
    Tamamlanmis cumleleri Alper'e erken verebilmek
    icin parcala.

    Son tamamlanmamis kisim tampon olarak kalir.
    """

    cumleler = []

    while True:

        m = re.search(
            r"^(.+?[.!?])(?:\s+|$)",
            tampon,
            flags=re.S
        )

        if not m:
            break

        cumle = m.group(1).strip()

        if cumle:
            cumleler.append(
                cumle
            )

        tampon = tampon[
            m.end():
        ]

    return cumleler, tampon


# ============================================================
# GEMINI'DEN BIR TUR CEVAP AL
# ============================================================

def jarvis_sor(kullanici_metni):

    tur_baslangici = time.perf_counter()

    mesaj_gonder(
        kullanici_metni
    )

    ilk_gemini = None

    akisan_metin_var = False
    ses_tamponu = ""

    ilk_ses_parcasi = True

    final_cevap = ""

    print(
        "\nJarvis: ",
        end="",
        flush=True
    )

    while True:

        satir = gemini.stdout.readline()

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


        # ----------------------------------------------------
        # STREAMING METIN
        # ----------------------------------------------------

        parca = text_delta_bul(
            olay
        )

        if parca:

            if ilk_gemini is None:

                ilk_gemini = (
                    time.perf_counter()
                    - tur_baslangici
                )

                print(
                    f"\n[Gemini ilk metin: "
                    f"{ilk_gemini:.2f} saniye]\n"
                    "Jarvis: ",
                    end="",
                    flush=True
                )

            akisan_metin_var = True

            print(
                parca,
                end="",
                flush=True
            )

            final_cevap += parca
            ses_tamponu += parca

            cumleler, ses_tamponu = (
                hazir_cumleleri_ayir(
                    ses_tamponu
                )
            )

            for cumle in cumleler:

                ses_kuyrugu.put(
                    (
                        cumle,
                        tur_baslangici,
                        ilk_ses_parcasi
                    )
                )

                ilk_ses_parcasi = False


        # ----------------------------------------------------
        # TUR TAMAMLANDI
        # ----------------------------------------------------

        if olay.get("event") == "result":

            sonuc = olay.get(
                "result",
                {}
            )

            if sonuc.get(
                "status"
            ) != "SUCCESS":

                print(
                    "\nGemini hatasi:",
                    sonuc.get(
                        "error",
                        "Bilinmeyen hata"
                    )
                )

                return

            sonuc_metni = str(
                sonuc.get(
                    "response",
                    ""
                )
            ).strip()


            # Stream eventi gelmediyse final response'u kullan
            if not akisan_metin_var:

                final_cevap = sonuc_metni

                if ilk_gemini is None:

                    ilk_gemini = (
                        time.perf_counter()
                        - tur_baslangici
                    )

                    print(
                        f"\n[Gemini cevap: "
                        f"{ilk_gemini:.2f} saniye]\n"
                        "Jarvis: ",
                        end="",
                        flush=True
                    )

                print(
                    final_cevap,
                    end="",
                    flush=True
                )

                ses_kuyrugu.put(
                    (
                        final_cevap,
                        tur_baslangici,
                        True
                    )
                )

            else:

                # Stream sonundaki noktalamasiz kalan parca
                if ses_tamponu.strip():

                    ses_kuyrugu.put(
                        (
                            ses_tamponu.strip(),
                            tur_baslangici,
                            ilk_ses_parcasi
                        )
                    )

            print()

            # Bu testte Jarvis konusmasini bitirsin,
            # sonra yeni kullanici girdisi al.
            ses_kuyrugu.join()

            return


# ============================================================
# GEMINI'YI ONCEDEN ISIT / KIMLIK VER
# ============================================================

print("Gemini oturumu isitiliyor...")


baslangic_talimati = """
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullanicinin adi Fatih.

Bu oturumun temel amaci DOGAL VE GENIS SOHBETTIR.

Kurallar:
- Turkce konus.
- Insan gibi dogal bir sohbet akisi kullan.
- Onceki mesajlari baglamda hatirla.
- Takip sorularini onceki konusmaya bagla.
- Varsayilan olarak kisa ve akici cevap ver.
- Fatih ayrinti isterse ayrintili cevap verebilirsin.
- Gereksiz markdown, baslik veya uzun listeler kullanma.
- Konusmaya uygun, sesli okunabilecek cevaplar ver.
- Fatih sadece sohbet etmek istediginde onunla sohbet et.
- Her cumleyi bilgisayar komutu sanma.
- Bu TEST surumunde terminal, dosya, internet veya bilgisayar
  araclarini KULLANMA.
- Bu testte sadece sohbet et ve cevap ver.

Bu talimati anladigini sadece:
HAZIR
diye cevaplayarak onayla.
"""


mesaj_gonder(
    baslangic_talimati
)


# Hazirlik cevabini sessizce tüket
while True:

    satir = gemini.stdout.readline()

    if not satir:
        raise RuntimeError(
            "Gemini baslangicta kapandi."
        )

    try:
        olay = json.loads(
            satir
        )

    except json.JSONDecodeError:
        continue

    if olay.get("event") == "result":
        break


# ============================================================
# CANLI SOHBET
# ============================================================

print()
print("=" * 58)
print("JARVIS CANLI SOHBET HAZIR")
print("Gemini: surekli oturum")
print("Ses: ElevenLabs Alper streaming")
print("Cikis: jarvis kapat")
print("=" * 58)


try:

    while True:

        kullanici = input(
            "\nSen: "
        ).strip()

        if not kullanici:
            continue

        if kullanici.casefold() in {
            "jarvis kapat",
            "çık",
            "cik",
            "exit",
            "quit",
        }:
            print(
                "\nJarvis: Görüşürüz Fatih."
            )

            alper_stream_konus(
                "Görüşürüz Fatih."
            )

            break

        jarvis_sor(
            kullanici
        )


except KeyboardInterrupt:

    print(
        "\nJarvis kapatiliyor..."
    )


finally:

    # Ses kuyrugunu kapat
    ses_kuyrugu.put(
        None
    )

    ses_kuyrugu.join()

    # Gemini surecini kapat
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