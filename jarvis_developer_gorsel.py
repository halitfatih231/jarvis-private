# -*- coding: utf-8 -*-

import ast
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import pyperclip
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

import jarvis_developer as core


# ============================================================
# AYARLAR
# ============================================================

GEMINI_URL = "https://gemini.google.com/app"
CONSOLE_TITLE = "JARVIS_DEVELOPER_GORSEL_V6"
GEMINI_TIMEOUT = 600

HOTKEY_ID = 7426
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_Q = ord("Q")

STOP_EVENT = threading.Event()


# ============================================================
# GORSEL YAZMA AYARLARI
# ============================================================

# Tek seferde bütün prompt yapıştırılmaz.
# Küçük bloklar halinde Gemini kutusunda görünür biçimde ilerler.

GORSEL_YAZMA_PARCA = 180
GORSEL_YAZMA_BEKLEME = 0.055


# ============================================================
# PATCH SINIRLARI
# ============================================================

MAX_FIND_CHARS = 12000
MAX_REPLACE_CHARS = 16000

MAX_REMOVED_LINES = 120
MAX_ADDED_LINES = 180
MAX_TOTAL_DIFF_LINES = 220


# ============================================================
# GELISTIRME ALANLARI
# ============================================================

FOCUS_AREAS = [

    (
        "Doğal dil güvenliği",
        "test_jarvis_sessiz.py",
        (
            "Belirsiz, soru biçimindeki veya olumsuz komutların "
            "yanlışlıkla bilgisayar işlemi başlatmasını azalt. "
            "Kritik güvenlik fonksiyonlarına dokunma."
        ),
    ),

    (
        "Uygulama kontrolü",
        "jarvis_tools.py",
        (
            "Uygulama açma ve hedefli uygulama kontrolünü daha "
            "güvenilir hale getir. Kritik kapatma ve güç "
            "fonksiyonlarına dokunma."
        ),
    ),

    (
        "Dosya bulma",
        "jarvis_tools.py",
        (
            "Yerel dosya ve klasör bulmayı daha güvenilir yap. "
            "Yanlış eşleşmeleri azalt ve mevcut çalışan davranışı bozma."
        ),
    ),

    (
        "Dosya takma adları",
        "test_jarvis_sessiz.py",
        (
            "file_aliases sisteminin doğal dil kullanımını ve "
            "güvenilirliğini küçük bir değişiklikle geliştir."
        ),
    ),

    (
        "Bağlam takibi",
        "test_jarvis_sessiz.py",
        (
            "\"onu aç\" gibi bağlamsal komutların yalnızca güvenilir "
            "önceki hedef varken çalışmasını geliştir. "
            "Kritik kapatma güvenlik fonksiyonlarına dokunma."
        ),
    ),

    (
        "Hata yönetimi",
        "test_jarvis_sessiz.py",
        (
            "Yerel araç hatalarının kullanıcıya daha anlaşılır ve "
            "kararlı biçimde aktarılmasını geliştir."
        ),
    ),

    (
        "Windows araçları",
        "jarvis_tools.py",
        (
            "Geri döndürülebilir Windows araçlarını daha sağlam yap. "
            "Güç, silme ve kritik süreç güvenliklerine dokunma."
        ),
    ),

    (
        "Kod kararlılığı",
        "jarvis_tools.py",
        (
            "Kırılgan kenar durumlarını veya gereksiz tekrarları "
            "küçük ve güvenli bir değişiklikle azalt."
        ),
    ),
]


# ============================================================
# KILITLI KRITIK BOLUMLER
# ============================================================

PROTECTED_FUNCTIONS = {

    "test_jarvis_sessiz.py": {
        "arac_guvenlik_kontrolu",
        "belirsiz_kapatma_komutu_mi",
        "olumsuz_kapatma_ifadesi_mi",
        "acik_bilgisayar_kapatma_istegi_mi",
        "acik_yeniden_baslatma_istegi_mi",
        "acik_kilitleme_istegi_mi",
    },

    "jarvis_tools.py": {
        "yerel_sil",
        "shutdown_pc",
        "restart_pc",
        "lock_pc",
    },
}


PROTECTED_VARIABLES = {

    "jarvis_tools.py": {
        "KRITIK_SURECLER",
    }
}


# ============================================================
# EKRAN
# ============================================================

def cizgi():
    print("=" * 78)


def baslik(metin):
    print()
    cizgi()
    print(metin)
    cizgi()


def bilgi(metin):
    print(
        f"  {metin}",
        flush=True
    )


def adim(metin):
    print(
        f"→ {metin}",
        flush=True
    )


def ok(metin):
    print(
        f"[✓] {metin}",
        flush=True
    )


def hata(metin):
    print(
        f"[X] {metin}",
        flush=True
    )


def uyari(metin):
    print(
        f"[!] {metin}",
        flush=True
    )


# ============================================================
# GLOBAL DURDURMA
# ============================================================

def hotkey_thread():

    user32 = ctypes.windll.user32

    sonuc = user32.RegisterHotKey(
        None,
        HOTKEY_ID,
        MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
        VK_Q
    )

    if not sonuc:
        return

    msg = wintypes.MSG()

    try:

        while not STOP_EVENT.is_set():

            r = user32.GetMessageW(
                ctypes.byref(msg),
                None,
                0,
                0
            )

            if r <= 0:
                break

            if (
                msg.message == 0x0312
                and
                msg.wParam == HOTKEY_ID
            ):

                STOP_EVENT.set()
                break

    finally:

        try:

            user32.UnregisterHotKey(
                None,
                HOTKEY_ID
            )

        except Exception:

            pass


def hotkey_baslat():

    t = threading.Thread(
        target=hotkey_thread,
        daemon=True
    )

    t.start()

    return t


# ============================================================
# CHROME
# ============================================================

def chrome_bul():

    adaylar = [

        Path(
            os.environ.get(
                "PROGRAMFILES",
                ""
            )
        )
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",

        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                ""
            )
        )
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",

        Path(
            os.environ.get(
                "LOCALAPPDATA",
                ""
            )
        )
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
    ]

    for yol in adaylar:

        if yol.exists():

            return str(
                yol
            )

    chrome = shutil.which(
        "chrome"
    )

    if chrome:

        return chrome

    raise RuntimeError(
        "Google Chrome bulunamadı."
    )


def gemini_ac():

    subprocess.Popen(
        [
            chrome_bul(),
            "--new-tab",
            GEMINI_URL,
        ]
    )

    adim(
        "Chrome açıldı. Gemini ekrana getiriliyor..."
    )


# ============================================================
# GEMINI PENCERESI
# ============================================================

