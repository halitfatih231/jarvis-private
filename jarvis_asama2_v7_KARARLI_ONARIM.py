# -*- coding: utf-8 -*-

import ast
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import jarvis_asama2_v6_DETERMINISTIK_ENTEGRASYON as v6

ROOT = Path.home() / "Jarvis"
DEV_ROOT = ROOT / "dev_workspace"


def _fonksiyon_kaynagi(kaynak, ad):
    tree = ast.parse(kaynak)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == ad:
            return node, ast.get_source_segment(kaynak, node) or ""
    return None, ""


def _fonksiyon_degistir(kaynak, ad, yeni_kod):
    node, _ = _fonksiyon_kaynagi(kaynak, ad)
    satirlar = kaynak.splitlines(keepends=True)

    if node is None:
        anchor = "def araci_calistir("
        if kaynak.count(anchor) != 1:
            raise RuntimeError(f"{ad} eklenemedi; araci_calistir bulunamadi.")
        return kaynak.replace(anchor, yeni_kod.rstrip() + "\n\n\n" + anchor, 1)

    bas = node.lineno - 1
    son = node.end_lineno
    return "".join(satirlar[:bas]) + yeni_kod.rstrip() + "\n\n\n" + "".join(satirlar[son:])


HELPERS = {
    "uygulama_durumu_sorgula": '''def uygulama_durumu_sorgula(app):
    app = str(app or "").strip()
    if not app:
        return sonuc(False, "Hangi uygulamayi sorgulayacagimi anlayamadim.")

    surecler = [str(ad) for ad in calisan_surecler() if str(ad).strip()]
    hedef = PROCESS_ESLEME.get(norm(app))

    if hedef:
        calisiyor = any(ad.casefold() == str(hedef).casefold() for ad in surecler)
        return sonuc(
            True,
            f"{app} {'calisiyor' if calisiyor else 'calismiyor'}.",
            {"running": calisiyor, "process": hedef if calisiyor else None},
        )

    eslesme = surec_eslesmesi_bul(app)
    calisiyor = eslesme is not None
    return sonuc(
        True,
        f"{app} {'calisiyor' if calisiyor else 'calismiyor'}.",
        {"running": calisiyor, "process": eslesme},
    )''',

    "calisan_uygulamalari_listele": '''def calisan_uygulamalari_listele():
    surecler = [str(ad).strip() for ad in calisan_surecler() if str(ad).strip()]
    benzersiz = sorted(set(surecler), key=str.casefold)
    return sonuc(True, f"{len(benzersiz)} calisan process bulundu.", benzersiz)''',

    "disk_bilgisi": '''def disk_bilgisi():
    try:
        kullanim = shutil.disk_usage(HOME)
        return sonuc(
            True,
            "Disk bilgisi alindi.",
            {"total": int(kullanim.total), "used": int(kullanim.used), "free": int(kullanim.free)},
        )
    except Exception as e:
        return sonuc(False, f"Disk bilgisi alinamadi: {e}")''',

    "bilinen_klasorleri_goster": '''def bilinen_klasorleri_goster():
    klasorler = {
        "desktop": HOME / "Desktop",
        "documents": HOME / "Documents",
        "downloads": HOME / "Downloads",
        "pictures": HOME / "Pictures",
        "music": HOME / "Music",
        "videos": HOME / "Videos",
        "onedrive": HOME / "OneDrive",
        "jarvis": HOME / "Jarvis",
    }
    veri = {
        ad: {"path": str(yol), "exists": bool(yol.exists())}
        for ad, yol in klasorler.items()
    }
    return sonuc(True, "Bilinen klasor bilgileri alindi.", veri)''',

    "yerel_hedef_metalari": '''def yerel_hedef_metalari(sorgu):
    sorgu = str(sorgu or "").strip()
    if not sorgu:
        return sonuc(False, "Metadata icin dosya veya klasor belirtilmedi.")

    yol = yerel_hedef_bul(sorgu)
    if yol is None:
        return sonuc(False, f"{sorgu} bulunamadi.")

    try:
        st = yol.stat()
    except Exception as e:
        return sonuc(False, f"Metadata alinamadi: {e}")

    if yol.is_file():
        tur = "file"
    elif yol.is_dir():
        tur = "directory"
    else:
        tur = "other"

    return sonuc(
        True,
        "Metadata alindi.",
        {
            "name": yol.name,
            "path": str(yol),
            "type": tur,
            "size": int(st.st_size),
            "mtime": float(st.st_mtime),
        },
    )''',

    "guvenli_yetenekleri_listele": '''def guvenli_yetenekleri_listele():
    actions = [
        "open_app", "close_app", "open_recycle_bin", "open_settings",
        "open_desktop", "open_documents", "open_downloads", "web_search",
        "open_url", "lock_pc", "shutdown_pc", "restart_pc", "cancel_shutdown",
        "open_godot_test", "find_local", "open_parent", "create_folder",
        "copy_local", "move_local", "rename_local", "delete_local",
        "app_status", "list_running_apps", "disk_info", "known_folders",
        "file_metadata", "capabilities",
    ]
    return sonuc(True, f"Jarvis {len(actions)} temel action sunuyor.", {"actions": actions})''',
}

