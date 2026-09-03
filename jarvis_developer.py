# -*- coding: utf-8 -*-

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path


# ============================================================
# TEMEL AYARLAR
# ============================================================

ROOT = Path.home() / "Jarvis"
DEV_ROOT = ROOT / "dev_workspace"
BACKUP_ROOT = ROOT / "developer_backups"

AGY = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"

SOURCE_FILES = [
    "test_jarvis_sessiz.py",
    "jarvis_tools.py",
]

MAX_DENEME = 4
MAX_FILE_CHARS = 220_000
DEVELOPER_LOG = DEV_ROOT / "developer_history.jsonl"

YASAK_YENI_KOD_PARCLARI = [
    "shutil.rmtree(",
    ".unlink(",
    "os.remove(",
    "os.rmdir(",
    "del /f",
    "del /q",
    "rd /s",
    "rmdir /s",
    "format c:",
    "format d:",
    "reg delete",
    "net user",
    "\"runas\"",
    "'runas'",
    "pip install",
    "python -m pip",
    "requests.get(",
    "requests.post(",
    "urllib.request",
    "socket.socket(",
    "eval(",
    "exec(",
    "os.system(",
    "shell=true",
]


# ============================================================
# EKRAN
# ============================================================

def cizgi():
    print("=" * 76)


def baslik(metin):
    print()
    cizgi()
    print(metin)
    cizgi()


def adim(metin):
    print(f"→ {metin}", flush=True)


def bilgi(metin):
    print(f"  {metin}", flush=True)


def basarili(metin):
    print(f"[✓] {metin}", flush=True)


def hata(metin):
    print(f"[X] {metin}", flush=True)


def uyari(metin):
    print(f"[!] {metin}", flush=True)


# ============================================================
# DOSYA / LOG
# ============================================================

def zaman_damgasi():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def log_yaz(event, data=None):
    DEV_ROOT.mkdir(parents=True, exist_ok=True)

    kayit = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "data": data,
    }

    with DEVELOPER_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def dosya_oku(path):
    metin = path.read_text(encoding="utf-8")

    if len(metin) > MAX_FILE_CHARS:
        raise RuntimeError(f"{path.name} geliştirici boyut sınırını aşıyor.")

    return metin


def dosya_yaz(path, metin):
    path.write_text(metin, encoding="utf-8")