def gemini_penceresi_bul(
    timeout=45
):

    bitis = (
        time.time()
        + timeout
    )

    while (
        time.time() < bitis
        and
        not STOP_EVENT.is_set()
    ):

        try:

            pencereler = (
                Desktop(
                    backend="uia"
                ).windows()
            )

        except Exception:

            pencereler = []

        for pencere in pencereler:

            try:

                title = (
                    pencere.window_text()
                    or ""
                ).casefold()

                if (
                    "gemini" in title
                    and
                    "chrome" in title
                ):

                    return pencere

            except Exception:

                pass

        time.sleep(
            0.5
        )

    if STOP_EVENT.is_set():

        return None

    raise RuntimeError(
        "Gemini Chrome penceresi bulunamadı."
    )


# ============================================================
# GEMINI YAZMA ALANI
# ============================================================

def prompt_alani_bul(
    pencere,
    timeout=45
):

    iyi = [

        "prompt",
        "gemini",
        "message",
        "mesaj",
        "istem",
        "ask",
        "sor",
    ]

    kotu = [

        "address",
        "adres",
        "search bar",
        "arama çubuğu",
        "arama cubugu",
    ]

    bitis = (
        time.time()
        + timeout
    )

    while (
        time.time() < bitis
        and
        not STOP_EVENT.is_set()
    ):

        adaylar = []

        try:

            editler = (
                pencere.descendants(
                    control_type="Edit"
                )
            )

        except Exception:

            editler = []

        for kontrol in editler:

            try:

                if not (
                    kontrol.is_visible()
                    and
                    kontrol.is_enabled()
                ):

                    continue

                ad1 = (
                    kontrol.window_text()
                    or ""
                )

                try:

                    ad2 = (
                        kontrol.element_info.name
                        or ""
                    )

                except Exception:

                    ad2 = ""

                isim = (
                    ad1
                    + " "
                    + ad2
                ).strip()

                kucuk = (
                    isim.casefold()
                )

                if any(
                    x in kucuk
                    for x in kotu
                ):

                    continue

                puan = sum(
                    1
                    for x in iyi
                    if x in kucuk
                )

                adaylar.append(
                    (
                        puan,
                        kontrol
                    )
                )

            except Exception:

                pass

        if adaylar:

            adaylar.sort(
                key=lambda x: x[0],
                reverse=True
            )

            return adaylar[
                0
            ][1]

        time.sleep(
            0.5
        )

    if STOP_EVENT.is_set():

        return None

    raise RuntimeError(
        "Gemini mesaj kutusu bulunamadı."
    )


# ============================================================
# ODAK KONTROLU
# ============================================================

def gemini_on_planda_mi(
    pencere
):

    try:

        return (
            ctypes.windll.user32.GetForegroundWindow()
            == pencere.handle
        )

    except Exception:

        return False


def gemini_yazma_odagini_hazirla(
    pencere,
    alan
):

    if STOP_EVENT.is_set():

        return False

    try:

        if not gemini_on_planda_mi(
            pencere
        ):

            pencere.set_focus()

            time.sleep(
                0.25
            )

        if not gemini_on_planda_mi(
            pencere
        ):

            return False

        try:

            alan.set_focus()

        except Exception:

            alan.click_input()

            time.sleep(
                0.15
            )

        # Her seferinde metnin sonuna git.
        send_keys(
            "^{END}",
            pause=0.01
        )

        return gemini_on_planda_mi(
            pencere
        )

    except Exception:

        return False


# ============================================================
# HIZLI AMA GORSEL YAZMA
# ============================================================

def metni_gorsel_hizli_yaz(
    pencere,
    alan,
    metin
):

    toplam = len(
        metin
    )

    yazilan = 0

    son_yuzde = -1

    while yazilan < toplam:

        if STOP_EVENT.is_set():

            return False

        # ----------------------------------------------------
        # HER PARCADAN ONCE ODAK KONTROLU
        # ----------------------------------------------------

        if not gemini_yazma_odagini_hazirla(
            pencere,
            alan
        ):

            raise RuntimeError(
                "Gemini yazma alanı odağı kayboldu. "
                "Güvenlik için yazma durduruldu. "
                "CMD'ye yazı gönderilmedi."
            )

        parca = metin[
            yazilan:
            yazilan + GORSEL_YAZMA_PARCA
        ]

        # ----------------------------------------------------
        # SADECE BU KUCUK PARCA PANODA
        # ----------------------------------------------------

        pyperclip.copy(
            parca
        )

        # ----------------------------------------------------
        # PASTE ONCESI SON ODAK KONTROLU
        # ----------------------------------------------------

        if not gemini_on_planda_mi(
            pencere
        ):

            raise RuntimeError(
                "Gemini penceresi ön plandan çıktı. "
                "Yanlış pencereye yazmamak için işlem kesildi."
            )

        # ----------------------------------------------------
        # KUCUK PARCAYI EKLE
        # ----------------------------------------------------

        send_keys(
            "^v",
            pause=0.01
        )

        yazilan += len(
            parca
        )

        yuzde = int(
            (
                yazilan
                / toplam
            )
            * 100
        )

        if (
            yuzde != son_yuzde
            and
            yuzde % 10 == 0
        ):

            son_yuzde = yuzde

            bilgi(
                f"Gemini yazma ilerlemesi: %{yuzde}"
            )

        time.sleep(
            GORSEL_YAZMA_BEKLEME
        )

    return True


# ============================================================
# GEMINI GONDER BUTONU
# ============================================================

def gemini_gonder_butonu_bul(
    pencere,
    timeout=20
):

    tam_isimler = {

        "send message",
        "send",
        "gönder",
        "gonder",
        "mesaj gönder",
        "mesaj gonder",
        "submit",
        "send prompt",
    }

    kismen = [

        "send message",
        "mesaj gönder",
        "mesaj gonder",
        "send prompt",
    ]

    bitis = (
        time.time()
        + timeout
    )

    while (
        time.time() < bitis
        and
        not STOP_EVENT.is_set()
    ):

        try:

            butonlar = (
                pencere.descendants(
                    control_type="Button"
                )
            )

        except Exception:

            butonlar = []

        for buton in reversed(
            butonlar
        ):

            try:

                if not (
                    buton.is_visible()
                    and
                    buton.is_enabled()
                ):

                    continue

                ad1 = (
                    buton.window_text()
                    or ""
                )

                try:

                    ad2 = (
                        buton.element_info.name
                        or ""
                    )

                except Exception:

                    ad2 = ""

                ad = (
                    ad1
                    + " "
                    + ad2
                ).strip().casefold()

                if (
                    ad in tam_isimler
                    or
                    any(
                        x in ad
                        for x in kismen
                    )
                ):

                    return buton

            except Exception:

                pass

        time.sleep(
            0.3
        )

    if STOP_EVENT.is_set():

        return None

    raise RuntimeError(
        "Gemini'nin ↑ Gönder düğmesi bulunamadı. "
        "Metin gönderilmedi."
    )


