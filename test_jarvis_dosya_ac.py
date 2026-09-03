# -*- coding: utf-8 -*-

import difflib
import json
import os
import re
import subprocess
import threading
import time
import unicodedata
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
import speech_recognition as sr


# ============================================================
# AYARLAR
# ============================================================

HOME = Path.home()
JARVIS_KLASORU = HOME / "Jarvis"

AGY = (
    Path(os.environ["LOCALAPPDATA"])
    / "agy"
    / "bin"
    / "agy.exe"
)

# Daha once dogruladigimiz mikrofon
MIKROFON_ID = 2

# ElevenLabs - Alper
VOICE_ID = "HllA1j2zLOqUQ4kLjMmK"
TTS_MODEL = "eleven_flash_v2_5"
TTS_SAMPLE_RATE = 24000

# Uzun cevaplari seslendirme parcasi
SES_PARCA_UZUNLUGU = 240


if not AGY.exists():
    print("HATA: Antigravity bulunamadi:")
    print(AGY)
    raise SystemExit


# ============================================================
# METIN NORMALIZASYONU
# ============================================================

def norm(metin):

    metin = str(metin).casefold()

    donusum = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    })

    metin = metin.translate(donusum)

    metin = unicodedata.normalize(
        "NFKD",
        metin
    )

    metin = "".join(
        karakter
        for karakter in metin
        if not unicodedata.combining(karakter)
    )

    metin = re.sub(
        r"[^a-z0-9\s._-]",
        " ",
        metin
    )

    metin = re.sub(
        r"\s+",
        " ",
        metin
    )

    return metin.strip()


# ============================================================
# DOSYA / KLASOR INDEKSI
# ============================================================

DOSYA_INDEKSI = []
DOSYA_INDEKSI_KILIT = threading.Lock()
DOSYA_INDEKSI_HAZIR = threading.Event()


def arama_kokleri():

    adaylar = [
        HOME / "Desktop",
        HOME / "Documents",
        HOME / "Downloads",
        HOME / "Pictures",
        HOME / "Videos",
        HOME / "Music",
        HOME / "OneDrive",
        JARVIS_KLASORU,
    ]

    kokler = []
    gorulen = set()

    for yol in adaylar:

        try:
            yol = yol.resolve()
        except Exception:
            pass

        anahtar = str(yol).casefold()

        if (
            yol.exists()
            and anahtar not in gorulen
        ):
            gorulen.add(anahtar)
            kokler.append(yol)

    return kokler


ATLANACAK_KLASORLER = {
    "appdata",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".cache",
}


def dosya_indeksi_olustur():

    yeni_indeks = []

    try:

        for kok in arama_kokleri():

            for mevcut, klasorler, dosyalar in os.walk(
                kok,
                topdown=True
            ):

                mevcut_path = Path(mevcut)

                # Asiri derine gitmeyelim
                try:
                    derinlik = len(
                        mevcut_path.relative_to(kok).parts
                    )
                except Exception:
                    derinlik = 0

                if derinlik >= 7:
                    klasorler[:] = []
                    continue

                klasorler[:] = [
                    k
                    for k in klasorler
                    if (
                        k.casefold()
                        not in ATLANACAK_KLASORLER
                        and not k.startswith(".")
                    )
                ]

                # Klasorleri de acabilmek icin indekse ekle
                for klasor in klasorler:

                    yol = mevcut_path / klasor

                    yeni_indeks.append(
                        (
                            yol,
                            True,
                            norm(klasor),
                            norm(str(yol))
                        )
                    )

                for dosya in dosyalar:

                    if dosya.startswith("~$"):
                        continue

                    yol = mevcut_path / dosya

                    yeni_indeks.append(
                        (
                            yol,
                            False,
                            norm(Path(dosya).stem),
                            norm(dosya)
                        )
                    )

        with DOSYA_INDEKSI_KILIT:
            DOSYA_INDEKSI.clear()
            DOSYA_INDEKSI.extend(
                yeni_indeks
            )

    finally:

        DOSYA_INDEKSI_HAZIR.set()


