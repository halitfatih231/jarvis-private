# -*- coding: utf-8 -*-

import ctypes
import os
import shutil
import subprocess
import time
from pathlib import Path

import pyperclip
from pywinauto import Desktop
from pywinauto.keyboard import send_keys


GEMINI_URL = "https://gemini.google.com/app"

TEST_PROMPT = (
    "Jarvis görsel bağlantı testi. "
    "Sadece şu cümleyi yaz: GÖRSEL BAĞLANTI BAŞARILI"
)

CONSOLE_TITLE = "JARVIS_GEMINI_GORSEL_TEST"


def chrome_bul():

    adaylar = [
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",

        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",

        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
    ]

    for yol in adaylar:

        if yol.exists():
            return str(yol)

    chrome = shutil.which("chrome")

    if chrome:
        return chrome

    raise RuntimeError(
        "Google Chrome bulunamadı."
    )


def gemini_penceresi_bul(timeout=30):

    bitis = time.time() + timeout

    while time.time() < bitis:

        for pencere in Desktop(
            backend="uia"
        ).windows():

            try:

                baslik = (
                    pencere.window_text()
                    or ""
                )

                baslik_kucuk = (
                    baslik.casefold()
                )

                if (
                    "gemini"
                    in baslik_kucuk
                    and
                    "chrome"
                    in baslik_kucuk
                ):

                    return pencere

            except Exception:
                pass

        time.sleep(1)

    raise RuntimeError(
        "Gemini Chrome penceresi bulunamadı."
    )


def prompt_alani_bul(
    pencere,
    timeout=30
):

    iyi_kelime = [
        "prompt",
        "gemini",
        "message",
        "mesaj",
        "istem",
        "sor",
        "ask",
    ]

    kotu_kelime = [
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

    while time.time() < bitis:

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

                ad = (
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

                tam_ad = (
                    ad
                    + " "
                    + ad2
                ).strip()

                kucuk = (
                    tam_ad.casefold()
                )

                if any(
                    kelime
                    in kucuk
                    for kelime
                    in kotu_kelime
                ):
                    continue

                puan = sum(
                    1
                    for kelime
                    in iyi_kelime
                    if kelime
                    in kucuk
                )

                adaylar.append(
                    (
                        puan,
                        kontrol,
                        tam_ad
                    )
                )

            except Exception:
                pass

        if adaylar:

            adaylar.sort(
                key=lambda x: x[0],
                reverse=True
            )

            return adaylar[0][1]

        time.sleep(1)

    raise RuntimeError(
        "Gemini mesaj kutusu otomatik bulunamadı."
    )


def copy_butonlari(
    pencere
):

    bulunan = []

    kelimeler = [
        "copy",
        "kopyala",
    ]

    try:

        butonlar = (
            pencere.descendants(
                control_type="Button"
            )
        )

    except Exception:

        butonlar = []

    for buton in butonlar:

        try:

            ad = (
                buton.window_text()
                or
                buton.element_info.name
                or
                ""
            )

            if any(
                kelime
                in ad.casefold()
                for kelime
                in kelimeler
            ):

                bulunan.append(
                    buton
                )

        except Exception:
            pass

    return bulunan


def cevap_kopyala(
    pencere,
    onceki_sayi,
    timeout=90
):

    bitis = (
        time.time()
        + timeout
    )

    while time.time() < bitis:

        butonlar = (
            copy_butonlari(
                pencere
            )
        )

        if (
            len(butonlar)
            > onceki_sayi
        ):

            son = butonlar[-1]

            son.click_input()

            time.sleep(1)

            cevap = (
                pyperclip.paste()
            )

            if cevap.strip():
                return cevap

        time.sleep(1)

    # Bazı Gemini arayüzlerinde copy butonu
    # farklı erişilebilirlik adıyla görünebilir.
    # Bu durumda test metnini sayfadaki Text
    # kontrollerinden kontrol ediyoruz.

    try:

        for kontrol in pencere.descendants(
            control_type="Text"
        ):

            metin = (
                kontrol.window_text()
                or ""
            )

            if (
                "GÖRSEL BAĞLANTI BAŞARILI"
                in metin.upper()
            ):

                return metin

    except Exception:
        pass

    raise RuntimeError(
        "Gemini yanıtı otomatik alınamadı."
    )


def cmd_one_getir():

    try:

        pencere = Desktop(
            backend="uia"
        ).window(
            title_re=(
                ".*"
                + CONSOLE_TITLE
                + ".*"
            )
        )

        pencere.set_focus()

    except Exception:
        pass


def main():

    ctypes.windll.kernel32.SetConsoleTitleW(
        CONSOLE_TITLE
    )

    print()
    print("=" * 70)
    print("JARVIS → GEMINI GORSEL BAGLANTI TESTI")
    print("=" * 70)

    chrome = chrome_bul()

    print()
    print(
        "→ Chrome açılıyor..."
    )

    subprocess.Popen(
        [
            chrome,
            "--new-tab",
            GEMINI_URL,
        ]
    )

    print(
        "→ Gemini'nin yüklenmesi bekleniyor..."
    )

    pencere = gemini_penceresi_bul()

    pencere.set_focus()

    time.sleep(2)

    print(
        "→ Gemini penceresi bulundu."
    )

    onceki_copy = len(
        copy_butonlari(
            pencere
        )
    )

    print(
        "→ Gemini mesaj kutusu aranıyor..."
    )

    prompt_alani = (
        prompt_alani_bul(
            pencere
        )
    )

    print(
        "→ Mesaj kutusu bulundu."
    )

    pyperclip.copy(
        TEST_PROMPT
    )

    print()
    print(
        "ŞİMDİ GÖZÜNÜ GEMINI EKRANINA BAK:"
    )

    print(
        "Jarvis mesajı kendisi yapıştıracak ve gönderecek."
    )

    time.sleep(2)

    prompt_alani.click_input()

    send_keys(
        "^v"
    )

    time.sleep(1)

    send_keys(
        "{ENTER}"
    )

    print(
        "→ Mesaj Gemini'ye gönderildi."
    )

    print(
        "→ Gemini yanıtı bekleniyor..."
    )

    cevap = cevap_kopyala(
        pencere,
        onceki_copy
    )

    cmd_one_getir()

    print()
    print("=" * 70)
    print("GEMINI'DEN ALINAN CEVAP")
    print("=" * 70)

    print(
        cevap
    )

    print("=" * 70)

    if (
        "GÖRSEL BAĞLANTI BAŞARILI"
        in cevap.upper()
    ):

        print()
        print(
            "[✓] TAM GÖRSEL BAĞLANTI BAŞARILI"
        )

        print()
        print(
            "Chrome → Gemini → mesaj → cevap → CMD zinciri çalışıyor."
        )

    else:

        print()
        print(
            "[!] Gemini'den cevap alındı fakat test cümlesi eşleşmedi."
        )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Test kullanıcı tarafından durduruldu."
        )

    except Exception as e:

        cmd_one_getir()

        print()
        print(
            "[X] TEST HATASI:"
        )

        print(
            e
        )