def sha256_dosya(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            parca = f.read(1024 * 1024)

            if not parca:
                break

            h.update(parca)

    return h.hexdigest()


def kaynak_hashleri(base):
    sonuc = {}

    for isim in SOURCE_FILES:
        sonuc[isim] = sha256_dosya(base / isim)

    return sonuc


def hashler_ayni_mi(base, onceki):
    sonuclar = []
    tumu_ayni = True

    for isim in SOURCE_FILES:
        simdiki = sha256_dosya(base / isim)
        ayni = simdiki == onceki.get(isim)

        if not ayni:
            tumu_ayni = False

        sonuclar.append({
            "file": isim,
            "unchanged": ayni,
        })

    return tumu_ayni, sonuclar


# ============================================================
# KAYNAKLAR / OTURUM
# ============================================================

def kaynaklari_kontrol_et():
    eksik = []

    for isim in SOURCE_FILES:
        yol = ROOT / isim

        if not yol.exists():
            eksik.append(str(yol))

    if eksik:
        hata("Gerekli Jarvis dosyaları bulunamadı.")

        for yol in eksik:
            print("   -", yol)

        raise SystemExit


def dev_oturumu_olustur():
    DEV_ROOT.mkdir(parents=True, exist_ok=True)

    session = DEV_ROOT / ("session_" + zaman_damgasi())
    workspace = session / "workspace"
    original = session / "original"
    iterations = session / "iterations"

    workspace.mkdir(parents=True, exist_ok=False)
    original.mkdir(parents=True, exist_ok=False)
    iterations.mkdir(parents=True, exist_ok=False)

    for isim in SOURCE_FILES:
        shutil.copy2(ROOT / isim, workspace / isim)
        shutil.copy2(ROOT / isim, original / isim)

    return {
        "session": session,
        "workspace": workspace,
        "original": original,
        "iterations": iterations,
    }


def iterasyon_yedegi(workspace, iterations, numara):
    hedef = iterations / f"before_iteration_{numara}"
    hedef.mkdir(parents=True, exist_ok=False)

    for isim in SOURCE_FILES:
        shutil.copy2(workspace / isim, hedef / isim)


# ============================================================
# ANTIGRAVITY / GEMINI
# ============================================================

def gemini_baslat():
    if not AGY.exists():
        raise RuntimeError(f"Antigravity bulunamadı: {AGY}")

    proc = subprocess.Popen(
        [
            str(AGY),
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--effort", "low",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=str(ROOT),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Antigravity başlatılamadı.")

    return proc


def gemini_mesaj_gonder(proc, metin):
    olay = {
        "event": "user",
        "message": {
            "content": metin
        }
    }

    proc.stdin.write(json.dumps(olay, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def text_delta_bul(obj):
    if isinstance(obj, dict):
        deger = obj.get("text_delta")

        if isinstance(deger, str):
            return deger

        for value in obj.values():
            sonuc = text_delta_bul(value)

            if sonuc:
                return sonuc

    elif isinstance(obj, list):
        for value in obj:
            sonuc = text_delta_bul(value)

            if sonuc:
                return sonuc

    return None


def gemini_cevap_al(proc):
    delta_toplam = ""

    while True:
        satir = proc.stdout.readline()

        if not satir:
            raise RuntimeError("Antigravity oturumu kapandı.")

        try:
            olay = json.loads(satir)
        except json.JSONDecodeError:
            continue

        parca = text_delta_bul(olay)

        if parca:
            delta_toplam += parca

        if olay.get("event") == "result":
            result = olay.get("result", {})

            if result.get("status") != "SUCCESS":
                raise RuntimeError(
                    str(
                        result.get(
                            "error",
                            "Bilinmeyen Gemini hatası."
                        )
                    )
                )

            cevap = str(
                result.get(
                    "response",
                    ""
                )
            ).strip()

            if not cevap:
                cevap = delta_toplam.strip()

            return cevap


# ============================================================
# GEMINI CEVABI
# ============================================================

def dev_json_ayikla(cevap):
    bas = "[[DEV]]"
    son = "[[/DEV]]"

    bas_index = cevap.find(bas)

    if bas_index == -1:
        raise ValueError("Gemini [[DEV]] bloğu döndürmedi.")

    bas_index += len(bas)
    son_index = cevap.find(son, bas_index)

    if son_index == -1:
        raise ValueError("Gemini [[/DEV]] kapanış etiketi döndürmedi.")

    veri = json.loads(
        cevap[
            bas_index:son_index
        ].strip()
    )

    if not isinstance(veri, dict):
        raise ValueError("DEV cevabı JSON nesnesi değil.")

    return veri


def workspace_kodlarini_oku(workspace):
    parcalar = []

    for isim in SOURCE_FILES:
        kod = dosya_oku(
            workspace / isim
        )

        parcalar.append(
            "\n"
            "==================================================\n"
            f"DOSYA: {isim}\n"
            "==================================================\n"
            + kod
        )

    return "\n".join(parcalar)


# ============================================================
# DIFF / STATIK GELISTIRICI GUVENLIGI
# ============================================================

def yeni_eklenen_satirlar(eski, yeni):
    eklenen = []

    for satir in difflib.ndiff(
        eski.splitlines(),
        yeni.splitlines()
    ):
        if satir.startswith("+ "):
            eklenen.append(
                satir[2:]
            )

    return eklenen


def diff_istatistik(eski, yeni):
    eklenen = 0
    silinen = 0

    for satir in difflib.ndiff(
        eski.splitlines(),
        yeni.splitlines()
    ):
        if satir.startswith("+ "):
            eklenen += 1

        elif satir.startswith("- "):
            silinen += 1

    return eklenen, silinen


def kod_guvenli_mi(eski, yeni):
    eklenen_metin = "\n".join(
        yeni_eklenen_satirlar(
            eski,
            yeni
        )
    ).casefold()

    bulunan = []

    for ifade in YASAK_YENI_KOD_PARCLARI:
        if ifade.casefold() in eklenen_metin:
            bulunan.append(ifade)

    if bulunan:
        return (
            False,
            "Yeni eklenen kodda izin verilmeyen ifadeler bulundu: "
            + ", ".join(bulunan)
        )

    return True, ""


def diff_olustur(original, workspace):
    parcalar = []

    for isim in SOURCE_FILES:
        eski = dosya_oku(
            original / isim
        ).splitlines(
            keepends=True
        )

        yeni = dosya_oku(
            workspace / isim
        ).splitlines(
            keepends=True
        )

        fark = difflib.unified_diff(
            eski,
            yeni,
            fromfile=f"original/{isim}",
            tofile=f"workspace/{isim}",
        )

        metin = "".join(fark)

        if metin:
            parcalar.append(metin)

    return "\n".join(parcalar)


def diff_kaydet(session_info):
    diff_path = (
        session_info[
            "session"
        ]
        / "changes.diff"
    )

    diff_path.write_text(
        diff_olustur(
            session_info[
                "original"
            ],
            session_info[
                "workspace"
            ]
        ),
        encoding="utf-8"
    )

    return diff_path


# ============================================================
# DERLEME / AST
# ============================================================

def py_compile_test(base):
    sonuclar = []
    tumu_basarili = True

    for isim in SOURCE_FILES:
        yol = base / isim

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(yol)
            ],
            cwd=str(base),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            ),
        )

        cikti = (
            proc.stderr.strip()
            or proc.stdout.strip()
        )

        ok = (
            proc.returncode == 0
        )

        if not ok:
            tumu_basarili = False

        sonuclar.append({
            "file": isim,
            "success": ok,
            "output": cikti,
        })

    return tumu_basarili, sonuclar


def ast_test(base):
    sonuclar = []
    tumu_basarili = True

    for isim in SOURCE_FILES:
        yol = base / isim

        try:
            ast.parse(
                dosya_oku(yol),
                filename=str(yol)
            )

            sonuclar.append({
                "name": f"{isim} AST",
                "success": True,
                "detail": "Python AST başarıyla oluşturuldu.",
            })

        except Exception as e:
            tumu_basarili = False

            sonuclar.append({
                "name": f"{isim} AST",
                "success": False,
                "detail": str(e),
            })

    return tumu_basarili, sonuclar


# ============================================================
# FONKSIYONLARI IZOLASYONDA TEST ET
# ============================================================

def fonksiyonlari_izole_yukle(
    kaynak_kod,
    fonksiyon_isimleri,
    ekstra_namespace=None
):
    tree = ast.parse(kaynak_kod)
    yeni_body = []

    for node in tree.body:
        if (
            isinstance(
                node,
                ast.FunctionDef
            )
            and node.name
            in fonksiyon_isimleri
        ):
            yeni_body.append(node)

    module = ast.Module(
        body=yeni_body,
        type_ignores=[]
    )

    ast.fix_missing_locations(
        module
    )

    namespace = {}

    if ekstra_namespace:
        namespace.update(
            ekstra_namespace
        )

    exec(
        compile(
            module,
            "<isolated-test>",
            "exec"
        ),
        namespace,
        namespace
    )

    return namespace


# ============================================================
# KAPATMA / GUC GUVENLIK TESTLERI
# ============================================================

def kapatma_guvenlik_testleri(base):
    kaynak = dosya_oku(
        base
        / "test_jarvis_sessiz.py"
    )

    gerekli_fonksiyonlar = {
        "norm",
        "olumsuz_kapatma_ifadesi_mi",
        "acik_bilgisayar_kapatma_istegi_mi",
        "acik_yeniden_baslatma_istegi_mi",
        "acik_kilitleme_istegi_mi",
        "uygulama_adi_metinde_var_mi",
        "son_acilan_uygulama",
        "arac_guvenlik_kontrolu",
        "belirsiz_kapatma_komutu_mi",
    }

    try:
        ns = fonksiyonlari_izole_yukle(
            kaynak,
            gerekli_fonksiyonlar,
            {
                "re": re,
                "unicodedata": unicodedata,
                "son_arac_baglami": None,
            }
        )

    except Exception as e:
        return False, [{
            "name": "Kapatma güvenlik fonksiyonları",
            "success": False,
            "detail": (
                "Fonksiyonlar izole yüklenemedi: "
                + str(e)
            ),
        }]

    testler = []

    def test_ekle(isim, sart, detay):
        testler.append({
            "name": isim,
            "success": bool(sart),
            "detail": detay,
        })

    try:
        belirsiz = ns[
            "belirsiz_kapatma_komutu_mi"
        ]

        shutdown_istegi = ns[
            "acik_bilgisayar_kapatma_istegi_mi"
        ]

        restart_istegi = ns[
            "acik_yeniden_baslatma_istegi_mi"
        ]

        kilit_istegi = ns[
            "acik_kilitleme_istegi_mi"
        ]

        guvenlik = ns[
            "arac_guvenlik_kontrolu"
        ]

        test_ekle(
            '"kapat" belirsiz',
            belirsiz(
                "kapat"
            ) is True,
            "Tek başına kapat araç çalıştırmamalı."
        )

        test_ekle(
            '"hey jarvis kapat" belirsiz',
            belirsiz(
                "hey jarvis kapat"
            ) is True,
            "Hitap içeren belirsiz kapatma da engellenmeli."
        )

        test_ekle(
            '"bilgisayarı kapat" açık güç komutu',
            shutdown_istegi(
                "Bilgisayarı kapat."
            ) is True,
            "Açık PC kapatma niyeti tanınmalı."
        )

        test_ekle(
            '"bilgisayarı kapatsam mı?" güç komutu değil',
            shutdown_istegi(
                "Bilgisayarı kapatsam mı?"
            ) is False,
            "Soru biçimi shutdown olmamalı."
        )

        test_ekle(
            '"bilgisayarı kapatmak istemiyorum" güç komutu değil',
            shutdown_istegi(
                "Bilgisayarı kapatmak istemiyorum."
            ) is False,
            "Olumsuz ifade shutdown olmamalı."
        )

        test_ekle(
            '"bilgisayarı yeniden başlat" açık restart',
            restart_istegi(
                "Bilgisayarı yeniden başlat."
            ) is True,
            "Açık restart niyeti tanınmalı."
        )

        test_ekle(
            '"yeniden başlatsam mı?" restart değil',
            restart_istegi(
                "Bilgisayarı yeniden başlatsam mı?"
            ) is False,
            "Soru biçimi restart olmamalı."
        )

        test_ekle(
            '"bilgisayarı kilitle" açık kilit',
            kilit_istegi(
                "Bilgisayarı kilitle."
            ) is True,
            "Açık kilit niyeti tanınmalı."
        )

        izin, _, _ = guvenlik(
            "kapat",
            "shutdown_pc",
            {}
        )

        test_ekle(
            "Gemini yanlış shutdown üretse bile yerel engel",
            izin is False,
            "Yerel Python güvenlik katmanı belirsiz shutdown'ı reddetmeli."
        )

        izin, _, _ = guvenlik(
            "Bilgisayarı kapatsam mı?",
            "shutdown_pc",
            {}
        )

        test_ekle(
            "Shutdown sorusu yerel olarak reddediliyor",
            izin is False,
            "Soru cümlesi gerçek shutdown başlatmamalı."
        )

        izin, _, _ = guvenlik(
            "Bilgisayarı kapat.",
            "shutdown_pc",
            {}
        )

        test_ekle(
            "Açık shutdown komutu yerel kapıdan geçiyor",
            izin is True,
            "Açık kullanıcı komutu engellenmemeli."
        )

        izin, _, _ = guvenlik(
            "Chrome'u kapat.",
            "close_app",
            {
                "app": "chrome"
            }
        )

        test_ekle(
            "Açık Chrome kapatma yalnız Chrome'a izin veriyor",
            izin is True,
            "Uygulama adı açıkça söylendiğinde hedefli kapatma kabul edilmeli."
        )

        izin, _, _ = guvenlik(
            "Chrome'u kapatma.",
            "close_app",
            {
                "app": "chrome"
            }
        )

        test_ekle(
            '"Chrome\'u kapatma" engelleniyor',
            izin is False,
            "Olumsuz komut uygulama kapatmamalı."
        )

        izin, _, _ = guvenlik(
            "her şeyi kapat",
            "close_app",
            {
                "app": "chrome"
            }
        )

        test_ekle(
            "Toplu kapatma close_app olarak reddediliyor",
            izin is False,
            "Her şeyi kapat ifadesi tek uygulamaya tahmin edilmemeli."
        )

        izin, _, _ = guvenlik(
            "Firefox'u kapat.",
            "close_app",
            {
                "app": "chrome"
            }
        )

        test_ekle(
            "Gemini yanlış uygulama hedefi seçerse engelleniyor",
            izin is False,
            "Kullanıcının söylemediği uygulama kapatılmamalı."
        )

        ns[
            "son_arac_baglami"
        ] = None

        izin, _, _ = guvenlik(
            "Onu kapat.",
            "close_app",
            {
                "app": "chrome"
            }
        )

        test_ekle(
            '"Onu kapat" bağlamsızken engelleniyor',
            izin is False,
            "Önceki açık hedef yoksa zamirle kapatma yapılmamalı."
        )

    except Exception as e:
        testler.append({
            "name": "Kapatma/güç davranış testi",
            "success": False,
            "detail": str(e),
        })

    return (
        all(
            item[
                "success"
            ]
            for item in testler
        ),
        testler
    )


# ============================================================
# SILME GUVENLIK TESTLERI
# ============================================================

def silme_guvenlik_testleri(base):
    kaynak = dosya_oku(
        base
        / "jarvis_tools.py"
    )

    gerekli = {
        "sonuc",
        "yerel_sil"
    }

    testler = []

    try:
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)

            hedef = (
                temp_root
                / "jarvis_delete_test.txt"
            )

            hedef.write_text(
                "test",
                encoding="utf-8"
            )

            trash_calls = []

            def fake_bul(sorgu):
                p = Path(sorgu)

                return (
                    p
                    if p.exists()
                    else None
                )

            def fake_send2trash(path):
                trash_calls.append(
                    str(path)
                )

            ns = fonksiyonlari_izole_yukle(
                kaynak,
                gerekli,
                {
                    "Path": Path,
                    "HOME": (
                        temp_root
                        / "fake_home"
                    ),
                    "yerel_hedef_bul": fake_bul,
                    "send2trash": fake_send2trash,
                }
            )

            yerel_sil = ns[
                "yerel_sil"
            ]

            sonuc1 = yerel_sil(
                str(hedef),
                confirmed=False
            )

            testler.append({
                "name": "Silme onaysız gerçekleşmiyor",
                "success": (
                    sonuc1.get(
                        "confirmation_required"
                    ) is True
                    and hedef.exists()
                    and len(
                        trash_calls
                    ) == 0
                ),
                "detail": (
                    "İlk çağrı sadece "
                    "EVET/HAYIR onayı istemeli."
                ),
            })

            sonuc2 = yerel_sil(
                str(hedef),
                confirmed=True
            )

            testler.append({
                "name": "Onaylı silme sadece send2trash çağırıyor",
                "success": (
                    sonuc2.get(
                        "success"
                    ) is True
                    and len(
                        trash_calls
                    ) == 1
                    and Path(
                        trash_calls[
                            0
                        ]
                    ) == hedef
                    and hedef.exists()
                ),
                "detail": (
                    "Testte send2trash sahtedir; "
                    "gerçek dosya silinmez."
                ),
            })

    except Exception as e:
        testler.append({
            "name": "Silme güvenlik testi",
            "success": False,
            "detail": str(e),
        })

    return (
        all(
            item[
                "success"
            ]
            for item in testler
        ),
        testler
    )