def dosya_indeksini_baslat():

    thread = threading.Thread(
        target=dosya_indeksi_olustur,
        daemon=True
    )

    thread.start()


# ============================================================
# DOSYA BENZERLIK PUANI
# ============================================================

def yol_puani(
    sorgu,
    kayit
):

    yol, klasor_mu, kok_ad, tam_ad = kayit

    q = norm(sorgu)

    if not q:
        return 0.0

    # Tam yol verilmis olabilir
    if q == norm(str(yol)):
        return 10.0

    puan = 0.0

    if q == kok_ad:
        puan += 5.0

    if q == tam_ad:
        puan += 4.5

    if q in kok_ad:
        puan += 2.3

    if q in tam_ad:
        puan += 2.0

    if kok_ad in q and len(kok_ad) > 3:
        puan += 1.2

    q_kelimeler = {
        k
        for k in q.split()
        if len(k) > 1
    }

    ad_kelimeler = {
        k
        for k in kok_ad.split()
        if len(k) > 1
    }

    if q_kelimeler:

        ortak = len(
            q_kelimeler
            & ad_kelimeler
        )

        oran = (
            ortak
            / len(q_kelimeler)
        )

        puan += oran * 2.4

        if ortak == len(q_kelimeler):
            puan += 1.1

    benzerlik = difflib.SequenceMatcher(
        None,
        q,
        kok_ad
    ).ratio()

    puan += benzerlik * 2.0

    # Dosyayi klasore gore biraz tercih et
    if not klasor_mu:
        puan += 0.10

    return puan


# ============================================================
# DOSYA / KLASOR BUL
# ============================================================

def yerel_yol_bul(sorgu):

    sorgu = str(sorgu).strip()

    if not sorgu:
        return None, 0.0

    # Gemini tam yol verdiyse direkt kullan
    try:

        direkt = Path(
            os.path.expandvars(
                os.path.expanduser(
                    sorgu.strip('"')
                )
            )
        )

        if direkt.exists():
            return direkt, 100.0

    except Exception:
        pass

    # Arka plandaki indeks icin kisa sure bekle
    DOSYA_INDEKSI_HAZIR.wait(
        timeout=3.0
    )

    with DOSYA_INDEKSI_KILIT:

        indeks = list(
            DOSYA_INDEKSI
        )

    if not indeks:

        return None, 0.0

    puanlilar = []

    for kayit in indeks:

        puan = yol_puani(
            sorgu,
            kayit
        )

        if puan > 0:
            puanlilar.append(
                (
                    puan,
                    kayit[0]
                )
            )

    if not puanlilar:
        return None, 0.0

    puanlilar.sort(
        key=lambda x: x[0],
        reverse=True
    )

    en_iyi_puan, en_iyi_yol = (
        puanlilar[0]
    )

    # Cok zayif eslesmeyi acma
    if en_iyi_puan < 2.1:
        return None, en_iyi_puan

    print()
    print(
        "[Dosya eslesmesi]",
        en_iyi_yol
    )

    print(
        f"[Eslesme puani: "
        f"{en_iyi_puan:.2f}]"
    )

    return (
        en_iyi_yol,
        en_iyi_puan
    )


# ============================================================
# DOSYA / KLASOR AC
# ============================================================

def yerel_yol_ac(sorgu):

    yol, puan = yerel_yol_bul(
        sorgu
    )

    if yol is None:

        return (
            False,
            None,
            "Bu isimle eşleşen bir dosya veya klasör bulamadım."
        )

    try:

        os.startfile(
            str(yol)
        )

        return (
            True,
            yol,
            f"Açtım Fatih. {yol.name}"
        )

    except Exception as e:

        return (
            False,
            yol,
            f"Dosyayı buldum ama açamadım: {e}"
        )


# ============================================================
# MIKROFON SESINI YAZIYA CEVIR
# ============================================================

def sesi_yaziya_cevir(
    kayit,
    ornekleme
):

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

        metin = str(
            metin
        ).strip()

        return metin or None

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
# AKILLI DINLEME
# ============================================================

