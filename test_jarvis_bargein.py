# -*- coding: utf-8 -*-

import json
import os
import queue
import re
import subprocess
import threading
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

MIKROFON_ID = 2

VOICE_ID = "HllA1j2zLOqUQ4kLjMmK"
TTS_MODEL = "eleven_flash_v2_5"
TTS_SAMPLE_RATE = 24000


if not AGY.exists():
    print("HATA: Antigravity bulunamadi:")
    print(AGY)
    raise SystemExit


# ============================================================
# GLOBAL SES / BARGE-IN DURUMU
# ============================================================

ses_kuyrugu = queue.Queue()

ses_kes_event = threading.Event()
tts_basladi_event = threading.Event()
barge_bulundu_event = threading.Event()
tur_bitti_event = threading.Event()

barge_komut_kuyrugu = queue.Queue()


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

        sonuc = taniyici.recognize_google(
            ses,
            language="tr-TR"
        )

        sonuc = str(sonuc).strip()

        return sonuc or None

    except sr.UnknownValueError:
        return None

    except sr.RequestError as e:

        print(
            "Jarvis: Ses tanima servisi hatasi:",
            e
        )

        return None


# ============================================================
# NORMAL AKILLI DINLEME
# ============================================================

def sesli_komut_al():

    BLOK_SURESI = 0.10
    ORTAM_OLCUM = 0.50
    KONUSMA_BEKLEME = 60.0
    SESSIZLIK_BITIS = 1.15
    MAKSIMUM_KONUSMA = 45.0
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

            ortamlar = []

            for _ in range(
                max(
                    1,
                    int(
                        ORTAM_OLCUM
                        / BLOK_SURESI
                    )
                )
            ):

                veri, _ = stream.read(
                    blok_boyutu
                )

                ortamlar.append(
                    float(
                        np.sqrt(
                            np.mean(
                                np.square(veri)
                            )
                        )
                    )
                )

            ortam = float(
                np.median(ortamlar)
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

                    on_kayit.append(veri)

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

                parcalar.append(veri)

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

        print(
            "Jarvis: Anliyorum..."
        )

        komut = sesi_yaziya_cevir(
            kayit,
            ornekleme
        )

        if komut:

            print(
                "Sen:",
                komut
            )

        else:

            print(
                "Jarvis: Ne dedigini anlayamadim."
            )

        return komut

    except Exception as e:

        print(
            "Jarvis: Mikrofon hatasi:",
            e
        )

        return None


# ============================================================
# ELEVENLABS ALPER STREAMING
# ============================================================

def alper_stream_konus(
    metin,
    tur_baslangici=None,
    ilk_parca=False
):

    metin = str(metin).strip()

    if not metin:
        return

    if ses_kes_event.is_set():
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
        ilk_ses = True

        with sd.RawOutputStream(
            samplerate=TTS_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=0
        ) as hoparlor:

            while True:

                if ses_kes_event.is_set():

                    try:
                        proc.terminate()
                    except Exception:
                        pass

                    break

                parca = proc.stdout.read(
                    4096
                )

                if not parca:
                    break

                if ilk_ses:

                    ilk_ses = False

                    tts_basladi_event.set()

                    if (
                        ilk_parca
                        and tur_baslangici is not None
                    ):

                        gecikme = (
                            time.perf_counter()
                            - tur_baslangici
                        )

                        print(
                            f"\n[Ilk ses: "
                            f"{gecikme:.2f} sn]"
                        )

                tampon += parca

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

        try:
            proc.wait(
                timeout=5
            )
        except Exception:
            pass

    except Exception as e:

        if not ses_kes_event.is_set():

            print(
                "Jarvis ses hatasi:",
                e
            )

        try:
            proc.kill()
        except Exception:
            pass


# ============================================================
# SES WORKER
# ============================================================

def ses_worker():

    while True:

        is_ = ses_kuyrugu.get()

        if is_ is None:

            ses_kuyrugu.task_done()
            break

        metin, baslangic, ilk = is_

        try:

            if not ses_kes_event.is_set():

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
# BEKLEYEN SESLERI IPTAL ET
# ============================================================

def bekleyen_sesleri_temizle():

    while True:

        try:

            ses_kuyrugu.get_nowait()
            ses_kuyrugu.task_done()

        except queue.Empty:
            break


# ============================================================
# BARGE-IN DINLEYICI
# ============================================================

def barge_in_dinle():
    """
    Jarvis konusurken mikrofonu izler.

    Once Jarvis'in hoparlorden mikrofona sizan sesini olcer.
    Bunun belirgin uzerine cikan insan sesi algilanirsa:
      - Alper susturulur
      - kullanicinin cumlesi kaydedilir
      - Turkce STT yapilir
    """

    try:

        # Jarvis'in gercekten ses vermesini bekle.
        while (
            not tts_basladi_event.is_set()
            and not tur_bitti_event.is_set()
        ):

            time.sleep(0.03)

        if tur_bitti_event.is_set():
            return

        cihaz = sd.query_devices(
            MIKROFON_ID
        )

        ornekleme = int(
            cihaz["default_samplerate"]
        )

        BLOK_SURESI = 0.10

        blok_boyutu = int(
            ornekleme * BLOK_SURESI
        )

        # Jarvis'in kendi ses sizintisini olcmek icin.
        KALIBRASYON = 0.70

        # Araya giris sonrasinda susunca bitir.
        SESSIZLIK_BITIS = 1.0

        # Yanlis pozitifleri azaltmak icin
        # art arda en az 2 guclu blok.
        GEREKLI_GUCLU_BLOK = 2

        with sd.InputStream(
            samplerate=ornekleme,
            channels=1,
            dtype="float32",
            device=MIKROFON_ID,
            blocksize=blok_boyutu
        ) as stream:

            # --------------------------------------------
            # JARVIS SES SIZINTISI KALIBRASYONU
            # --------------------------------------------

            kalibrasyon = []

            bas = time.perf_counter()

            while (
                time.perf_counter() - bas
                < KALIBRASYON
            ):

                if tur_bitti_event.is_set():
                    return

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

                kalibrasyon.append(rms)

            if not kalibrasyon:
                return

            sizinti_medyan = float(
                np.median(
                    kalibrasyon
                )
            )

            sizinti_yuksek = float(
                np.percentile(
                    kalibrasyon,
                    90
                )
            )

            # Jarvis'in hoparlorden gelen sesinden
            # belirgin yuksek bir insan sesi ariyoruz.
            barge_esigi = max(
                0.018,
                sizinti_yuksek * 1.55,
                sizinti_medyan * 2.0
            )

            on_kayit = deque(
                maxlen=5
            )

            guclu_blok = 0

            # --------------------------------------------
            # ARA GIRISI BEKLE
            # --------------------------------------------

            while not tur_bitti_event.is_set():

                veri, _ = stream.read(
                    blok_boyutu
                )

                veri = veri.copy()

                on_kayit.append(veri)

                rms = float(
                    np.sqrt(
                        np.mean(
                            np.square(veri)
                        )
                    )
                )

                if rms >= barge_esigi:

                    guclu_blok += 1

                else:

                    guclu_blok = max(
                        0,
                        guclu_blok - 1
                    )

                if guclu_blok < GEREKLI_GUCLU_BLOK:
                    continue

                # ----------------------------------------
                # KULLANICI JARVIS'IN SOZUNU KESTI
                # ----------------------------------------

                ses_kes_event.set()
                barge_bulundu_event.set()

                bekleyen_sesleri_temizle()

                print()
                print(
                    "Jarvis: Seni dinliyorum..."
                )

                parcalar = list(
                    on_kayit
                )

                sessizlik_baslangici = None
                yakalama_baslangici = (
                    time.perf_counter()
                )

                # Jarvis sustuktan sonra kullanicinin
                # devam eden cumlesini almaya devam et.
                while True:

                    veri, _ = stream.read(
                        blok_boyutu
                    )

                    veri = veri.copy()

                    parcalar.append(veri)

                    rms = float(
                        np.sqrt(
                            np.mean(
                                np.square(veri)
                            )
                        )
                    )

                    # Jarvis artik sustugu icin
                    # normal insan sesi esigine don.
                    sessiz_esik = 0.006

                    if rms < sessiz_esik:

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
                        - yakalama_baslangici
                        >= 20.0
                    ):

                        break

                kayit = np.concatenate(
                    parcalar,
                    axis=0
                )

                print(
                    "Jarvis: Anliyorum..."
                )

                komut = sesi_yaziya_cevir(
                    kayit,
                    ornekleme
                )

                if komut:

                    print(
                        "Sen (araya girdin):",
                        komut
                    )

                    barge_komut_kuyrugu.put(
                        komut
                    )

                else:

                    print(
                        "Jarvis: Araya girdigini duydum "
                        "ama cumleni anlayamadim."
                    )

                return

    except Exception as e:

        if not tur_bitti_event.is_set():

            print(
                "Barge-in hatasi:",
                e
            )


