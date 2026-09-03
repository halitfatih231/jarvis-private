# -*- coding: utf-8 -*-

import subprocess
from pathlib import Path

import jarvis_developer_yetenek as stage2


# ============================================================
# JARVIS ASAMA 2 V4
# GPT-OSS + NO-TOOLS AGENT + BOS AI WORKSPACE
# ============================================================

AGENT = "jarvis-advisor"

AI_TEMP = (
    Path.home()
    / "Jarvis_AI_Temp"
)


def agy_single_shot_v4(prompt):

    AI_TEMP.mkdir(
        parents=True,
        exist_ok=True
    )

    if len(prompt) > stage2.MAX_PROMPT_CHARS:

        raise RuntimeError(
            f"Prompt fazla buyuk: {len(prompt):,} karakter. "
            "Guvenli token siniri nedeniyle gonderilmedi."
        )

    command = [

        stage2.find_agy(),

        "-p",
        prompt,

        "--agent",
        AGENT,

        "--model",
        stage2.MODEL,

        "--output-format",
        "json",

        "--sandbox",
    ]

    try:

        process = subprocess.run(

            command,

            # KRITIK:
            # Antigravity Jarvis proje klasorunde
            # CALISMIYOR.
            #
            # Boylece Jarvis reposunu/workspace'ini
            # otomatik context olarak yukleyemez.
            cwd=str(
                AI_TEMP
            ),

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=stage2.AGY_TIMEOUT,
        )

    except subprocess.TimeoutExpired:

        raise RuntimeError(
            f"Antigravity {stage2.AGY_TIMEOUT} saniyede "
            "cevap vermedi."
        )

    except Exception as exc:

        raise RuntimeError(
            "Antigravity baslatilamadi: "
            + str(
                exc
            )
        )

    stdout = (
        process.stdout
        or ""
    )

    stderr = (
        process.stderr
        or ""
    ).strip()

    try:

        outer = (
            stage2.parse_outer_agy_json(
                stdout
            )
        )

    except Exception as exc:

        raise RuntimeError(
            str(
                exc
            )
            +
            (
                "\nSTDERR:\n"
                + stderr

                if stderr
                else ""
            )
        )

    status = (
        str(
            outer.get(
                "status",
                ""
            )
        ).upper()
    )

    usage = (
        outer.get(
            "usage"
        )
        or {}
    )

    if status != "SUCCESS":

        error = (
            outer.get(
                "error"
            )
            or
            stderr
            or
            "Bilinmeyen Antigravity hatasi."
        )

        total_tokens = (
            usage.get(
                "total_tokens"
            )
        )

        if total_tokens is not None:

            raise RuntimeError(
                f"Antigravity ERROR: {error} "
                f"| token={total_tokens}"
            )

        raise RuntimeError(
            "Antigravity ERROR: "
            + str(
                error
            )
        )

    response = (
        outer.get(
            "response"
        )
    )

    if not isinstance(
        response,
        str
    ):

        raise RuntimeError(
            "Antigravity response metin degil."
        )

    return (
        response,
        usage
    )


def main():

    # ========================================================
    # V2'NIN GUVENLIK SISTEMINI KORU
    # ========================================================

    # Degisen tek sey:
    # Antigravity cagrisinin nereden ve hangi
    # ajanla yapildigi.
    #
    # Patch kontrolu, rollback, ana Jarvis hash
    # kontrolu, kritik fonksiyon kilitleri,
    # py_compile ve 31/31 regresyon testleri
    # V2'den aynen devam eder.

    stage2.agy_single_shot = (
        agy_single_shot_v4
    )

    print()
    print("=" * 78)
    print(
        "JARVIS ASAMA 2 V4 - DUSUK TOKEN OTONOM YETENEK GELISTIRICI"
    )
    print("=" * 78)

    print(
        "[MODEL] gpt-oss-120b-medium"
    )

    print(
        "[AGENT] jarvis-advisor"
    )

    print(
        "[TOOLS] KAPALI"
    )

    print(
        "[COMMAND] KAPALI"
    )

    print(
        "[JSON_SCHEMA] KAPALI"
    )

    print(
        "[STREAM_JSON] KAPALI"
    )

    print(
        "[SANDBOX] AKTIF"
    )

    print(
        "[AI_WORKSPACE] "
        + str(
            AI_TEMP
        )
    )

    print(
        "[JARVIS_PROJE_CONTEXT] OTOMATIK YUKLEME KAPALI"
    )

    print(
        "[TOKEN] Jarvis kodu yalniz secilen parcalar halinde prompta gider."
    )

    print(
        "[GUVENLIK] dangerously-skip-permissions KULLANILMIYOR"
    )

    print(
        "[ANA_JARVIS] Otomatik degistirme KAPALI"
    )

    print(
        "[DURDUR] Ctrl+C"
    )

    print()

    stage2.main()


if __name__ == "__main__":

    main()