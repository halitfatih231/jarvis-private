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


print("Gemini hizli surekli oturumu baslatiliyor...")


proc = subprocess.Popen(
    [
        str(AGY),
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--effort",
        "low",
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

    ilk_metin_zamani = None
    cevap_parcalari = []

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

        if olay.get("event") == "step_update":
            guncelleme = olay.get(
                "step_update",
                {}
            )

            parca = guncelleme.get(
                "text_delta"
            )

            if parca:
                if ilk_metin_zamani is None:
                    ilk_metin_zamani = (
                        time.time()
                        - baslangic
                    )

                cevap_parcalari.append(
                    str(parca)
                )

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

            if not cevap and cevap_parcalari:
                cevap = "".join(
                    cevap_parcalari
                ).strip()

            toplam_sure = (
                time.time()
                - baslangic
            )

            print()
            print("Jarvis:", cevap)

            if ilk_metin_zamani is not None:
                print(
                    f"[Ilk kelime: {ilk_metin_zamani:.2f} saniye]"
                )

            print(
                f"[Tam cevap: {toplam_sure:.2f} saniye]"
            )

            return cevap


try:
    sor(
        "Bundan sonra sen benim Jarvis asistanimsin. "
        "Benimle dogal Turkce konus. "
        "Onceki mesajlarimi bu oturum boyunca hatirla. "
        "Cevaplarini gereksiz uzatma. "
        "Benim adim Fatih. "
        "Bana kisa bir selam ver."
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