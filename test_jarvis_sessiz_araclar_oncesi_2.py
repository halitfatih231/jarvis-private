# -*- coding: utf-8 -*-

import difflib
import json
import os
import re
import subprocess
import threading
import unicodedata
from collections import deque
from datetime import datetime
from pathlib import Path


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

MEMORY_FILE = JARVIS_KLASORU / "jarvis_memory.json"
HISTORY_FILE = JARVIS_KLASORU / "jarvis_history.jsonl"

SON_MESAJ_SAYISI = 20
MAX_HAFIZA = 100


if not AGY.exists():
    print("HATA: Antigravity bulunamadi:")
    print(AGY)
    raise SystemExit


# ============================================================
# NORMALIZASYON
# ============================================================

def norm(metin):

    metin = str(metin).casefold()

    metin = metin.translate(
        str.maketrans({
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
    )

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
        r"[^a-z0-9\s._:\\/-]",
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
# HAFIZA DOSYALARI
# ============================================================

def varsayilan_hafiza():

    return {
        "preferred_address": "Fatih hocam",
        "facts": [],
        "file_aliases": {}
    }


def hafiza_dosyalari_hazirla():

    JARVIS_KLASORU.mkdir(
        parents=True,
        exist_ok=True
    )

    if not MEMORY_FILE.exists():

        MEMORY_FILE.write_text(
            json.dumps(
                varsayilan_hafiza(),
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    if not HISTORY_FILE.exists():
        HISTORY_FILE.touch()


def hafiza_yukle():

    try:

        veri = json.loads(
            MEMORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(veri, dict):
            raise ValueError

    except Exception:

        veri = varsayilan_hafiza()

    if not isinstance(
        veri.get("facts"),
        list
    ):
        veri["facts"] = []

    if not isinstance(
        veri.get("file_aliases"),
        dict
    ):
        veri["file_aliases"] = {}

    if not veri.get(
        "preferred_address"
    ):
        veri["preferred_address"] = "Fatih hocam"

    return veri


def hafiza_kaydet(hafiza):

    MEMORY_FILE.write_text(
        json.dumps(
            hafiza,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ============================================================
# GENEL BILGI HAFIZASI
# ============================================================

def bilgi_hatirla(metin):

    metin = str(metin).strip()

    if not metin:
        return False

    hafiza = hafiza_yukle()
    facts = hafiza["facts"]

    yeni = norm(metin)

    for eski in facts:

        if norm(eski) == yeni:
            return False

    facts.append(metin)

    if len(facts) > MAX_HAFIZA:
        facts = facts[-MAX_HAFIZA:]

    hafiza["facts"] = facts

    hafiza_kaydet(hafiza)

    print(
        "[Hafizaya kaydedildi]",
        metin
    )

    return True


def bilgi_unut(sorgu):

    sorgu = str(sorgu).strip()

    if not sorgu:
        return False

    hafiza = hafiza_yukle()

    sorgu_n = norm(sorgu)

    kalanlar = []
    silinenler = []

    for bilgi in hafiza["facts"]:

        bilgi_n = norm(bilgi)

        if (
            sorgu_n in bilgi_n
            or bilgi_n in sorgu_n
        ):
            silinenler.append(bilgi)
        else:
            kalanlar.append(bilgi)

    if not silinenler:
        return False

    hafiza["facts"] = kalanlar
    hafiza_kaydet(hafiza)

    for bilgi in silinenler:
        print(
            "[Hafizadan silindi]",
            bilgi
        )

    return True


# ============================================================
# HITAP
# ============================================================

def hitap_degistir(yeni_hitap):

    yeni_hitap = str(
        yeni_hitap
    ).strip()

    if not yeni_hitap:
        return False

    hafiza = hafiza_yukle()

    hafiza[
        "preferred_address"
    ] = yeni_hitap

    hafiza_kaydet(hafiza)

    print(
        "[Hitap guncellendi]",
        yeni_hitap
    )

    return True


# ============================================================
# DOSYA TAKMA ADI HAFIZASI
# ============================================================

def dosya_takma_adi_kaydet(
    takma_ad,
    hedef
):

    takma_ad = str(
        takma_ad
    ).strip()

    hedef = str(
        hedef
    ).strip()

    if not takma_ad or not hedef:
        return False

    hafiza = hafiza_yukle()

    anahtar = norm(
        takma_ad
    )

    hafiza[
        "file_aliases"
    ][anahtar] = {
        "name": takma_ad,
        "target": hedef
    }

    hafiza_kaydet(
        hafiza
    )

    print(
        f"[Dosya hafizasi] "
        f"{takma_ad} -> {hedef}"
    )

    return True


def dosya_takma_adi_sil(
    takma_ad
):

    takma_ad = norm(
        takma_ad
    )

    if not takma_ad:
        return False

    hafiza = hafiza_yukle()

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    if takma_ad not in aliases:
        return False

    eski = aliases.pop(
        takma_ad
    )

    hafiza[
        "file_aliases"
    ] = aliases

    hafiza_kaydet(
        hafiza
    )

    print(
        "[Dosya hafizasi silindi]",
        eski.get(
            "name",
            takma_ad
        )
    )

    return True


def dosya_takma_adi_coz(
    sorgu
):

    sorgu_n = norm(
        sorgu
    )

    if not sorgu_n:
        return None

    hafiza = hafiza_yukle()

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    # Once tam eslesme
    if sorgu_n in aliases:

        hedef = aliases[
            sorgu_n
        ].get(
            "target"
        )

        if hedef:

            print(
                f"[Hafizadan dosya] "
                f"{sorgu} -> {hedef}"
            )

            return hedef

    # "tez dosyam", "tezimi" gibi durumlar icin
    # takma adi sorgunun icinde ara.
    en_iyi = None

    for anahtar, bilgi in aliases.items():

        if not anahtar:
            continue

        if (
            anahtar in sorgu_n
            or sorgu_n in anahtar
        ):

            hedef = bilgi.get(
                "target"
            )

            if hedef:

                uzunluk = len(
                    anahtar
                )

                if (
                    en_iyi is None
                    or uzunluk > en_iyi[0]
                ):

                    en_iyi = (
                        uzunluk,
                        bilgi.get(
                            "name",
                            anahtar
                        ),
                        hedef
                    )

    if en_iyi:

        _, isim, hedef = en_iyi

        print(
            f"[Hafizadan dosya] "
            f"{isim} -> {hedef}"
        )

        return hedef

    return None


# ============================================================
# SOHBET GECMISI
# ============================================================

def gecmise_ekle(
    rol,
    metin
):

    metin = str(metin).strip()

    if not metin:
        return

    kayit = {
        "time": datetime.now().isoformat(
            timespec="seconds"
        ),
        "role": rol,
        "content": metin
    }

    with HISTORY_FILE.open(
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                kayit,
                ensure_ascii=False
            )
            + "\n"
        )


def son_gecmisi_yukle(
    adet=SON_MESAJ_SAYISI
):

    sonlar = deque(
        maxlen=adet
    )

    try:

        with HISTORY_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            for satir in f:

                satir = satir.strip()

                if not satir:
                    continue

                try:
                    veri = json.loads(
                        satir
                    )
                except Exception:
                    continue

                if isinstance(
                    veri,
                    dict
                ):
                    sonlar.append(
                        veri
                    )

    except Exception:
        pass

    return list(sonlar)


# ============================================================
# GEMINI ICIN HAFIZA BAGLAMI
# ============================================================

def hafiza_baglami_olustur():

    hafiza = hafiza_yukle()

    hitap = hafiza.get(
        "preferred_address",
        "Fatih hocam"
    )

    facts = hafiza.get(
        "facts",
        []
    )

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    if facts:

        bilgi_metni = "\n".join(
            f"- {bilgi}"
            for bilgi in facts
        )

    else:

        bilgi_metni = (
            "- Henuz kalici bilgi yok."
        )

    if aliases:

        alias_satirlari = []

        for bilgi in aliases.values():

            alias_satirlari.append(
                f"- {bilgi.get('name')} "
                f"-> {bilgi.get('target')}"
            )

        alias_metni = "\n".join(
            alias_satirlari
        )

    else:

        alias_metni = (
            "- Henuz kayitli "
            "dosya takma adi yok."
        )

    return f"""
Tercih edilen hitap:
{hitap}

Kalici bilgiler:
{bilgi_metni}

Kayitli dosya ve klasor takma adlari:
{alias_metni}
""".strip()


def gecmis_baglami_olustur():

    gecmis = son_gecmisi_yukle()

    if not gecmis:

        return (
            "Onceki sohbet kaydi yok."
        )

    satirlar = []

    for kayit in gecmis:

        rol = kayit.get(
            "role",
            ""
        )

        metin = kayit.get(
            "content",
            ""
        )

        if rol == "user":
            ad = "Kullanici"
        else:
            ad = "Jarvis"

        satirlar.append(
            f"{ad}: {metin}"
        )

    return "\n".join(
        satirlar
    )


# ============================================================
# MEMORY KOMUTLARI
# ============================================================

def memory_komutlarini_ayikla(
    cevap
):

    if not cevap:
        return "", []

    desen = (
        r"\[\[MEMORY\]\]"
        r"\s*(\{.*?\})\s*"
        r"\[\[/MEMORY\]\]"
    )

    islemler = []

    for eslesme in re.finditer(
        desen,
        cevap,
        flags=re.DOTALL
    ):

        try:

            veri = json.loads(
                eslesme.group(1)
            )

            if isinstance(
                veri,
                dict
            ):
                islemler.append(
                    veri
                )

        except Exception:
            pass

    temiz = re.sub(
        desen,
        "",
        cevap,
        flags=re.DOTALL
    ).strip()

    return temiz, islemler


def memory_islemlerini_uygula(
    islemler
):

    for islem in islemler:

        op = str(
            islem.get(
                "op",
                ""
            )
        ).strip()

        if op == "remember":

            metin = str(
                islem.get(
                    "text",
                    ""
                )
            ).strip()

            if metin:
                bilgi_hatirla(
                    metin
                )

        elif op == "forget":

            sorgu = str(
                islem.get(
                    "query",
                    ""
                )
            ).strip()

            if sorgu:
                bilgi_unut(
                    sorgu
                )

        elif op == "set_address":

            deger = str(
                islem.get(
                    "value",
                    ""
                )
            ).strip()

            if deger:
                hitap_degistir(
                    deger
                )

        elif op == "set_file_alias":

            takma_ad = str(
                islem.get(
                    "alias",
                    ""
                )
            ).strip()

            hedef = str(
                islem.get(
                    "target",
                    ""
                )
            ).strip()

            if takma_ad and hedef:

                dosya_takma_adi_kaydet(
                    takma_ad,
                    hedef
                )

        elif op == "forget_file_alias":

            takma_ad = str(
                islem.get(
                    "alias",
                    ""
                )
            ).strip()

            if takma_ad:

                dosya_takma_adi_sil(
                    takma_ad
                )


# ============================================================
# DOSYA INDEKSI
# ============================================================

DOSYA_INDEKSI = []
DOSYA_INDEKSI_KILIT = threading.Lock()
DOSYA_INDEKSI_HAZIR = threading.Event()


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

        anahtar = str(
            yol
        ).casefold()

        if (
            yol.exists()
            and anahtar not in gorulen
        ):

            gorulen.add(
                anahtar
            )

            kokler.append(
                yol
            )

    return kokler


def dosya_indeksi_olustur():

    yeni_indeks = []

    try:

        for kok in arama_kokleri():

            for mevcut, klasorler, dosyalar in os.walk(
                kok,
                topdown=True
            ):

                mevcut_path = Path(
                    mevcut
                )

                try:

                    derinlik = len(
                        mevcut_path
                        .relative_to(kok)
                        .parts
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

                    if dosya.startswith(
                        "~$"
                    ):
                        continue

                    yol = mevcut_path / dosya

                    yeni_indeks.append(
                        (
                            yol,
                            False,
                            norm(
                                Path(
                                    dosya
                                ).stem
                            ),
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

    threading.Thread(
        target=dosya_indeksi_olustur,
        daemon=True
    ).start()


# ============================================================
# DOSYA PUANI
# ============================================================

def yol_puani(
    sorgu,
    kayit
):

    yol, klasor_mu, kok_ad, tam_ad = kayit

    q = norm(
        sorgu
    )

    if not q:
        return 0.0

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
        kelime
        for kelime in q.split()
        if len(kelime) > 1
    }

    ad_kelimeler = {
        kelime
        for kelime in kok_ad.split()
        if len(kelime) > 1
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

        if ortak == len(
            q_kelimeler
        ):
            puan += 1.1

    benzerlik = difflib.SequenceMatcher(
        None,
        q,
        kok_ad
    ).ratio()

    puan += benzerlik * 2.0

    if not klasor_mu:
        puan += 0.10

    return puan


# ============================================================
# DOSYA BUL
# ============================================================

def yerel_yol_bul(
    sorgu,
    alias_kullan=True
):

    sorgu = str(
        sorgu
    ).strip()

    if not sorgu:
        return None, 0.0

    # --------------------------------------------------------
    # ONCE KALICI DOSYA HAFIZASINA BAK
    # --------------------------------------------------------

    if alias_kullan:

        hafiza_hedefi = (
            dosya_takma_adi_coz(
                sorgu
            )
        )

        if hafiza_hedefi:

            return yerel_yol_bul(
                hafiza_hedefi,
                alias_kullan=False
            )

    # --------------------------------------------------------
    # TAM DOSYA YOLU VERILMIS OLABILIR
    # --------------------------------------------------------

    try:

        direkt = Path(
            os.path.expandvars(
                os.path.expanduser(
                    sorgu.strip('"')
                )
            )
        )

        if direkt.exists():

            return (
                direkt,
                100.0
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # NORMAL DOSYA INDEKSI
    # --------------------------------------------------------

    DOSYA_INDEKSI_HAZIR.wait(
        timeout=3.0
    )

    with DOSYA_INDEKSI_KILIT:

        indeks = list(
            DOSYA_INDEKSI
        )

    if not indeks:

        return (
            None,
            0.0
        )

    sonuclar = []

    for kayit in indeks:

        puan = yol_puani(
            sorgu,
            kayit
        )

        if puan > 0:

            sonuclar.append(
                (
                    puan,
                    kayit[0]
                )
            )

    if not sonuclar:

        return (
            None,
            0.0
        )

    sonuclar.sort(
        key=lambda x: x[0],
        reverse=True
    )

    en_iyi_puan, en_iyi_yol = (
        sonuclar[0]
    )

    if en_iyi_puan < 2.1:

        return (
            None,
            en_iyi_puan
        )

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
# DOSYA AC
# ============================================================

def yerel_yol_ac(
    sorgu
):

    yol, puan = yerel_yol_bul(
        sorgu
    )

    if yol is None:

        return (
            False,
            None,
            "Fatih hocam, bu isimle eşleşen "
            "bir dosya veya klasör bulamadım."
        )

    try:

        os.startfile(
            str(yol)
        )

        return (
            True,
            yol,
            f"Açtım Fatih hocam: {yol.name}"
        )

    except Exception as e:

        return (
            False,
            yol,
            "Fatih hocam, dosyayı buldum "
            f"ama açamadım: {e}"
        )


# ============================================================
# TOOL KOMUTU
# ============================================================

def arac_komutu_ayikla(
    cevap
):

    if not cevap:
        return None

    eslesme = re.search(
        r"\[\[TOOL\]\]"
        r"\s*(\{.*?\})\s*"
        r"\[\[/TOOL\]\]",
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
# DOSYALARI HAZIRLA
# ============================================================

hafiza_dosyalari_hazirla()

print(
    "Dosya indeksi hazirlaniyor..."
)

dosya_indeksini_baslat()


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

def mesaj_gonder(
    metin
):

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


def text_delta_bul(
    obj
):

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
# SOHBET TURU
# ============================================================

def jarvis_sor(
    kullanici_metni
):

    gecmise_ekle(
        "user",
        kullanici_metni
    )

    mesaj_gonder(
        kullanici_metni
    )

    cevap = gemini_cevap_al()

    if not cevap:
        return

    # Hafiza islemlerini ayir
    temiz_cevap, hafiza_islemleri = (
        memory_komutlarini_ayikla(
            cevap
        )
    )

    memory_islemlerini_uygula(
        hafiza_islemleri
    )

    # Tool var mi?
    arac = arac_komutu_ayikla(
        temiz_cevap
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
                "[Jarvis araci: "
                "dosya/klasor ac]"
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

            gecmise_ekle(
                "assistant",
                mesaj
            )

            return

        mesaj = (
            "Fatih hocam, bu işlemi "
            "henüz yapacak bir aracım yok."
        )

        print()
        print(
            "Jarvis:",
            mesaj
        )

        gecmise_ekle(
            "assistant",
            mesaj
        )

        return

    if not temiz_cevap:

        if hafiza_islemleri:

            temiz_cevap = (
                "Hatırladım Fatih hocam."
            )

        else:

            temiz_cevap = (
                "Fatih hocam, cevap "
                "oluşturamadım."
            )

    print()
    print(
        "Jarvis:",
        temiz_cevap
    )

    gecmise_ekle(
        "assistant",
        temiz_cevap
    )


# ============================================================
# GEMINI'YE KALICI BAGLAMI VER
# ============================================================

print(
    "Kalici hafiza yukleniyor..."
)

hafiza_metni = (
    hafiza_baglami_olustur()
)

gecmis_metni = (
    gecmis_baglami_olustur()
)

print(
    "Gemini oturumu isitiliyor..."
)


sistem_talimati = f"""
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullaniciya dogal yerlerde "Fatih hocam" diye hitap et.

Bu Jarvis'in kalici hafizali sessiz gelistirme surumudur.

========================
KALICI HAFIZA
========================

{hafiza_metni}

========================
SON SOHBET KAYITLARI
========================

{gecmis_metni}

========================
GENEL DAVRANIS
========================

- Turkce konus.
- Dogal ve insani konus.
- Onceki baglami koru.
- Gecmis sohbetleri baglam olarak kullan.
- Her mesaji bilgisayar komutu sanma.
- Varsayilan cevaplari kisa ve akici tut.
- Gereksiz markdown kullanma.
- Her cevabin sonunda soru sormak zorunda degilsin.
- Kullaniciya her cumlede "Fatih hocam" deme;
  dogal yerlerde kullan.

========================
GENEL KALICI HAFIZA
========================

Kullanici acikca:
"bunu hatirla"
"unutma"
"bunu kaydet"
"bundan sonra"

gibi bir istekle gelecekte yararli bir bilgi verirse:

[[MEMORY]]{{"op":"remember","text":"KAYDEDILECEK BILGI"}}[[/MEMORY]]

Daha once kaydedilen bir bilgiyi unutmani isterse:

[[MEMORY]]{{"op":"forget","query":"UNUTULACAK BILGI"}}[[/MEMORY]]

Hitap seklini degistirirse:

[[MEMORY]]{{"op":"set_address","value":"YENI HITAP"}}[[/MEMORY]]

========================
DOSYA HAFIZASI
========================

Kullanici belirli bir dosya veya klasore
insan gibi bir takma ad verirse bunu AYRI DOSYA HAFIZASI
olarak kaydet.

Ornek:

Kullanici:
"Bunu hatirla: tez dosyam Kisisel Bilgi Kayit Formu."

Cevabinin sonuna:

[[MEMORY]]{{"op":"set_file_alias","alias":"tez","target":"Kişisel Bilgi Kayıt Formu"}}[[/MEMORY]]

Kullanici:
"Bundan sonra Cemil projesi dedigimde
Cemil_Jarvis_Test klasorunu kastedecegim."

Cevabinin sonuna:

[[MEMORY]]{{"op":"set_file_alias","alias":"Cemil projesi","target":"Cemil_Jarvis_Test"}}[[/MEMORY]]

Kullanici tam Windows yolu verirse hedefe tam yolu yazabilirsin.

Ornek:

[[MEMORY]]{{"op":"set_file_alias","alias":"tez","target":"C:\\Users\\Kullanici\\Documents\\tez.docx"}}[[/MEMORY]]

Bir dosya takma adini unutmani isterse:

[[MEMORY]]{{"op":"forget_file_alias","alias":"tez"}}[[/MEMORY]]

DOSYA TAKMA ADLARINI normal facts hafizasina
tekrar yazma. set_file_alias kullan.

========================
DOSYA / KLASOR ACMA
========================

Kullanici bilgisayarindaki bir dosyayi veya klasoru
acmani istediginde:

[[TOOL]]{{"action":"open_local","query":"DOSYA VEYA TAKMA AD"}}[[/TOOL]]

formatini kullan.

Bu durumda TOOL disinda hicbir sey yazma.

Ornek:

Kullanici:
"Kisisel bilgi kayit formunu ac."

Sen:
[[TOOL]]{{"action":"open_local","query":"kişisel bilgi kayıt formu"}}[[/TOOL]]

Kullanici:
"Tezimi ac."

Eger kalici hafizada "tez" dosya takma adi varsa:

[[TOOL]]{{"action":"open_local","query":"tez"}}[[/TOOL]]

Kullanici:
"Jarvis klasorunu ac."

Sen:
[[TOOL]]{{"action":"open_local","query":"Jarvis"}}[[/TOOL]]

ONEMLI:

"Izafiyet teorisini acikla."
dosya acma komutu DEGILDIR.

"Bu konuyu biraz daha ac."
dosya acma komutu DEGILDIR.

"Bunu aciklar misin?"
dosya acma komutu DEGILDIR.

Su anda sadece open_local aracini kullan.

Dosya SILME.
Dosya TASIMA.
Dosya DEGISTIRME.
Dosya YENIDEN ADLANDIRMA.

Parola, API anahtari veya hassas giris bilgisini
hafizaya kaydetme.

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
# DURUM
# ============================================================

mevcut_hafiza = hafiza_yukle()

hafiza_adedi = len(
    mevcut_hafiza.get(
        "facts",
        []
    )
)

alias_adedi = len(
    mevcut_hafiza.get(
        "file_aliases",
        {}
    )
)

gecmis_adedi = len(
    son_gecmisi_yukle()
)


print()
print("=" * 66)
print("JARVIS KALICI HAFIZALI SESSIZ MOD HAZIR")
print("Hitap: Fatih hocam")
print("Beyin: Gemini / Antigravity")
print("Ses: KAPALI")
print("Mikrofon: KAPALI")
print("Dosya / klasor acma: AKTIF")
print("Kalici hafiza: AKTIF")
print(f"Genel kalici bilgi: {hafiza_adedi}")
print(f"Kayitli dosya takma adi: {alias_adedi}")
print(f"Yuklenen son mesaj: {gecmis_adedi}")
print("Cikis: jarvis kapat")
print("=" * 66)


# ============================================================
# ANA DONGU
# ============================================================

try:

    while True:

        kullanici = input(
            "\nSen: "
        ).strip()

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
                "Jarvis: Görüşürüz Fatih hocam."
            )

            gecmise_ekle(
                "assistant",
                "Görüşürüz Fatih hocam."
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