# ============================================================
# GEMINI CEVAP URETIYOR MU?
# ============================================================

def gemini_uretim_suruyor_mu(
    pencere
):

    durdur_isimleri = [

        "stop response",
        "stop generating",
        "yanıtı durdur",
        "yaniti durdur",
        "oluşturmayı durdur",
        "olusturmayi durdur",
    ]

    try:

        butonlar = (
            pencere.descendants(
                control_type="Button"
            )
        )

    except Exception:

        return False

    for buton in butonlar:

        try:

            if not buton.is_visible():

                continue

            ad1 = (
                buton.window_text()
                or ""
            )

            try:

                ad2 = (
                    buton.element_info.name
                    or ""
                )

            except Exception:

                ad2 = ""

            ad = (
                ad1
                + " "
                + ad2
            ).strip().casefold()

            if any(
                isim in ad
                for isim
                in durdur_isimleri
            ):

                return True

        except Exception:

            pass

    return False


# ============================================================
# COPY BUTONLARI
# ============================================================

def copy_butonlari(
    pencere
):

    bulunan = []

    try:

        butonlar = (
            pencere.descendants(
                control_type="Button"
            )
        )

    except Exception:

        return []

    for buton in butonlar:

        try:

            if not buton.is_visible():

                continue

            ad1 = (
                buton.window_text()
                or ""
            )

            try:

                ad2 = (
                    buton.element_info.name
                    or ""
                )

            except Exception:

                ad2 = ""

            ad = (
                ad1
                + " "
                + ad2
            ).strip().casefold()

            if (
                "copy" in ad
                or
                "kopyala" in ad
            ):

                bulunan.append(
                    buton
                )

        except Exception:

            pass

    return bulunan


# ============================================================
# CMD ONE GETIR
# ============================================================

def cmd_one_getir():

    try:

        pencere = (
            Desktop(
                backend="uia"
            ).window(
                title_re=(
                    ".*"
                    + CONSOLE_TITLE
                    + ".*"
                )
            )
        )

        pencere.set_focus()

    except Exception:

        pass


# ============================================================
# DEV CEVAP AYIKLA
# ============================================================

def dev_cevabi_ayikla(
    cevap,
    beklenen_request_id
):

    if not isinstance(
        cevap,
        str
    ):

        raise ValueError(
            "Gemini cevabı metin değil."
        )

    bas = cevap.find(
        "[[DEV]]"
    )

    if bas == -1:

        raise ValueError(
            "[[DEV]] bulunamadı."
        )

    bas += len(
        "[[DEV]]"
    )

    find_tag = cevap.find(
        "[[FIND]]",
        bas
    )

    dev_end = cevap.find(
        "[[/DEV]]",
        bas
    )

    # ========================================================
    # DONE
    # ========================================================

    if (
        dev_end != -1
        and
        (
            find_tag == -1
            or
            dev_end < find_tag
        )
    ):

        metadata_text = (
            cevap[
                bas:dev_end
            ].strip()
        )

        veri = json.loads(
            metadata_text
        )

        if (
            veri.get(
                "request_id"
            )
            != beklenen_request_id
        ):

            raise ValueError(
                "Cevap başka geliştirme turuna ait."
            )

        if (
            str(
                veri.get(
                    "status",
                    ""
                )
            ).casefold()
            != "done"
        ):

            raise ValueError(
                "DONE cevabında status=done değil."
            )

        return {

            "status":
                "done",

            "request_id":
                beklenen_request_id,

            "summary":
                str(
                    veri.get(
                        "summary",
                        ""
                    )
                ),

            "reason":
                str(
                    veri.get(
                        "reason",
                        ""
                    )
                ),
        }

    # ========================================================
    # PATCH
    # ========================================================

    if find_tag == -1:

        raise ValueError(
            "[[FIND]] bulunamadı."
        )

    metadata_text = (
        cevap[
            bas:find_tag
        ].strip()
    )

    veri = json.loads(
        metadata_text
    )

    if (
        veri.get(
            "request_id"
        )
        != beklenen_request_id
    ):

        raise ValueError(
            "Cevap başka geliştirme turuna ait."
        )

    if (
        str(
            veri.get(
                "status",
                ""
            )
        ).casefold()
        != "patch"
    ):

        raise ValueError(
            "PATCH cevabında status=patch değil."
        )

    find_bas = (
        find_tag
        + len(
            "[[FIND]]"
        )
    )

    find_end = (
        cevap.find(
            "[[/FIND]]",
            find_bas
        )
    )

    if find_end == -1:

        raise ValueError(
            "[[/FIND]] bulunamadı."
        )

    replace_tag = (
        cevap.find(
            "[[REPLACE]]",
            find_end
        )
    )

    if replace_tag == -1:

        raise ValueError(
            "[[REPLACE]] bulunamadı."
        )

    replace_bas = (
        replace_tag
        + len(
            "[[REPLACE]]"
        )
    )

    replace_end = (
        cevap.find(
            "[[/REPLACE]]",
            replace_bas
        )
    )

    if replace_end == -1:

        raise ValueError(
            "[[/REPLACE]] bulunamadı."
        )

    dev_end = (
        cevap.find(
            "[[/DEV]]",
            replace_end
        )
    )

    if dev_end == -1:

        raise ValueError(
            "[[/DEV]] bulunamadı."
        )

    find_text = (
        cevap[
            find_bas:find_end
        ]
    )

    replace_text = (
        cevap[
            replace_bas:replace_end
        ]
    )

    if find_text.startswith(
        "\r\n"
    ):

        find_text = (
            find_text[
                2:
            ]
        )

    elif find_text.startswith(
        "\n"
    ):

        find_text = (
            find_text[
                1:
            ]
        )

    if find_text.endswith(
        "\r\n"
    ):

        find_text = (
            find_text[
                :-2
            ]
        )

    elif find_text.endswith(
        "\n"
    ):

        find_text = (
            find_text[
                :-1
            ]
        )

    if replace_text.startswith(
        "\r\n"
    ):

        replace_text = (
            replace_text[
                2:
            ]
        )

    elif replace_text.startswith(
        "\n"
    ):

        replace_text = (
            replace_text[
                1:
            ]
        )

    if replace_text.endswith(
        "\r\n"
    ):

        replace_text = (
            replace_text[
                :-2
            ]
        )

    elif replace_text.endswith(
        "\n"
    ):

        replace_text = (
            replace_text[
                :-1
            ]
        )

    return {

        "status":
            "patch",

        "request_id":
            beklenen_request_id,

        "target_file":
            str(
                veri.get(
                    "target_file",
                    ""
                )
            ).strip(),

        "summary":
            str(
                veri.get(
                    "summary",
                    ""
                )
            ),

        "reason":
            str(
                veri.get(
                    "reason",
                    ""
                )
            ),

        "find":
            find_text,

        "replace":
            replace_text,
    }


