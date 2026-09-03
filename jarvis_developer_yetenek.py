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
import time
import uuid
from datetime import datetime
from pathlib import Path

import jarvis_developer as core


# ============================================================
# JARVIS ASAMA 2 V2
# OTONOM YENI YETENEK GELISTIRICI
# ============================================================

ROOT = Path.home() / "Jarvis"
DEV_ROOT = ROOT / "dev_workspace"

SOURCE_FILES = [
    "test_jarvis_sessiz.py",
    "jarvis_tools.py",
]

MODEL = "gpt-oss-120b-medium"

AGY_DEFAULT = (
    Path.home()
    / "AppData"
    / "Local"
    / "agy"
    / "bin"
    / "agy.exe"
)

AGY_TIMEOUT = 420


# ============================================================
# TOKEN TASARRUFU
# ============================================================

MAX_CONTEXT_PER_FILE = 5000
MAX_INDEX_CHARS = 2200

# Windows komut satiri sinirina yaklasmamak icin
# toplam prompt da sinirlanir.
MAX_PROMPT_CHARS = 23000

TURN_WAIT_SECONDS = 2
PLATEAU_WAIT_SECONDS = 120

MAX_FAILURE_PER_FOCUS = 3


# ============================================================
# PATCH SINIRLARI
# ============================================================

MAX_PATCHES = 2

MAX_FIND_CHARS = 6500
MAX_REPLACE_CHARS = 9000

MAX_ADDED_LINES = 140
MAX_REMOVED_LINES = 80
MAX_TOTAL_DIFF_LINES = 180

MAX_FILE_SHRINK_RATIO = 0.90


# ============================================================
# YETENEK YOL HARITASI
# ============================================================

CAPABILITY_ROADMAP = [

    {
        "name": "Pencere farkindaligi",

        "keywords": [
            "window",
            "pencere",
            "desktop",
            "pywinauto",
            "focus",
            "title",
            "open_app",
            "close_app",
            "action",
            "tool",
        ],

        "goal": (
            "Kullanici acikca sordugunda acik Windows "
            "pencerelerini salt-okuma biciminde listeleyebilecek "
            "veya belirli bir pencerenin acik olup olmadigini "
            "soyleyebilecek guvenli bir yetenek ekle. "
            "Mouse, klavye veya toplu kapatma ekleme."
        ),
    },

    {
        "name": "Uygulama durum sorgusu",

        "keywords": [
            "app",
            "uygulama",
            "process",
            "running",
            "open_app",
            "close_app",
            "action",
            "tool",
        ],

        "goal": (
            "Kullanici bir uygulamanin acik olup olmadigini "
            "sordugunda salt-okuma biciminde cevap verebilecek "
            "yeni bir yetenek ekle."
        ),
    },

    {
        "name": "Dosya metadata bilgisi",

        "keywords": [
            "file",
            "folder",
            "dosya",
            "klasor",
            "path",
            "stat",
            "find_local",
            "yerel_hedef_bul",
            "open_local",
            "action",
        ],

        "goal": (
            "Kullanicinin acikca belirttigi dosya veya klasor "
            "icin boyut, tur ve konum gibi zararsiz metadata "
            "bilgilerini verebilecek yeni bir yetenek ekle. "
            "Dosya icerigini proaktif olarak okuma."
        ),
    },

    {
        "name": "Disk alan bilgisi",

        "keywords": [
            "disk",
            "drive",
            "disk_usage",
            "shutil",
            "system",
            "windows",
            "action",
            "tool",
        ],

        "goal": (
            "Kullanici sordugunda disk toplam, kullanilan ve bos "
            "alan bilgisini salt-okuma biciminde verebilecek "
            "guvenli bir yetenek ekle."
        ),
    },

    {
        "name": "Temel sistem bilgisi",

        "keywords": [
            "system",
            "platform",
            "windows",
            "computer",
            "bilgisayar",
            "python",
            "version",
            "action",
            "tool",
        ],

        "goal": (
            "Kullanici sordugunda Windows surumu, Python surumu "
            "ve benzeri zararsiz temel sistem bilgilerini "
            "verebilecek salt-okuma bir yetenek ekle."
        ),
    },

    {
        "name": "Bilinen klasorleri acma",

        "keywords": [
            "folder",
            "klasor",
            "desktop",
            "documents",
            "downloads",
            "explorer",
            "open_local",
            "open_parent",
            "action",
        ],

        "goal": (
            "Masaustu, Belgeler veya Indirilenler gibi bilinen "
            "kullanici klasorlerini acik bir kullanici komutuyla "
            "daha kolay acabilecek guvenli ve geri dondurulebilir "
            "bir yetenek ekle."
        ),
    },

    {
        "name": "Dosya arama sonucunu aciklama",

        "keywords": [
            "find_local",
            "yerel_hedef_bul",
            "search",
            "result",
            "score",
            "file",
            "folder",
            "dosya",
            "klasor",
            "action",
        ],

        "goal": (
            "Yerel arama sonucunun dosya mi klasor mu oldugunu, "
            "tam yolunu veya temel eslesme bilgisini kullaniciya "
            "daha anlasilir aktarabilecek yeni bir yetenek ekle."
        ),
    },

    {
        "name": "Son degistirilme bilgisi",

        "keywords": [
            "mtime",
            "modified",
            "stat",
            "datetime",
            "time",
            "file",
            "folder",
            "path",
            "action",
        ],

        "goal": (
            "Kullanicinin acikca belirttigi dosya veya klasorun "
            "son degistirilme zamanini salt-okuma biciminde "
            "soyleyebilecek yeni bir yetenek ekle."
        ),
    },

    {
        "name": "Jarvis yetenek sorgusu",

        "keywords": [
            "tool",
            "action",
            "jarvis_tools",
            "system_prompt",
            "yetenek",
            "yardim",
            "help",
            "neler",
        ],

        "goal": (
            "Kullanici Jarvis'e neler yapabildigini sordugunda "
            "gercekte kayitli yerel yetenekleri daha dogru "
            "anlatabilmesini saglayacak guvenli bir yetenek ekle."
        ),
    },

    {
        "name": "Guvenli baglam zinciri",

        "keywords": [
            "son_arac_baglami",
            "tool_result",
            "feedback",
            "action",
            "args",
            "open_app",
            "open_local",
            "memory",
        ],

        "goal": (
            "Birbirini takip eden zararsiz komutlarda onceki "
            "basarili hedefi daha guvenilir kullanabilecek "
            "kucuk bir baglamsal yetenek ekle. "
            "Tehlikeli islemleri otomatik zincirleme."
        ),
    },
]


# ============================================================
# KILITLI KRITIK KODLAR
# ============================================================

PROTECTED_FUNCTIONS = {

    "test_jarvis_sessiz.py": {
        "arac_guvenlik_kontrolu",
        "belirsiz_kapatma_komutu_mi",
        "olumsuz_kapatma_ifadesi_mi",
        "acik_bilgisayar_kapatma_istegi_mi",
        "acik_yeniden_baslatma_istegi_mi",
        "acik_kilitleme_istegi_mi",
    },

    "jarvis_tools.py": {
        "yerel_sil",
        "delete_local",
        "shutdown_pc",
        "restart_pc",
        "lock_pc",
    },
}


PROTECTED_VARIABLES = {

    "jarvis_tools.py": {
        "KRITIK_SURECLER",
    },
}