# ============================================================
# STATIK KORUMA / REGRESYON TESTLERI
# ============================================================

def statik_guvenlik_testleri(base):
    main_kod = dosya_oku(
        base
        / "test_jarvis_sessiz.py"
    )

    tools_kod = dosya_oku(
        base
        / "jarvis_tools.py"
    )

    testler = []

    def ekle(
        isim,
        sart,
        detay
    ):
        testler.append({
            "name": isim,
            "success": bool(sart),
            "detail": detay,
        })

    ekle(
        "Yerel kritik tool güvenlik kapısı mevcut",
        "def arac_guvenlik_kontrolu" in main_kod,
        "Gemini araç üretse bile ikinci Python kontrolü bulunmalı."
    )

    ekle(
        "Belirsiz kapatma yerel engeli mevcut",
        "def belirsiz_kapatma_komutu_mi" in main_kod,
        "Tek başına kapat doğrudan modele bırakılmamalı."
    )

    ekle(
        "Kalıcı hafıza dosyası korunuyor",
        "jarvis_memory.json" in main_kod,
        "Jarvis'in kalıcı hafıza sistemi kaybolmamalı."
    )

    ekle(
        "Geçmiş dosyası korunuyor",
        "jarvis_history.jsonl" in main_kod,
        "Konuşma geçmişi mekanizması kaybolmamalı."
    )

    ekle(
        "Dosya takma adı desteği korunuyor",
        "file_aliases" in main_kod,
        "Kullanıcının dosya takma adları korunmalı."
    )

    ekle(
        "Tool-result geri bildirimi korunuyor",
        "YEREL_SISTEM_BILDIRIMI" in main_kod,
        "Yerel işlem sonucu aynı Gemini oturumuna geri bildirilmelidir."
    )

    ekle(
        "Silme onay parametresi korunuyor",
        "confirmation_required=True" in tools_kod,
        "Silme ilk çağrıda onay istemeli."
    )

    ekle(
        "Geri Dönüşüm Kutusu sistemi korunuyor",
        "send2trash" in tools_kod,
        "Kalıcı silme yerine send2trash bulunmalı."
    )

    ekle(
        "Kritik Windows süreç listesi mevcut",
        "KRITIK_SURECLER" in tools_kod,
        "Sistem süreçleri korunmalı."
    )

    ekle(
        "Cemil test projesi sınırı mevcut",
        "Cemil_Jarvis_Test" in tools_kod,
        "Godot işlemleri ana Cemil projesine yönelmemeli."
    )

    ekle(
        "Godot güvenlik sınırı korunuyor",
        (
            "yeni-oyun-projesi"
            in tools_kod
            or "Cemil_Jarvis_Test"
            in tools_kod
        ),
        "Godot test sınırı kaybolmamalı."
    )

    return (
        all(
            item[
                "success"
            ]
            for item in testler
        ),
        testler
    )