# ============================================================
# COPY BUTONUNDAN METIN AL
# ============================================================

def butondan_pano_al(
    buton
):

    sentinel = (
        "__JARVIS_CLIPBOARD_"
        + uuid.uuid4().hex
        + "__"
    )

    pyperclip.copy(
        sentinel
    )

    try:

        buton.click_input()

    except Exception:

        return None

    bitis = (
        time.time()
        + 2.5
    )

    while time.time() < bitis:

        try:

            metin = (
                pyperclip.paste()
            )

        except Exception:

            metin = ""

        if (
            isinstance(
                metin,
                str
            )
            and
            metin != sentinel
        ):

            return metin

        time.sleep(
            0.1
        )

    return None


# ============================================================
# GEMINI CEVABI BEKLE
# ============================================================

def gemini_cevabi_bekle(
    pencere,
    gonderilen_prompt,
    request_id
):

    bitis = (
        time.time()
        + GEMINI_TIMEOUT
    )

    son_hata = ""

    while time.time() < bitis:

        if STOP_EVENT.is_set():

            return None

        # Gemini hâlâ yazıyorsa bekle.
        if gemini_uretim_suruyor_mu(
            pencere
        ):

            time.sleep(
                1.2
            )

            continue

        butonlar = (
            copy_butonlari(
                pencere
            )
        )

        # En yeni Kopyala düğmesinden eskiye doğru git.
        for buton in reversed(
            butonlar
        ):

            if STOP_EVENT.is_set():

                return None

            cevap = (
                butondan_pano_al(
                    buton
                )
            )

            if not cevap:

                continue

            # Kendi promptumuz cevap olamaz.
            if (
                cevap.strip()
                == gonderilen_prompt.strip()
            ):

                son_hata = (
                    "Promptun Kopyala düğmesi bulundu; "
                    "cevap olmadığı için yok sayıldı."
                )

                continue

            try:

                dev_cevabi_ayikla(
                    cevap,
                    request_id
                )

                return cevap

            except Exception as e:

                son_hata = (
                    str(
                        e
                    )
                )

        time.sleep(
            1
        )

    raise RuntimeError(
        "Gemini'den bu tura ait doğru cevap alınamadı. "
        + son_hata
    )


# ============================================================
# GEMINI'YE GORSEL SOR
# ============================================================

def gorsel_gemini_sor(
    pencere,
    prompt,
    request_id
):

    if STOP_EVENT.is_set():

        return None

    try:

        pencere.set_focus()

    except Exception:

        pass

    time.sleep(
        0.8
    )

    alan = (
        prompt_alani_bul(
            pencere
        )
    )

    if alan is None:

        return None

    baslik(
        "GEMINI'YE GIDILIYOR"
    )

    bilgi(
        "Tur kimliği: "
        + request_id
    )

    bilgi(
        f"Yazılacak prompt: "
        f"{len(prompt):,} karakter"
    )

    bilgi(
        f"Görsel yazma: "
        f"{GORSEL_YAZMA_PARCA} karakterlik küçük parçalar"
    )

    bilgi(
        "Şimdi Chrome/Gemini ekranını izleyin."
    )

    try:

        pencere.set_focus()

        alan.click_input()

    except Exception as e:

        raise RuntimeError(
            "Gemini yazma alanına odaklanılamadı: "
            + str(
                e
            )
        )

    time.sleep(
        0.4
    )

    # Eski yazıyı temizle.
    send_keys(
        "^a",
        pause=0.03
    )

    send_keys(
        "{BACKSPACE}",
        pause=0.03
    )

    time.sleep(
        0.4
    )

    baslik(
        "JARVIS GEMINI'YE GORSEL OLARAK YAZIYOR"
    )

    bilgi(
        f"{len(prompt):,} karakter bir anda "
        "yapıştırılmayacak."
    )

    ok(
        "Yazı küçük bloklar halinde gözünüzün önünde akacak."
    )

    # ========================================================
    # GORSEL YAZMA
    # ========================================================

    yazildi = (
        metni_gorsel_hizli_yaz(
            pencere,
            alan,
            prompt
        )
    )

    if not yazildi:

        return None

    ok(
        "Promptun tamamı Gemini yazma kutusuna ulaştı."
    )

    if STOP_EVENT.is_set():

        return None

    # ========================================================
    # GONDERME ONCESI ODAK
    # ========================================================

    if not gemini_yazma_odagini_hazirla(
        pencere,
        alan
    ):

        raise RuntimeError(
            "Gönderme öncesi Gemini odağı doğrulanamadı."
        )

    # ========================================================
    # GERCEK YUKARI OK / GONDER
    # ========================================================

    adim(
        "Gemini'nin gerçek ↑ Gönder düğmesi aranıyor..."
    )

    gonder_butonu = (
        gemini_gonder_butonu_bul(
            pencere,
            timeout=20
        )
    )

    if gonder_butonu is None:

        return None

    time.sleep(
        0.5
    )

    if not gemini_on_planda_mi(
        pencere
    ):

        raise RuntimeError(
            "Gönder düğmesine basmadan önce "
            "Gemini odağı kayboldu."
        )

    # GERCEK BUTONA TIKLA
    gonder_butonu.click_input()

    ok(
        "Gemini'nin gerçek ↑ Gönder düğmesine tıklandı."
    )

    adim(
        "İstek gönderildi."
    )

    adim(
        "Gemini'nin cevabı bekleniyor..."
    )

    time.sleep(
        1
    )

    # ========================================================
    # CEVABI AL
    # ========================================================

    cevap = (
        gemini_cevabi_bekle(
            pencere,
            prompt,
            request_id
        )
    )

    cmd_one_getir()

    time.sleep(
        0.4
    )

    if cevap is not None:

        baslik(
            "GEMINI CEVABI ALINDI"
        )

        bilgi(
            f"Gerçek cevap uzunluğu: "
            f"{len(cevap):,} karakter"
        )

        ok(
            "Prompt cevap sanılmadı."
        )

        ok(
            "Request ID doğrulandı."
        )

        ok(
            "Tam DEV cevabı doğrulandı."
        )

    return cevap


# ============================================================
# KRITIK KOD SNAPSHOT
# ============================================================

def node_source(
    kaynak,
    node
):

    metin = (
        ast.get_source_segment(
            kaynak,
            node
        )
    )

    return (
        metin
        if metin is not None
        else ""
    )