# ============================================================
# YENI KODDA YASAK KALIPLAR
# ============================================================

FORBIDDEN_NEW_PATTERNS = [

    "os.system(",

    "subprocess.popen(",
    "subprocess.run(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",

    "powershell",
    "cmd.exe",

    "taskkill",
    "shutdown /",

    "shutil.rmtree(",

    "os.remove(",
    "os.unlink(",
    ".unlink(",

    "send2trash(",

    "os.rename(",
    ".rename(",
    "shutil.move(",

    "requests.",
    "httpx.",
    "urllib.request",
    "socket.",

    "winreg.",

    "eval(",
    "exec(",

    "send_keys(",
    "type_keys(",
    "click_input(",

    "pyautogui",

    "password",
    "credential",
    "cookie",
    "api_key",

    "--dangerously-skip-permissions",
]


# ============================================================
# EKRAN
# ============================================================

def line():

    print(
        "=" * 78,
        flush=True
    )


def title(
    text
):

    print()

    line()

    print(
        text,
        flush=True
    )

    line()


def log(
    tag,
    text
):

    print(
        f"[{tag}] {text}",
        flush=True
    )


# ============================================================
# DOSYA YARDIMCILARI
# ============================================================

def read_text(
    path
):

    return Path(
        path
    ).read_text(
        encoding="utf-8"
    )


def write_text(
    path,
    content
):

    Path(
        path
    ).write_text(
        content,
        encoding="utf-8"
    )


def sha256_file(
    path
):

    h = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):

            h.update(
                block
            )

    return h.hexdigest()


def source_hashes(
    base
):

    return {

        name:
            sha256_file(
                Path(
                    base
                )
                / name
            )

        for name
        in SOURCE_FILES
    }


def hashes_equal(
    base,
    baseline
):

    current = (
        source_hashes(
            base
        )
    )

    changed = [

        name

        for name
        in SOURCE_FILES

        if (
            current.get(
                name
            )
            !=
            baseline.get(
                name
            )
        )
    ]

    return (
        not changed,
        changed
    )


# ============================================================
# ONCEKI WORKSPACE
# ============================================================

def workspace_valid(
    workspace
):

    workspace = Path(
        workspace
    )

    return all(
        (
            workspace
            / filename
        ).exists()

        for filename
        in SOURCE_FILES
    )


def latest_previous_workspace():

    if not DEV_ROOT.exists():

        return ROOT

    candidates = []

    for session in DEV_ROOT.iterdir():

        if not session.is_dir():

            continue

        workspace = (
            session
            / "workspace"
        )

        if not workspace_valid(
            workspace
        ):

            continue

        try:

            stamp = max(
                (
                    workspace
                    / filename
                ).stat().st_mtime

                for filename
                in SOURCE_FILES
            )

        except Exception:

            continue

        candidates.append(
            (
                stamp,
                workspace
            )
        )

    if not candidates:

        return ROOT

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[
        0
    ][1]


# ============================================================
# YENI SESSION
# ============================================================

def create_session(
    source_base
):

    stamp = (
        datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
    )

    session = (
        DEV_ROOT
        / f"yetenek_v2_{stamp}"
    )

    workspace = (
        session
        / "workspace"
    )

    original = (
        session
        / "original"
    )

    iterations = (
        session
        / "iterations"
    )

    workspace.mkdir(
        parents=True,
        exist_ok=False
    )

    original.mkdir(
        parents=True,
        exist_ok=True
    )

    iterations.mkdir(
        parents=True,
        exist_ok=True
    )

    for filename in SOURCE_FILES:

        shutil.copy2(
            Path(
                source_base
            )
            / filename,
            workspace
            / filename
        )

        shutil.copy2(
            Path(
                source_base
            )
            / filename,
            original
            / filename
        )

    return {

        "session":
            session,

        "workspace":
            workspace,

        "original":
            original,

        "iterations":
            iterations,

        "source":
            Path(
                source_base
            ),
    }


def make_backup(
    workspace,
    iterations,
    turn
):

    backup = (
        iterations
        / f"before_{turn:05d}"
    )

    backup.mkdir(
        parents=True,
        exist_ok=False
    )

    for filename in SOURCE_FILES:

        shutil.copy2(
            workspace
            / filename,
            backup
            / filename
        )

    return backup


def restore_backup(
    backup,
    workspace
):

    for filename in SOURCE_FILES:

        shutil.copy2(
            backup
            / filename,
            workspace
            / filename
        )


# ============================================================
# AST / KRITIK SNAPSHOT
# ============================================================

def ast_source(
    source,
    node
):

    return (
        ast.get_source_segment(
            source,
            node
        )
        or
        ""
    )


def protected_snapshot(
    workspace
):

    snapshot = {}

    for filename in SOURCE_FILES:

        source = (
            read_text(
                workspace
                / filename
            )
        )

        tree = (
            ast.parse(
                source
            )
        )

        functions = (
            PROTECTED_FUNCTIONS.get(
                filename,
                set()
            )
        )

        variables = (
            PROTECTED_VARIABLES.get(
                filename,
                set()
            )
        )

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):

                if node.name in functions:

                    snapshot[
                        (
                            filename,
                            "function",
                            node.name
                        )
                    ] = (
                        ast_source(
                            source,
                            node
                        )
                    )

            elif isinstance(
                node,
                ast.Assign
            ):

                for target in node.targets:

                    if (
                        isinstance(
                            target,
                            ast.Name
                        )
                        and
                        target.id
                        in variables
                    ):

                        snapshot[
                            (
                                filename,
                                "variable",
                                target.id
                            )
                        ] = (
                            ast_source(
                                source,
                                node
                            )
                        )

            elif isinstance(
                node,
                ast.AnnAssign
            ):

                target = (
                    node.target
                )

                if (
                    isinstance(
                        target,
                        ast.Name
                    )
                    and
                    target.id
                    in variables
                ):

                    snapshot[
                        (
                            filename,
                            "variable",
                            target.id
                        )
                    ] = (
                        ast_source(
                            source,
                            node
                        )
                    )

    return snapshot


def protected_unchanged(
    workspace,
    baseline
):

    return (
        protected_snapshot(
            workspace
        )
        == baseline
    )


# ============================================================
# KOD INDEKSI
# ============================================================

def source_index(
    source
):

    tree = (
        ast.parse(
            source
        )
    )

    rows = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            rows.append(
                (
                    f"FUNC {node.name} "
                    f"L{node.lineno}-"
                    f"L{getattr(node, 'end_lineno', node.lineno)}"
                )
            )

        elif isinstance(
            node,
            ast.ClassDef
        ):

            rows.append(
                (
                    f"CLASS {node.name} "
                    f"L{node.lineno}-"
                    f"L{getattr(node, 'end_lineno', node.lineno)}"
                )
            )

    text = "\n".join(
        rows
    )

    if len(text) > MAX_INDEX_CHARS:

        text = (
            text[
                :MAX_INDEX_CHARS
            ]
            + "\n[INDEX_KESILDI]"
        )

    return text


# ============================================================
# DUSUK TOKEN BAGLAM SECIMI
# ============================================================

COMMON_KEYWORDS = [

    "action",
    "args",
    "tool",
    "jarvis_tools",
    "tool_result",
    "tool result",
    "yerel_sistem",
    "execute",
    "dispatch",
    "system_prompt",
    "system prompt",
    "[[tool]]",
    "son_arac_baglami",
]


