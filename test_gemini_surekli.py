# -*- coding: utf-8 -*-

import json
import os
import subprocess
import time
from pathlib import Path


AGY = (
    Path(os.environ["LOCALAPPDATA"])
    / "agy"
    / "bin"
    / "agy.exe"
)

if not AGY.exists():
    print("HATA: agy.exe bulunamadi:", AGY)
    raise SystemExit


print("Gemini surekli oturumu baslatiliyor...")


proc = subprocess.Popen(
    [
        str(AGY),
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1,
    cwd=str(Path.home() / "Jarvis"),
    creationflags=getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0
    ),
)


def sor(metin):
    mesaj = {
        "event": "user",
        "message": {
            "content": metin
        }
    }

    baslangic = time.time()

    proc.stdin.write(
        json.dumps(
            mesaj,
            ensure_ascii=False
        )
        + "\n"
    )

    proc.stdin.flush()

    while True:

        satir = proc.stdout.readline()

        if not satir:
            raise RuntimeError(
                "Antigravity oturumu beklenmedik sekilde kapandi."
            )

        try:
            olay = json.loads(satir)

        except json.JSONDecodeError:
            continue

        if olay.get("event") == "result":

            sonuc = olay.get(
                "result",
                {}
            )

            if sonuc.get("status") != "SUCCESS":
                print(
                    "HATA:",
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

            sure = time.time() - baslangic

            print()
            print("Jarvis:", cevap)
            print(
                f"[Cevap suresi: {sure:.2f} saniye]"
            )

            return cevap


try:

    sor(
        "Bundan sonra sen benim Jarvis asistanimsin. "
        "Benimle dogal Turkce sohbet et. "
        "Onceki mesajlarimi bu oturum boyunca hatirla. "
        "Kisa, hizli ve dogal cevap ver. "
        "Bu testte bilgisayarda arac veya komut kullanma. "
        "Benim adim Fatih. Bana sadece kisa bir selam ver."
    )

    sor(
        "Peki benim adim ne ve sana hangi adi verdim?"
    )

finally:

    if proc.stdin:
        proc.stdin.close()

    try:
        proc.terminate()
    except Exception:
        pass