ROUTES = {
    "app_status": '''    if action == "app_status":
        return uygulama_durumu_sorgula(args.get("app", ""))
''',
    "list_running_apps": '''    if action == "list_running_apps":
        return calisan_uygulamalari_listele()
''',
    "disk_info": '''    if action == "disk_info":
        return disk_bilgisi()
''',
    "known_folders": '''    if action == "known_folders":
        return bilinen_klasorleri_goster()
''',
    "file_metadata": '''    if action == "file_metadata":
        return yerel_hedef_metalari(args.get("query", ""))
''',
    "capabilities": '''    if action == "capabilities":
        return guvenli_yetenekleri_listele()
''',
}

TOOL_BLOCKS = {
    "app_status": '\n\napp_status\nargs:\n{"app":"uygulama adi"}\n\nBir uygulamanin calisip calismadigini read-only sorgular. Yalnizca kullanici acikca sorarsa kullan.\n',
    "list_running_apps": '\n\nlist_running_apps\nargs:\n{}\n\nCalisan uygulama/process adlarini read-only listeler. Yalnizca kullanici acikca isterse kullan.\n',
    "disk_info": '\n\ndisk_info\nargs:\n{}\n\nDisk toplam/kullanilan/bos alan bilgisini read-only verir. Yalnizca kullanici disk alanini acikca sorarsa kullan.\n',
    "known_folders": '\n\nknown_folders\nargs:\n{}\n\nTemel kullanici klasorlerinin yollarini read-only verir. Yalnizca kullanici bu yollari acikca sorarsa kullan.\n',
    "file_metadata": '\n\nfile_metadata\nargs:\n{"query":"dosya veya klasor"}\n\nBelirli bir dosya veya klasorun metadata bilgisini read-only verir. Dosya icerigini okumaz; yalnizca kullanici acikca isterse kullan.\n',
    "capabilities": '\n\ncapabilities\nargs:\n{}\n\nJarvis\'in kullaniciya sunabildigi temel yetenekleri read-only listeler. Yalnizca kullanici Jarvis\'in neler yapabildigini acikca sorarsa kullan.\n',
}


def _action_if_mi(node, action):
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "action"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == action
    )


def _route_duzelt(func_src, action, blok):
    tree = ast.parse(func_src)
    fn = tree.body[0]
    satirlar = func_src.splitlines(keepends=True)

    for node in fn.body:
        if _action_if_mi(node, action):
            bas = node.lineno - 1
            son = node.end_lineno
            return "".join(satirlar[:bas]) + blok.rstrip() + "\n\n" + "".join(satirlar[son:])

    final_anchor = "\n    return sonuc("
    pos = func_src.rfind(final_anchor)
    if pos < 0:
        raise RuntimeError(f"{action} route'u icin final return bulunamadi.")

    return func_src[:pos] + "\n" + blok.rstrip() + "\n" + func_src[pos:]


def _tool_aciklamalarini_duzelt(kaynak):
    node, eski = _fonksiyon_kaynagi(kaynak, "arac_aciklamalari")
    if node is None:
        raise RuntimeError("arac_aciklamalari bulunamadi.")

    yeni = eski
    for action, blok in TOOL_BLOCKS.items():
        isaret = "\n" + action + "\nargs:\n"
        if isaret not in yeni:
            kapanis = yeni.rfind('"""')
            if kapanis < 0:
                raise RuntimeError("arac_aciklamalari kapanis tirnagi bulunamadi.")
            yeni = yeni[:kapanis] + blok + yeni[kapanis:]

    return _fonksiyon_degistir(kaynak, "arac_aciklamalari", yeni)


def _son_stage2_workspace():
    adaylar = []
    if DEV_ROOT.exists():
        for session in DEV_ROOT.glob("yetenek_stage2_*"):
            if "v7_repair" in session.name:
                continue
            workspace = session / "workspace"
            if (
                workspace.is_dir()
                and (workspace / "jarvis_tools.py").exists()
                and (workspace / "test_jarvis_sessiz.py").exists()
            ):
                adaylar.append(session)

    if not adaylar:
        raise RuntimeError("Onarilacak Stage 2 workspace bulunamadi.")

    return max(adaylar, key=lambda p: p.stat().st_mtime) / "workspace"