def merge_ranges(
    ranges
):

    if not ranges:

        return []

    ranges = sorted(
        ranges
    )

    merged = [
        list(
            ranges[
                0
            ]
        )
    ]

    for start, end in ranges[
        1:
    ]:

        previous = (
            merged[
                -1
            ]
        )

        if (
            start
            <= previous[
                1
            ]
            + 1
        ):

            previous[
                1
            ] = max(
                previous[
                    1
                ],
                end
            )

        else:

            merged.append(
                [
                    start,
                    end
                ]
            )

    return [
        tuple(
            item
        )
        for item
        in merged
    ]


def build_context_for_file(
    path,
    keywords,
    max_chars
):

    source = (
        read_text(
            path
        )
    )

    lines = (
        source.splitlines(
            keepends=True
        )
    )

    search_words = list(
        dict.fromkeys(
            [
                word.casefold()

                for word
                in (
                    keywords
                    + COMMON_KEYWORDS
                )

                if word
            ]
        )
    )

    hits = []

    for index, line_text in enumerate(
        lines
    ):

        lowered = (
            line_text.casefold()
        )

        score = 0

        for word in search_words:

            if word in lowered:

                score += 1

        if score:

            hits.append(
                (
                    score,
                    index
                )
            )

    hits.sort(
        key=lambda item: (
            -item[
                0
            ],
            item[
                1
            ]
        )
    )

    ranges = []

    # Imports ve ana global yapilar
    ranges.append(
        (
            0,
            min(
                len(
                    lines
                ),
                65
            )
        )
    )

    # En alakali bolgeler
    for _, index in hits[
        :16
    ]:

        ranges.append(
            (
                max(
                    0,
                    index - 11
                ),
                min(
                    len(
                        lines
                    ),
                    index + 12
                )
            )
        )

    # Dosya sonunda main/dispatch olabilir
    if lines:

        ranges.append(
            (
                max(
                    0,
                    len(
                        lines
                    )
                    - 70
                ),
                len(
                    lines
                )
            )
        )

    ranges = (
        merge_ranges(
            ranges
        )
    )

    display_parts = []
    raw_parts = []

    used = 0

    for start, end in ranges:

        raw = "".join(
            lines[
                start:end
            ]
        )

        if not raw.strip():

            continue

        remaining = (
            max_chars
            - used
        )

        if remaining <= 300:

            break

        if len(raw) > remaining:

            raw = raw[
                :remaining
            ]

        display_parts.append(
            (
                f"\n<<<LINES {start + 1}-{end}>>>\n"
                + raw
                + "\n<<<END_LINES>>>\n"
            )
        )

        raw_parts.append(
            raw
        )

        used += len(
            raw
        )

        if used >= max_chars:

            break

    if not raw_parts:

        raw = (
            source[
                :max_chars
            ]
        )

        raw_parts = [
            raw
        ]

        display_parts = [
            raw
        ]

        used = len(
            raw
        )

    return {

        "source_chars":
            len(
                source
            ),

        "context_chars":
            used,

        "index":
            source_index(
                source
            ),

        "display":
            "".join(
                display_parts
            ),

        "raw":
            "\n".join(
                raw_parts
            ),
    }


def build_turn_context(
    workspace,
    focus
):

    tools_context = (
        build_context_for_file(

            workspace
            / "jarvis_tools.py",

            focus[
                "keywords"
            ],

            MAX_CONTEXT_PER_FILE
        )
    )

    assistant_context = (
        build_context_for_file(

            workspace
            / "test_jarvis_sessiz.py",

            focus[
                "keywords"
            ],

            MAX_CONTEXT_PER_FILE
        )
    )

    return {

        "jarvis_tools.py":
            tools_context,

        "test_jarvis_sessiz.py":
            assistant_context,

        "total_chars":
            (
                tools_context[
                    "context_chars"
                ]
                +
                assistant_context[
                    "context_chars"
                ]
            ),
    }


# ============================================================
# AGY BUL
# ============================================================

def find_agy():

    if AGY_DEFAULT.exists():

        return str(
            AGY_DEFAULT
        )

    found = (
        shutil.which(
            "agy"
        )
        or
        shutil.which(
            "agy.exe"
        )
    )

    if found:

        return found

    raise FileNotFoundError(
        (
            "Antigravity agy.exe bulunamadi: "
            + str(
                AGY_DEFAULT
            )
        )
    )


# ============================================================
# AGY SINGLE-SHOT
# JSON-SCHEMA YOK
# STREAM-JSON YOK
# ============================================================

def parse_outer_agy_json(
    stdout
):

    stdout = (
        stdout
        or ""
    ).strip()

    if not stdout:

        raise RuntimeError(
            "Antigravity bos cikti dondurdu."
        )

    try:

        return json.loads(
            stdout
        )

    except Exception:

        pass

    # Bazen stdout'ta ek satir olursa
    # sondan gecerli JSON bul.
    lines = [
        line.strip()

        for line
        in stdout.splitlines()

        if line.strip()
    ]

    for line_text in reversed(
        lines
    ):

        try:

            data = json.loads(
                line_text
            )

            if isinstance(
                data,
                dict
            ):

                return data

        except Exception:

            continue

    start = (
        stdout.find(
            "{"
        )
    )

    end = (
        stdout.rfind(
            "}"
        )
    )

    if (
        start != -1
        and
        end > start
    ):

        try:

            return json.loads(
                stdout[
                    start:end + 1
                ]
            )

        except Exception:

            pass

    raise RuntimeError(
        (
            "Antigravity dis JSON cikisi ayrıştırilamadi:\n"
            + stdout[
                :1500
            ]
        )
    )