# ============================================================
# DAVRANIS TEST PAKETI
# ============================================================

def davranis_testleri(
    base,
    baslik_yaz=True
):
    tum_sonuclar = []
    toplam_basarili = True

    if baslik_yaz:
        baslik(
            "OTOMATIK DAVRANIS / REGRESYON TESTLERI"
        )

    paketler = [
        (
            "AST / yapı",
            ast_test
        ),
        (
            "Kapatma ve güç güvenliği",
            kapatma_guvenlik_testleri
        ),
        (
            "Silme güvenliği",
            silme_guvenlik_testleri
        ),
        (
            "Statik korumalar",
            statik_guvenlik_testleri
        ),
    ]

    for paket_adi, fonksiyon in paketler:
        adim(
            paket_adi
            + " testleri çalışıyor..."
        )

        try:
            paket_ok, sonuclar = (
                fonksiyon(base)
            )

        except Exception as e:
            paket_ok = False

            sonuclar = [{
                "name": paket_adi,
                "success": False,
                "detail": str(e),
            }]

        if not paket_ok:
            toplam_basarili = False

        for item in sonuclar:
            tum_sonuclar.append(
                item
            )

            if item[
                "success"
            ]:
                basarili(
                    item[
                        "name"
                    ]
                )

            else:
                hata(
                    item[
                        "name"
                    ]
                )

                bilgi(
                    item.get(
                        "detail",
                        ""
                    )
                )

    basarili_sayi = sum(
        1
        for item in tum_sonuclar
        if item[
            "success"
        ]
    )

    toplam_sayi = len(
        tum_sonuclar
    )

    print()

    if toplam_basarili:
        basarili(
            f"Davranış/regresyon testleri: "
            f"{basarili_sayi}/{toplam_sayi}"
        )

    else:
        hata(
            f"Davranış/regresyon testleri: "
            f"{basarili_sayi}/{toplam_sayi}"
        )

    return (
        toplam_basarili,
        tum_sonuclar
    )