def sesli_komut_al():

    BLOK_SURESI = 0.10
    ORTAM_OLCUM_SURESI = 0.45
    KONUSMA_BEKLEME = 60.0
    SESSIZLIK_BITIS = 1.20
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
            ornekleme
            * BLOK_SURESI
        )

        print()
        print(
            "Jarvis: Dinliyorum..."
        )

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

                parcalar.append(
                    veri
                )

                if rms < devam_esigi:

                    if (
                        sessizlik_baslangici
                        is None
                    ):

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
# UZUN METNI SES PARCALARINA AYIR
# ============================================================

def metni_ses_parcalarina_bol(
    metin,
    maksimum=SES_PARCA_UZUNLUGU
):

    metin = re.sub(
        r"\s+",
        " ",
        str(metin)
    ).strip()

    if not metin:
        return []

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

        if len(cumle) > maksimum:

            if mevcut:
                parcalar.append(
                    mevcut
                )
                mevcut = ""

            kelimeler = cumle.split()
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
# ELEVENLABS ALPER
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

                    if (
                        tur_baslangici
                        is not None
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
                    len(tampon)
                    // 2
                ) * 2

                if yazilabilir:

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
            return False

        return (
            proc.returncode == 0
            and ilk_ses_geldi
        )

    except Exception as e:

        print(
            "Jarvis: Ses hatasi:",
            e
        )

        try:
            proc.kill()
        except Exception:
            pass

        return False


# ============================================================
# CEVABI SESLENDIR
# ============================================================

def cevabi_seslendir(
    cevap,
    tur_baslangici=None
):

    parcalar = (
        metni_ses_parcalarina_bol(
            cevap
        )
    )

    if not parcalar:
        return False

    for sira, parca in enumerate(
        parcalar,
        start=1
    ):

        baslangic = (
            tur_baslangici
            if sira == 1
            else None
        )

        basarili = alper_stream_konus(
            parca,
            baslangic
        )

        if not basarili:

            print(
                f"Jarvis: Ses parcasi "
                f"{sira} okunamadi."
            )

            return False

    return True


# ============================================================
# GEMINI / ANTIGRAVITY
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
# GEMINI MESAJ
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
# STREAM DELTA
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
# GEMINI CEVABI
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

                print(
                    "Jarvis: Gemini hatasi:",
                    sonuc.get(
                        "error",
                        "Bilinmeyen hata"
                    )
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
                    delta_toplam.strip()
                )

            return cevap or None


# ============================================================
# GEMINI ARAÇ KOMUTUNU AYIKLA
# ============================================================

def arac_komutu_ayikla(
    cevap
):

    if not cevap:
        return None

    eslesme = re.search(
        r"\[\[TOOL\]\]\s*(\{.*?\})\s*\[\[/TOOL\]\]",
        cevap,
        flags=re.DOTALL
    )

    if not eslesme:
        return None

    try:

        veri = json.loads(
            eslesme.group(1)
        )

    except Exception:
        return None

    if not isinstance(
        veri,
        dict
    ):
        return None

    return veri


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

    # ========================================================
    # GEMINI YEREL ARAÇ İSTEDİ Mİ?
    # ========================================================

    arac = arac_komutu_ayikla(
        cevap
    )

    if arac:

        action = str(
            arac.get(
                "action",
                ""
            )
        ).strip()

        sorgu = str(
            arac.get(
                "query",
                ""
            )
        ).strip()

        if action == "open_local":

            print()
            print(
                f"[Jarvis araci: "
                f"dosya/klasor ac]"
            )

            print(
                f"[Aranan: {sorgu}]"
            )

            basarili, yol, mesaj = (
                yerel_yol_ac(
                    sorgu
                )
            )

            print()
            print(
                "Jarvis:",
                mesaj
            )

            alper_stream_konus(
                mesaj,
                tur_baslangici
            )

            time.sleep(
                0.20
            )

            return

        # Bilinmeyen araç varsa çalıştırma
        mesaj = (
            "Bu işlemi henüz yapacak "
            "bir aracım yok Fatih."
        )

        print()
        print(
            "Jarvis:",
            mesaj
        )

        alper_stream_konus(
            mesaj,
            tur_baslangici
        )

        return

    # ========================================================
    # NORMAL SOHBET
    # ========================================================

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

    cevabi_seslendir(
        cevap,
        tur_baslangici
    )

    time.sleep(
        0.20
    )


