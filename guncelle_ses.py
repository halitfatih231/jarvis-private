# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")

metin = jarvis.read_text(encoding="utf-8")

if "def konus(metin):" in metin:
    print("Ses sistemi zaten eklenmiş.")
    raise SystemExit


ses_kodu = r'''
def konus(metin):
    """Jarvis'in yazili cevabini Windows sesiyle seslendirir."""
    try:
        metin = str(metin).strip()

        if not metin:
            return

        ortam = os.environ.copy()
        ortam["JARVIS_TTS_TEXT"] = metin

        ps_kodu = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Volume = 100; "
            "$s.Rate = 0; "
            "$s.Speak($env:JARVIS_TTS_TEXT)"
        )

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                ps_kodu
            ],
            env=ortam,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            )
        )

    except Exception:
        pass

'''


hedef = "def norm(metin):"

if hedef not in metin:
    print("HATA: Ses kodunun eklenecegi yer bulunamadi.")
    raise SystemExit

yeni = metin.replace(
    hedef,
    ses_kodu + "\n" + hedef,
    1
)

ana = "def main():"

if ana not in yeni:
    print("HATA: main() bulunamadi.")
    raise SystemExit

yeni = yeni.replace(
    ana,
    'def main():\n    konus("Jarvis hazır.")',
    1
)

# Dosyayi bozmadan once Python sözdizimini kontrol et
compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
yedek = jarvis.with_name(
    f"jarvis_yedek_ses_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Jarvis ses sistemi eklendi.")
print("YEDEK:", yedek)
print('TEST: python jarvis.py')