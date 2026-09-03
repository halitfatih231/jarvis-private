# -*- coding: utf-8 -*-

import csv
import difflib
import os
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from send2trash import send2trash


# ============================================================
# TEMEL AYARLAR
# ============================================================

HOME = Path.home()

START_MENU_KOKLERI = [
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs",

    Path(
        os.environ.get(
            "PROGRAMDATA",
            r"C:\ProgramData"
        )
    )
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs",
]


ARAMA_KOKLERI = [
    HOME / "Desktop",
    HOME / "Documents",
    HOME / "Downloads",
    HOME / "Pictures",
    HOME / "Videos",
    HOME / "Music",
    HOME / "OneDrive",
    HOME / "Jarvis",
]


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


# ============================================================
# OZEL UYGULAMALAR
# ============================================================

OZEL_UYGULAMALAR = {
    "godot": (
        r"C:\Users\Halit Fatih Böcek\Documents"
        r"\Godot_4.7.1"
        r"\Godot_v4.7.1-stable_win64.exe"
    ),
}


DOGRUDAN_UYGULAMALAR = {
    "not defteri": "notepad.exe",
    "notepad": "notepad.exe",

    "hesap makinesi": "calc.exe",
    "calculator": "calc.exe",

    "dosya gezgini": "explorer.exe",
    "explorer": "explorer.exe",

    "cmd": "cmd.exe",
    "komut istemi": "cmd.exe",

    "powershell": "powershell.exe",

    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",

    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",

    "word": "winword.exe",
    "microsoft word": "winword.exe",

    "powerpoint": "powerpnt.exe",
    "microsoft powerpoint": "powerpnt.exe",

    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
}


PROCESS_ESLEME = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",

    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",

    "word": "winword.exe",
    "microsoft word": "winword.exe",

    "powerpoint": "powerpnt.exe",
    "microsoft powerpoint": "powerpnt.exe",

    "excel": "excel.exe",
    "microsoft excel": "excel.exe",

    "not defteri": "notepad.exe",
    "notepad": "notepad.exe",

    "hesap makinesi": "calculatorapp.exe",

    "godot": "Godot_v4.7.1-stable_win64.exe",
}


KRITIK_SURECLER = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "dwm.exe",
    "winlogon.exe",
    "explorer.exe",
}


ZORLA_KAPATILABILIR = {
    "chrome.exe",
    "msedge.exe",
}


# ============================================================
# GENEL YARDIMCILAR
# ============================================================

def norm(metin):

    metin = str(
        metin
    ).strip().casefold()

    metin = metin.translate(
        str.maketrans({
            "ı": "i",
            "ş": "s",
            "ğ": "g",
            "ü": "u",
            "ö": "o",
            "ç": "c",
        })
    )

    return " ".join(
        metin.split()
    )


def sonuc(
    basarili,
    mesaj,
    veri=None,
    confirmation_required=False
):

    return {
        "success": bool(
            basarili
        ),
        "message": str(
            mesaj
        ),
        "data": veri,
        "confirmation_required":
            bool(confirmation_required),
    }


def gizli_pencere_bayragi():

    return getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0
    )


# ============================================================
# START MENU
# ============================================================

def start_menu_uygulamalari():

    uygulamalar = []

    for kok in START_MENU_KOKLERI:

        if not kok.exists():
            continue

        try:

            for yol in kok.rglob("*"):

                if not yol.is_file():
                    continue

                if yol.suffix.casefold() not in {
                    ".lnk",
                    ".url",
                    ".appref-ms",
                }:
                    continue

                uygulamalar.append(
                    (
                        yol.stem,
                        yol
                    )
                )

        except Exception:
            continue

    return uygulamalar