# ============================================================
# GEMINI SUREKLI OTURUM
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

    print(
        "HATA: Gemini baslatilamadi."
    )

    raise SystemExit


# ============================================================
# GEMINI YARDIMCILARI
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

    if isinstance(obj, dict):

        deger = obj.get(
            "text_delta"
        )

        if isinstance(deger, str):
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


def hazir_parcalari_ayir(tampon):

    parcalar = []

    while True:

        m = re.search(
            r"^(.+?[.!?])(?:\s+|$)",
            tampon,
            flags=re.S
        )

        if not m:
            break

        aday = m.group(1).strip()
        kalan = tampon[m.end():]

        if len(aday) >= 30:

            parcalar.append(aday)
            tampon = kalan

        else:

            break

    return parcalar, tampon


# ============================================================
# BIR GEMINI SOHBET TURU
# ============================================================

def jarvis_sor(kullanici_metni):

    ses_kes_event.clear()
    tts_basladi_event.clear()
    barge_bulundu_event.clear()
    tur_bitti_event.clear()

    while not barge_komut_kuyrugu.empty():

        try:
            barge_komut_kuyrugu.get_nowait()
        except queue.Empty:
            break

    tur_baslangici = (
        time.perf_counter()
    )

    mesaj_gonder(
        kullanici_metni
    )

    ses_tamponu = ""
    final_cevap = ""

    akisan_metin_var = False
    ilk_ses_parcasi = True

    barge_thread = threading.Thread(
        target=barge_in_dinle,
        daemon=True
    )

    barge_thread.start()

    print()
    print(
        "Jarvis: ",
        end="",
        flush=True
    )

    while True:

        satir = gemini.stdout.readline()

        if not satir:

            tur_bitti_event.set()

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

        if (
            parca
            and not barge_bulundu_event.is_set()
        ):

            akisan_metin_var = True

            print(
                parca,
                end="",
                flush=True
            )

            final_cevap += parca
            ses_tamponu += parca

            hazirlar, ses_tamponu = (
                hazir_parcalari_ayir(
                    ses_tamponu
                )
            )

            for hazir in hazirlar:

                if barge_bulundu_event.is_set():
                    break

                ses_kuyrugu.put(
                    (
                        hazir,
                        tur_baslangici,
                        ilk_ses_parcasi
                    )
                )

                ilk_ses_parcasi = False

        if olay.get("event") == "result":

            sonuc = olay.get(
                "result",
                {}
            )

            if sonuc.get(
                "status"
            ) != "SUCCESS":

                print()
                print(
                    "Gemini hatasi:",
                    sonuc.get(
                        "error",
                        "Bilinmeyen hata"
                    )
                )

                tur_bitti_event.set()

                return None

            sonuc_metni = str(
                sonuc.get(
                    "response",
                    ""
                )
            ).strip()

            if not barge_bulundu_event.is_set():

                if not akisan_metin_var:

                    final_cevap = sonuc_metni

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

                elif ses_tamponu.strip():

                    ses_kuyrugu.put(
                        (
                            ses_tamponu.strip(),
                            tur_baslangici,
                            ilk_ses_parcasi
                        )
                    )

            print()

            break

    # --------------------------------------------------------
    # NORMAL TUR / BARGE-IN AYRIMI
    # --------------------------------------------------------

    if barge_bulundu_event.is_set():

        ses_kes_event.set()
        bekleyen_sesleri_temizle()

        # STT'nin araya girilen cumleyi tamamlamasini bekle.
        barge_thread.join(
            timeout=25
        )

        tur_bitti_event.set()

        try:

            return barge_komut_kuyrugu.get_nowait()

        except queue.Empty:

            return None

    # Normal konusma bittiyse sesin bitmesini bekle.
    ses_kuyrugu.join()

    tur_bitti_event.set()

    barge_thread.join(
        timeout=1
    )

    return None


