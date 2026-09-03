# -*- coding: utf-8 -*-

import subprocess

import jarvis_developer_yetenek as stage2


AGENT = "jarvis-advisor"


def agy_single_shot_v3(prompt):

    if len(prompt) > stage2.MAX_PROMPT_CHARS:

        raise RuntimeError(
            f"Prompt fazla buyuk: {len(prompt):,} karakter. "
            "Guvenli sinir nedeniyle gonderilmedi."
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

            cwd=str(
                stage2.ROOT
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
            + str(exc)
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
            str(exc)
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
            + str(error)
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

    # V2'nin tum guvenlik, workspace,
    # rollback ve 31/31 test sistemi aynen korunur.
    #
    # Sadece Antigravity cagrisini,
    # arac kullanamayan jarvis-advisor agent'ina
    # yonlendiriyoruz.

    stage2.agy_single_shot = (
        agy_single_shot_v3
    )

    print()
    print("=" * 78)
    print(
        "JARVIS ASAMA 2 V3 - GPT-OSS + NO-TOOLS ADVISOR"
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
        "[GUVENLIK] dangerously-skip-permissions KULLANILMIYOR"
    )

    print(
        "[DURDUR] Ctrl+C"
    )

    print()

    stage2.main()


if __name__ == "__main__":

    main()