def start_menu_eslesmesi(
    sorgu
):

    q = norm(
        sorgu
    )

    if not q:
        return None

    en_iyi = None

    for isim, yol in start_menu_uygulamalari():

        isim_n = norm(
            isim
        )

        puan = 0.0

        if q == isim_n:
            puan += 10.0

        if q in isim_n:
            puan += 5.0

        if isim_n in q:
            puan += 2.0

        puan += (
            difflib.SequenceMatcher(
                None,
                q,
                isim_n
            ).ratio()
            * 4.0
        )

        if (
            en_iyi is None
            or puan > en_iyi[0]
        ):

            en_iyi = (
                puan,
                isim,
                yol
            )

    if (
        en_iyi is None
        or en_iyi[0] < 3.0
    ):
        return None

    return en_iyi


# ============================================================
# UYGULAMA AC
# ============================================================

def uygulama_ac(
    uygulama
):

    q = norm(
        uygulama
    )

    if not q:

        return sonuc(
            False,
            "Hangi uygulamayı açacağımı anlayamadım."
        )

    if q in OZEL_UYGULAMALAR:

        yol = Path(
            OZEL_UYGULAMALAR[q]
        )

        if not yol.exists():

            return sonuc(
                False,
                f"{uygulama} için kayıtlı uygulama bulunamadı."
            )

        try:

            subprocess.Popen(
                [str(yol)]
            )

            return sonuc(
                True,
                f"{uygulama} açıldı."
            )

        except Exception as e:

            return sonuc(
                False,
                f"{uygulama} açılamadı: {e}"
            )

    if q in DOGRUDAN_UYGULAMALAR:

        exe = DOGRUDAN_UYGULAMALAR[
            q
        ]

        try:

            subprocess.Popen(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    exe,
                ],
                creationflags=
                    gizli_pencere_bayragi()
            )

            return sonuc(
                True,
                f"{uygulama} açıldı."
            )

        except Exception:
            pass

    exe = shutil.which(
        uygulama
    )

    if exe:

        try:

            subprocess.Popen(
                [exe]
            )

            return sonuc(
                True,
                f"{uygulama} açıldı."
            )

        except Exception as e:

            return sonuc(
                False,
                f"{uygulama} açılamadı: {e}"
            )

    eslesme = start_menu_eslesmesi(
        uygulama
    )

    if eslesme:

        puan, isim, yol = eslesme

        try:

            os.startfile(
                str(yol)
            )

            return sonuc(
                True,
                f"{isim} açıldı.",
                {
                    "match": isim,
                    "path": str(yol),
                    "score": round(
                        puan,
                        2
                    )
                }
            )

        except Exception as e:

            return sonuc(
                False,
                f"{isim} bulundu ama açılamadı: {e}"
            )

    return sonuc(
        False,
        f"{uygulama} uygulamasını bulamadım."
    )


# ============================================================
# CALISAN SURECLER
# ============================================================