def protected_snapshot(
    workspace
):

    snapshot = {}

    for dosya_adi in core.SOURCE_FILES:

        kaynak = (
            core.dosya_oku(
                workspace
                / dosya_adi
            )
        )

        tree = (
            ast.parse(
                kaynak
            )
        )

        protected_funcs = (
            PROTECTED_FUNCTIONS.get(
                dosya_adi,
                set()
            )
        )

        protected_vars = (
            PROTECTED_VARIABLES.get(
                dosya_adi,
                set()
            )
        )

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):

                if (
                    node.name
                    in protected_funcs
                ):

                    snapshot[
                        (
                            dosya_adi,
                            "function",
                            node.name
                        )
                    ] = node_source(
                        kaynak,
                        node
                    )

            elif isinstance(
                node,
                ast.Assign
            ):

                for target in node.targets:

                    if (
                        isinstance(
                            target,
                            ast.Name
                        )
                        and
                        target.id
                        in protected_vars
                    ):

                        snapshot[
                            (
                                dosya_adi,
                                "variable",
                                target.id
                            )
                        ] = node_source(
                            kaynak,
                            node
                        )

            elif isinstance(
                node,
                ast.AnnAssign
            ):

                target = (
                    node.target
                )

                if (
                    isinstance(
                        target,
                        ast.Name
                    )
                    and
                    target.id
                    in protected_vars
                ):

                    snapshot[
                        (
                            dosya_adi,
                            "variable",
                            target.id
                        )
                    ] = node_source(
                        kaynak,
                        node
                    )

    return snapshot


def protected_ayni_mi(
    workspace,
    baseline
):

    return (
        protected_snapshot(
            workspace
        )
        == baseline
    )


# ============================================================
# PATCH UYGULA
# ============================================================

def patch_uygula(
    veri,
    workspace,
    protected_baseline,
    seen_patch_hashes,
    beklenen_target
):

    durum = (
        str(
            veri.get(
                "status",
                ""
            )
        ).casefold()
    )

    if durum == "done":

        return {

            "done":
                True,

            "summary":
                veri.get(
                    "summary",
                    ""
                ),

            "reason":
                veri.get(
                    "reason",
                    ""
                ),
        }

    if durum != "patch":

        raise ValueError(
            "Status patch veya done olmalı."
        )

    hedef = (
        veri.get(
            "target_file",
            ""
        )
    )

    if hedef not in core.SOURCE_FILES:

        raise ValueError(
            "İzin verilmeyen hedef dosya: "
            + str(
                hedef
            )
        )

    if hedef != beklenen_target:

        raise ValueError(
            "Gemini yanlış hedef dosya seçti. "
            f"Beklenen: {beklenen_target}, "
            f"gelen: {hedef}"
        )

    find_text = (
        veri.get(
            "find",
            ""
        )
    )

    replace_text = (
        veri.get(
            "replace",
            ""
        )
    )

    if not isinstance(
        find_text,
        str
    ):

        raise ValueError(
            "FIND metni geçersiz."
        )

    if not isinstance(
        replace_text,
        str
    ):

        raise ValueError(
            "REPLACE metni geçersiz."
        )

    if not find_text.strip():

        raise ValueError(
            "FIND boş olamaz."
        )

    if (
        len(
            find_text
        )
        > MAX_FIND_CHARS
    ):

        raise ValueError(
            "FIND bloğu fazla büyük."
        )

    if (
        len(
            replace_text
        )
        > MAX_REPLACE_CHARS
    ):

        raise ValueError(
            "REPLACE bloğu fazla büyük."
        )

    yasak_placeholder = [

        "HEDEF DOSYANIN TAM ICERIGI",
        "Kisa gelistirme ozeti",
        "Kisa gerekce",
        "BURAYA KOD",
        "...existing code...",
        "... mevcut kod ...",
    ]

    toplam_patch = (
        find_text
        + "\n"
        + replace_text
    )

    for placeholder in yasak_placeholder:

        if (
            placeholder.casefold()
            in toplam_patch.casefold()
        ):

            raise ValueError(
                "Gemini gerçek kod yerine "
                "şablon döndürdü: "
                + placeholder
            )

    patch_hash = (
        hashlib.sha256(
            (
                hedef
                + "\0"
                + find_text
                + "\0"
                + replace_text
            ).encode(
                "utf-8"
            )
        ).hexdigest()
    )

    if (
        patch_hash
        in seen_patch_hashes
    ):

        raise ValueError(
            "Aynı patch daha önce denendi."
        )

    hedef_yol = (
        workspace
        / hedef
    )

    eski = (
        core.dosya_oku(
            hedef_yol
        )
    )

    adet = (
        eski.count(
            find_text
        )
    )

    if adet == 0:

        raise ValueError(
            "Gemini'nin FIND bloğu dosyada bulunamadı."
        )

    if adet > 1:

        raise ValueError(
            f"FIND bloğu dosyada "
            f"{adet} kez bulundu. "
            "Patch yeterince kesin değil."
        )

    yeni = (
        eski.replace(
            find_text,
            replace_text,
            1
        )
    )

    if yeni == eski:

        raise ValueError(
            "Patch hiçbir değişiklik üretmedi."
        )

    eklenen, silinen = (
        core.diff_istatistik(
            eski,
            yeni
        )
    )

    if (
        silinen
        > MAX_REMOVED_LINES
    ):

        raise ValueError(
            f"Tek turda {silinen} satır "
            "silme girişimi var."
        )

    if (
        eklenen
        > MAX_ADDED_LINES
    ):

        raise ValueError(
            f"Tek turda {eklenen} satır "
            "ekleme girişimi var."
        )

    if (
        eklenen
        + silinen
        > MAX_TOTAL_DIFF_LINES
    ):

        raise ValueError(
            "Patch tek tur için fazla büyük."
        )

    eski_satir = max(
        1,
        len(
            eski.splitlines()
        )
    )

    yeni_satir = (
        len(
            yeni.splitlines()
        )
    )

    if (
        yeni_satir
        < eski_satir * 0.90
    ):

        raise ValueError(
            "Patch dosyanın %10'dan fazlasını "
            "küçültmeye çalıştı."
        )

    guvenli, neden = (
        core.kod_guvenli_mi(
            eski,
            yeni
        )
    )

    if not guvenli:

        raise ValueError(
            neden
        )

    core.dosya_yaz(
        hedef_yol,
        yeni
    )

    if not protected_ayni_mi(
        workspace,
        protected_baseline
    ):

        raise ValueError(
            "Patch kilitli kritik güvenlik "
            "kodlarından birini değiştirdi."
        )

    seen_patch_hashes.add(
        patch_hash
    )

    return {

        "done":
            False,

        "target":
            hedef,

        "summary":
            veri.get(
                "summary",
                ""
            ),

        "reason":
            veri.get(
                "reason",
                ""
            ),

        "added_lines":
            eklenen,

        "removed_lines":
            silinen,

        "patch_hash":
            patch_hash,
    }


# ============================================================
# WORKSPACE GERİ YUKLE
# ============================================================

