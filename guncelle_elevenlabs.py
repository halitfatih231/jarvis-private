# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")

metin = jarvis.read_text(encoding="utf-8")

baslangic = metin.find("def konus(metin):")
bitis = metin.find("def norm(metin):")

if baslangic == -1:
    print("HATA: Mevcut konus() fonksiyonu bulunamadi.")
    raise SystemExit

if bitis == -1 or bitis <= baslangic:
    print("HATA: norm() fonksiyonu bulunamadi.")
    raise SystemExit


yeni_ses_kodu = r'''def konus(metin):
    """Jarvis'i ElevenLabs Alper sesiyle konusturur."""

    try:
        import ctypes
        import winreg

        metin = str(metin).strip()

        if not metin:
            return

        # API anahtarini Windows kullanici ortamindan al.
        api_key = os.environ.get("ELEVENLABS_API_KEY")

        if not api_key:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    "Environment"
                ) as key:
                    api_key, _ = winreg.QueryValueEx(
                        key,
                        "ELEVENLABS_API_KEY"
                    )
            except Exception:
                api_key = None

        if not api_key:
            print(
                "Jarvis: ElevenLabs API anahtari bulunamadi."
            )
            return

        voice_id = "HllA1j2zLOqUQ4kLjMmK"

        # Ayni cumle tekrar soylenirse yeniden kredi harcama.
        cache_klasoru = JARVIS_KLASORU / "ses_cache"
        cache_klasoru.mkdir(
            parents=True,
            exist_ok=True
        )

        kimlik = hashlib.sha256(
            (
                voice_id
                + "|multilingual_v2|"
                + metin
            ).encode("utf-8")
        ).hexdigest()

        ses_dosyasi = (
            cache_klasoru
            / f"{kimlik}.mp3"
        )

        if not ses_dosyasi.exists():

            url = (
                "https://api.elevenlabs.io/"
                "v1/text-to-speech/"
                + voice_id
                + "?output_format=mp3_44100_128"
            )

            veri = {
                "text": metin,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.80,
                    "similarity_boost": 0.60,
                    "style": 0.0,
                    "use_speaker_boost": True,
                    "speed": 0.90
                }
            }

            istek = Request(
                url,
                data=json.dumps(
                    veri
                ).encode("utf-8"),
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                },
                method="POST"
            )

            try:
                with urlopen(
                    istek,
                    timeout=60
                ) as cevap:
                    ses = cevap.read()

            except Exception as e:
                print(
                    "Jarvis: ElevenLabs ses uretim hatasi:",
                    e
                )
                return

            if not ses:
                print(
                    "Jarvis: ElevenLabs bos ses dondurdu."
                )
                return

            ses_dosyasi.write_bytes(
                ses
            )

        # Windows'un kendi MCI sistemiyle MP3 oynat.
        mci = ctypes.windll.winmm.mciSendStringW

        alias = (
            "jarvis_ses_"
            + str(os.getpid())
        )

        mci(
            f'close {alias}',
            None,
            0,
            None
        )

        sonuc = mci(
            f'open "{ses_dosyasi}" type mpegvideo alias {alias}',
            None,
            0,
            None
        )

        if sonuc != 0:
            print(
                "Jarvis: Ses dosyasi acilamadi."
            )
            return

        try:
            mci(
                f'play {alias} wait',
                None,
                0,
                None
            )
        finally:
            mci(
                f'close {alias}',
                None,
                0,
                None
            )

    except Exception as e:
        print(
            "Jarvis: Ses sistemi hatasi:",
            e
        )


'''


yeni = (
    metin[:baslangic]
    + yeni_ses_kodu
    + metin[bitis:]
)

# Degisiklikten once syntax kontrolu.
compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_elevenlabs_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: ElevenLabs Alper sesi Jarvis'e baglandi.")
print("YEDEK:", yedek)
print("SES: Alper")
print("MODEL: eleven_multilingual_v2")
print("ONBELLEK: aktif")
print("TEST: python jarvis.py")