def calisan_surecler():

    try:

        cikti = subprocess.check_output(
            [
                "tasklist",
                "/FO",
                "CSV",
                "/NH",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=
                gizli_pencere_bayragi()
        )

    except Exception:

        return []

    surecler = []

    okuyucu = csv.reader(
        cikti.splitlines()
    )

    for satir in okuyucu:

        if satir:

            surecler.append(
                satir[0]
            )

    return surecler


def surec_eslesmesi_bul(
    uygulama
):

    q = norm(
        uygulama
    )

    en_iyi = None

    for surec in calisan_surecler():

        surec_n = norm(
            Path(surec).stem
        )

        puan = (
            difflib.SequenceMatcher(
                None,
                q,
                surec_n
            ).ratio()
        )

        if q == surec_n:
            puan += 2.0

        elif q in surec_n:
            puan += 1.0

        if (
            en_iyi is None
            or puan > en_iyi[0]
        ):

            en_iyi = (
                puan,
                surec
            )

    if (
        en_iyi is None
        or en_iyi[0] < 0.65
    ):

        return None

    return en_iyi[1]


# ============================================================
# UYGULAMA KAPAT
# ============================================================

def uygulama_kapat(
    uygulama
):

    q = norm(
        uygulama
    )

    if not q:

        return sonuc(
            False,
            "Hangi uygulamayı kapatacağımı anlayamadım."
        )

    hedef = PROCESS_ESLEME.get(
        q
    )

    if hedef is None:

        hedef = surec_eslesmesi_bul(
            uygulama
        )

        if hedef is None:

            return sonuc(
                False,
                f"{uygulama} için çalışan bir uygulama bulamadım."
            )

    hedef_lower = hedef.casefold()

    if hedef_lower in KRITIK_SURECLER:

        return sonuc(
            False,
            "Bu Windows sistem sürecini kapatmayacağım."
        )

    try:

        komut = [
            "taskkill",
            "/IM",
            hedef,
            "/T",
        ]

        if hedef_lower in ZORLA_KAPATILABILIR:

            komut.append(
                "/F"
            )

        proc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=
                gizli_pencere_bayragi()
        )

        if proc.returncode == 0:

            return sonuc(
                True,
                f"{uygulama} kapatıldı."
            )

        hata = (
            proc.stderr.strip()
            or proc.stdout.strip()
        )

        return sonuc(
            False,
            f"{uygulama} kapatılamadı. {hata}"
        )

    except Exception as e:

        return sonuc(
            False,
            f"{uygulama} kapatılamadı: {e}"
        )


# ============================================================
# WINDOWS OZEL YERLER
# ============================================================

def geri_donusum_kutusunu_ac():

    try:

        subprocess.Popen(
            [
                "explorer.exe",
                "shell:RecycleBinFolder"
            ]
        )

        return sonuc(
            True,
            "Geri Dönüşüm Kutusu açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Geri Dönüşüm Kutusu açılamadı: {e}"
        )


def windows_ayarlari_ac():

    try:

        os.startfile(
            "ms-settings:"
        )

        return sonuc(
            True,
            "Windows Ayarları açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Windows Ayarları açılamadı: {e}"
        )


def masaustunu_ac():

    return klasor_yolunu_ac(
        HOME / "Desktop",
        "Masaüstü"
    )


def belgeleri_ac():

    return klasor_yolunu_ac(
        HOME / "Documents",
        "Belgeler"
    )


def indirilenleri_ac():

    return klasor_yolunu_ac(
        HOME / "Downloads",
        "İndirilenler"
    )


def klasor_yolunu_ac(
    yol,
    ad
):

    try:

        os.startfile(
            str(yol)
        )

        return sonuc(
            True,
            f"{ad} klasörü açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"{ad} klasörü açılamadı: {e}"
        )


# ============================================================
# WEB
# ============================================================

def web_ara(
    sorgu
):

    sorgu = str(
        sorgu
    ).strip()

    if not sorgu:

        return sonuc(
            False,
            "Aranacak bir konu verilmedi."
        )

    url = (
        "https://www.google.com/search?q="
        + quote_plus(sorgu)
    )

    try:

        webbrowser.open(
            url
        )

        return sonuc(
            True,
            f"{sorgu} için Google araması açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Arama açılamadı: {e}"
        )


def web_sayfasi_ac(
    url
):

    url = str(
        url
    ).strip()

    if not url:

        return sonuc(
            False,
            "Açılacak adres verilmedi."
        )

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):

        url = (
            "https://"
            + url
        )

    try:

        webbrowser.open(
            url
        )

        return sonuc(
            True,
            "Web sayfası açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Web sayfası açılamadı: {e}"
        )


# ============================================================
# PC
# ============================================================

def bilgisayari_kilitle():

    try:

        subprocess.Popen(
            [
                "rundll32.exe",
                "user32.dll,LockWorkStation"
            ]
        )

        return sonuc(
            True,
            "Bilgisayar kilitleniyor."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Bilgisayar kilitlenemedi: {e}"
        )