def workspace_geri_yukle(
    backup,
    workspace
):

    for isim in core.SOURCE_FILES:

        shutil.copy2(
            backup / isim,
            workspace / isim
        )


# ============================================================
# ILK TESTLER
# ============================================================

def ilk_testleri_yap(
    workspace
):

    baslik(
        "ILK TEST DURUMU"
    )

    compile_ok, compile_results = (
        core.py_compile_test(
            workspace
        )
    )

    for item in compile_results:

        if item[
            "success"
        ]:

            ok(
                item[
                    "file"
                ]
                + " py_compile"
            )

        else:

            hata(
                item[
                    "file"
                ]
                + " py_compile"
            )

            bilgi(
                item.get(
                    "output",
                    ""
                )
            )

    if not compile_ok:

        return False

    behavior_ok, _ = (
        core.davranis_testleri(
            workspace
        )
    )

    if not behavior_ok:

        return False

    ok(
        "Başlangıç test sürümü sağlam."
    )

    return True


# ============================================================
# GEMINI TALIMATI
# ============================================================

PATCH_SYSTEM = r"""
Sen Jarvis'in kontrollu yazilim gelistirme ajanisin.

Bu sistemde TAM DOSYA DONDURMEK YASAKTIR.

Sadece bir adet kucuk, kesin ve test edilebilir
BUL -> DEGISTIR patch'i uretebilirsin.

KESIN KURALLAR:

1. Sadece sana verilen hedef Python dosyasi uzerinde calis.

2. Tum dosyayi yeniden yazma.

3. FIND blogu mevcut dosyadan HARFI HARFINE kopyalanmis
benzersiz bir kod parcasi olmali.

4. FIND blogu dosyada yalnizca bir kez bulunmali.

5. REPLACE blogu FIND blogunun yerine yazilacak gercek kod olmali.

6. Placeholder veya "..." kullanma.

7. Bir turda kucuk degisiklik yap.

8. Kapatma, shutdown, restart, lock, kalici silme,
kritik surec korumasi ve Cemil ana proje guvenliklerini
zayiflatma.

9. Dosya silme send2trash + kullanici onayi mantigini koru.

10. Sifre, API anahtari, tarayici kimlik bilgisi veya
gizli kullanici verisi arayan ozellik ekleme.

11. Internetten kod indirme veya paket kurma ekleme.

12. UAC atlatma ekleme.

13. Ana Jarvis'e otomatik terfi kodu ekleme.

14. Gereksiz degisiklik yapma.

15. Uygun gelistirme yoksa status=done kullan.

16. Markdown code fence kullanma.

17. Gizli dusunce surecini yazma.
Sadece kisa summary ve reason yaz.

PATCH CEVAP FORMATI:

[[DEV]]
{
  "request_id": "REQUEST_ID_BURAYA",
  "status": "patch",
  "target_file": "DOSYA_ADI",
  "summary": "Gercek kisa gelistirme ozeti",
  "reason": "Gercek kisa gerekce"
}
[[FIND]]
DOSYADAN HARFI HARFINE ALINMIS ESKI KOD
[[/FIND]]
[[REPLACE]]
YENI GERCEK KOD
[[/REPLACE]]
[[/DEV]]

DEGISIKLIK GEREKMIYORSA:

[[DEV]]
{
  "request_id": "REQUEST_ID_BURAYA",
  "status": "done",
  "summary": "Bu alanda guvenli yeni degisiklik gerekmiyor",
  "reason": "Kisa gerekce"
}
[[/DEV]]

Bunun disinda hicbir sey yazma.
""".strip()


def gelistirici_promptu(
    workspace,
    tur,
    request_id,
    focus_name,
    target_file,
    focus_text,
    onceki_feedback
):

    kod = (
        core.dosya_oku(
            workspace
            / target_file
        )
    )

    return f"""
{PATCH_SYSTEM}

==================================================
BU TURUN REQUEST ID'SI
==================================================

{request_id}

Cevabindaki request_id TAM OLARAK bu deger olmali.

==================================================
TUR
==================================================

{tur}

==================================================
HEDEF DOSYA
==================================================

{target_file}

==================================================
GELISTIRME ALANI
==================================================

{focus_name}

==================================================
AMAC
==================================================

{focus_text}

==================================================
ONCEKI TEST GERI BILDIRIMI
==================================================

{onceki_feedback or "Yok."}

==================================================
KILITLI GUVENLIK
==================================================

Kritik kapatma, shutdown, restart, lock,
silme ve kritik Windows surec guvenlik fonksiyonlari
yerel sistem tarafindan kilitlidir.

Onlari degistirmeye calisma.

==================================================
MEVCUT DOSYA
==================================================

{kod}

==================================================
GOREV
==================================================

Yalnizca bu dosyada gercekten faydali KUCK bir
iyilestirme bul.

Tum dosyayi dondurme.

Bir adet benzersiz FIND + REPLACE patch'i dondur.

FIND metni mevcut dosyadan birebir alinmali.

Uygun degisiklik yoksa DONE dondur.

Cevabindaki request_id:
{request_id}
""".strip()


# ============================================================
# RAPOR
# ============================================================