# ============================================================
# DOSYA INDEKSINI ARKA PLANDA BASLAT
# ============================================================

print(
    "Dosya indeksi hazirlaniyor..."
)

dosya_indeksini_baslat()


# ============================================================
# GEMINI'YI ISIT
# ============================================================

print(
    "Gemini oturumu isitiliyor..."
)


sistem_talimati = r"""
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullanicinin adi Fatih.

Fatih seninle dogal Turkce konusur.

Iki temel davranisin var:

1. NORMAL SOHBET
2. FATIH'IN BILGISAYARINDA YEREL DOSYA VEYA KLASOR ACMA

NORMAL SOHBET KURALLARI:

- Turkce konus.
- Dogal ve insani konus.
- Onceki mesajlari baglamda tut.
- Takip sorularini onceki mesaja bagla.
- Varsayilan olarak kisa ve akici cevap ver.
- Fatih ayrinti isterse ayrintili cevap verebilirsin.
- Gereksiz markdown kullanma.
- Her cevabin sonunda soru sorma zorunlulugun yok.
- Fatih'in her cumlesini bilgisayar komutu sanma.

YEREL DOSYA/KLASOR ACMA KURALLARI:

Fatih gercekten bilgisayarindaki bir dosyayi veya klasoru
acmani istiyorsa SADECE su formati dondur:

[[TOOL]]{"action":"open_local","query":"DOSYA VEYA KLASOR ADI"}[[/TOOL]]

Bu durumda bu satirin disinda HICBIR SEY yazma.

query alanina sadece dosyayi bulmaya yarayacak temiz adi yaz.

Ornek:

Fatih:
"Kisisel bilgi kayit formunu acar misin?"

Cevap:
[[TOOL]]{"action":"open_local","query":"kişisel bilgi kayıt formu"}[[/TOOL]]

Fatih:
"Masaustundeki tez dosyami ac."

Cevap:
[[TOOL]]{"action":"open_local","query":"tez"}[[/TOOL]]

Fatih:
"Jarvis klasorunu ac."

Cevap:
[[TOOL]]{"action":"open_local","query":"Jarvis"}[[/TOOL]]

ANCAK:

Fatih:
"Izafiyet teorisini acikla."

Bu bir dosya acma istegi DEGILDIR.
Normal olarak izafiyet teorisini anlat.

Fatih:
"Bu konuyu biraz daha ac."

Bu da dosya acma istegi DEGILDIR.
Onceki konuyu daha ayrintili acikla.

Fatih:
"Bana aciklar misin?"

Bu da dosya komutu DEGILDIR.

Dosya veya klasor adi yeterince belli degilse
TOOL kullanma; Fatih'e hangi dosyayi kastettigini sor.

Bu testte su an SADECE open_local aracini kullanabilirsin.

Dosya silme, tasima, yeniden adlandirma veya degistirme YAPMA.

Talimati anladigini sadece HAZIR diyerek cevapla.
"""


mesaj_gonder(
    sistem_talimati
)


isitma = gemini_cevap_al()

if not isitma:

    print(
        "HATA: Gemini isitilamadi."
    )

    raise SystemExit


# ============================================================
# ANA DONGU
# ============================================================

print()
print("=" * 64)
print("JARVIS DOSYA ACMA TESTI HAZIR")
print("Sohbet: Gemini / Antigravity")
print("Ses: ElevenLabs Alper")
print("Mikrofon: AMD Microphone Array")
print("Yeni yetenek: Dogal konusmayla dosya / klasor acma")
print("Cikis: 'Jarvis kapat'")
print("=" * 64)


try:

    while True:

        kullanici = (
            sesli_komut_al()
        )

        if not kullanici:
            continue

        cikis = norm(
            kullanici
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