# ============================================================
# GEMINI'YI ISIT
# ============================================================

print(
    "Gemini oturumu isitiliyor..."
)


sistem_talimati = """
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullanicinin adi Fatih.

Ana gorevin Fatih ile dogal, genis kapsamli ve devamli
bir Turkce sohbet surdurmektir.

Kurallar:

- Turkce konus.
- Dogal ve insani sohbet et.
- Onceki mesajlari bu oturum boyunca hatirla.
- Takip cumlelerini onceki baglama gore anla.
- Fatih her konuda seninle sohbet edebilir.
- Her cumleyi bilgisayar komutu sanma.
- Varsayilan olarak kisa ve akici cevap ver.
- Fatih ayrinti isterse ayrintili cevap ver.
- Sesli okunmaya uygun cumleler kur.
- Gereksiz markdown ve uzun listeler kullanma.
- Fatih sen konusurken araya girebilir.
- Araya girdiginde yeni soyledigi seyi oncelikli kabul et.
- Bu testte bilgisayarda arac veya dosya islemi yapma.
- Sadece sohbet et.

Sadece HAZIR diye cevapla.
"""


mesaj_gonder(
    sistem_talimati
)


while True:

    satir = gemini.stdout.readline()

    if not satir:

        raise RuntimeError(
            "Gemini isitma sirasinda kapandi."
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
# BARGE-IN CANLI SOHBET
# ============================================================

print()
print("=" * 60)
print("JARVIS BARGE-IN TEST HAZIR")
print("Jarvis konusurken dogrudan araya girebilirsin.")
print("Araya girerken tam cumleni soyle.")
print("Cikis: 'Jarvis kapat'")
print("=" * 60)


bekleyen_komut = None


try:

    while True:

        if bekleyen_komut:

            kullanici = bekleyen_komut
            bekleyen_komut = None

        else:

            kullanici = sesli_komut_al()

        if not kullanici:
            continue

        cikis = (
            kullanici
            .casefold()
            .replace("ı", "i")
        )

        if cikis in {
            "jarvis kapat",
            "jarvisi kapat",
            "jarvis cik",
            "cik",
            "exit",
            "quit",
        }:

            print(
                "Jarvis: Görüşürüz Fatih."
            )

            ses_kes_event.clear()

            alper_stream_konus(
                "Görüşürüz Fatih."
            )

            break

        araya_girilen_komut = jarvis_sor(
            kullanici
        )

        if araya_girilen_komut:

            bekleyen_komut = (
                araya_girilen_komut
            )


except KeyboardInterrupt:

    print()
    print(
        "Jarvis kapatiliyor..."
    )


finally:

    ses_kes_event.set()

    bekleyen_sesleri_temizle()

    ses_kuyrugu.put(None)
    ses_kuyrugu.join()

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