def rapor_kaydet(
    session_info,
    toplam_tur,
    accepted,
    rejected,
    done_count,
    stop_reason,
    main_hash_before
):

    main_ok, integrity = (
        core.hashler_ayni_mi(
            core.ROOT,
            main_hash_before
        )
    )

    rapor = {

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "total_iterations":
            toplam_tur,

        "accepted_changes":
            accepted,

        "rejected_changes":
            rejected,

        "no_change_responses":
            done_count,

        "stop_reason":
            stop_reason,

        "main_files_unchanged":
            main_ok,

        "main_integrity":
            integrity,

        "workspace":
            str(
                session_info[
                    "workspace"
                ]
            ),

        "automatic_promotion":
            False,
    }

    yol = (
        session_info[
            "session"
        ]
        / "visual_developer_v6_report.json"
    )

    yol.write_text(
        json.dumps(
            rapor,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return yol


# ============================================================
# ANA GELISTIRME DONGUSU
# ============================================================

def surekli_gelistir():

    core.kaynaklari_kontrol_et()

    main_hash_before = (
        core.kaynak_hashleri(
            core.ROOT
        )
    )

    session_info = (
        core.dev_oturumu_olustur()
    )

    workspace = (
        session_info[
            "workspace"
        ]
    )

    iterations = (
        session_info[
            "iterations"
        ]
    )

    protected_baseline = (
        protected_snapshot(
            workspace
        )
    )

    seen_patch_hashes = set()

    baslik(
        "JARVIS DEVELOPER - GORSEL SUREKLI V6"
    )

    ok(
        "Ana Jarvis dosyaları korunuyor."
    )

    ok(
        "Gemini Chrome'da gözünüzün önünde çalışacak."
    )

    ok(
        "Prompt bir anda yapışmayacak."
    )

    ok(
        "Yazı küçük bloklar halinde ekranda akacak."
    )

    ok(
        "Gemini odağı kaybolursa CMD'ye yazmayacak."
    )

    ok(
        "Gerçek ↑ Gönder düğmesine tıklanacak."
    )

    ok(
        "Cevap request ID ile doğrulanacak."
    )

    ok(
        "Kritik güvenlik fonksiyonları kilitli."
    )

    ok(
        "Başarısız patch geri alınacak."
    )

    ok(
        "Ana sürüme otomatik terfi KAPALI."
    )

    print()

    uyari(
        "DURDURMA: CTRL + ALT + Q"
    )

    print()

    bilgi(
        "Test çalışma alanı:"
    )

    print(
        workspace
    )

    if not ilk_testleri_yap(
        workspace
    ):

        raise RuntimeError(
            "Başlangıç test sürümü mevcut testlerden geçemedi."
        )

    gemini_ac()

    pencere = (
        gemini_penceresi_bul()
    )

    if pencere is None:

        return

    time.sleep(
        2
    )

    toplam_tur = 0

    accepted = 0
    rejected = 0
    done_count = 0

    focus_cursor = 0

    onceki_feedback = ""

    while not STOP_EVENT.is_set():

        toplam_tur += 1

        (
            focus_name,
            target_file,
            focus_text
        ) = (
            FOCUS_AREAS[
                focus_cursor
                % len(
                    FOCUS_AREAS
                )
            ]
        )

        request_id = (
            "JARVIS-"
            + uuid.uuid4().hex[
                :12
            ].upper()
        )

        baslik(
            f"GELISTIRME TURU {toplam_tur}"
        )

        bilgi(
            "İncelenen alan: "
            + focus_name
        )

        bilgi(
            "Hedef dosya: "
            + target_file
        )

        bilgi(
            focus_text
        )

        core.iterasyon_yedegi(
            workspace,
            iterations,
            toplam_tur
        )

        backup = (
            iterations
            / f"before_iteration_{toplam_tur}"
        )

        prompt = (
            gelistirici_promptu(
                workspace,
                toplam_tur,
                request_id,
                focus_name,
                target_file,
                focus_text,
                onceki_feedback
            )
        )

        try:

            cevap = (
                gorsel_gemini_sor(
                    pencere,
                    prompt,
                    request_id
                )
            )

        except Exception as e:

            rejected += 1

            cmd_one_getir()

            hata(
                "Gemini işlemi başarısız."
            )

            bilgi(
                str(
                    e
                )
            )

            onceki_feedback = (
                "Onceki tur teknik bir nedenle tamamlanamadi. "
                "Ayni alanda tekrar dene."
            )

            time.sleep(
                2
            )

            continue

        if STOP_EVENT.is_set():

            break

        if cevap is None:

            break

        cmd_one_getir()

        adim(
            "Gemini cevabı ayrıştırılıyor..."
        )

        try:

            veri = (
                dev_cevabi_ayikla(
                    cevap,
                    request_id
                )
            )

        except Exception as e:

            rejected += 1

            hata(
                "Gemini DEV cevabı geçersiz."
            )

            bilgi(
                str(
                    e
                )
            )

            workspace_geri_yukle(
                backup,
                workspace
            )

            onceki_feedback = (
                "Onceki cevabin DEV formati gecersizdi: "
                + str(
                    e
                )
            )

            time.sleep(
                2
            )

            continue

        # ====================================================
        # DONE
        # ====================================================

        if (
            veri.get(
                "status"
            )
            == "done"
        ):

            done_count += 1

            baslik(
                "BU ALANDA DEGISIKLIK YOK"
            )

            ok(
                veri.get(
                    "summary",
                    "Değişiklik gerekmedi."
                )
            )

            bilgi(
                veri.get(
                    "reason",
                    ""
                )
            )

            focus_cursor += 1

            onceki_feedback = (
                "Onceki alanda yeni degisiklik gerekmedi. "
                "Simdi sonraki gelistirme alanini incele."
            )

            time.sleep(
                2
            )

            continue

        # ====================================================
        # PATCH
        # ====================================================

        baslik(
            "GEMINI PATCH'I"
        )

        bilgi(
            "Hedef: "
            + veri.get(
                "target_file",
                ""
            )
        )

        bilgi(
            "Ne değişiyor: "
            + veri.get(
                "summary",
                ""
            )
        )

        bilgi(
            "Neden: "
            + veri.get(
                "reason",
                ""
            )
        )

        bilgi(
            "FIND bloğu: "
            + str(
                len(
                    veri.get(
                        "find",
                        ""
                    )
                )
            )
            + " karakter"
        )

        bilgi(
            "REPLACE bloğu: "
            + str(
                len(
                    veri.get(
                        "replace",
                        ""
                    )
                )
            )
            + " karakter"
        )

        try:

            uygulama = (
                patch_uygula(
                    veri,
                    workspace,
                    protected_baseline,
                    seen_patch_hashes,
                    target_file
                )
            )

        except Exception as e:

            rejected += 1

            hata(
                "PATCH YEREL GÜVENLİK TARAFINDAN REDDEDİLDİ"
            )

            bilgi(
                str(
                    e
                )
            )

            workspace_geri_yukle(
                backup,
                workspace
            )

            onceki_feedback = (
                "Onceki patch yerel sistem tarafindan reddedildi: "
                + str(
                    e
                )
                + ". Daha kucuk ve kesin patch yap."
            )

            time.sleep(
                2
            )

            continue

        ok(
            "Patch yalnız test çalışma alanına uygulandı."
        )

        bilgi(
            f"Kod farkı: "
            f"+{uygulama['added_lines']} "
            f"/ -{uygulama['removed_lines']} satır"
        )

        # ====================================================
        # PYTHON DERLEME TESTI
        # ====================================================

        baslik(
            "PYTHON DERLEME TESTI"
        )

        compile_ok, compile_results = (
            core.py_compile_test(
                workspace
            )
        )

        for item in compile_results:

            if item[
                "success"
            ]:

                ok(
                    item[
                        "file"
                    ]
                    + " py_compile"
                )

            else:

                hata(
                    item[
                        "file"
                    ]
                    + " py_compile"
                )

                bilgi(
                    item.get(
                        "output",
                        ""
                    )
                )

        if not compile_ok:

            rejected += 1

            test_hatasi = (
                core.test_hatasi_olustur(
                    compile_results,
                    []
                )
            )

            hata(
                "Patch Python derleme testinden geçemedi."
            )

            uyari(
                "Son başarılı test sürümüne geri dönülüyor."
            )

            workspace_geri_yukle(
                backup,
                workspace
            )

            onceki_feedback = (
                "Onceki patch py_compile testinden gecmedi "
                "ve geri alindi:\n"
                + test_hatasi
            )

            time.sleep(
                2
            )

            continue

        # ====================================================
        # DAVRANIS TESTLERI
        # ====================================================

        behavior_ok, behavior_results = (
            core.davranis_testleri(
                workspace
            )
        )

        if not behavior_ok:

            rejected += 1

            test_hatasi = (
                core.test_hatasi_olustur(
                    compile_results,
                    behavior_results
                )
            )

            hata(
                "Patch güvenlik/regresyon testlerinden geçemedi."
            )

            uyari(
                "Son başarılı test sürümüne geri dönülüyor."
            )

            workspace_geri_yukle(
                backup,
                workspace
            )

            onceki_feedback = (
                "Onceki patch guvenlik/regresyon testlerinden "
                "gecmedi ve geri alindi:\n"
                + test_hatasi
            )

            time.sleep(
                2
            )

            continue

        # ====================================================
        # KRITIK KOD
        # ====================================================

        if not protected_ayni_mi(
            workspace,
            protected_baseline
        ):

            rejected += 1

            hata(
                "Kritik güvenlik kodu değişmiş görünüyor."
            )

            workspace_geri_yukle(
                backup,
                workspace
            )

            onceki_feedback = (
                "Kilitli kritik guvenlik koduna dokunuldu. "
                "Bu kisimlari degistirmeden tekrar dene."
            )

            time.sleep(
                2
            )

            continue

        # ====================================================
        # ANA JARVIS BUTUNLUGU
        # ====================================================

        main_ok, integrity = (
            core.hashler_ayni_mi(
                core.ROOT,
                main_hash_before
            )
        )

        if not main_ok:

            hata(
                "ANA JARVIS DOSYALARINDA BEKLENMEDİK DEĞİŞİKLİK!"
            )

            for item in integrity:

                if not item[
                    "unchanged"
                ]:

                    hata(
                        item[
                            "file"
                        ]
                    )

            STOP_EVENT.set()

            break

        # ====================================================
        # KABUL
        # ====================================================

        accepted += 1

        focus_cursor += 1

        baslik(
            f"TUR {toplam_tur} KABUL EDILDI"
        )

        ok(
            "Gerçek Gemini cevabı doğrulandı."
        )

        ok(
            "Patch küçük ve benzersizdi."
        )

        ok(
            "Python derleme testi başarılı."
        )

        ok(
            "Güvenlik/regresyon testleri başarılı."
        )

        ok(
            "Kilitli güvenlik fonksiyonları değişmedi."
        )

        ok(
            "Ana Jarvis dosyaları değişmedi."
        )

        ok(
            "Bu patch yeni test tabanı oldu."
        )

        print()

        bilgi(
            f"Kabul edilen geliştirme: "
            f"{accepted}"
        )

        bilgi(
            f"Reddedilen geliştirme: "
            f"{rejected}"
        )

        bilgi(
            f"Değişiklik gerekmeyen alan: "
            f"{done_count}"
        )

        onceki_feedback = (
            "Onceki patch tum testlerden basariyla gecti. "
            "Ayni degisikligi tekrarlama."
        )

        print()

        uyari(
            "Durdurmak için CTRL + ALT + Q"
        )

        time.sleep(
            2
        )

    # ========================================================
    # DURDURMA
    # ========================================================

    cmd_one_getir()

    baslik(
        "SUREKLI GELISTIRME DURDURULDU"
    )

    diff_path = (
        core.diff_kaydet(
            session_info
        )
    )

    stop_reason = (
        "Kullanıcı durdurdu."
        if STOP_EVENT.is_set()
        else
        "Döngü sona erdi."
    )

    rapor = (
        rapor_kaydet(
            session_info,
            toplam_tur,
            accepted,
            rejected,
            done_count,
            stop_reason,
            main_hash_before
        )
    )

    main_ok, _ = (
        core.hashler_ayni_mi(
            core.ROOT,
            main_hash_before
        )
    )

    if main_ok:

        ok(
            "Ana Jarvis dosyaları hâlâ değiştirilmedi."
        )

    else:

        hata(
            "Ana Jarvis bütünlük kontrolü başarısız."
        )

    print()

    bilgi(
        f"Toplam tur: {toplam_tur}"
    )

    bilgi(
        f"Kabul edilen geliştirme: {accepted}"
    )

    bilgi(
        f"Reddedilen geliştirme: {rejected}"
    )

    bilgi(
        f"Değişiklik gerekmeyen tur: {done_count}"
    )

    print()

    bilgi(
        "Son test sürümü:"
    )

    print(
        workspace
    )

    print()

    bilgi(
        "Tüm değişiklik farkı:"
    )

    print(
        diff_path
    )

    print()

    bilgi(
        "Rapor:"
    )

    print(
        rapor
    )

    print()

    cizgi()

    print(
        "ANA test_jarvis_sessiz.py: DEGISTIRILMEDI"
    )

    print(
        "ANA jarvis_tools.py: DEGISTIRILMEDI"
    )

    print(
        "ANA SURUME OTOMATIK TERFI: KAPALI"
    )

    cizgi()


# ============================================================
# MAIN
# ============================================================

def main():

    ctypes.windll.kernel32.SetConsoleTitleW(
        CONSOLE_TITLE
    )

    hotkey_baslat()

    baslik(
        "JARVIS GORSEL OTONOM GELISTIRICI V6"
    )

    ok(
        "Program çalıştırılınca otomatik başlar."
    )

    ok(
        "Chrome/Gemini gözünüzün önünde çalışır."
    )

    ok(
        "Yazı küçük parçalar halinde ekrana akar."
    )

    ok(
        "53 bin karakter için dakikalarca beklenmez."
    )

    ok(
        "Gemini odağı kaybolursa yanlış pencereye yazmaz."
    )

    ok(
        "Gerçek ↑ Gönder düğmesine tıklanır."
    )

    ok(
        "Cevap request ID ile doğrulanır."
    )

    ok(
        "Kritik güvenlik fonksiyonları kilitlidir."
    )

    ok(
        "Başarısız patch geri alınır."
    )

    ok(
        "Ana Jarvis otomatik değiştirilmez."
    )

    print()

    uyari(
        "DURDURMA TUŞU: CTRL + ALT + Q"
    )

    print()

    adim(
        "Otonom geliştirme otomatik başlatılıyor..."
    )

    surekli_gelistir()


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        STOP_EVENT.set()

        cmd_one_getir()

        print()

        print(
            "Jarvis Developer kullanıcı tarafından durduruldu."
        )

    except Exception as e:

        STOP_EVENT.set()

        cmd_one_getir()

        print()

        hata(
            "JARVIS GORSEL DEVELOPER V6 HATASI"
        )

        print(
            e
        )