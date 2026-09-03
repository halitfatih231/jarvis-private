from pathlib import Path
import shutil
import py_compile

jarvis = Path.home() / "Jarvis" / "jarvis.py"
yedek = Path.home() / "Jarvis" / "jarvis_yedek_godot_oncesi.py"

if not jarvis.exists():
    raise SystemExit(f"HATA: jarvis.py bulunamadı: {jarvis}")

kod = jarvis.read_text(encoding="utf-8")

# Daha önce eklenmişse tekrar ekleme
if "def godot_test_projesini_ac" in kod:
    print("BİLGİ: Godot test özelliği zaten jarvis.py içinde.")
    raise SystemExit

# Önce güvenli yedek
shutil.copy2(jarvis, yedek)

fonksiyon = r'''

def godot_test_projesini_ac():
    from pathlib import Path
    import subprocess

    godot_exe = Path(
        r"C:\Users\Halit Fatih Böcek\Documents\Godot_4.7.1\Godot_v4.7.1-stable_win64.exe"
    )

    proje = Path(
        r"C:\Users\Halit Fatih Böcek\Documents\Cemil_Jarvis_Test"
    )

    project_file = proje / "project.godot"

    if not godot_exe.exists():
        print("Jarvis: Godot bulunamadı:")
        print(godot_exe)
        return

    if not project_file.exists():
        print("Jarvis: Cemil test projesi bulunamadı:")
        print(project_file)
        return

    print("Jarvis: Cemil Godot TEST projesi açılıyor.")
    print("Jarvis: Ana projeye dokunulmuyor.")
    print(f"Jarvis: Proje: {proje}")

    try:
        subprocess.Popen(
            [
                str(godot_exe),
                "--editor",
                "--path",
                str(proje),
            ],
            cwd=str(proje),
        )
        print("Jarvis: Godot test projesi başlatıldı.")
    except Exception as e:
        print(f"Jarvis: Godot açılamadı: {e}")

'''

# Fonksiyonu KOMUTLAR bölümünden önce ekle
marker = "# KOMUTLAR"

if marker not in kod:
    shutil.copy2(yedek, jarvis)
    raise SystemExit("HATA: '# KOMUTLAR' bölümü bulunamadı. jarvis.py değiştirilmedi.")

kod = kod.replace(marker, fonksiyon + "\n" + marker, 1)

komut_blogu = '''
    if k in {
        "godot test projesini ac",
        "cemil test projesini ac",
        "test godot projesini ac",
    }:
        godot_test_projesini_ac()
        return True

'''

# Önceki yapımızdaki Masaüstü bölümünün önüne ekle
adaylar = [
    "    # Masaüstü",
    "    # MASAÜSTÜ",
    "    # Masaustu",
    "    # MASAUSTU",
]

bulundu = None

for aday in adaylar:
    if aday in kod:
        bulundu = aday
        break

if bulundu is None:
    shutil.copy2(yedek, jarvis)
    raise SystemExit(
        "HATA: Komut ekleme noktası bulunamadı. "
        "jarvis.py değiştirilmedi."
    )

kod = kod.replace(bulundu, komut_blogu + bulundu, 1)

jarvis.write_text(kod, encoding="utf-8")

# Sözdizimini kontrol et
try:
    py_compile.compile(str(jarvis), doraise=True)
except Exception as e:
    shutil.copy2(yedek, jarvis)
    raise SystemExit(
        f"HATA: Kod kontrolü başarısız. Yedek geri yüklendi.\n{e}"
    )

print()
print("TAMAM: jarvis.py güncellendi.")
print(f"YEDEK: {yedek}")
print()
print("YENİ KOMUT:")
print("godot test projesini aç")