def _smoke(workspace):
    kod = '''import json,sys
sys.path.insert(0,sys.argv[1])
import jarvis_tools as j
w=sys.argv[1]
son={}
r=j.araci_calistir("app_status",{"app":"__jarvis_bulunmayan_uygulama_98765__"},confirmed=False)
assert isinstance(r,dict) and r.get("success") is True and isinstance(r.get("data"),dict) and r["data"].get("running") is False
son["app_status"]=True
r=j.araci_calistir("list_running_apps",{},confirmed=False)
assert r.get("success") is True and isinstance(r.get("data"),list)
son["list_running_apps"]=True
r=j.araci_calistir("disk_info",{},confirmed=False)
assert r.get("success") is True and all(isinstance(r["data"].get(k),int) for k in ("total","used","free"))
son["disk_info"]=True
r=j.araci_calistir("known_folders",{},confirmed=False)
assert r.get("success") is True and isinstance(r.get("data"),dict) and "desktop" in r["data"]
son["known_folders"]=True
r=j.araci_calistir("file_metadata",{"query":w},confirmed=False)
assert r.get("success") is True and r["data"].get("type")=="directory"
son["file_metadata"]=True
r=j.araci_calistir("capabilities",{},confirmed=False)
assert r.get("success") is True and isinstance(r.get("data"),dict)
actions=set(r["data"].get("actions",[]))
for a in ("app_status","list_running_apps","disk_info","known_folders","file_metadata","capabilities"):
    assert a in actions
son["capabilities"]=True
metin=j.arac_aciklamalari()
for a in son:
    assert ("\\n"+a+"\\nargs:\\n") in metin
print("__V7__"+json.dumps(son,ensure_ascii=False))'''

    p = subprocess.run(
        [sys.executable, "-c", kod, str(workspace)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    if p.returncode != 0:
        return False, p.stderr.strip() or p.stdout.strip()

    for satir in p.stdout.splitlines():
        if satir.startswith("__V7__"):
            return True, satir[len("__V7__"):]

    return False, "V7 smoke sonucu bulunamadi."


def main():
    v6.kaynaklari_kontrol_et()
    main_hash_before = v6.kaynak_hashleri(ROOT)

    kaynak_workspace = _son_stage2_workspace()
    zaman = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session = DEV_ROOT / ("yetenek_stage2_v7_repair_" + zaman)
    workspace = session / "workspace"
    original = session / "original"

    workspace.mkdir(parents=True, exist_ok=False)
    original.mkdir(parents=True, exist_ok=True)

    for isim in v6.SOURCE_FILES:
        shutil.copy2(kaynak_workspace / isim, workspace / isim)
        shutil.copy2(kaynak_workspace / isim, original / isim)

    protected_baseline = v6.protected_snapshot(workspace)

    kaynak = (workspace / "jarvis_tools.py").read_text(encoding="utf-8")

    for helper, helper_kodu in HELPERS.items():
        kaynak = _fonksiyon_degistir(kaynak, helper, helper_kodu)

    node, dispatcher = _fonksiyon_kaynagi(kaynak, "araci_calistir")
    if node is None:
        raise RuntimeError("araci_calistir bulunamadi.")

    for action, blok in ROUTES.items():
        dispatcher = _route_duzelt(dispatcher, action, blok)

    kaynak = _fonksiyon_degistir(kaynak, "araci_calistir", dispatcher)
    kaynak = _tool_aciklamalarini_duzelt(kaynak)

    ast.parse(kaynak)
    (workspace / "jarvis_tools.py").write_text(kaynak, encoding="utf-8")

    if not v6.protected_ayni_mi(workspace, protected_baseline):
        raise RuntimeError("Kilitli kritik guvenlik kodu degisti; V7 durduruldu.")

    test_ok, test_msg = v6.tam_test(workspace)
    if not test_ok:
        raise RuntimeError("Mevcut davranis/guvenlik testleri gecmedi: " + str(test_msg))

    smoke_ok, smoke_msg = _smoke(workspace)
    if not smoke_ok:
        raise RuntimeError("Guclendirilmis V7 smoke testi gecmedi: " + str(smoke_msg))

    main_ok, farklar = v6.hashler_ayni_mi(ROOT, main_hash_before)
    if not main_ok:
        raise RuntimeError("Ana Jarvis dosyalari degisti: " + ", ".join(farklar))

    session_info = {"session": session, "workspace": workspace, "original": original}
    diff_path = v6.diff_kaydet(session_info)

    rapor = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "stage": "2-v7-repair",
        "source_workspace": str(kaynak_workspace),
        "workspace": str(workspace),
        "completed_capabilities": list(ROUTES),
        "behavior_test": test_msg,
        "strong_smoke": smoke_msg,
        "main_files_unchanged": True,
        "automatic_promotion": False,
    }
    report_path = session / "stage2_v7_report.json"
    report_path.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")

    v6.baslik("JARVIS ASAMA 2 V7 ONARIM TAMAMLANDI")
    v6.durum("YETENEK", ", ".join(ROUTES))
    v6.durum("TEST", str(test_msg))
    v6.durum("SMOKE", str(smoke_msg))
    v6.durum("WORKSPACE", str(workspace))
    v6.durum("DIFF", str(diff_path))
    v6.durum("RAPOR", str(report_path))
    v6.durum("ANA_JARVIS", "Guvende. Ana dosyalar degistirilmedi.")
    v6.durum("TERFI", "Otomatik terfi KAPALI.")


if __name__ == "__main__":
    main()