def agy_single_shot(
    prompt
):

    if len(prompt) > MAX_PROMPT_CHARS:

        raise RuntimeError(
            (
                f"Prompt fazla buyuk: {len(prompt):,} karakter. "
                "Token/Windows komut satiri guvenligi icin "
                "istek gonderilmedi."
            )
        )

    command = [

        find_agy(),

        "-p",
        prompt,

        "--model",
        MODEL,

        "--output-format",
        "json",

        "--sandbox",
    ]

    try:

        process = (
            subprocess.run(

                command,

                cwd=
                    str(
                        ROOT
                    ),

                capture_output=
                    True,

                text=
                    True,

                encoding=
                    "utf-8",

                errors=
                    "replace",

                timeout=
                    AGY_TIMEOUT,
            )
        )

    except subprocess.TimeoutExpired:

        raise RuntimeError(
            (
                f"Antigravity {AGY_TIMEOUT} saniyede "
                "cevap vermedi."
            )
        )

    except Exception as exc:

        raise RuntimeError(
            (
                "Antigravity baslatilamadi: "
                + str(
                    exc
                )
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
            parse_outer_agy_json(
                stdout
            )
        )

    except Exception as exc:

        raise RuntimeError(
            (
                str(
                    exc
                )
                + (
                    "\nSTDERR:\n"
                    + stderr
                    if stderr
                    else ""
                )
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

        usage = (
            outer.get(
                "usage"
            )
            or {}
        )

        total_tokens = (
            usage.get(
                "total_tokens"
            )
        )

        if total_tokens is not None:

            raise RuntimeError(
                (
                    f"Antigravity ERROR: {error} "
                    f"| token={total_tokens}"
                )
            )

        raise RuntimeError(
            (
                "Antigravity ERROR: "
                + str(
                    error
                )
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

    usage = (
        outer.get(
            "usage"
        )
        or {}
    )

    return (
        response,
        usage
    )


# ============================================================
# MODEL JSON CEVABINI AYIKLA
# ============================================================

def strip_code_fence(
    text
):

    text = (
        text
        or ""
    ).strip()

    if text.startswith(
        "```"
    ):

        lines = (
            text.splitlines()
        )

        if lines:

            lines = lines[
                1:
            ]

        if (
            lines
            and
            lines[
                -1
            ].strip().startswith(
                "```"
            )
        ):

            lines = lines[
                :-1
            ]

        text = (
            "\n".join(
                lines
            ).strip()
        )

    return text


def extract_first_json_object(
    text
):

    in_string = False
    escape = False
    depth = 0
    start = None

    for index, char in enumerate(
        text
    ):

        if in_string:

            if escape:

                escape = False

            elif char == "\\":

                escape = True

            elif char == '"':

                in_string = False

            continue

        if char == '"':

            in_string = True

            continue

        if char == "{":

            if depth == 0:

                start = index

            depth += 1

        elif char == "}":

            if depth > 0:

                depth -= 1

                if (
                    depth == 0
                    and
                    start is not None
                ):

                    return text[
                        start:index + 1
                    ]

    return None


def parse_model_json(
    response
):

    cleaned = (
        strip_code_fence(
            response
        )
    )

    try:

        data = json.loads(
            cleaned
        )

        if isinstance(
            data,
            dict
        ):

            return data

    except Exception:

        pass

    candidate = (
        extract_first_json_object(
            cleaned
        )
    )

    if candidate:

        try:

            data = json.loads(
                candidate
            )

            if isinstance(
                data,
                dict
            ):

                return data

        except Exception:

            pass

    raise ValueError(
        (
            "GPT-OSS gecerli JSON dondurmedi. "
            "Cevabin basi: "
            + cleaned[
                :500
            ].replace(
                "\n",
                " "
            )
        )
    )


# ============================================================
# PROMPT
# ============================================================

def recent_capabilities_text(
    recent
):

    if not recent:

        return "Yok."

    return "\n".join(
        (
            "- "
            + item
        )

        for item
        in recent[
            -8:
        ]
    )


def build_prompt(
    turn,
    request_id,
    focus,
    contexts,
    recent,
    feedback
):

    prompt = f"""
Sen Jarvis'in kontrollu yeni-yetenek gelistirme ajanisin.

Bu islem GPT-OSS 120B ile yapiliyor.

SEN DOSYA YAZMAYACAKSIN.
SEN KOMUT CALISTIRMAYACAKSIN.
SEN ARAC CALISTIRMAYACAKSIN.

Sadece JSON olarak kucuk bir kod degisikligi oner.
Gercek patch'i yerel Python sistemi uygulayip test edecek.

TUR:
{turn}

REQUEST_ID:
{request_id}

YETENEK ALANI:
{focus['name']}

HEDEF:
{focus['goal']}

SON KABUL EDILEN YETENEKLER:
{recent_capabilities_text(recent)}

ONCEKI GERI BILDIRIM:
{feedback or "Yok."}


KESIN KURALLAR:

1. Bir turda en fazla BIR yeni yetenek ekle.

2. Yeni action/fonksiyon adi snake_case olmali.

3. capability_name yeni action/fonksiyonun TAM adi olmali.

4. Yetenek mumkunse salt-okuma veya kolay geri
   dondurulebilir olmali.

5. shutdown, restart, lock, silme, rename, move,
   toplu kapatma gibi kritik yetenek ekleme.

6. Mevcut kritik guvenlik fonksiyonlarini degistirme.

7. Klavye yazma, mouse tiklama veya keyfi GUI
   otomasyonu ekleme.

8. Shell, PowerShell, CMD veya yeni subprocess
   mekanizmasi ekleme.

9. Network veya internet erisimi ekleme.

10. Sifre, credential, cookie veya API key okuma ekleme.

11. Cemil ana Godot projesine dokunma.

12. Kullanici istemeden ozel dosya icerigi okuma ekleme.

13. Yeni yetenek jarvis_tools.py icinde gercek bir
    fonksiyon/action olarak bulunmali.

14. test_jarvis_sessiz.py icindeki mevcut tool/action
    mimarisine de baglanmali.

15. Gerekirse EN FAZLA iki patch kullan:
    biri jarvis_tools.py,
    biri test_jarvis_sessiz.py.

16. FIND metni SADECE asagida sana gosterilen
    gercek koddan HARFI HARFINE alinmali.

17. FIND benzersiz ve kucuk olmali.

18. Tum dosyayi yeniden yazma.

19. Placeholder veya uc nokta kullanma.

20. Gerekli entegrasyon kodu gosterilmiyorsa tahmin etme.
    status degerini "done" yap.

21. Yetenek zaten varsa tekrar ekleme.

22. Aciklama, Markdown veya code fence YAZMA.

23. SADECE tek bir gecerli JSON nesnesi dondur.


PATCH VARSA TAM FORMAT:

{{
  "request_id": "{request_id}",
  "status": "patch",
  "capability_name": "yeni_action_adi",
  "summary": "Kisa aciklama",
  "reason": "Kisa gerekce",
  "patches": [
    {{
      "target_file": "jarvis_tools.py",
      "find": "DOSYADAN BIREBIR GERCEK KOD",
      "replace": "GERCEK YENI KOD"
    }},
    {{
      "target_file": "test_jarvis_sessiz.py",
      "find": "DOSYADAN BIREBIR GERCEK KOD",
      "replace": "GERCEK YENI KOD"
    }}
  ]
}}

DEGISIKLIK GEREKMIYORSA TAM FORMAT:

{{
  "request_id": "{request_id}",
  "status": "done",
  "capability_name": "none",
  "summary": "Bu alanda yeni guvenli yetenek gerekmiyor",
  "reason": "Kisa gerekce",
  "patches": []
}}


==================================================
jarvis_tools.py INDEX
==================================================

{contexts['jarvis_tools.py']['index']}

==================================================
jarvis_tools.py GOSTERILEN KOD
==================================================

{contexts['jarvis_tools.py']['display']}

==================================================
test_jarvis_sessiz.py INDEX
==================================================

{contexts['test_jarvis_sessiz.py']['index']}

==================================================
test_jarvis_sessiz.py GOSTERILEN KOD
==================================================

{contexts['test_jarvis_sessiz.py']['display']}

==================================================
SON TALIMAT
==================================================

Sadece gecerli JSON dondur.

request_id TAM OLARAK:
{request_id}
""".strip()

    if len(prompt) > MAX_PROMPT_CHARS:

        raise RuntimeError(
            (
                f"Olusturulan prompt {len(prompt):,} karakter. "
                "Guvenli sinir asildi."
            )
        )

    return prompt


# ============================================================
# RESPONSE VALIDATION
# ============================================================

def validate_response(
    data,
    request_id
):

    if not isinstance(
        data,
        dict
    ):

        raise ValueError(
            "Cevap JSON object degil."
        )

    required = {
        "request_id",
        "status",
        "capability_name",
        "summary",
        "reason",
        "patches",
    }

    missing = (
        required
        - set(
            data.keys()
        )
    )

    if missing:

        raise ValueError(
            (
                "Eksik JSON alanlari: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )
        )

    if (
        data.get(
            "request_id"
        )
        != request_id
    ):

        raise ValueError(
            "request_id eslesmedi."
        )

    status = (
        str(
            data.get(
                "status",
                ""
            )
        ).casefold()
    )

    if status not in {
        "patch",
        "done",
    }:

        raise ValueError(
            "status patch veya done olmali."
        )

    summary = (
        data.get(
            "summary"
        )
    )

    reason = (
        data.get(
            "reason"
        )
    )

    if not isinstance(
        summary,
        str
    ):

        raise ValueError(
            "summary string olmali."
        )

    if not isinstance(
        reason,
        str
    ):

        raise ValueError(
            "reason string olmali."
        )

    patches = (
        data.get(
            "patches"
        )
    )

    if not isinstance(
        patches,
        list
    ):

        raise ValueError(
            "patches liste olmali."
        )

    if status == "done":

        if patches:

            raise ValueError(
                "done cevabinda patches bos olmali."
            )

        return

    capability = (
        str(
            data.get(
                "capability_name",
                ""
            )
        ).strip()
    )

    if not re.fullmatch(
        r"[a-z][a-z0-9_]{2,48}",
        capability
    ):

        raise ValueError(
            (
                "capability_name gecersiz: "
                + capability
            )
        )

    if not (
        1
        <= len(
            patches
        )
        <= MAX_PATCHES
    ):

        raise ValueError(
            "Patch sayisi 1 veya 2 olmali."
        )

    targets = []

    for patch in patches:

        if not isinstance(
            patch,
            dict
        ):

            raise ValueError(
                "Patch nesnesi dict olmali."
            )

        target = (
            patch.get(
                "target_file"
            )
        )

        if target not in SOURCE_FILES:

            raise ValueError(
                (
                    "Gecersiz target_file: "
                    + str(
                        target
                    )
                )
            )

        targets.append(
            target
        )

        find_text = (
            patch.get(
                "find"
            )
        )

        replace_text = (
            patch.get(
                "replace"
            )
        )

        if not isinstance(
            find_text,
            str
        ):

            raise ValueError(
                "find string olmali."
            )

        if not isinstance(
            replace_text,
            str
        ):

            raise ValueError(
                "replace string olmali."
            )

        if not find_text.strip():

            raise ValueError(
                "find bos olamaz."
            )

        if len(find_text) > MAX_FIND_CHARS:

            raise ValueError(
                "find fazla buyuk."
            )

        if len(replace_text) > MAX_REPLACE_CHARS:

            raise ValueError(
                "replace fazla buyuk."
            )

        placeholder_text = (
            find_text
            + "\n"
            + replace_text
        ).casefold()

        forbidden_placeholders = [

            "...existing code...",
            "buraya kod",
            "hedef dosyanin tam icerigi",
            "kisa gelistirme ozeti",
            "todo: implement",
        ]

        for placeholder in forbidden_placeholders:

            if (
                placeholder
                in placeholder_text
            ):

                raise ValueError(
                    (
                        "Placeholder bulundu: "
                        + placeholder
                    )
                )

    if (
        len(
            targets
        )
        != len(
            set(
                targets
            )
        )
    ):

        raise ValueError(
            "Ayni dosyaya iki patch verilemez."
        )


# ============================================================
# DIFF / YENI KOD GUVENLIGI
# ============================================================

def diff_stats(
    old,
    new
):

    matcher = (
        difflib.SequenceMatcher(

            a=
                old.splitlines(),

            b=
                new.splitlines(),

            autojunk=False
        )
    )

    added = 0
    removed = 0

    for (
        tag,
        i1,
        i2,
        j1,
        j2
    ) in matcher.get_opcodes():

        if tag == "insert":

            added += (
                j2
                - j1
            )

        elif tag == "delete":

            removed += (
                i2
                - i1
            )

        elif tag == "replace":

            removed += (
                i2
                - i1
            )

            added += (
                j2
                - j1
            )

    return (
        added,
        removed
    )


def get_added_lines(
    old,
    new
):

    return [

        item[
            2:
        ]

        for item
        in difflib.ndiff(
            old.splitlines(),
            new.splitlines()
        )

        if item.startswith(
            "+ "
        )
    ]


def check_new_dangerous_code(
    old,
    new
):

    added = (
        "\n".join(
            get_added_lines(
                old,
                new
            )
        ).casefold()
    )

    hits = [

        pattern

        for pattern
        in FORBIDDEN_NEW_PATTERNS

        if (
            pattern.casefold()
            in added
        )
    ]

    if hits:

        return (
            False,
            (
                "Yasak yeni kod kalibi: "
                + ", ".join(
                    hits
                )
            )
        )

    return (
        True,
        ""
    )


def make_patch_hash(
    target,
    find_text,
    replace_text
):

    return (
        hashlib.sha256(
            (
                target
                + "\0"
                + find_text
                + "\0"
                + replace_text
            ).encode(
                "utf-8"
            )
        ).hexdigest()
    )


# ============================================================
# ACTION GERCEKTEN VAR MI?
# ============================================================

def top_level_function_exists(
    source,
    function_name
):

    tree = (
        ast.parse(
            source
        )
    )

    for node in tree.body:

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            )
            and
            node.name
            == function_name
        ):

            return True

    return False


# ============================================================
# PATCH UYGULAMA
# ============================================================

def apply_model_patches(
    data,
    workspace,
    contexts,
    protected_baseline,
    seen_hashes
):

    capability = (
        data[
            "capability_name"
        ]
    )

    results = []
    pending_hashes = []

    for patch in data[
        "patches"
    ]:

        target = (
            patch[
                "target_file"
            ]
        )

        find_text = (
            patch[
                "find"
            ]
        )

        replace_text = (
            patch[
                "replace"
            ]
        )

        # Model yalniz kendisine gosterilen
        # kodu hedefleyebilir.
        if (
            find_text
            not in contexts[
                target
            ][
                "raw"
            ]
        ):

            raise ValueError(
                (
                    target
                    + " FIND modele gosterilen "
                    "kod baglaminda yok."
                )
            )

        path = (
            workspace
            / target
        )

        old = (
            read_text(
                path
            )
        )

        count = (
            old.count(
                find_text
            )
        )

        if count == 0:

            raise ValueError(
                (
                    target
                    + " FIND mevcut workspace "
                    "dosyasinda bulunamadi."
                )
            )

        if count > 1:

            raise ValueError(
                (
                    target
                    + f" FIND {count} kez geciyor; "
                    "benzersiz degil."
                )
            )

        patch_hash = (
            make_patch_hash(
                target,
                find_text,
                replace_text
            )
        )

        if (
            patch_hash
            in seen_hashes
            or
            patch_hash
            in pending_hashes
        ):

            raise ValueError(
                "Ayni patch daha once denendi."
            )

        new = (
            old.replace(
                find_text,
                replace_text,
                1
            )
        )

        if new == old:

            raise ValueError(
                "Patch degisiklik uretmedi."
            )

        added, removed = (
            diff_stats(
                old,
                new
            )
        )

        if added > MAX_ADDED_LINES:

            raise ValueError(
                (
                    f"{target}: +{added} satir "
                    "tek tur icin fazla."
                )
            )

        if removed > MAX_REMOVED_LINES:

            raise ValueError(
                (
                    f"{target}: -{removed} satir "
                    "tek tur icin fazla."
                )
            )

        if (
            added
            + removed
            > MAX_TOTAL_DIFF_LINES
        ):

            raise ValueError(
                (
                    target
                    + ": toplam diff siniri asildi."
                )
            )

        old_line_count = max(
            1,
            len(
                old.splitlines()
            )
        )

        new_line_count = (
            len(
                new.splitlines()
            )
        )

        if (
            new_line_count
            <
            old_line_count
            * MAX_FILE_SHRINK_RATIO
        ):

            raise ValueError(
                (
                    target
                    + ": dosyanin buyuk bolumunu "
                    "silmeye calisan patch reddedildi."
                )
            )

        safe, reason = (
            check_new_dangerous_code(
                old,
                new
            )
        )

        if not safe:

            raise ValueError(
                reason
            )

        if hasattr(
            core,
            "kod_guvenli_mi"
        ):

            safe2, reason2 = (
                core.kod_guvenli_mi(
                    old,
                    new
                )
            )

            if not safe2:

                raise ValueError(
                    (
                        "Cekirdek guvenlik reddi: "
                        + str(
                            reason2
                        )
                    )
                )

        # Python syntax
        ast.parse(
            new
        )

        # SADECE WORKSPACE
        write_text(
            path,
            new
        )

        pending_hashes.append(
            patch_hash
        )

        results.append(
            {
                "target":
                    target,

                "added":
                    added,

                "removed":
                    removed,
            }
        )

    # Kritik fonksiyonlar degisti mi?
    if not protected_unchanged(
        workspace,
        protected_baseline
    ):

        raise ValueError(
            "Kilitli kritik guvenlik kodu degisti."
        )

    tools_source = (
        read_text(
            workspace
            / "jarvis_tools.py"
        )
    )

    assistant_source = (
        read_text(
            workspace
            / "test_jarvis_sessiz.py"
        )
    )

    # Yeni yetenek jarvis_tools.py'de
    # gercek fonksiyon olmali.
    if not top_level_function_exists(
        tools_source,
        capability
    ):

        raise ValueError(
            (
                capability
                + " jarvis_tools.py icinde "
                "top-level fonksiyon olarak bulunamadi."
            )
        )

    # Assistant/tool protokolune de baglanmis olmali.
    if capability not in assistant_source:

        raise ValueError(
            (
                capability
                + " test_jarvis_sessiz.py "
                "entegrasyonunda bulunamadi."
            )
        )

    return (
        results,
        pending_hashes
    )


# ============================================================
# PY_COMPILE
# ============================================================

def py_compile_test(
    workspace
):

    for filename in SOURCE_FILES:

        process = (
            subprocess.run(

                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(
                        workspace
                        / filename
                    ),
                ],

                cwd=
                    str(
                        workspace
                    ),

                capture_output=
                    True,

                text=True,

                encoding="utf-8",

                errors="replace",

                timeout=45,
            )
        )

        if (
            process.returncode
            != 0
        ):

            message = (
                process.stderr
                or
                process.stdout
                or
                "Bilinmeyen py_compile hatasi."
            )

            return (
                False,
                (
                    filename
                    + ": "
                    + message.strip()
                )
            )

    return (
        True,
        "py_compile basarili."
    )


# ============================================================
# IMPORT SMOKE TEST
# ============================================================

def import_smoke_test(
    workspace
):

    process = (
        subprocess.run(

            [
                sys.executable,
                "-c",
                (
                    "import jarvis_tools; "
                    "print('IMPORT_OK')"
                ),
            ],

            cwd=
                str(
                    workspace
                ),

            capture_output=
                True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=30,
        )
    )

    if (
        process.returncode
        != 0
    ):

        return (
            False,
            (
                process.stderr
                or
                process.stdout
                or
                "Import hatasi."
            ).strip()
        )

    if (
        "IMPORT_OK"
        not in process.stdout
    ):

        return (
            False,
            "jarvis_tools import testi basarisiz."
        )

    return (
        True,
        "jarvis_tools import basarili."
    )


# ============================================================
# DAVRANIS TESTLERI
# ============================================================

def behavior_tests(
    workspace
):

    try:

        ok_result, results = (
            core.davranis_testleri(
                workspace,
                baslik_yaz=False
            )
        )

    except Exception as exc:

        return (
            False,
            (
                "Davranis testleri calismadi: "
                + str(
                    exc
                )
            ),
            None,
        )

    if not ok_result:

        return (
            False,
            (
                "Davranis/regresyon "
                "testlerinden biri basarisiz."
            ),
            results,
        )

    if isinstance(
        results,
        list
    ):

        count = len(
            results
        )

        return (
            True,
            (
                f"Davranis/regresyon testleri: "
                f"{count}/{count}"
            ),
            results,
        )

    return (
        True,
        "Davranis/regresyon testleri basarili.",
        results,
    )


def full_test(
    workspace
):

    ok1, msg1 = (
        py_compile_test(
            workspace
        )
    )

    if not ok1:

        return (
            False,
            msg1
        )

    ok2, msg2 = (
        import_smoke_test(
            workspace
        )
    )

    if not ok2:

        return (
            False,
            msg2
        )

    ok3, msg3, _ = (
        behavior_tests(
            workspace
        )
    )

    if not ok3:

        return (
            False,
            msg3
        )

    return (
        True,
        (
            msg1
            + " | "
            + msg2
            + " | "
            + msg3
        )
    )


# ============================================================
# TOKEN GOSTERGESI
# ============================================================

def print_usage(
    usage
):

    if not isinstance(
        usage,
        dict
    ):

        return

    input_tokens = (
        usage.get(
            "input_tokens"
        )
    )

    output_tokens = (
        usage.get(
            "output_tokens"
        )
    )

    thinking_tokens = (
        usage.get(
            "thinking_tokens"
        )
    )

    cache_tokens = (
        usage.get(
            "cache_read_tokens"
        )
    )

    total_tokens = (
        usage.get(
            "total_tokens"
        )
    )

    parts = []

    if input_tokens is not None:

        parts.append(
            f"giris={input_tokens}"
        )

    if output_tokens is not None:

        parts.append(
            f"cikis={output_tokens}"
        )

    if thinking_tokens is not None:

        parts.append(
            f"dusunme={thinking_tokens}"
        )

    if cache_tokens is not None:

        parts.append(
            f"cache={cache_tokens}"
        )

    if total_tokens is not None:

        parts.append(
            f"toplam={total_tokens}"
        )

    if parts:

        log(
            "TOKEN",
            (
                "Bu tur: "
                + " | ".join(
                    parts
                )
            )
        )


# ============================================================
# DIFF / RAPOR
# ============================================================

def save_diff(
    session_info
):

    path = (
        session_info[
            "session"
        ]
        / "stage2_v2_capabilities.diff"
    )

    chunks = []

    for filename in SOURCE_FILES:

        old = (
            read_text(
                session_info[
                    "original"
                ]
                / filename
            ).splitlines(
                keepends=True
            )
        )

        new = (
            read_text(
                session_info[
                    "workspace"
                ]
                / filename
            ).splitlines(
                keepends=True
            )
        )

        chunks.extend(

            difflib.unified_diff(

                old,
                new,

                fromfile=
                    f"original/{filename}",

                tofile=
                    f"workspace/{filename}",
            )
        )

    path.write_text(
        "".join(
            chunks
        ),
        encoding="utf-8"
    )

    return path


def save_report(
    session_info,
    turns,
    accepted,
    rejected,
    done,
    capabilities,
    main_baseline,
    stop_reason
):

    main_ok, changed = (
        hashes_equal(
            ROOT,
            main_baseline
        )
    )

    report = {

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "stage":
            "2_v2",

        "model":
            MODEL,

        "antigravity_mode":
            "single_shot_json_no_schema",

        "turns":
            turns,

        "accepted":
            accepted,

        "rejected":
            rejected,

        "done":
            done,

        "capabilities":
            capabilities,

        "source_workspace":
            str(
                session_info[
                    "source"
                ]
            ),

        "workspace":
            str(
                session_info[
                    "workspace"
                ]
            ),

        "main_files_unchanged":
            main_ok,

        "main_changed_files":
            changed,

        "automatic_promotion":
            False,

        "stop_reason":
            stop_reason,
    }

    path = (
        session_info[
            "session"
        ]
        / "stage2_v2_report.json"
    )

    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    for filename in SOURCE_FILES:

        if not (
            ROOT
            / filename
        ).exists():

            raise FileNotFoundError(
                (
                    "Ana Jarvis dosyasi eksik: "
                    + filename
                )
            )

    # Onceki en gelismis test workspace'ini devral.
    source_base = (
        latest_previous_workspace()
    )

    session_info = (
        create_session(
            source_base
        )
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

    main_baseline = (
        source_hashes(
            ROOT
        )
    )

    protected_baseline = (
        protected_snapshot(
            workspace
        )
    )

    seen_hashes = set()

    title(
        "JARVIS ASAMA 2 V2 - OTONOM YENI YETENEK GELISTIRICI"
    )

    log(
        "MODEL",
        MODEL
    )

    log(
        "ANTIGRAVITY",
        "Single-shot headless mod"
    )

    log(
        "JSON_SCHEMA",
        "KAPALI"
    )

    log(
        "STREAM_JSON",
        "KAPALI"
    )

    log(
        "SANDBOX",
        "AKTIF"
    )

    log(
        "KAYNAK",
        str(
            source_base
        )
    )

    log(
        "WORKSPACE",
        str(
            workspace
        )
    )

    log(
        "TOKEN",
        (
            "Dusuk-token kod parcasi modu."
        )
    )

    log(
        "GUVENLIK",
        (
            "Ana Jarvis'e otomatik yazma KAPALI."
        )
    )

    log(
        "DURDUR",
        "Ctrl+C"
    )

    baseline_ok, baseline_msg = (
        full_test(
            workspace
        )
    )

    if not baseline_ok:

        raise RuntimeError(
            (
                "Devralinan test surumu saglam degil: "
                + baseline_msg
            )
        )

    log(
        "TEST",
        baseline_msg
    )

    turn = 0
    accepted = 0
    rejected = 0
    done = 0

    focus_cursor = 0
    failure_count = 0
    done_streak = 0

    feedback = ""

    capabilities = []

    stop_reason = (
        "Kullanici durdurdu."
    )

    try:

        while True:

            turn += 1

            focus = (
                CAPABILITY_ROADMAP[
                    focus_cursor
                    % len(
                        CAPABILITY_ROADMAP
                    )
                ]
            )

            request_id = (
                "JARVIS-CAP-"
                + uuid.uuid4().hex[
                    :12
                ].upper()
            )

            print()

            log(
                "JARVIS",
                (
                    f"Tur {turn} | "
                    f"{focus['name']}"
                )
            )

            # ===============================================
            # ANA JARVIS HASH KONTROLU
            # ===============================================

            main_ok, changed = (
                hashes_equal(
                    ROOT,
                    main_baseline
                )
            )

            if not main_ok:

                stop_reason = (
                    "Ana Jarvis dosyalarinda "
                    "beklenmedik degisiklik algilandi."
                )

                raise RuntimeError(
                    (
                        stop_reason
                        + " "
                        + ", ".join(
                            changed
                        )
                    )
                )

            # ===============================================
            # TUR YEDEGI
            # ===============================================

            backup = (
                make_backup(
                    workspace,
                    iterations,
                    turn
                )
            )

            # ===============================================
            # KOD BAGLAMI
            # ===============================================

            contexts = (
                build_turn_context(
                    workspace,
                    focus
                )
            )

            log(
                "TOKEN",
                (
                    "Gonderilen gercek kod baglami: "
                    f"{contexts['total_chars']:,} karakter"
                )
            )

            # ===============================================
            # PROMPT
            # ===============================================

            try:

                prompt = (
                    build_prompt(
                        turn,
                        request_id,
                        focus,
                        contexts,
                        capabilities,
                        feedback
                    )
                )

            except Exception as exc:

                rejected += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "HATA",
                    str(
                        exc
                    )
                )

                focus_cursor += 1
                failure_count = 0

                continue

            log(
                "PROMPT",
                (
                    f"{len(prompt):,} karakter"
                )
            )

            log(
                "ANTIGRAVITY",
                "GPT-OSS yeni guvenli yetenek ariyor..."
            )

            # ===============================================
            # AGY SINGLE-SHOT
            # ===============================================

            try:

                response, usage = (
                    agy_single_shot(
                        prompt
                    )
                )

                print_usage(
                    usage
                )

            except Exception as exc:

                rejected += 1
                failure_count += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "HATA",
                    str(
                        exc
                    )
                )

                feedback = (
                    "Onceki Antigravity turu teknik olarak "
                    "tamamlanamadi. Daha kucuk ve kesin cevap ver."
                )

                if (
                    failure_count
                    >= MAX_FAILURE_PER_FOCUS
                ):

                    log(
                        "ATLA",
                        (
                            "Bu alan 3 kez takildi. "
                            "Sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    failure_count = 0

                time.sleep(
                    TURN_WAIT_SECONDS
                )

                continue

            # ===============================================
            # GPT-OSS JSON
            # ===============================================

            try:

                data = (
                    parse_model_json(
                        response
                    )
                )

                validate_response(
                    data,
                    request_id
                )

            except Exception as exc:

                rejected += 1
                failure_count += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "JSON_RED",
                    str(
                        exc
                    )
                )

                feedback = (
                    (
                        "Onceki cevap gecerli yerel JSON "
                        "dogrulamasindan gecmedi: "
                        + str(
                            exc
                        )
                        + ". Sadece istenen JSON nesnesini dondur."
                    )
                )

                if (
                    failure_count
                    >= MAX_FAILURE_PER_FOCUS
                ):

                    log(
                        "ATLA",
                        (
                            "Bu alan 3 kez JSON/format hatasi verdi. "
                            "Sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    failure_count = 0

                time.sleep(
                    TURN_WAIT_SECONDS
                )

                continue

            status = (
                str(
                    data[
                        "status"
                    ]
                ).casefold()
            )

            # ===============================================
            # DONE
            # ===============================================

            if status == "done":

                done += 1
                done_streak += 1

                focus_cursor += 1
                failure_count = 0

                log(
                    "DEGISIKLIK_YOK",
                    (
                        data.get(
                            "summary"
                        )
                        or
                        focus[
                            "name"
                        ]
                    )
                )

                if data.get(
                    "reason"
                ):

                    log(
                        "NEDEN",
                        data[
                            "reason"
                        ]
                    )

                feedback = (
                    "Onceki alanda yeni guvenli yetenek "
                    "gerekmiyordu. Sonraki alana gec."
                )

                if (
                    done_streak
                    >= len(
                        CAPABILITY_ROADMAP
                    )
                ):

                    log(
                        "PLATO",
                        (
                            "Tum yetenek alanlari yeni "
                            "degisiklik bulamadi."
                        )
                    )

                    log(
                        "BEKLE",
                        (
                            f"Token tasarrufu icin "
                            f"{PLATEAU_WAIT_SECONDS} saniye."
                        )
                    )

                    done_streak = 0

                    time.sleep(
                        PLATEAU_WAIT_SECONDS
                    )

                else:

                    time.sleep(
                        TURN_WAIT_SECONDS
                    )

                continue

            done_streak = 0

            capability = (
                data[
                    "capability_name"
                ]
            )

            log(
                "YENI_YETENEK",
                capability
            )

            log(
                "ONERI",
                (
                    data.get(
                        "summary"
                    )
                    or
                    "Yeni yetenek onerildi."
                )
            )

            # ===============================================
            # PATCH
            # ===============================================

            try:

                (
                    patch_results,
                    pending_hashes
                ) = (
                    apply_model_patches(
                        data,
                        workspace,
                        contexts,
                        protected_baseline,
                        seen_hashes
                    )
                )

            except Exception as exc:

                rejected += 1
                failure_count += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "GUVENLIK_RED",
                    str(
                        exc
                    )
                )

                log(
                    "GERI_AL",
                    "Patch tamamen geri alindi."
                )

                feedback = (
                    (
                        "Onceki patch yerel guvenlik "
                        "tarafindan reddedildi: "
                        + str(
                            exc
                        )
                        + ". Mevcut mimariye uyan daha kucuk "
                        "ve gercek bir entegrasyon oner."
                    )
                )

                if (
                    failure_count
                    >= MAX_FAILURE_PER_FOCUS
                ):

                    log(
                        "ATLA",
                        (
                            "Bu alan 3 kez reddedildi. "
                            "Sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    failure_count = 0

                time.sleep(
                    TURN_WAIT_SECONDS
                )

                continue

            for result in patch_results:

                log(
                    "PATCH",
                    (
                        f"{result['target']} "
                        f"+{result['added']} "
                        f"/ -{result['removed']} satir"
                    )
                )

            # ===============================================
            # FULL TEST
            # ===============================================

            log(
                "TEST",
                (
                    "py_compile + import + "
                    "davranis/regresyon testleri..."
                )
            )

            test_ok, test_msg = (
                full_test(
                    workspace
                )
            )

            if not test_ok:

                rejected += 1
                failure_count += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "TEST_RED",
                    test_msg
                )

                log(
                    "GERI_AL",
                    (
                        "Yeni yetenek basarisiz. "
                        "Son saglam surume donuldu."
                    )
                )

                feedback = (
                    (
                        "Onceki yetenek testlerden gecmedi: "
                        + test_msg
                        + ". Daha kucuk ve mevcut mimariye "
                        "uygun patch oner."
                    )
                )

                if (
                    failure_count
                    >= MAX_FAILURE_PER_FOCUS
                ):

                    log(
                        "ATLA",
                        (
                            "Bu alan 3 kez testten kaldi. "
                            "Sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    failure_count = 0

                time.sleep(
                    TURN_WAIT_SECONDS
                )

                continue

            # ===============================================
            # KRITIK GUVENLIK
            # ===============================================

            if not protected_unchanged(
                workspace,
                protected_baseline
            ):

                rejected += 1

                restore_backup(
                    backup,
                    workspace
                )

                log(
                    "GUVENLIK_RED",
                    (
                        "Kilitli kritik kod degisti. "
                        "Patch geri alindi."
                    )
                )

                focus_cursor += 1
                failure_count = 0

                continue

            # ===============================================
            # ANA JARVIS DEGISMEDI MI
            # ===============================================

            main_ok, changed = (
                hashes_equal(
                    ROOT,
                    main_baseline
                )
            )

            if not main_ok:

                stop_reason = (
                    "Ana Jarvis butunlugu bozuldu."
                )

                raise RuntimeError(
                    (
                        stop_reason
                        + " "
                        + ", ".join(
                            changed
                        )
                    )
                )

            # ===============================================
            # KABUL
            # ===============================================

            accepted += 1
            failure_count = 0
            focus_cursor += 1

            for item in pending_hashes:

                seen_hashes.add(
                    item
                )

            capability_record = (
                (
                    capability
                    + " — "
                    + (
                        data.get(
                            "summary"
                        )
                        or
                        ""
                    )
                )
            )

            capabilities.append(
                capability_record
            )

            capabilities = (
                capabilities[
                    -30:
                ]
            )

            log(
                "TEST",
                test_msg
            )

            log(
                "KABUL",
                (
                    capability
                    + " test surumune eklendi."
                )
            )

            log(
                "ANA_JARVIS",
                "Degistirilmedi."
            )

            log(
                "SAYAC",
                (
                    f"Yeni yetenek={accepted} | "
                    f"Red={rejected} | "
                    f"Degisiklik yok={done}"
                )
            )

            feedback = (
                (
                    "Onceki yetenek tum testlerden gecti: "
                    + capability
                    + ". Ayni yetenegi tekrar ekleme."
                )
            )

            time.sleep(
                TURN_WAIT_SECONDS
            )

    # ========================================================
    # CTRL+C
    # ========================================================

    except KeyboardInterrupt:

        stop_reason = (
            "Kullanici Ctrl+C ile durdurdu."
        )

        print()

        log(
            "DURDUR",
            (
                "Ctrl+C alindi. "
                "Son saglam workspace korunuyor."
            )
        )

    # ========================================================
    # FINAL
    # ========================================================

    finally:

        diff_path = (
            save_diff(
                session_info
            )
        )

        report_path = (
            save_report(
                session_info,
                turn,
                accepted,
                rejected,
                done,
                capabilities,
                main_baseline,
                stop_reason
            )
        )

        main_ok, changed = (
            hashes_equal(
                ROOT,
                main_baseline
            )
        )

        title(
            "JARVIS ASAMA 2 V2 DURDU"
        )

        log(
            "TUR",
            str(
                turn
            )
        )

        log(
            "YENI_YETENEK",
            str(
                accepted
            )
        )

        log(
            "RED",
            str(
                rejected
            )
        )

        log(
            "DEGISIKLIK_YOK",
            str(
                done
            )
        )

        log(
            "WORKSPACE",
            str(
                workspace
            )
        )

        log(
            "DIFF",
            str(
                diff_path
            )
        )

        log(
            "RAPOR",
            str(
                report_path
            )
        )

        if main_ok:

            log(
                "ANA_JARVIS",
                (
                    "Guvende. "
                    "Ana dosyalar degistirilmedi."
                )
            )

        else:

            log(
                "UYARI",
                (
                    "Ana dosyalarda beklenmedik fark: "
                    + ", ".join(
                        changed
                    )
                )
            )

        log(
            "TERFI",
            (
                "Otomatik terfi KAPALI. "
                "Yeni yetenekler test workspace'inde."
            )
        )


if __name__ == "__main__":

    main()