# ============================================================
# GELISTIRICI TALIMATI
# ============================================================

DEVELOPER_SYSTEM = r"""
Sen Jarvis'in kontrollu yazilim gelistirme ajanisin.

Amacin Jarvis'in:
- guvenligini
- kararliligini
- dogal dil anlayisini
- Windows araclarini
- kullanici deneyimini

kucuk ve test edilebilir adimlarla iyilestirmektir.

KESIN KURALLAR:

1. Sadece test_jarvis_sessiz.py veya jarvis_tools.py
dosyalarindan BIRINI degistir.

2. Her turda sadece bir dosya degistir.

3. Buyuk yeniden yazim yapma.

4. Mevcut calisan ozellikleri bozma.

5. Kapatma guvenliklerini zayiflatma.

6. "kapat" tek basina bilgisayar, uygulama veya
pencere kapatmamali.

7. Bilgisayar kapatma/restart/kilit ancak acik
kullanici niyetiyle calismali.

8. Dosya silme kalici olmamali;
send2trash + EVET/HAYIR onayi korunmali.

9. Cemil ana Godot projesine dokunma;
Cemil_Jarvis_Test sinirini koru.

10. Sifre, API anahtari, tarayici kimlik bilgisi
veya gizli veri arayan ozellik ekleme.

11. Internetten kod indirme, paket kurma veya
UAC atlatma ozelligi ekleme.

12. Geri donulemez silme ekleme.

13. Ana Jarvis'e otomatik kurulum/promotion
kodu ekleme.

14. Test hatasi verilirse once o hatayi duzelt.

15. Gereksiz degisiklik yapma; yeterliyse DONE de.

16. Degisiklikte hedef dosyanin TAMAMINI dondur.

17. Gizli dusunce surecini yazma.
Sadece kisa "summary" ve "reason" ver.

CEVAP FORMATI:

[[DEV]]
{
  "status": "change",
  "target_file": "jarvis_tools.py",
  "summary": "Kisa gelistirme ozeti",
  "reason": "Kisa gerekce",
  "content": "HEDEF DOSYANIN TAM ICERIGI"
}
[[/DEV]]

veya:

[[DEV]]
{
  "status": "done",
  "summary": "Gelistirme yeterli durumda",
  "reason": "Yeni degisiklik gerekmiyor"
}
[[/DEV]]

Baska hicbir sey yazma.
""".strip()


def ilk_gelistirme_istegi(
    hedef,
    workspace
):
    return f"""
{DEVELOPER_SYSTEM}

KULLANICI HEDEFI:
{hedef}

MEVCUT TEST KODLARI:
{workspace_kodlarini_oku(workspace)}

GOREV:
En faydali KUCK, GUVENLI ve TEST EDILEBILIR
iyilestirmeyi sec.

Zorunlu [[DEV]] JSON formatinda cevap ver.
""".strip()


def hata_duzeltme_istegi(
    hata_metni,
    workspace
):
    return f"""
{DEVELOPER_SYSTEM}

ONCEKI DEGISTIRME TESTTEN GECMEDI.

TEST HATASI:
{hata_metni}

GUNCEL TEST KODLARI:
{workspace_kodlarini_oku(workspace)}

GOREV:
Hatayi guvenligi zayiflatmadan duzelt.

Sadece bir dosyayi degistir.

Zorunlu [[DEV]] JSON formatinda cevap ver.
""".strip()


def sonraki_iyilestirme_istegi(
    hedef,
    workspace
):
    return f"""
{DEVELOPER_SYSTEM}

Onceki gelistirme tum yerel testlerden gecti.

KULLANICI HEDEFI:
{hedef}

GUNCEL KOD:
{workspace_kodlarini_oku(workspace)}

GOREV:
Bir sonraki kucuk ve guvenli gelistirme
gercekten faydaliysa yap.

Gereksizse status=done dondur.
""".strip()


# ============================================================
# GEMINI DEGISIKLIGINI UYGULA
# ============================================================

def degisikligi_uygula(
    veri,
    workspace
):
    durum = str(
        veri.get(
            "status",
            ""
        )
    ).strip().casefold()

    if durum == "done":
        return {
            "done": True,
            "changed": False,
            "summary": str(
                veri.get(
                    "summary",
                    "Geliştirme tamamlandı."
                )
            ),
            "reason": str(
                veri.get(
                    "reason",
                    ""
                )
            ),
        }

    if durum != "change":
        raise ValueError(
            "DEV status yalnızca change veya done olabilir."
        )

    hedef = str(
        veri.get(
            "target_file",
            ""
        )
    ).strip()

    if hedef not in SOURCE_FILES:
        raise ValueError(
            "İzin verilmeyen hedef dosya: "
            + hedef
        )

    content = veri.get(
        "content"
    )

    if (
        not isinstance(
            content,
            str
        )
        or not content.strip()
    ):
        raise ValueError(
            "Tam dosya içeriği bulunamadı."
        )

    if len(content) > MAX_FILE_CHARS:
        raise ValueError(
            "Yeni dosya izin verilen boyuttan büyük."
        )

    hedef_yol = (
        workspace
        / hedef
    )

    eski = dosya_oku(
        hedef_yol
    )

    guvenli, neden = kod_guvenli_mi(
        eski,
        content
    )

    if not guvenli:
        raise ValueError(
            neden
        )

    eklenen, silinen = (
        diff_istatistik(
            eski,
            content
        )
    )

    dosya_yaz(
        hedef_yol,
        content
    )

    return {
        "done": False,
        "changed": True,
        "target": hedef,
        "summary": str(
            veri.get(
                "summary",
                ""
            )
        ),
        "reason": str(
            veri.get(
                "reason",
                ""
            )
        ),
        "added_lines": eklenen,
        "removed_lines": silinen,
    }