def bilgisayari_kapat():

    try:

        subprocess.Popen(
            [
                "shutdown",
                "/s",
                "/t",
                "10",
                "/c",
                "Jarvis tarafından kullanıcı isteğiyle kapatılıyor.",
            ],
            creationflags=
                gizli_pencere_bayragi()
        )

        return sonuc(
            True,
            "Bilgisayar 10 saniye içinde kapanacak."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Kapatma işlemi başlatılamadı: {e}"
        )


def bilgisayari_yeniden_baslat():

    try:

        subprocess.Popen(
            [
                "shutdown",
                "/r",
                "/t",
                "10",
                "/c",
                "Jarvis tarafından kullanıcı isteğiyle yeniden başlatılıyor.",
            ],
            creationflags=
                gizli_pencere_bayragi()
        )

        return sonuc(
            True,
            "Bilgisayar 10 saniye içinde yeniden başlayacak."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Yeniden başlatma işlemi başlatılamadı: {e}"
        )


def kapatmayi_iptal_et():

    try:

        proc = subprocess.run(
            [
                "shutdown",
                "/a",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=
                gizli_pencere_bayragi()
        )

        if proc.returncode == 0:

            return sonuc(
                True,
                "Bekleyen kapatma veya yeniden başlatma iptal edildi."
            )

        return sonuc(
            False,
            "İptal edilecek bekleyen kapatma işlemi yok."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Kapatma iptal edilemedi: {e}"
        )


# ============================================================
# GODOT TEST PROJESI
# ============================================================

def godot_test_projesini_ac():

    godot = Path(
        OZEL_UYGULAMALAR[
            "godot"
        ]
    )

    proje = Path(
        r"C:\Users\Halit Fatih Böcek\Documents\Cemil_Jarvis_Test"
    )

    if not godot.exists():

        return sonuc(
            False,
            "Godot çalıştırılabilir dosyası bulunamadı."
        )

    if not proje.exists():

        return sonuc(
            False,
            "Cemil_Jarvis_Test klasörü bulunamadı."
        )

    try:

        subprocess.Popen(
            [
                str(godot),
                "--editor",
                "--path",
                str(proje),
            ]
        )

        return sonuc(
            True,
            "Godot test projesi açıldı."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Godot test projesi açılamadı: {e}"
        )


# ============================================================
# DOSYA ARAMA
# ============================================================

def arama_koklerini_getir():

    kokler = []
    gorulen = set()

    for kok in ARAMA_KOKLERI:

        if not kok.exists():
            continue

        try:
            gercek = kok.resolve()
        except Exception:
            gercek = kok

        anahtar = str(
            gercek
        ).casefold()

        if anahtar in gorulen:
            continue

        gorulen.add(
            anahtar
        )

        kokler.append(
            gercek
        )

    return kokler


def dosya_puani(
    sorgu,
    yol
):

    q = norm(
        sorgu
    )

    ad = norm(
        yol.name
    )

    kok_ad = norm(
        yol.stem
        if yol.is_file()
        else yol.name
    )

    puan = 0.0

    if q == kok_ad:
        puan += 10.0

    if q == ad:
        puan += 9.0

    if q in kok_ad:
        puan += 5.0

    if q in ad:
        puan += 4.0

    q_kelimeler = set(
        q.split()
    )

    ad_kelimeler = set(
        kok_ad.split()
    )

    if q_kelimeler:

        ortak = len(
            q_kelimeler
            & ad_kelimeler
        )

        puan += (
            ortak
            / len(q_kelimeler)
        ) * 4.0

    puan += (
        difflib.SequenceMatcher(
            None,
            q,
            kok_ad
        ).ratio()
        * 3.0
    )

    return puan


def yerel_hedef_bul(
    sorgu
):

    sorgu = str(
        sorgu
    ).strip()

    if not sorgu:

        return None

    # --------------------------------------------------------
    # TAM YOL
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

            return direkt

    except Exception:

        pass

    # --------------------------------------------------------
    # OZEL KLASOR ADLARI
    # --------------------------------------------------------

    ozel = {
        "masaustu":
            HOME / "Desktop",

        "masaustu klasoru":
            HOME / "Desktop",

        "belgeler":
            HOME / "Documents",

        "belgeler klasoru":
            HOME / "Documents",

        "indirilenler":
            HOME / "Downloads",

        "indirilenler klasoru":
            HOME / "Downloads",

        "jarvis":
            HOME / "Jarvis",
    }

    q = norm(
        sorgu
    )

    if q in ozel:

        yol = ozel[q]

        if yol.exists():
            return yol

    # --------------------------------------------------------
    # DOSYA SISTEMINDE ARA
    # --------------------------------------------------------

    en_iyi = None

    for kok in arama_koklerini_getir():

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

            adaylar = []

            for klasor in klasorler:

                adaylar.append(
                    mevcut_path
                    / klasor
                )

            for dosya in dosyalar:

                if dosya.startswith(
                    "~$"
                ):
                    continue

                adaylar.append(
                    mevcut_path
                    / dosya
                )

            for aday in adaylar:

                try:

                    puan = dosya_puani(
                        sorgu,
                        aday
                    )

                except Exception:

                    continue

                if (
                    en_iyi is None
                    or puan > en_iyi[0]
                ):

                    en_iyi = (
                        puan,
                        aday
                    )

    if (
        en_iyi is None
        or en_iyi[0] < 3.5
    ):

        return None

    return en_iyi[1]


# ============================================================
# DOSYA BUL
# ============================================================

def dosya_bul(
    sorgu
):

    yol = yerel_hedef_bul(
        sorgu
    )

    if yol is None:

        return sonuc(
            False,
            f"{sorgu} bulunamadı."
        )

    return sonuc(
        True,
        f"Buldum: {yol.name}",
        {
            "path": str(yol),
            "name": yol.name,
            "is_file": yol.is_file(),
            "is_dir": yol.is_dir(),
        }
    )


# ============================================================
# BULUNDUGU KLASORU AC
# ============================================================

def bulundugu_klasoru_ac(
    sorgu
):

    yol = yerel_hedef_bul(
        sorgu
    )

    if yol is None:

        return sonuc(
            False,
            f"{sorgu} bulunamadı."
        )

    try:

        if yol.is_dir():

            os.startfile(
                str(yol)
            )

        else:

            subprocess.Popen(
                [
                    "explorer.exe",
                    "/select,",
                    str(yol),
                ]
            )

        return sonuc(
            True,
            f"{yol.name} bulunduğu konumda açıldı.",
            {
                "path": str(yol)
            }
        )

    except Exception as e:

        return sonuc(
            False,
            f"Konum açılamadı: {e}"
        )


# ============================================================
# KLASOR OLUSTUR
# ============================================================

def klasor_olustur(
    parent,
    name
):

    parent = str(
        parent
    ).strip()

    name = str(
        name
    ).strip()

    if not name:

        return sonuc(
            False,
            "Oluşturulacak klasörün adı belirtilmedi."
        )

    ana = yerel_hedef_bul(
        parent
    )

    if ana is None:

        return sonuc(
            False,
            f"{parent} klasörü bulunamadı."
        )

    if not ana.is_dir():

        return sonuc(
            False,
            "Yeni klasör yalnızca bir klasörün içinde oluşturulabilir."
        )

    yeni = (
        ana
        / name
    )

    if yeni.exists():

        return sonuc(
            False,
            f"{name} zaten mevcut."
        )

    try:

        yeni.mkdir(
            parents=False,
            exist_ok=False
        )

        return sonuc(
            True,
            f"{name} klasörü oluşturuldu.",
            {
                "path": str(yeni)
            }
        )

    except Exception as e:

        return sonuc(
            False,
            f"Klasör oluşturulamadı: {e}"
        )


# ============================================================
# DOSYA / KLASOR KOPYALA
# ============================================================

def yerel_kopyala(
    source,
    destination,
    confirmed=False
):

    kaynak = yerel_hedef_bul(
        source
    )

    hedef_klasor = yerel_hedef_bul(
        destination
    )

    if kaynak is None:

        return sonuc(
            False,
            f"Kaynak bulunamadı: {source}"
        )

    if hedef_klasor is None:

        return sonuc(
            False,
            f"Hedef klasör bulunamadı: {destination}"
        )

    if not hedef_klasor.is_dir():

        return sonuc(
            False,
            "Kopyalama hedefi bir klasör olmalı."
        )

    hedef = (
        hedef_klasor
        / kaynak.name
    )

    if hedef.exists():

        return sonuc(
            False,
            (
                f"{hedef.name} hedefte zaten var. "
                "Mevcut dosyanın üzerine yazmayı "
                "şimdilik otomatik yapmıyorum."
            )
        )

    try:

        if kaynak.is_dir():

            shutil.copytree(
                kaynak,
                hedef
            )

        else:

            shutil.copy2(
                kaynak,
                hedef
            )

        return sonuc(
            True,
            f"{kaynak.name} kopyalandı.",
            {
                "source": str(kaynak),
                "destination": str(hedef),
            }
        )

    except Exception as e:

        return sonuc(
            False,
            f"Kopyalama başarısız: {e}"
        )


# ============================================================
# DOSYA / KLASOR TASI
# ============================================================

def yerel_tasi(
    source,
    destination,
    confirmed=False
):

    kaynak = yerel_hedef_bul(
        source
    )

    hedef_klasor = yerel_hedef_bul(
        destination
    )

    if kaynak is None:

        return sonuc(
            False,
            f"Kaynak bulunamadı: {source}"
        )

    if hedef_klasor is None:

        return sonuc(
            False,
            f"Hedef klasör bulunamadı: {destination}"
        )

    if not hedef_klasor.is_dir():

        return sonuc(
            False,
            "Taşıma hedefi bir klasör olmalı."
        )

    hedef = (
        hedef_klasor
        / kaynak.name
    )

    if hedef.exists():

        return sonuc(
            False,
            (
                f"{hedef.name} hedefte zaten mevcut. "
                "Üzerine yazma işlemini otomatik yapmıyorum."
            )
        )

    try:

        yeni = shutil.move(
            str(kaynak),
            str(hedef)
        )

        return sonuc(
            True,
            f"{kaynak.name} taşındı.",
            {
                "destination": str(yeni)
            }
        )

    except Exception as e:

        return sonuc(
            False,
            f"Taşıma başarısız: {e}"
        )


# ============================================================
# YENIDEN ADLANDIR
# ============================================================

def yerel_yeniden_adlandir(
    target,
    new_name
):

    yol = yerel_hedef_bul(
        target
    )

    new_name = str(
        new_name
    ).strip()

    if yol is None:

        return sonuc(
            False,
            f"{target} bulunamadı."
        )

    if not new_name:

        return sonuc(
            False,
            "Yeni ad belirtilmedi."
        )

    # Dosyada uzanti belirtilmediyse eskisini koru.
    if (
        yol.is_file()
        and "." not in new_name
        and yol.suffix
    ):

        new_name += (
            yol.suffix
        )

    yeni_yol = (
        yol.parent
        / new_name
    )

    if yeni_yol.exists():

        return sonuc(
            False,
            f"{new_name} adında başka bir öğe zaten var."
        )

    try:

        yol.rename(
            yeni_yol
        )

        return sonuc(
            True,
            f"{yol.name}, {yeni_yol.name} olarak yeniden adlandırıldı.",
            {
                "path": str(yeni_yol)
            }
        )

    except Exception as e:

        return sonuc(
            False,
            f"Yeniden adlandırma başarısız: {e}"
        )


# ============================================================
# GUVENLI SILME
# ============================================================

def yerel_sil(
    target,
    confirmed=False
):

    yol = yerel_hedef_bul(
        target
    )

    if yol is None:

        return sonuc(
            False,
            f"{target} bulunamadı."
        )

    # Ana kullanıcı klasörleri silinemez.
    korunacak = {
        HOME.resolve(),
        (HOME / "Desktop").resolve(),
        (HOME / "Documents").resolve(),
        (HOME / "Downloads").resolve(),
        (HOME / "Jarvis").resolve(),
    }

    try:

        gercek = yol.resolve()

        if gercek in korunacak:

            return sonuc(
                False,
                "Bu ana klasörü silmeyeceğim."
            )

    except Exception:
        pass

    if not confirmed:

        return sonuc(
            False,
            (
                f"{yol.name} Geri Dönüşüm Kutusu'na gönderilecek. "
                "Onaylıyor musunuz?"
            ),
            {
                "target": str(yol),
                "action": "delete_local",
            },
            confirmation_required=True
        )

    try:

        send2trash(
            str(yol)
        )

        return sonuc(
            True,
            f"{yol.name} Geri Dönüşüm Kutusu'na gönderildi."
        )

    except Exception as e:

        return sonuc(
            False,
            f"Silme işlemi başarısız: {e}"
        )


# ============================================================
# ANA ARAC YONETICISI
# ============================================================

def araci_calistir(
    action,
    args=None,
    confirmed=False
):

    args = args or {}

    if not isinstance(
        args,
        dict
    ):

        args = {}

    action = str(
        action
    ).strip()

    # --------------------------------------------------------
    # UYGULAMALAR
    # --------------------------------------------------------

    if action == "open_app":

        return uygulama_ac(
            args.get(
                "app",
                ""
            )
        )

    if action == "close_app":

        return uygulama_kapat(
            args.get(
                "app",
                ""
            )
        )

    # --------------------------------------------------------
    # WINDOWS
    # --------------------------------------------------------

    if action == "open_recycle_bin":

        return geri_donusum_kutusunu_ac()

    if action == "open_settings":

        return windows_ayarlari_ac()

    if action == "open_desktop":

        return masaustunu_ac()

    if action == "open_documents":

        return belgeleri_ac()

    if action == "open_downloads":

        return indirilenleri_ac()

    # --------------------------------------------------------
    # WEB
    # --------------------------------------------------------

    if action == "web_search":

        return web_ara(
            args.get(
                "query",
                ""
            )
        )

    if action == "open_url":

        return web_sayfasi_ac(
            args.get(
                "url",
                ""
            )
        )

    # --------------------------------------------------------
    # PC
    # --------------------------------------------------------

    if action == "lock_pc":

        return bilgisayari_kilitle()

    if action == "shutdown_pc":

        return bilgisayari_kapat()

    if action == "restart_pc":

        return bilgisayari_yeniden_baslat()

    if action == "cancel_shutdown":

        return kapatmayi_iptal_et()

    # --------------------------------------------------------
    # GODOT
    # --------------------------------------------------------

    if action == "open_godot_test":

        return godot_test_projesini_ac()

    # --------------------------------------------------------
    # DOSYA YONETIMI
    # --------------------------------------------------------

    if action == "find_local":

        return dosya_bul(
            args.get(
                "query",
                ""
            )
        )

    if action == "open_parent":

        return bulundugu_klasoru_ac(
            args.get(
                "query",
                ""
            )
        )

    if action == "create_folder":

        return klasor_olustur(
            args.get(
                "parent",
                ""
            ),
            args.get(
                "name",
                ""
            )
        )

    if action == "copy_local":

        return yerel_kopyala(
            args.get(
                "source",
                ""
            ),
            args.get(
                "destination",
                ""
            ),
            confirmed=confirmed
        )

    if action == "move_local":

        return yerel_tasi(
            args.get(
                "source",
                ""
            ),
            args.get(
                "destination",
                ""
            ),
            confirmed=confirmed
        )

    if action == "rename_local":

        return yerel_yeniden_adlandir(
            args.get(
                "target",
                ""
            ),
            args.get(
                "new_name",
                ""
            )
        )

    if action == "delete_local":

        return yerel_sil(
            args.get(
                "target",
                ""
            ),
            confirmed=confirmed
        )

    return sonuc(
        False,
        f"Bilinmeyen Jarvis aracı: {action}"
    )


# ============================================================
# GEMINI'YE VERILECEK ARAC ACIKLAMALARI
# ============================================================

def arac_aciklamalari():

    return """
Kullanabilecegin yerel Jarvis araclari:

open_app
args:
{"app":"uygulama adi"}

Kullanicinin acikca istedigi uygulamayi acar.


close_app
args:
{"app":"uygulama adi"}

Kullanicinin acikca istedigi uygulamayi kapatir.


open_recycle_bin
args:
{}

Geri Donusum Kutusunu acar.


open_settings
args:
{}

Windows Ayarlarini acar.


open_desktop
args:
{}

Masaustu klasorunu acar.


open_documents
args:
{}

Belgeler klasorunu acar.


open_downloads
args:
{}

Indirilenler klasorunu acar.


web_search
args:
{"query":"aranacak konu"}

Google aramasi acar.


open_url
args:
{"url":"https://..."}

Belirli bir web adresini acar.


lock_pc
args:
{}

Kullanici acikca isterse bilgisayari kilitler.


shutdown_pc
args:
{}

Kullanici acikca isterse bilgisayari kapatir.


restart_pc
args:
{}

Kullanici acikca isterse bilgisayari yeniden baslatir.


cancel_shutdown
args:
{}

Bekleyen kapatma veya yeniden baslatmayi iptal eder.


open_godot_test
args:
{}

Cemil_Jarvis_Test projesini Godot ile acar.
Ana Cemil projesine dokunmaz.


find_local
args:
{"query":"dosya veya klasor adi"}

Yerel bilgisayarda dosya veya klasor bulur.


open_parent
args:
{"query":"dosya veya klasor adi"}

Dosyanin bulundugu yeri Dosya Gezgini'nde acar.


create_folder
args:
{
  "parent":"masaustu veya belgeler gibi hedef klasor",
  "name":"yeni klasor adi"
}

Yeni klasor olusturur.


copy_local
args:
{
  "source":"kaynak dosya veya klasor",
  "destination":"hedef klasor"
}

Dosya veya klasoru kopyalar.
Hedefte ayni ad varsa uzerine otomatik yazmaz.


move_local
args:
{
  "source":"kaynak dosya veya klasor",
  "destination":"hedef klasor"
}

Dosya veya klasoru tasir.
Hedefte ayni ad varsa uzerine otomatik yazmaz.


rename_local
args:
{
  "target":"dosya veya klasor",
  "new_name":"yeni ad"
}

Dosya veya klasorun adini degistirir.
Dosya uzantisi soylenmezse mevcut uzanti korunur.


delete_local
args:
{
  "target":"dosya veya klasor"
}

Kalici silme YAPMAZ.
Geri Donusum Kutusu'na gonderir.
Bu arac her zaman kullanicidan onay gerektirir.


ONEMLI KURALLAR:

- Kullanici istemedigi surece hicbir araci calistirma.
- Normal bilgi sorularinda arac kullanma.
- Dosya silme icin mutlaka yerel onay mekanizmasini kullan.
- Kalici silme yapma.
- Parola, API anahtari veya ozel veriyi kendiliginden okuma.
- Ana Cemil Godot projesini degistirme.
- Ucretli Higgsfield islemini kendiliginden baslatma.
"""