# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")

metin = jarvis.read_text(encoding="utf-8")

baslangic = metin.find("def konus(metin):")
bitis = metin.find("def norm(metin):")

if baslangic == -1:
    print("HATA: konus() fonksiyonu bulunamadi.")
    raise SystemExit

if bitis == -1 or bitis <= baslangic:
    print("HATA: norm() fonksiyonu bulunamadi.")
    raise SystemExit


yeni_ses_kodu = r'''def konus(metin):
    """Jarvis'i ElevenLabs OAuth + Alper sesiyle konusturur."""

    try:
        import ctypes

        metin = str(metin).strip()

        if not metin:
            return

        voice_id = "HllA1j2zLOqUQ4kLjMmK"
        model_id = "eleven_multilingual_v2"

        # Ayni cumle tekrar soylenirse yeniden ElevenLabs
        # kullanimi yapmamak icin yerel ses onbellegi.
        cache_klasoru = JARVIS_KLASORU / "ses_cache"
        cache_klasoru.mkdir(
            parents=True,
            exist_ok=True
        )

        kimlik = hashlib.sha256(
            (
                voice_id
                + "|"
                + model_id
                + "|"
                + metin
            ).encode("utf-8")
        ).hexdigest()

        ses_dosyasi = (
            cache_klasoru
            / f"{kimlik}.mp3"
        )

        if not ses_dosyasi.exists():

            komut = [
                "cmd",
                "/c",
                "elevenlabs",
                "text-to-speech",
                "convert",
                "--model-id",
                model_id,
                "--voice-id",
                voice_id,
                "--text",
                metin,
                "--output",
                str(ses_dosyasi)
            ]

            sonuc = subprocess.run(
                komut,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                )
            )

            if sonuc.returncode != 0:
                hata = (
                    sonuc.stderr.strip()
                    or sonuc.stdout.strip()
                    or "Bilinmeyen ElevenLabs hatasi"
                )

                print(
                    "Jarvis: ElevenLabs OAuth ses hatasi:",
                    hata
                )

                return

            if (
                not ses_dosyasi.exists()
                or ses_dosyasi.stat().st_size == 0
            ):
                print(
                    "Jarvis: ElevenLabs ses dosyasi olusturmadi."
                )
                return

        # MP3 dosyasini Windows MCI ile oynat.
        mci = ctypes.windll.winmm.mciSendStringW

        alias = (
            "jarvis_ses_"
            + str(os.getpid())
        )

        mci(
            f"close {alias}",
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
                f"play {alias} wait",
                None,
                0,
                None
            )

        finally:
            mci(
                f"close {alias}",
                None,
                0,
                None
            )

    except subprocess.TimeoutExpired:
        print(
            "Jarvis: ElevenLabs ses istegi zaman asimina ugradi."
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

# jarvis.py'yi degistirmeden once syntax kontrolu
compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_oauth_ses_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: Jarvis ElevenLabs OAuth sistemine gecirildi.")
print("SES: Alper")
print("MODEL: eleven_multilingual_v2")
print("API KEY: kullanilmiyor")
print("OAUTH: Windows Credential Manager")
print("SES ONBELLEGI: aktif")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")