def test_hatasi_olustur(
    compile_results,
    behavior_results
):
    sorunlar = []

    for item in compile_results:
        if not item.get(
            "success"
        ):
            sorunlar.append(
                item.get(
                    "file",
                    "?"
                )
                + " py_compile:\n"
                + item.get(
                    "output",
                    ""
                )
            )

    for item in behavior_results:
        if not item.get(
            "success"
        ):
            sorunlar.append(
                item.get(
                    "name",
                    "Davranış testi"
                )
                + ":\n"
                + item.get(
                    "detail",
                    ""
                )
            )

    return "\n\n".join(
        sorunlar
    )


# ============================================================
# GELISTIRME DONGUSU
# ============================================================

def gelistir(hedef):
    kaynaklari_kontrol_et()

    ana_hash_once = kaynak_hashleri(
        ROOT
    )

    session_info = (
        dev_oturumu_olustur()
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

    baslik(
        "JARVIS DEVELOPER V3 - CANLI GUVENLI GELISTIRME"
    )

    bilgi(
        "Ana Jarvis dosyaları: KORUMALI"
    )

    bilgi(
        "Geliştirme alanı: "
        + str(workspace)
    )

    bilgi(
        "Maksimum tur: "
        + str(MAX_DENEME)
    )

    bilgi(
        "Gerçek PC kapatma testi: YOK"
    )

    bilgi(
        "Gerçek uygulama kapatma testi: YOK"
    )

    bilgi(
        "Gerçek dosya silme testi: YOK"
    )

    bilgi(
        "Ana sürüme geçiş: SADECE TEST + EVET SONRASI"
    )

    log_yaz(
        "session_started",
        {
            "session": str(
                session_info[
                    "session"
                ]
            ),
            "goal": hedef,
        }
    )

    gemini = gemini_baslat()

    islemler = []
    son_compile = []
    son_behavior = []
    genel_ok = False

    try:
        prompt = ilk_gelistirme_istegi(
            hedef,
            workspace
        )

        for deneme in range(
            1,
            MAX_DENEME + 1
        ):
            baslik(
                f"GELISTIRME TURU "
                f"{deneme}/{MAX_DENEME}"
            )

            iterasyon_yedegi(
                workspace,
                iterations,
                deneme
            )

            adim(
                "Gemini mevcut Jarvis kodunu inceliyor..."
            )

            baslangic = (
                time.perf_counter()
            )

            gemini_mesaj_gonder(
                gemini,
                prompt
            )

            cevap = gemini_cevap_al(
                gemini
            )

            bilgi(
                f"Gemini cevabı "
                f"{time.perf_counter() - baslangic:.1f} "
                f"saniyede geldi."
            )

            try:
                veri = dev_json_ayikla(
                    cevap
                )

                uygulama = degisikligi_uygula(
                    veri,
                    workspace
                )

            except Exception as e:
                red = (
                    "Geliştirici cevabı reddedildi: "
                    + str(e)
                )

                hata(red)

                islemler.append({
                    "iteration": deneme,
                    "status": "rejected",
                    "error": red,
                })

                prompt = hata_duzeltme_istegi(
                    red,
                    workspace
                )

                continue

            if uygulama.get(
                "done"
            ):
                basarili(
                    "Gemini yeni değişiklik gerekmiyor dedi."
                )

                bilgi(
                    "Karar: "
                    + uygulama.get(
                        "summary",
                        ""
                    )
                )

                if uygulama.get(
                    "reason"
                ):
                    bilgi(
                        "Gerekçe: "
                        + uygulama.get(
                            "reason",
                            ""
                        )
                    )

                adim(
                    "Son py_compile testi..."
                )

                compile_ok, son_compile = (
                    py_compile_test(
                        workspace
                    )
                )

                if compile_ok:
                    basarili(
                        "py_compile başarılı."
                    )

                else:
                    hata(
                        "py_compile başarısız."
                    )

                behavior_ok, son_behavior = (
                    davranis_testleri(
                        workspace
                    )
                )

                genel_ok = (
                    compile_ok
                    and behavior_ok
                )

                break

            basarili(
                "Gemini bir geliştirme seçti."
            )

            bilgi(
                "Hedef dosya: "
                + uygulama.get(
                    "target",
                    ""
                )
            )

            bilgi(
                "Ne değişiyor: "
                + uygulama.get(
                    "summary",
                    ""
                )
            )

            bilgi(
                "Neden: "
                + uygulama.get(
                    "reason",
                    ""
                )
            )

            bilgi(
                f"Kod farkı: "
                f"+{uygulama.get('added_lines', 0)} "
                f"/ -{uygulama.get('removed_lines', 0)} satır"
            )

            islemler.append({
                "iteration": deneme,
                "status": "changed",
                "target": uygulama.get(
                    "target"
                ),
                "summary": uygulama.get(
                    "summary"
                ),
                "reason": uygulama.get(
                    "reason"
                ),
                "added_lines": uygulama.get(
                    "added_lines"
                ),
                "removed_lines": uygulama.get(
                    "removed_lines"
                ),
            })

            adim(
                "Python sözdizimi testi çalışıyor..."
            )

            compile_ok, son_compile = (
                py_compile_test(
                    workspace
                )
            )

            for item in son_compile:
                if item[
                    "success"
                ]:
                    basarili(
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
                prompt = hata_duzeltme_istegi(
                    test_hatasi_olustur(
                        son_compile,
                        []
                    ),
                    workspace
                )

                uyari(
                    "Derleme hatası Gemini'ye geri gönderiliyor."
                )

                continue

            behavior_ok, son_behavior = (
                davranis_testleri(
                    workspace
                )
            )

            if not behavior_ok:
                prompt = hata_duzeltme_istegi(
                    test_hatasi_olustur(
                        son_compile,
                        son_behavior
                    ),
                    workspace
                )

                uyari(
                    "Davranış testi hatası Gemini'ye geri gönderiliyor."
                )

                continue

            baslik(
                f"TUR {deneme} BASARILI"
            )

            basarili(
                "Kod derleniyor."
            )

            basarili(
                "Güvenlik/regresyon testleri geçildi."
            )

            basarili(
                "Ana Jarvis'e hiçbir şey yazılmadı."
            )

            genel_ok = True

            if deneme < MAX_DENEME:
                adim(
                    "Bir sonraki küçük geliştirme için "
                    "Gemini'ye tekrar sorulacak."
                )

                prompt = sonraki_iyilestirme_istegi(
                    hedef,
                    workspace
                )

            else:
                break

        else:
            compile_ok, son_compile = (
                py_compile_test(
                    workspace
                )
            )

            behavior_ok, son_behavior = (
                davranis_testleri(
                    workspace
                )
            )

            genel_ok = (
                compile_ok
                and behavior_ok
            )

        baslik(
            "ANA JARVIS DOSYALARI KONTROLU"
        )

        kaynaklar_ayni, source_integrity = (
            hashler_ayni_mi(
                ROOT,
                ana_hash_once
            )
        )

        for item in source_integrity:
            if item[
                "unchanged"
            ]:
                basarili(
                    item[
                        "file"
                    ]
                    + " değiştirilmedi."
                )

            else:
                hata(
                    item[
                        "file"
                    ]
                    + " beklenmedik şekilde değişti!"
                )

        if not kaynaklar_ayni:
            genel_ok = False

        return {
            "success": genel_ok,
            "session_info": session_info,
            "iterations": islemler,
            "compile_results": son_compile,
            "behavior_results": son_behavior,
            "source_integrity": source_integrity,
            "main_hash_before": ana_hash_once,
        }

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


# ============================================================
# TERFI ONCESI SON KONTROL
# ============================================================

def son_terfi_oncesi_kontrol(
    workspace
):
    baslik(
        "TERFI ONCESI SON KONTROL"
    )

    compile_ok, compile_results = (
        py_compile_test(
            workspace
        )
    )

    if compile_ok:
        basarili(
            "Test sürümü py_compile testinden geçti."
        )

    else:
        hata(
            "Test sürümü py_compile testinden geçemedi."
        )

    behavior_ok, behavior_results = (
        davranis_testleri(
            workspace
        )
    )

    return (
        compile_ok
        and behavior_ok,
        compile_results,
        behavior_results,
    )


# ============================================================
# YEDEK
# ============================================================

def promotion_yedegi_olustur():
    BACKUP_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    backup = (
        BACKUP_ROOT
        / (
            "before_promotion_"
            + zaman_damgasi()
        )
    )

    backup.mkdir(
        parents=True,
        exist_ok=False
    )

    for isim in SOURCE_FILES:
        shutil.copy2(
            ROOT / isim,
            backup / isim
        )

    metadata = {
        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "files": {
            isim:
                sha256_dosya(
                    backup
                    / isim
                )

            for isim
            in SOURCE_FILES
        }
    }

    (
        backup
        / "backup_info.json"
    ).write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return backup


# ============================================================
# ATOMIK KOPYALAMA
# ============================================================

def atomik_kopyala(
    kaynak,
    hedef
):
    temp = hedef.with_name(
        hedef.name
        + ".jarvis_new"
    )

    if temp.exists():
        temp.unlink()

    shutil.copy2(
        kaynak,
        temp
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(temp)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        ),
    )

    if proc.returncode != 0:
        try:
            temp.unlink()

        except Exception:
            pass

        raise RuntimeError(
            f"{hedef.name} geçici kopyası derlenemedi: "
            + (
                proc.stderr.strip()
                or proc.stdout.strip()
            )
        )

    os.replace(
        temp,
        hedef
    )


# ============================================================
# GERI DONUS
# ============================================================

def yedekten_geri_don(
    backup
):
    baslik(
        "OTOMATIK GERI DONUS"
    )

    for isim in SOURCE_FILES:
        shutil.copy2(
            backup / isim,
            ROOT / isim
        )

        basarili(
            isim
            + " eski sürüme döndürüldü."
        )

    compile_ok, _ = (
        py_compile_test(
            ROOT
        )
    )

    if compile_ok:
        basarili(
            "Geri yüklenen ana sürüm "
            "py_compile testinden geçti."
        )

    else:
        hata(
            "UYARI: Geri yüklenen sürüm "
            "py_compile testinden geçemedi."
        )

    return compile_ok


# ============================================================
# GUVENLI TERFI
# ============================================================

def guvenli_terfi(
    workspace,
    beklenen_main_hash
):
    baslik(
        "GUVENLI ANA SURUME TERFI"
    )

    main_ayni, durum = hashler_ayni_mi(
        ROOT,
        beklenen_main_hash
    )

    if not main_ayni:
        hata(
            "Ana Jarvis dosyaları geliştirme sırasında değişmiş."
        )

        bilgi(
            "Çakışma riski nedeniyle terfi iptal edildi."
        )

        for item in durum:
            if not item[
                "unchanged"
            ]:
                bilgi(
                    "Değişen dosya: "
                    + item[
                        "file"
                    ]
                )

        return False, None

    kontrol_ok, _, _ = (
        son_terfi_oncesi_kontrol(
            workspace
        )
    )

    if not kontrol_ok:
        hata(
            "Son kontrol başarısız. "
            "Ana sürüme geçiş iptal edildi."
        )

        return False, None

    print()

    uyari(
        "Şimdiye kadar ANA Jarvis hâlâ değiştirilmedi."
    )

    print()
    print(
        "Test sürümünü ana Jarvis'e geçirmek istiyorsanız:"
    )
    print()
    print(
        "EVET"
    )
    print()
    print(
        "Başka herhangi bir cevap terfiyi iptal eder."
    )
    print()

    cevap = input(
        "Ana sürüme geçirilsin mi? "
    ).strip().casefold()

    if cevap != "evet":
        uyari(
            "Ana sürüme geçiş kullanıcı tarafından iptal edildi."
        )

        return False, None

    backup = promotion_yedegi_olustur()

    basarili(
        "Ana sürüm yedeği oluşturuldu:"
    )

    print(
        backup
    )

    try:
        adim(
            "Test sürümü ana Jarvis'e atomik olarak aktarılıyor..."
        )

        for isim in SOURCE_FILES:
            atomik_kopyala(
                workspace / isim,
                ROOT / isim
            )

            basarili(
                isim
                + " aktarıldı."
            )

        baslik(
            "TERFI SONRASI ANA SURUM TESTI"
        )

        compile_ok, compile_results = (
            py_compile_test(
                ROOT
            )
        )

        if compile_ok:
            basarili(
                "Ana sürüm py_compile testinden geçti."
            )

        else:
            hata(
                "Ana sürüm py_compile testinden geçemedi."
            )

        behavior_ok, behavior_results = (
            davranis_testleri(
                ROOT
            )
        )

        if (
            compile_ok
            and behavior_ok
        ):
            basarili(
                "TERFI BASARILI."
            )

            basarili(
                "Yeni sürüm ana Jarvis oldu."
            )

            return True, {
                "backup": str(
                    backup
                ),
                "compile_results":
                    compile_results,
                "behavior_results":
                    behavior_results,
            }

        hata(
            "Terfi sonrası test başarısız."
        )

        uyari(
            "Eski sürüm otomatik geri yüklenecek."
        )

        yedekten_geri_don(
            backup
        )

        return False, {
            "backup": str(
                backup
            ),
            "rolled_back": True,
        }

    except Exception as e:
        hata(
            "Terfi sırasında hata: "
            + str(e)
        )

        uyari(
            "Eski sürüm otomatik geri yüklenecek."
        )

        try:
            yedekten_geri_don(
                backup
            )

        except Exception as geri_hata:
            hata(
                "GERI DONUS HATASI: "
                + str(
                    geri_hata
                )
            )

        return False, {
            "backup": str(
                backup
            ),
            "rolled_back": True,
            "error": str(e),
        }


# ============================================================
# RAPOR
# ============================================================

def rapor_yaz(
    session_info,
    hedef,
    gelistirme_sonucu,
    promotion_result=None
):
    rapor = {
        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "goal":
            hedef,

        "development_success":
            gelistirme_sonucu[
                "success"
            ],

        "iterations":
            gelistirme_sonucu[
                "iterations"
            ],

        "compile_results":
            gelistirme_sonucu[
                "compile_results"
            ],

        "behavior_results":
            gelistirme_sonucu[
                "behavior_results"
            ],

        "main_source_integrity":
            gelistirme_sonucu[
                "source_integrity"
            ],

        "promotion":
            promotion_result,
    }

    rapor_path = (
        session_info[
            "session"
        ]
        / "developer_report.json"
    )

    rapor_path.write_text(
        json.dumps(
            rapor,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return rapor_path


# ============================================================
# MAIN
# ============================================================

def main():
    baslik(
        "JARVIS DEVELOPER V3 - "
        "GELISTIR + TEST ET + GUVENLI TERFI"
    )

    basarili(
        "Geliştirme yalnız dev_workspace içinde başlar."
    )

    basarili(
        "Canlı geliştirme özeti ekranda gösterilir."
    )

    basarili(
        "py_compile + AST + güvenlik/regresyon testleri vardır."
    )

    basarili(
        "Ana sürüm geliştirme sırasında korunur."
    )

    basarili(
        "Terfi için kullanıcıdan EVET gerekir."
    )

    basarili(
        "Terfi öncesi yedek alınır."
    )

    basarili(
        "Terfi sonrası test başarısızsa otomatik geri dönülür."
    )

    print()
    print(
        "Geliştirme hedefini yazabilirsiniz."
    )

    print(
        "Boş bırakırsanız Jarvis küçük ve güvenli "
        "bir iyileştirmeyi kendisi seçer."
    )

    print()

    hedef = input(
        "Gelistirme hedefi: "
    ).strip()

    if not hedef:
        hedef = (
            "Mevcut Jarvis kodunu incele. "
            "Kullanicinin acik komutlarini daha guvenli, "
            "kararli ve dogal bicimde yerine getirmesini "
            "saglayacak en faydali kucuk iyilestirmeleri yap. "
            "Mevcut calisan ozellikleri ve sert kapatma "
            "guvenliklerini bozma."
        )

    try:
        sonuc = gelistir(
            hedef
        )

        session_info = sonuc[
            "session_info"
        ]

        diff_path = diff_kaydet(
            session_info
        )

        promotion_result = {
            "attempted": False,
            "success": False,
        }

        baslik(
            "GELISTIRME SONUCU"
        )

        if sonuc[
            "success"
        ]:
            basarili(
                "GELISTIRME TESTLERI BASARILI"
            )

            bilgi(
                "Test sürümü: "
                + str(
                    session_info[
                        "workspace"
                    ]
                )
            )

            bilgi(
                "Değişiklik farkı: "
                + str(
                    diff_path
                )
            )

            terfi_ok, terfi_bilgi = (
                guvenli_terfi(
                    session_info[
                        "workspace"
                    ],
                    sonuc[
                        "main_hash_before"
                    ]
                )
            )

            promotion_result = {
                "attempted":
                    (
                        terfi_bilgi
                        is not None
                        or terfi_ok
                    ),

                "success":
                    terfi_ok,

                "details":
                    terfi_bilgi,
            }

            if terfi_ok:
                baslik(
                    "SON DURUM"
                )

                basarili(
                    "Yeni geliştirilmiş sürüm ana Jarvis'e geçti."
                )

                basarili(
                    "Terfi sonrası testler başarılı."
                )

            else:
                baslik(
                    "SON DURUM"
                )

                uyari(
                    "Ana Jarvis yeni test sürümüne geçirilmedi."
                )

                bilgi(
                    "Mevcut ana sürüm korunuyor."
                )

        else:
            hata(
                "GELISTIRME TAM OLARAK ONAYLANMADI"
            )

            bilgi(
                "Ana Jarvis değiştirilmedi."
            )

        rapor = rapor_yaz(
            session_info,
            hedef,
            sonuc,
            promotion_result
        )

        print()

        bilgi(
            "Rapor: "
            + str(
                rapor
            )
        )

        bilgi(
            "Diff: "
            + str(
                diff_path
            )
        )

    except KeyboardInterrupt:
        print()

        uyari(
            "Jarvis Developer kullanıcı tarafından durduruldu."
        )

    except Exception as e:
        print()

        hata(
            "JARVIS DEVELOPER HATASI"
        )

        print(
            e
        )

        log_yaz(
            "fatal_error",
            {
                "error": str(e)
            }
        )


if __name__ == "__main__":
    main()