# -*- coding: utf-8 -*-

import ast
import difflib
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import jarvis_developer as core


# ============================================================
# TEMEL AYARLAR
# ============================================================

ROOT = Path.home() / "Jarvis"
DEV_ROOT = ROOT / "dev_workspace"

SOURCE_FILES = [
    "test_jarvis_sessiz.py",
    "jarvis_tools.py",
]

AGY_DEFAULT = (
    Path.home()
    / "AppData"
    / "Local"
    / "agy"
    / "bin"
    / "agy.exe"
)

AGY_EFFORT = "low"
AGY_RESPONSE_TIMEOUT = 420


# ============================================================
# DUSUK TOKEN AYARLARI
# ============================================================

# Her tur yepyeni Antigravity oturumu kullanilir.
# Boylece onceki turlarin devasa konusma baglami tekrar tasinmaz.
FRESH_AGY_EVERY_TURN = True

# Tum dosya yerine yalnizca ilgili kod bolumleri gider.
MAX_CONTEXT_CHARS = 9000
MAX_INDEX_CHARS = 3500
MAX_NODE_CHARS = 4500
MAX_SELECTED_NODES = 5

TUR_ARASI_BEKLEME = 2.0
TAM_DONGU_BEKLEME = 20.0

# Ayni alanda arka arkaya hata olursa token yakmamak icin atla.
MAX_RETRY_PER_FOCUS = 3


# ============================================================
# PATCH SINIRLARI
# ============================================================

MAX_FIND_CHARS = 9000
MAX_REPLACE_CHARS = 12000

MAX_REMOVED_LINES = 120
MAX_ADDED_LINES = 180
MAX_TOTAL_DIFF_LINES = 220

MAX_FILE_SHRINK_RATIO = 0.90


# ============================================================
# GELISTIRME ALANLARI
# ============================================================

FOCUS_AREAS = [

    {
        "name": "Dogal dil guvenligi",

        "target": "test_jarvis_sessiz.py",

        "keywords": [
            "guvenlik",
            "kapat",
            "olumsuz",
            "belirsiz",
            "komut",
            "arac",
            "tool",
            "son_arac_baglami",
            "bekleyen_onay",
            "yerel_sistem",
        ],

        "goal": (
            "Belirsiz, soru bicimindeki veya olumsuz komutlarin "
            "yanlislikla yerel arac calistirmasini azalt. "
            "Kritik guvenlik fonksiyonlarina dokunma."
        ),
    },

    {
        "name": "Uygulama kontrolu",

        "target": "jarvis_tools.py",

        "keywords": [
            "open_app",
            "close_app",
            "uygulama",
            "app",
            "process",
            "kisayol",
            "lnk",
            "start menu",
            "program files",
        ],

        "goal": (
            "Uygulama adlarini cozumleme ve guvenilir uygulama "
            "bulmayi gelistir. Yeni tehlikeli yurutme mekanizmasi ekleme."
        ),
    },

    {
        "name": "Dosya bulma",

        "target": "jarvis_tools.py",

        "keywords": [
            "yerel_hedef_bul",
            "find_local",
            "dosya",
            "klasor",
            "path",
            "fuzzy",
            "sequencematcher",
            "search",
            "roots",
            "skip",
        ],

        "goal": (
            "Yerel dosya ve klasor aramasinda yanlis eslesmeleri azalt. "
            "Isim normalizasyonunu ve siralamayi gelistir. "
            "Silme davranisini degistirme."
        ),
    },

    {
        "name": "Dosya takma adlari",

        "target": "test_jarvis_sessiz.py",

        "keywords": [
            "file_alias",
            "alias",
            "takma",
            "memory",
            "hafiza",
            "hedef",
            "open_local",
        ],

        "goal": (
            "file_aliases kullanimini daha dogal ve guvenilir yap. "
            "Mevcut bellegi bozma."
        ),
    },

    {
        "name": "Baglam takibi",

        "target": "test_jarvis_sessiz.py",

        "keywords": [
            "son_arac_baglami",
            "baglam",
            "onu",
            "onceki",
            "tool result",
            "yerel_sistem",
            "open_app",
            "close_app",
        ],

        "goal": (
            "'onu ac' gibi baglamsal komutlarda yalnizca guvenilir "
            "son hedefin kullanilmasini gelistir. "
            "Kapatma guvenlik kapisini zayiflatma."
        ),
    },

    {
        "name": "Hata yonetimi",

        "target": "test_jarvis_sessiz.py",

        "keywords": [
            "try",
            "except",
            "error",
            "hata",
            "exception",
            "timeout",
            "result",
            "feedback",
        ],

        "goal": (
            "Yerel arac hatalarini daha kararli ele al. "
            "Dongunun gereksiz yere cokmesini azalt."
        ),
    },

    {
        "name": "Windows yardimcilari",

        "target": "jarvis_tools.py",

        "keywords": [
            "windows",
            "settings",
            "recycle",
            "open_settings",
            "open_recycle_bin",
            "path",
            "shell",
            "explorer",
        ],

        "goal": (
            "Var olan geri dondurulebilir Windows yardimcilarinin "
            "hata toleransini gelistir. "
            "Guc, silme ve kritik surec korumalarina dokunma."
        ),
    },

    {
        "name": "Kod kararliligi",

        "target": "jarvis_tools.py",

        "keywords": [
            "try",
            "except",
            "return",
            "none",
            "error",
            "hata",
            "path",
            "exists",
            "timeout",
        ],

        "goal": (
            "Kirilgan kenar durumlarini, tekrarlari veya "
            "guvenilirlik sorunlarini kucuk bir degisiklikle azalt."
        ),
    },
]


# ============================================================
# KILITLI KRITIK BOLUMLER
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
    }
}


# ============================================================
# YENI EKLENMESI YASAK TEHLIKELI KALIPLAR
# ============================================================

FORBIDDEN_NEW_PATTERNS = [

    "os.system(",

    "subprocess.popen(",
    "subprocess.run(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",

    "shutil.rmtree(",

    "os.remove(",
    "os.unlink(",
    ".unlink(",

    "send2trash(",

    "requests.",
    "httpx.",
    "urllib.request",
    "socket.",

    "winreg.",

    "powershell",
    "cmd.exe",

    "taskkill",
    "shutdown /",

    "eval(",
    "exec(",

    "--dangerously-skip-permissions",
]


# ============================================================
# ANTIGRAVITY STRUCTURED OUTPUT
# ============================================================

DEVELOPER_SCHEMA = {

    "type": "object",

    "additionalProperties": False,

    "properties": {

        "request_id": {
            "type": "string"
        },

        "status": {
            "type": "string",
            "enum": [
                "patch",
                "done",
            ],
        },

        "target_file": {
            "type": "string",
            "enum": SOURCE_FILES,
        },

        "summary": {
            "type": "string"
        },

        "reason": {
            "type": "string"
        },

        "find": {
            "type": "string"
        },

        "replace": {
            "type": "string"
        },
    },

    "required": [
        "request_id",
        "status",
        "target_file",
        "summary",
        "reason",
        "find",
        "replace",
    ],
}


# ============================================================
# CMD
# ============================================================

def cizgi():

    print(
        "=" * 76,
        flush=True
    )


def baslik(
    metin
):

    print()

    cizgi()

    print(
        metin,
        flush=True
    )

    cizgi()


def durum(
    etiket,
    metin
):

    print(
        f"[{etiket}] {metin}",
        flush=True
    )


# ============================================================
# DOSYA
# ============================================================

def dosya_oku(
    yol
):

    return Path(
        yol
    ).read_text(
        encoding="utf-8"
    )


def dosya_yaz(
    yol,
    icerik
):

    Path(
        yol
    ).write_text(
        icerik,
        encoding="utf-8"
    )


def sha256_file(
    yol
):

    h = hashlib.sha256()

    with open(
        yol,
        "rb"
    ) as f:

        for parca in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):

            h.update(
                parca
            )

    return h.hexdigest()


def kaynak_hashleri(
    base
):

    return {

        isim:
            sha256_file(
                Path(
                    base
                )
                / isim
            )

        for isim
        in SOURCE_FILES
    }


def hashler_ayni_mi(
    base,
    onceki
):

    simdi = (
        kaynak_hashleri(
            base
        )
    )

    farklar = [

        isim

        for isim
        in SOURCE_FILES

        if (
            simdi.get(
                isim
            )
            !=
            onceki.get(
                isim
            )
        )
    ]

    return (
        len(
            farklar
        ) == 0,
        farklar
    )


# ============================================================
# KAYNAKLAR
# ============================================================

def kaynaklari_kontrol_et():

    eksik = [

        isim

        for isim
        in SOURCE_FILES

        if not (
            ROOT
            / isim
        ).exists()
    ]

    if eksik:

        raise FileNotFoundError(
            "Eksik ana Jarvis dosyalari: "
            + ", ".join(
                eksik
            )
        )

    if not (
        ROOT
        / "jarvis_developer.py"
    ).exists():

        raise FileNotFoundError(
            "jarvis_developer.py bulunamadi."
        )


# ============================================================
# DEV WORKSPACE
# ============================================================

def dev_oturumu_olustur():

    zaman = (
        datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
    )

    session = (
        DEV_ROOT
        / (
            "otonom_low_token_"
            + zaman
        )
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

    for isim in SOURCE_FILES:

        shutil.copy2(
            ROOT
            / isim,
            workspace
            / isim
        )

        shutil.copy2(
            ROOT
            / isim,
            original
            / isim
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
    }


def tur_yedegi_olustur(
    workspace,
    iterations,
    tur
):

    backup = (
        iterations
        / f"tur_{tur:05d}_oncesi"
    )

    backup.mkdir(
        parents=True,
        exist_ok=False
    )

    for isim in SOURCE_FILES:

        shutil.copy2(
            workspace
            / isim,
            backup
            / isim
        )

    return backup


def workspace_geri_yukle(
    backup,
    workspace
):

    for isim in SOURCE_FILES:

        shutil.copy2(
            backup
            / isim,
            workspace
            / isim
        )


# ============================================================
# KRITIK KOD SNAPSHOT
# ============================================================

def node_source(
    kaynak,
    node
):

    return (
        ast.get_source_segment(
            kaynak,
            node
        )
        or
        ""
    )


def protected_snapshot(
    workspace
):

    snapshot = {}

    for dosya_adi in SOURCE_FILES:

        kaynak = (
            dosya_oku(
                workspace
                / dosya_adi
            )
        )

        tree = (
            ast.parse(
                kaynak
            )
        )

        funcs = (
            PROTECTED_FUNCTIONS.get(
                dosya_adi,
                set()
            )
        )

        vars_ = (
            PROTECTED_VARIABLES.get(
                dosya_adi,
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

                if (
                    node.name
                    in funcs
                ):

                    snapshot[
                        (
                            dosya_adi,
                            "function",
                            node.name
                        )
                    ] = (
                        node_source(
                            kaynak,
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
                        in vars_
                    ):

                        snapshot[
                            (
                                dosya_adi,
                                "variable",
                                target.id
                            )
                        ] = (
                            node_source(
                                kaynak,
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
                    in vars_
                ):

                    snapshot[
                        (
                            dosya_adi,
                            "variable",
                            target.id
                        )
                    ] = (
                        node_source(
                            kaynak,
                            node
                        )
                    )

    return snapshot


def protected_ayni_mi(
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
# TOKEN TASARRUFLU KOD BAGLAMI
# ============================================================

def top_level_name(
    node
):

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef
        )
    ):

        return node.name

    if isinstance(
        node,
        (
            ast.Assign,
            ast.AnnAssign
        )
    ):

        names = []

        targets = (
            node.targets
            if isinstance(
                node,
                ast.Assign
            )
            else
            [
                node.target
            ]
        )

        for target in targets:

            if isinstance(
                target,
                ast.Name
            ):

                names.append(
                    target.id
                )

        return ",".join(
            names
        )

    return ""


def dosya_indeksi(
    kaynak
):

    tree = (
        ast.parse(
            kaynak
        )
    )

    satirlar = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            satirlar.append(
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

            satirlar.append(
                (
                    f"CLASS {node.name} "
                    f"L{node.lineno}-"
                    f"L{getattr(node, 'end_lineno', node.lineno)}"
                )
            )

        elif isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign
            )
        ):

            name = (
                top_level_name(
                    node
                )
            )

            if name:

                satirlar.append(
                    f"GLOBAL {name} L{node.lineno}"
                )

    metin = (
        "\n".join(
            satirlar
        )
    )

    if (
        len(
            metin
        )
        > MAX_INDEX_CHARS
    ):

        metin = (
            metin[
                :MAX_INDEX_CHARS
            ]
            + "\n[INDEX_KESILDI]"
        )

    return metin


def import_bolumu(
    kaynak,
    limit=2200
):

    tree = (
        ast.parse(
            kaynak
        )
    )

    parcalar = []

    toplam = 0

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom
            )
        ):

            parca = (
                node_source(
                    kaynak,
                    node
                )
            )

            if (
                toplam
                + len(
                    parca
                )
                + 1
                > limit
            ):

                break

            parcalar.append(
                parca
            )

            toplam += (
                len(
                    parca
                )
                + 1
            )

    return (
        "\n".join(
            parcalar
        )
    )


def dugum_puani(
    name,
    metin,
    keywords
):

    ad = (
        name
        or ""
    ).casefold()

    kucuk = (
        metin.casefold()
    )

    puan = 0

    for kelime in keywords:

        k = (
            kelime.casefold()
        )

        if k in ad:

            puan += 30

        adet = (
            kucuk.count(
                k
            )
        )

        puan += (
            min(
                adet,
                8
            )
            * 3
        )

    if (
        "except"
        in kucuk
    ):

        puan += 1

    return puan


def kod_baglami_olustur(
    workspace,
    focus
):

    hedef = (
        focus[
            "target"
        ]
    )

    kaynak = (
        dosya_oku(
            workspace
            / hedef
        )
    )

    tree = (
        ast.parse(
            kaynak
        )
    )

    protected = (
        PROTECTED_FUNCTIONS.get(
            hedef,
            set()
        )
    )

    adaylar = []

    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.Assign,
                ast.AnnAssign
            )
        ):

            continue

        name = (
            top_level_name(
                node
            )
        )

        if (
            name
            in protected
        ):

            continue

        metin = (
            node_source(
                kaynak,
                node
            )
        )

        if not metin:

            continue

        puan = (
            dugum_puani(
                name,
                metin,
                focus[
                    "keywords"
                ]
            )
        )

        if puan > 0:

            adaylar.append(
                (
                    puan,
                    node.lineno,
                    name,
                    metin
                )
            )

    adaylar.sort(
        key=lambda x: (
            -x[
                0
            ],
            x[
                1
            ]
        )
    )

    secilen = []

    toplam = 0

    for (
        puan,
        lineno,
        name,
        metin
    ) in adaylar:

        if (
            len(
                secilen
            )
            >= MAX_SELECTED_NODES
        ):

            break

        parca = (
            metin
        )

        if (
            len(
                parca
            )
            > MAX_NODE_CHARS
        ):

            bas = parca[
                :int(
                    MAX_NODE_CHARS
                    * 0.72
                )
            ]

            son = parca[
                -int(
                    MAX_NODE_CHARS
                    * 0.25
                ):
            ]

            parca = (
                bas
                + "\n# [ORTA KISIM TOKEN TASARRUFU ICIN GOSTERILMEDI]\n"
                + son
            )

        etiketli = (
            f"\n### {name or 'GLOBAL'} "
            f"| L{lineno} "
            f"| skor={puan}\n"
            f"{parca}\n"
        )

        if (
            toplam
            + len(
                etiketli
            )
            > MAX_CONTEXT_CHARS
        ):

            continue

        secilen.append(
            etiketli
        )

        toplam += (
            len(
                etiketli
            )
        )

    if not secilen:

        secilen.append(
            kaynak[
                :MAX_CONTEXT_CHARS
            ]
        )

    return {

        "target":
            hedef,

        "index":
            dosya_indeksi(
                kaynak
            ),

        "imports":
            import_bolumu(
                kaynak
            ),

        "context":
            "\n".join(
                secilen
            ),

        "source_chars":
            len(
                kaynak
            ),

        "context_chars":
            sum(
                len(
                    x
                )
                for x
                in secilen
            ),
    }


# ============================================================
# ANTIGRAVITY
# ============================================================

def agy_bul():

    if AGY_DEFAULT.exists():

        return str(
            AGY_DEFAULT
        )

    bulunan = (
        shutil.which(
            "agy"
        )
        or
        shutil.which(
            "agy.exe"
        )
    )

    if bulunan:

        return bulunan

    raise FileNotFoundError(
        "Antigravity agy.exe bulunamadi: "
        + str(
            AGY_DEFAULT
        )
    )


class AntigravitySession:

    def __init__(
        self,
        session_dir
    ):

        self.session_dir = (
            Path(
                session_dir
            )
        )

        self.agy = (
            agy_bul()
        )

        self.events = (
            queue.Queue()
        )

        self.stderr_lines = []

        self.schema_path = (
            self.session_dir
            / "developer_schema.json"
        )

        self.schema_path.write_text(
            json.dumps(
                DEVELOPER_SCHEMA,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        cmd = [

            self.agy,

            "--model",
            "gpt-oss-120b-medium",

            "--input-format",
            "stream-json",

            "--output-format",
            "stream-json",

            "--json-schema",
            str(
                self.schema_path
            ),

            "--sandbox",
        ]

        creationflags = (
            getattr(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0
            )
            if os.name == "nt"
            else 0
        )

        self.proc = (
            subprocess.Popen(

                cmd,

                stdin=
                    subprocess.PIPE,

                stdout=
                    subprocess.PIPE,

                stderr=
                    subprocess.PIPE,

                text=True,

                encoding=
                    "utf-8",

                errors=
                    "replace",

                bufsize=
                    1,

                cwd=
                    str(
                        self.session_dir
                    ),

                creationflags=
                    creationflags,
            )
        )

        threading.Thread(
            target=
                self._stdout_reader,
            daemon=True
        ).start()

        threading.Thread(
            target=
                self._stderr_reader,
            daemon=True
        ).start()


    def _stdout_reader(
        self
    ):

        try:

            for line in self.proc.stdout:

                line = (
                    line.strip()
                )

                if not line:

                    continue

                try:

                    self.events.put(
                        json.loads(
                            line
                        )
                    )

                except Exception:

                    self.events.put(
                        {
                            "event":
                                "_invalid_json",

                            "raw":
                                line,
                        }
                    )

        finally:

            self.events.put(
                {
                    "event":
                        "_stdout_closed"
                }
            )


    def _stderr_reader(
        self
    ):

        try:

            for line in self.proc.stderr:

                line = (
                    line.rstrip(
                        "\r\n"
                    )
                )

                if line:

                    self.stderr_lines.append(
                        line
                    )

                    self.stderr_lines = (
                        self.stderr_lines[
                            -100:
                        ]
                    )

        except Exception:

            pass


    def alive(
        self
    ):

        return (
            self.proc.poll()
            is None
        )


    def last_stderr(
        self,
        limit=8
    ):

        return (
            "\n".join(
                self.stderr_lines[
                    -limit:
                ]
            )
        )


    def ask(
        self,
        prompt,
        timeout=AGY_RESPONSE_TIMEOUT
    ):

        if not self.alive():

            raise RuntimeError(
                "Antigravity sureci kapali.\n"
                + self.last_stderr()
            )

        mesaj = {

            "event":
                "user",

            "message": {

                "content":
                    prompt,
            },
        }

        self.proc.stdin.write(
            json.dumps(
                mesaj,
                ensure_ascii=False
            )
            + "\n"
        )

        self.proc.stdin.flush()

        deadline = (
            time.monotonic()
            + timeout
        )

        while True:

            kalan = (
                deadline
                - time.monotonic()
            )

            if kalan <= 0:

                raise TimeoutError(
                    f"Antigravity {timeout} saniye "
                    "icinde cevap vermedi."
                )

            try:

                event = (
                    self.events.get(
                        timeout=min(
                            1.0,
                            kalan
                        )
                    )
                )

            except queue.Empty:

                if not self.alive():

                    raise RuntimeError(
                        "Antigravity beklenmedik sekilde kapandi.\n"
                        + self.last_stderr()
                    )

                continue

            if (
                event.get(
                    "event"
                )
                == "_stdout_closed"
            ):

                raise RuntimeError(
                    "Antigravity stdout kapandi.\n"
                    + self.last_stderr()
                )

            if (
                event.get(
                    "event"
                )
                != "result"
            ):

                continue

            sonuc = (
                event.get(
                    "result"
                )
                or {}
            )

            if (
                str(
                    sonuc.get(
                        "status",
                        ""
                    )
                ).upper()
                != "SUCCESS"
            ):

                raise RuntimeError(
                    "Antigravity sonucu basarisiz: "
                    + str(
                        sonuc.get(
                            "status"
                        )
                    )
                    + "\n"
                    + self.last_stderr()
                )

            structured = (
                sonuc.get(
                    "structured_output"
                )
            )

            if isinstance(
                structured,
                str
            ):

                try:

                    structured = (
                        json.loads(
                            structured
                        )
                    )

                except Exception:

                    structured = None

            if not isinstance(
                structured,
                dict
            ):

                response = (
                    sonuc.get(
                        "response",
                        ""
                    )
                )

                if isinstance(
                    response,
                    str
                ):

                    try:

                        structured = (
                            json.loads(
                                response
                            )
                        )

                    except Exception:

                        structured = None

            if not isinstance(
                structured,
                dict
            ):

                raise RuntimeError(
                    "Antigravity structured_output dondurmedi."
                )

            return (
                structured,
                (
                    sonuc.get(
                        "usage"
                    )
                    or {}
                )
            )


    def close(
        self
    ):

        try:

            if self.proc.stdin:

                self.proc.stdin.close()

        except Exception:

            pass

        try:

            self.proc.terminate()

            self.proc.wait(
                timeout=3
            )

        except Exception:

            try:

                self.proc.kill()

            except Exception:

                pass


# ============================================================
# PROMPT
# ============================================================

def recent_changes_text(
    recent_changes,
    limit=6
):

    if not recent_changes:

        return "Yok."

    return (
        "\n".join(
            f"- {x}"
            for x
            in recent_changes[
                -limit:
            ]
        )
    )


def gelistirici_promptu(
    workspace,
    tur,
    request_id,
    focus,
    onceki_feedback,
    recent_changes
):

    baglam = (
        kod_baglami_olustur(
            workspace,
            focus
        )
    )

    prompt = f"""
Sen Jarvis'in kontrollu otonom gelistirme danismanisin.

Bu sistem TOKEN TASARRUFLU MODDA calisiyor.

Sana tum dosya verilmedi.
Sadece ilgili kod bolumleri verildi.

Yalnizca GOSTERILEN KOD ICINDE
kucuk bir iyilestirme oner.

Gerekli kod gorunmuyorsa status='done' dondur.
Tahmin etme.

DOSYA YAZMA.
KOMUT CALISTIRMA.
ARAC KULLANMA.

Gercek degisikligi ve testleri
yerel guvenlik katmani yapacak.

TUR:
{tur}

REQUEST_ID:
{request_id}

HEDEF DOSYA:
{focus['target']}

ALAN:
{focus['name']}

AMAC:
{focus['goal']}

ONCEKI GERI BILDIRIM:
{onceki_feedback or 'Yok.'}

SON KABUL EDILEN GELISTIRMELER:
{recent_changes_text(recent_changes)}

KESIN KURALLAR:

- Sadece {focus['target']} icin cevap ver.

- En fazla BIR kucuk ve faydali degisiklik oner.

- Tum dosyayi yeniden yazma.

- status='patch' ise find,
  asagidaki GOSTERILEN KOD'dan
  HARFI HARFINE alinmis olmali.

- find benzersiz ve mumkun oldugunca kucuk olmali.

- replace gercek kod olmali.

- Placeholder veya '...' kullanma.

- Gosterilmeyen kodu degistirmeye calisma.

- Kritik kapatma, shutdown, restart,
  lock, silme ve kritik surec
  guvenligini zayiflatma.

- Cemil ana projeye dokunma.

- Yeni shell, PowerShell, CMD,
  subprocess, network, silme veya
  credential mekanizmasi ekleme.

- Ana Jarvis'e otomatik terfi
  mekanizmasi ekleme.

- Fayda yoksa status='done' kullan.

- status='done' ise find ve replace
  bos string olsun.

- request_id TAM OLARAK:
  {request_id}

- Yanit yalnizca tanimli
  yapisal semaya uymali.

DOSYA BOYUTU:
{baglam['source_chars']} karakter

BU TUR GONDERILEN KOD:
{baglam['context_chars']} karakter


IMPORTLAR:

{baglam['imports']}


DOSYA INDEKSI:

{baglam['index']}


GOSTERILEN KOD:

<<<CONTEXT_BEGIN>>>

{baglam['context']}

<<<CONTEXT_END>>>
""".strip()

    return (
        prompt,
        baglam
    )


# ============================================================
# DIFF
# ============================================================

def diff_istatistik(
    eski,
    yeni
):

    sm = (
        difflib.SequenceMatcher(
            a=
                eski.splitlines(),
            b=
                yeni.splitlines(),
            autojunk=False
        )
    )

    eklenen = 0
    silinen = 0

    for (
        tag,
        i1,
        i2,
        j1,
        j2
    ) in sm.get_opcodes():

        if tag == "insert":

            eklenen += (
                j2
                - j1
            )

        elif tag == "delete":

            silinen += (
                i2
                - i1
            )

        elif tag == "replace":

            silinen += (
                i2
                - i1
            )

            eklenen += (
                j2
                - j1
            )

    return (
        eklenen,
        silinen
    )


def yeni_eklenen_satirlar(
    eski,
    yeni
):

    return [

        x[
            2:
        ]

        for x
        in difflib.ndiff(
            eski.splitlines(),
            yeni.splitlines()
        )

        if x.startswith(
            "+ "
        )
    ]


def yeni_tehlikeli_kod_var_mi(
    eski,
    yeni
):

    eklenenler = (
        "\n".join(
            yeni_eklenen_satirlar(
                eski,
                yeni
            )
        ).casefold()
    )

    bulunan = [

        p

        for p
        in FORBIDDEN_NEW_PATTERNS

        if (
            p.casefold()
            in eklenenler
        )
    ]

    if bulunan:

        return (
            False,
            (
                "Yeni tehlikeli yurutme kalibi: "
                + ", ".join(
                    bulunan
                )
            )
        )

    return (
        True,
        ""
    )


# ============================================================
# MODEL CEVABI
# ============================================================

def model_cevabini_dogrula(
    veri,
    request_id,
    target_file,
    context_text
):

    if not isinstance(
        veri,
        dict
    ):

        raise ValueError(
            "Antigravity cevabi sozluk degil."
        )

    if (
        veri.get(
            "request_id"
        )
        != request_id
    ):

        raise ValueError(
            "request_id eslesmedi."
        )

    status = (
        str(
            veri.get(
                "status",
                ""
            )
        ).casefold()
    )

    if status not in {
        "patch",
        "done"
    }:

        raise ValueError(
            "status patch veya done olmali."
        )

    if (
        veri.get(
            "target_file"
        )
        != target_file
    ):

        raise ValueError(
            "Yanlis hedef dosya: "
            + str(
                veri.get(
                    "target_file"
                )
            )
        )

    for alan in [
        "summary",
        "reason",
        "find",
        "replace"
    ]:

        if not isinstance(
            veri.get(
                alan
            ),
            str
        ):

            raise ValueError(
                f"{alan} metin olmali."
            )

    if status == "done":

        return

    find_text = (
        veri[
            "find"
        ]
    )

    replace_text = (
        veri[
            "replace"
        ]
    )

    if not find_text.strip():

        raise ValueError(
            "find bos olamaz."
        )

    if (
        len(
            find_text
        )
        > MAX_FIND_CHARS
        or
        len(
            replace_text
        )
        > MAX_REPLACE_CHARS
    ):

        raise ValueError(
            "Patch metni token/guvenlik sinirini asti."
        )

    if (
        find_text
        not in context_text
    ):

        raise ValueError(
            "find bu tur Antigravity'ye "
            "gosterilen kod baglaminda yok."
        )

    toplam = (
        (
            find_text
            + "\n"
            + replace_text
        ).casefold()
    )

    placeholders = [

        "HEDEF DOSYANIN TAM ICERIGI",
        "Kisa gelistirme ozeti",
        "Kisa gerekce",
        "BURAYA KOD",
        "...existing code...",
        "... mevcut kod ...",
    ]

    for p in placeholders:

        if (
            p.casefold()
            in toplam
        ):

            raise ValueError(
                "Placeholder cevap reddedildi: "
                + p
            )


# ============================================================
# PATCH
# ============================================================

def patch_uygula(
    veri,
    workspace,
    protected_baseline,
    seen_patch_hashes
):

    if (
        str(
            veri[
                "status"
            ]
        ).casefold()
        == "done"
    ):

        return {

            "done":
                True,

            "summary":
                veri[
                    "summary"
                ],

            "reason":
                veri[
                    "reason"
                ],
        }

    hedef = (
        veri[
            "target_file"
        ]
    )

    find_text = (
        veri[
            "find"
        ]
    )

    replace_text = (
        veri[
            "replace"
        ]
    )

    hedef_yol = (
        workspace
        / hedef
    )

    eski = (
        dosya_oku(
            hedef_yol
        )
    )

    adet = (
        eski.count(
            find_text
        )
    )

    if adet == 0:

        raise ValueError(
            "find mevcut workspace "
            "dosyasinda bulunamadi."
        )

    if adet > 1:

        raise ValueError(
            f"find dosyada {adet} kez geciyor; "
            "yeterince benzersiz degil."
        )

    patch_hash = (
        hashlib.sha256(
            (
                hedef
                + "\0"
                + find_text
                + "\0"
                + replace_text
            ).encode(
                "utf-8"
            )
        ).hexdigest()
    )

    if (
        patch_hash
        in seen_patch_hashes
    ):

        raise ValueError(
            "Ayni patch daha once denendi."
        )

    yeni = (
        eski.replace(
            find_text,
            replace_text,
            1
        )
    )

    if yeni == eski:

        raise ValueError(
            "Patch degisiklik uretmedi."
        )

    (
        eklenen,
        silinen
    ) = (
        diff_istatistik(
            eski,
            yeni
        )
    )

    if (
        silinen
        > MAX_REMOVED_LINES
    ):

        raise ValueError(
            f"Tek turda {silinen} satir "
            "silme siniri asildi."
        )

    if (
        eklenen
        > MAX_ADDED_LINES
    ):

        raise ValueError(
            f"Tek turda {eklenen} satir "
            "ekleme siniri asildi."
        )

    if (
        eklenen
        + silinen
        > MAX_TOTAL_DIFF_LINES
    ):

        raise ValueError(
            "Toplam diff siniri asildi."
        )

    eski_satir = max(
        1,
        len(
            eski.splitlines()
        )
    )

    yeni_satir = (
        len(
            yeni.splitlines()
        )
    )

    if (
        yeni_satir
        <
        eski_satir
        * MAX_FILE_SHRINK_RATIO
    ):

        raise ValueError(
            "Dosyanin buyuk kismini "
            "silmeye calisan patch reddedildi."
        )

    (
        guvenli,
        neden
    ) = (
        yeni_tehlikeli_kod_var_mi(
            eski,
            yeni
        )
    )

    if not guvenli:

        raise ValueError(
            neden
        )

    if hasattr(
        core,
        "kod_guvenli_mi"
    ):

        (
            guvenli2,
            neden2
        ) = (
            core.kod_guvenli_mi(
                eski,
                yeni
            )
        )

        if not guvenli2:

            raise ValueError(
                "Cekirdek guvenlik reddi: "
                + str(
                    neden2
                )
            )

    # SADECE TEST WORKSPACE
    dosya_yaz(
        hedef_yol,
        yeni
    )

    ast.parse(
        yeni
    )

    if not protected_ayni_mi(
        workspace,
        protected_baseline
    ):

        raise ValueError(
            "Kilitli kritik guvenlik kodu "
            "degistirilmeye calisildi."
        )

    seen_patch_hashes.add(
        patch_hash
    )

    return {

        "done":
            False,

        "target":
            hedef,

        "summary":
            veri[
                "summary"
            ],

        "reason":
            veri[
                "reason"
            ],

        "added_lines":
            eklenen,

        "removed_lines":
            silinen,
    }


# ============================================================
# TEST
# ============================================================

def py_compile_test(
    workspace
):

    sonuclar = []

    genel = True

    for isim in SOURCE_FILES:

        try:

            p = (
                subprocess.run(

                    [
                        sys.executable,
                        "-m",
                        "py_compile",
                        str(
                            workspace
                            / isim
                        ),
                    ],

                    cwd=
                        str(
                            workspace
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
                        45,
                )
            )

            ok_ = (
                p.returncode
                == 0
            )

            cikti = (
                (
                    p.stdout
                    or ""
                )
                +
                (
                    p.stderr
                    or ""
                )
            ).strip()

        except Exception as e:

            ok_ = False

            cikti = (
                str(
                    e
                )
            )

        sonuclar.append(
            {

                "file":
                    isim,

                "success":
                    ok_,

                "output":
                    cikti,
            }
        )

        genel = (
            genel
            and ok_
        )

    return (
        genel,
        sonuclar
    )


def tam_test(
    workspace
):

    (
        compile_ok,
        compile_results
    ) = (
        py_compile_test(
            workspace
        )
    )

    if not compile_ok:

        hata_metin = (
            " | ".join(

                f"{x['file']}: {x['output']}"

                for x
                in compile_results

                if not x[
                    "success"
                ]
            )
        )

        return (
            False,
            (
                "py_compile basarisiz: "
                + hata_metin
            )
        )

    try:

        (
            behavior_ok,
            behavior_results
        ) = (
            core.davranis_testleri(
                workspace,
                baslik_yaz=False
            )
        )

    except Exception as e:

        return (
            False,
            (
                "Davranis testleri calistirilamadi: "
                + str(
                    e
                )
            )
        )

    if not behavior_ok:

        return (
            False,
            (
                "Davranis/guvenlik testlerinden "
                "en az biri basarisiz."
            )
        )

    toplam = (
        len(
            behavior_results
        )
        if isinstance(
            behavior_results,
            list
        )
        else None
    )

    basarili = 0

    if isinstance(
        behavior_results,
        list
    ):

        for item in behavior_results:

            if item is True:

                basarili += 1

            elif (
                isinstance(
                    item,
                    dict
                )
                and
                (
                    item.get(
                        "success"
                    )
                    is True
                    or
                    item.get(
                        "passed"
                    )
                    is True
                )
            ):

                basarili += 1

    if toplam:

        return (
            True,
            (
                "py_compile basarili; "
                f"davranis testleri "
                f"{basarili}/{toplam}."
            )
        )

    return (
        True,
        (
            "py_compile ve davranis/"
            "guvenlik testleri basarili."
        )
    )


# ============================================================
# TOKEN GOSTERGESI
# ============================================================

def token_bilgisi_yaz(
    usage
):

    if not isinstance(
        usage,
        dict
    ):

        return

    if not usage:

        return

    input_tokens = (
        usage.get(
            "input_tokens",
            usage.get(
                "prompt_tokens"
            )
        )
    )

    output_tokens = (
        usage.get(
            "output_tokens",
            usage.get(
                "completion_tokens"
            )
        )
    )

    total_tokens = (
        usage.get(
            "total_tokens"
        )
    )

    parcalar = []

    if input_tokens is not None:

        parcalar.append(
            f"giris={input_tokens}"
        )

    if output_tokens is not None:

        parcalar.append(
            f"cikis={output_tokens}"
        )

    if total_tokens is not None:

        parcalar.append(
            f"toplam={total_tokens}"
        )

    if parcalar:

        durum(
            "TOKEN",
            (
                "Bu tur: "
                + " | ".join(
                    parcalar
                )
            )
        )


# ============================================================
# FINAL DIFF
# ============================================================

def diff_kaydet(
    session_info
):

    yol = (
        session_info[
            "session"
        ]
        / "final_changes.diff"
    )

    parcalar = []

    for isim in SOURCE_FILES:

        eski = (
            dosya_oku(
                session_info[
                    "original"
                ]
                / isim
            ).splitlines(
                keepends=True
            )
        )

        yeni = (
            dosya_oku(
                session_info[
                    "workspace"
                ]
                / isim
            ).splitlines(
                keepends=True
            )
        )

        parcalar.extend(

            difflib.unified_diff(

                eski,

                yeni,

                fromfile=
                    f"original/{isim}",

                tofile=
                    f"workspace/{isim}",
            )
        )

    yol.write_text(
        "".join(
            parcalar
        ),
        encoding="utf-8"
    )

    return yol


# ============================================================
# RAPOR
# ============================================================

def rapor_kaydet(
    session_info,
    toplam_tur,
    accepted,
    rejected,
    done_count,
    main_hash_before,
    stop_reason
):

    (
        main_ok,
        main_farklar
    ) = (
        hashler_ayni_mi(
            ROOT,
            main_hash_before
        )
    )

    rapor = {

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "mode":
            "low_token",

        "total_turns":
            toplam_tur,

        "accepted_changes":
            accepted,

        "rejected_changes":
            rejected,

        "done_responses":
            done_count,

        "stop_reason":
            stop_reason,

        "main_files_unchanged":
            main_ok,

        "main_changed_files":
            main_farklar,

        "workspace":
            str(
                session_info[
                    "workspace"
                ]
            ),

        "automatic_promotion":
            False,

        "max_context_chars_per_turn":
            MAX_CONTEXT_CHARS,

        "fresh_antigravity_session_each_turn":
            FRESH_AGY_EVERY_TURN,
    }

    yol = (
        session_info[
            "session"
        ]
        / "otonom_low_token_report.json"
    )

    yol.write_text(
        json.dumps(
            rapor,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return yol


# ============================================================
# MAIN
# ============================================================

def main():

    kaynaklari_kontrol_et()

    main_hash_before = (
        kaynak_hashleri(
            ROOT
        )
    )

    session_info = (
        dev_oturumu_olustur()
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

    protected_baseline = (
        protected_snapshot(
            workspace
        )
    )

    seen_patch_hashes = set()

    baslik(
        "JARVIS OTONOM GELISTIRICI - DUSUK TOKEN MODU"
    )

    durum(
        "AI",
        "Antigravity agy.exe"
    )

    durum(
        "TOKEN",
        (
            "Tum dosya yerine yalnizca "
            "ilgili kod bolumleri gonderilir."
        )
    )

    durum(
        "TOKEN",
        (
            "Her tur yeni Antigravity oturumu; "
            "eski konusma baglami tasinmaz."
        )
    )

    durum(
        "GUVENLIK",
        (
            "Ana Jarvis dosyalarina "
            "otomatik yazma KAPALI."
        )
    )

    durum(
        "GUVENLIK",
        (
            "Kritik kapatma/guc/silme "
            "kodlari kilitli."
        )
    )

    durum(
        "DURDUR",
        "Ctrl+C"
    )

    durum(
        "WORKSPACE",
        str(
            workspace
        )
    )

    (
        baseline_ok,
        baseline_msg
    ) = (
        tam_test(
            workspace
        )
    )

    if not baseline_ok:

        raise RuntimeError(
            (
                "Baslangic test kopyasi "
                "saglam degil: "
                + baseline_msg
            )
        )

    durum(
        "TEST",
        baseline_msg
    )

    toplam_tur = 0

    accepted = 0
    rejected = 0
    done_count = 0

    focus_cursor = 0
    focus_retry = 0
    done_streak = 0

    onceki_feedback = ""

    recent_changes = []

    stop_reason = (
        "Kullanici durdurdu."
    )

    try:

        while True:

            toplam_tur += 1

            focus = (
                FOCUS_AREAS[
                    focus_cursor
                    % len(
                        FOCUS_AREAS
                    )
                ]
            )

            request_id = (
                "JARVIS-"
                + uuid.uuid4().hex[
                    :12
                ].upper()
            )

            print()

            durum(
                "JARVIS",
                (
                    f"Tur {toplam_tur} | "
                    f"{focus['name']} | "
                    f"{focus['target']}"
                )
            )

            # =================================================
            # ANA JARVIS BUTUNLUK KONTROLU
            # =================================================

            (
                main_ok,
                main_farklar
            ) = (
                hashler_ayni_mi(
                    ROOT,
                    main_hash_before
                )
            )

            if not main_ok:

                stop_reason = (
                    "Ana Jarvis dosyalarinda "
                    "beklenmedik degisiklik algilandi."
                )

                raise RuntimeError(
                    stop_reason
                    + " "
                    + ", ".join(
                        main_farklar
                    )
                )

            # =================================================
            # YEDEK
            # =================================================

            backup = (
                tur_yedegi_olustur(
                    workspace,
                    iterations,
                    toplam_tur
                )
            )

            # =================================================
            # TOKEN TASARRUFLU PROMPT
            # =================================================

            (
                prompt,
                baglam
            ) = (
                gelistirici_promptu(
                    workspace,
                    toplam_tur,
                    request_id,
                    focus,
                    onceki_feedback,
                    recent_changes
                )
            )

            durum(
                "TOKEN",
                (
                    f"Tam dosya="
                    f"{baglam['source_chars']:,} karakter"
                    " | "
                    f"gonderilen kod="
                    f"{baglam['context_chars']:,} karakter"
                    " | "
                    f"toplam prompt="
                    f"{len(prompt):,}"
                )
            )

            durum(
                "ANTIGRAVITY",
                "Kucuk kod baglami inceleniyor..."
            )

            # =================================================
            # HER TUR YENI ANTIGRAVITY
            # =================================================

            agy = None

            try:

                agy = (
                    AntigravitySession(
                        session_info[
                            "session"
                        ]
                    )
                )

                (
                    veri,
                    usage
                ) = (
                    agy.ask(
                        prompt
                    )
                )

                token_bilgisi_yaz(
                    usage
                )

            except Exception as e:

                rejected += 1
                focus_retry += 1

                workspace_geri_yukle(
                    backup,
                    workspace
                )

                durum(
                    "HATA",
                    (
                        "Antigravity turu tamamlanamadi: "
                        + str(
                            e
                        )
                    )
                )

                onceki_feedback = (
                    "Onceki tur teknik olarak tamamlanamadi. "
                    "Daha kucuk ve kesin cevap ver."
                )

                if (
                    focus_retry
                    >= MAX_RETRY_PER_FOCUS
                ):

                    durum(
                        "ATLA",
                        (
                            "Bu alan 3 kez takildi; "
                            "token israfini onlemek icin "
                            "sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    focus_retry = 0

                time.sleep(
                    TUR_ARASI_BEKLEME
                )

                continue

            finally:

                if agy is not None:

                    agy.close()

            # =================================================
            # MODEL CEVABI
            # =================================================

            try:

                model_cevabini_dogrula(
                    veri,
                    request_id,
                    focus[
                        "target"
                    ],
                    baglam[
                        "context"
                    ]
                )

            except Exception as e:

                rejected += 1
                focus_retry += 1

                workspace_geri_yukle(
                    backup,
                    workspace
                )

                durum(
                    "RED",
                    (
                        "Yapisal cevap reddedildi: "
                        + str(
                            e
                        )
                    )
                )

                onceki_feedback = (
                    "Onceki cevap yerel "
                    "dogrulamadan gecmedi: "
                    + str(
                        e
                    )
                )

                if (
                    focus_retry
                    >= MAX_RETRY_PER_FOCUS
                ):

                    durum(
                        "ATLA",
                        (
                            "Bu alan 3 kez reddedildi; "
                            "token israfini onlemek icin "
                            "sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    focus_retry = 0

                time.sleep(
                    TUR_ARASI_BEKLEME
                )

                continue

            # =================================================
            # DONE
            # =================================================

            if (
                str(
                    veri[
                        "status"
                    ]
                ).casefold()
                == "done"
            ):

                done_count += 1
                done_streak += 1

                focus_cursor += 1
                focus_retry = 0

                durum(
                    "DEGISIKLIK_YOK",
                    (
                        veri[
                            "summary"
                        ]
                        or
                        focus[
                            "name"
                        ]
                    )
                )

                onceki_feedback = (
                    "Onceki alanda uygun "
                    "yeni degisiklik bulunmadi."
                )

                if (
                    done_streak
                    >= len(
                        FOCUS_AREAS
                    )
                ):

                    durum(
                        "BEKLE",
                        (
                            "Tum alanlar temiz gorunuyor; "
                            "token tasarrufu icin "
                            "20 saniye bekleniyor."
                        )
                    )

                    done_streak = 0

                    time.sleep(
                        TAM_DONGU_BEKLEME
                    )

                else:

                    time.sleep(
                        TUR_ARASI_BEKLEME
                    )

                continue

            done_streak = 0

            durum(
                "ONERI",
                (
                    veri[
                        "summary"
                    ]
                    or
                    "Kucuk kod degisikligi onerildi."
                )
            )

            # =================================================
            # PATCH
            # =================================================

            try:

                uygulama = (
                    patch_uygula(
                        veri,
                        workspace,
                        protected_baseline,
                        seen_patch_hashes
                    )
                )

            except Exception as e:

                rejected += 1
                focus_retry += 1

                workspace_geri_yukle(
                    backup,
                    workspace
                )

                durum(
                    "RED",
                    (
                        "Patch yerel guvenlik "
                        "tarafindan reddedildi: "
                        + str(
                            e
                        )
                    )
                )

                onceki_feedback = (
                    "Onceki patch reddedildi: "
                    + str(
                        e
                    )
                    + ". Daha kucuk ve kesin patch oner."
                )

                if (
                    focus_retry
                    >= MAX_RETRY_PER_FOCUS
                ):

                    durum(
                        "ATLA",
                        (
                            "Bu alan 3 kez reddedildi; "
                            "token israfini onlemek icin "
                            "sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    focus_retry = 0

                time.sleep(
                    TUR_ARASI_BEKLEME
                )

                continue

            durum(
                "PATCH",
                (
                    f"{uygulama['target']} | "
                    f"+{uygulama['added_lines']} "
                    f"/ -{uygulama['removed_lines']} satir"
                )
            )

            # =================================================
            # TEST
            # =================================================

            durum(
                "TEST",
                (
                    "Derleme ve davranis "
                    "testleri calisiyor..."
                )
            )

            (
                test_ok,
                test_msg
            ) = (
                tam_test(
                    workspace
                )
            )

            if not test_ok:

                rejected += 1
                focus_retry += 1

                workspace_geri_yukle(
                    backup,
                    workspace
                )

                durum(
                    "TEST_RED",
                    test_msg
                )

                durum(
                    "GERI_AL",
                    "Basarisiz patch geri alindi."
                )

                onceki_feedback = (
                    "Onceki patch testlerden gecmedi: "
                    + test_msg
                )

                if (
                    focus_retry
                    >= MAX_RETRY_PER_FOCUS
                ):

                    durum(
                        "ATLA",
                        (
                            "Bu alan 3 kez basarisiz oldu; "
                            "token israfini onlemek icin "
                            "sonraki alana geciliyor."
                        )
                    )

                    focus_cursor += 1
                    focus_retry = 0

                time.sleep(
                    TUR_ARASI_BEKLEME
                )

                continue

            # =================================================
            # KRITIK KOD
            # =================================================

            if not protected_ayni_mi(
                workspace,
                protected_baseline
            ):

                rejected += 1

                workspace_geri_yukle(
                    backup,
                    workspace
                )

                durum(
                    "GUVENLIK_RED",
                    (
                        "Kilitli kritik kod degisti; "
                        "patch geri alindi."
                    )
                )

                focus_cursor += 1
                focus_retry = 0

                time.sleep(
                    TUR_ARASI_BEKLEME
                )

                continue

            # =================================================
            # ANA JARVIS
            # =================================================

            (
                main_ok,
                main_farklar
            ) = (
                hashler_ayni_mi(
                    ROOT,
                    main_hash_before
                )
            )

            if not main_ok:

                stop_reason = (
                    "Ana Jarvis butunlugu bozuldu."
                )

                raise RuntimeError(
                    stop_reason
                    + " "
                    + ", ".join(
                        main_farklar
                    )
                )

            # =================================================
            # KABUL
            # =================================================

            accepted += 1

            focus_cursor += 1
            focus_retry = 0

            recent_changes.append(
                (
                    f"{uygulama['target']}: "
                    f"{uygulama['summary']}"
                )
            )

            recent_changes = (
                recent_changes[
                    -8:
                ]
            )

            durum(
                "TEST",
                test_msg
            )

            durum(
                "KABUL",
                (
                    "Degisiklik test surumune "
                    "kabul edildi."
                )
            )

            durum(
                "ANA_JARVIS",
                "Degistirilmedi."
            )

            durum(
                "SAYAC",
                (
                    f"Kabul={accepted} | "
                    f"Red={rejected} | "
                    f"Degisiklik yok={done_count}"
                )
            )

            onceki_feedback = (
                "Onceki patch tum testlerden gecti. "
                "Ayni degisikligi tekrarlama."
            )

            time.sleep(
                TUR_ARASI_BEKLEME
            )

    # ========================================================
    # CTRL+C
    # ========================================================

    except KeyboardInterrupt:

        stop_reason = (
            "Kullanici Ctrl+C ile durdurdu."
        )

        print()

        durum(
            "DURDUR",
            (
                "Ctrl+C alindi; "
                "otonom gelistirme kapatiliyor..."
            )
        )

    # ========================================================
    # RAPOR
    # ========================================================

    finally:

        diff_path = (
            diff_kaydet(
                session_info
            )
        )

        report_path = (
            rapor_kaydet(
                session_info,
                toplam_tur,
                accepted,
                rejected,
                done_count,
                main_hash_before,
                stop_reason
            )
        )

        (
            main_ok,
            main_farklar
        ) = (
            hashler_ayni_mi(
                ROOT,
                main_hash_before
            )
        )

        baslik(
            "JARVIS DUSUK TOKEN OTONOM GELISTIRICI DURDU"
        )

        durum(
            "TUR",
            str(
                toplam_tur
            )
        )

        durum(
            "KABUL",
            str(
                accepted
            )
        )

        durum(
            "RED",
            str(
                rejected
            )
        )

        durum(
            "DEGISIKLIK_YOK",
            str(
                done_count
            )
        )

        durum(
            "WORKSPACE",
            str(
                workspace
            )
        )

        durum(
            "DIFF",
            str(
                diff_path
            )
        )

        durum(
            "RAPOR",
            str(
                report_path
            )
        )

        if main_ok:

            durum(
                "ANA_JARVIS",
                (
                    "Guvenli; ana dosyalar "
                    "degistirilmedi."
                )
            )

        else:

            durum(
                "UYARI",
                (
                    "Ana dosyalarda beklenmedik fark: "
                    + ", ".join(
                        main_farklar
                    )
                )
            )

        durum(
            "TERFI",
            (
                "Otomatik terfi yapilmadi; "
                "son test surumu workspace'te kaldi."
            )
        )


# ============================================================
# ASAMA 2 EKLENTISI
# Asama 1'in test/rollback/patch motoru korunur.
# Sadece yeni read-only yetenekler ve yeni AI cagrisi eklenir.
# ============================================================

ASAMA2_MODEL = "gpt-oss-120b-medium"
ASAMA2_AGENT = "jarvis-advisor"
ASAMA2_AI_TEMP = Path.home() / "Jarvis_AI_Temp"
ASAMA2_MAX_PROMPT = 24000
ASAMA2_MAX_RETRY = 2
ASAMA2_CONTEXT_LIMIT = 10500

ASAMA2_YETENEKLER = [
    {
        "name": "Uygulama durum sorgusu",
        "action": "app_status",
        "helper": "uygulama_durumu_sorgula",
        "tool_keywords": [
            "araci_calistir",
            "calisan_surecler",
            "surec_eslesmesi_bul",
            "PROCESS_ESLEME",
            "uygulama",
            "process",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak app_status action'ini ekle. args.app bir uygulama adi olsun. "
            "Yalnizca kullanici acikca sordugunda o uygulamanin calisip calismadigini "
            "read-only sorgula. Var olan calisan_surecler/surec_eslesmesi_bul "
            "mekanizmasini yeniden kullan. Uygulama acma veya kapatma yapma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina app_status action'ini ekle. "
            "args {\"app\":\"uygulama adi\"}. Yalnizca kullanici acikca bir "
            "uygulamanin calisip calismadigini sorarsa kullanilacagini belirt."
        ),
    },
    {
        "name": "Calisan uygulamalari listeleme",
        "action": "list_running_apps",
        "helper": "calisan_uygulamalari_listele",
        "tool_keywords": [
            "araci_calistir",
            "calisan_surecler",
            "process",
            "uygulama",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak list_running_apps action'ini ekle. args bos olabilir. "
            "Var olan calisan_surecler() sonucunu read-only kullanarak calisan "
            "uygulama/process adlarini tekrar etmeyecek sekilde dondur. "
            "Hicbir sureci sonlandirma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina list_running_apps action'ini ekle. "
            "args bos nesne. Yalnizca kullanici acikca calisan uygulamalari "
            "listelemeyi isterse kullanilacagini belirt."
        ),
    },
    {
        "name": "Disk bos alan bilgisi",
        "action": "disk_info",
        "helper": "disk_bilgisi",
        "tool_keywords": [
            "araci_calistir",
            "shutil",
            "HOME",
            "disk",
            "Path",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak disk_info action'ini ekle. Varsayilan olarak HOME'un "
            "bulundugu diskin total/used/free bilgisini read-only dondur. "
            "Mevcut shutil ve HOME/Path yapilarini kullan; yeni import ekleme. "
            "Dosya tarama, yazma veya silme yapma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina disk_info action'ini ekle. args bos nesne. "
            "Kullanici disk alani veya bos alani acikca sordugunda kullanilacagini belirt."
        ),
    },
    {
        "name": "Bilinen klasor bilgisi",
        "action": "known_folders",
        "helper": "bilinen_klasorleri_goster",
        "tool_keywords": [
            "araci_calistir",
            "HOME",
            "Desktop",
            "Documents",
            "Downloads",
            "Path",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak known_folders action'ini ekle. HOME, Desktop, Documents "
            "ve Downloads gibi temel kullanici klasorlerinin yollarini ve "
            "mevcut olup olmadiklarini read-only dondur. Klasor acma, olusturma, "
            "tasima veya silme yapma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina known_folders action'ini ekle. args bos nesne. "
            "Yalnizca kullanici temel klasor yollarini acikca sorarsa kullan."
        ),
    },
    {
        "name": "Yerel hedef metadata sorgusu",
        "action": "file_metadata",
        "helper": "yerel_hedef_metalari",
        "tool_keywords": [
            "araci_calistir",
            "yerel_hedef_bul",
            "find_local",
            "Path",
            "stat",
            "dosya",
            "klasor",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak file_metadata action'ini ekle. args.query hedef dosya "
            "veya klasor sorgusu olsun. Var olan yerel hedef bulma mantigini "
            "yeniden kullan. Yalnizca ad, tam yol, dosya/klasor turu, boyut ve "
            "mtime gibi metadata dondur; dosya icerigini okuma ve hicbir sey yazma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina file_metadata action'ini ekle. "
            "args {\"query\":\"dosya veya klasor\"}. Yalnizca kullanici belirli "
            "bir hedefin metadata/boyut/degistirilme bilgisini acikca sorarsa kullan."
        ),
    },
    {
        "name": "Jarvis yetenek sorgusu",
        "action": "capabilities",
        "helper": "guvenli_yetenekleri_listele",
        "tool_keywords": [
            "araci_calistir",
            "action",
            "open_app",
            "find_local",
            "web_search",
            "sonuc",
        ],
        "tool_goal": (
            "Tam olarak capabilities action'ini ekle. args bos nesne. "
            "Jarvis'in kullaniciya sunabildigi temel action adlarini read-only "
            "bir liste olarak dondur. Hicbir action'i calistirma."
        ),
        "assistant_goal": (
            "Mevcut TOOL talimatlarina capabilities action'ini ekle. args bos nesne. "
            "Kullanici Jarvis'in neler yapabildigini acikca sorarsa kullan."
        ),
    },
]

ASAMA2_YENI_SATIR_YASAK = [
    "os.startfile(",
    "subprocess.",
    "os.system(",
    "uygulama_ac(",
    "uygulama_kapat(",
    "bilgisayari_kilitle(",
    "bilgisayari_kapat(",
    "bilgisayari_yeniden_baslat(",
    "yerel_sil(",
    "yerel_tasi(",
    "yerel_kopyala(",
    "yerel_yeniden_adlandir(",
    "web_ara(",
    "web_sayfasi_ac(",
    "godot_test_projesini_ac(",
    "geri_donusum_kutusunu_ac(",
    "windows_ayarlari_ac(",
    ".read_text(",
    ".read_bytes(",
    "open(",
    "send2trash(",
    "shutil.copy(",
    "shutil.copy2(",
    "shutil.move(",
    "shutil.rmtree(",
    ".write_text(",
    ".write_bytes(",
    ".mkdir(",
    ".rename(",
    ".unlink(",
    ".touch(",
    "requests.",
    "httpx.",
    "urllib.request",
    "socket.",
    "winreg.",
    "pyautogui",
    "send_keys(",
    "type_keys(",
    "click_input(",
    "taskkill",
    "--dangerously-skip-permissions",
]


def asama2_stage1_adaylari():
    adaylar = []

    if not DEV_ROOT.exists():
        return adaylar

    for session in DEV_ROOT.glob("otonom_low_token_*"):
        if not session.is_dir():
            continue

        workspace = session / "workspace"
        rapor_yolu = session / "otonom_low_token_report.json"

        if not workspace.is_dir():
            continue

        if not all(
            (workspace / isim).exists()
            for isim in SOURCE_FILES
        ):
            continue

        rapor = {}

        if rapor_yolu.exists():
            try:
                rapor = json.loads(
                    rapor_yolu.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                rapor = {}

        if rapor.get("main_files_unchanged") is False:
            continue

        try:
            accepted = int(
                rapor.get(
                    "accepted_changes",
                    0
                )
                or 0
            )
        except Exception:
            accepted = 0

        try:
            turns = int(
                rapor.get(
                    "total_turns",
                    0
                )
                or 0
            )
        except Exception:
            turns = 0

        try:
            mtime = session.stat().st_mtime
        except Exception:
            mtime = 0.0

        adaylar.append(
            {
                "session": session,
                "workspace": workspace,
                "accepted": accepted,
                "turns": turns,
                "mtime": mtime,
            }
        )

    adaylar.sort(
        key=lambda x: (
            x["accepted"],
            x["turns"],
            x["mtime"],
        ),
        reverse=True,
    )

    return adaylar


def asama2_stage1_kaynagini_sec():
    for aday in asama2_stage1_adaylari()[:12]:
        try:
            ok, msg = tam_test(
                aday["workspace"]
            )
        except Exception:
            ok = False
            msg = ""

        if ok:
            return aday, msg

    ok, msg = tam_test(ROOT)

    if not ok:
        raise RuntimeError(
            "Saglam Asama 1 workspace'i bulunamadi ve "
            "ana Jarvis de testten gecmedi: "
            + str(msg)
        )

    return (
        {
            "session": ROOT,
            "workspace": ROOT,
            "accepted": 0,
            "turns": 0,
            "mtime": 0.0,
        },
        msg,
    )


def asama2_oturumu_olustur(source_workspace):
    zaman = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    session = (
        DEV_ROOT
        / (
            "yetenek_stage2_"
            + zaman
        )
    )

    workspace = session / "workspace"
    original = session / "original"
    iterations = session / "iterations"
    cap_backups = session / "capability_backups"

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
    cap_backups.mkdir(
        parents=True,
        exist_ok=True
    )

    for isim in SOURCE_FILES:
        shutil.copy2(
            source_workspace / isim,
            workspace / isim
        )
        shutil.copy2(
            source_workspace / isim,
            original / isim
        )

    return {
        "session": session,
        "workspace": workspace,
        "original": original,
        "iterations": iterations,
        "capability_backups": cap_backups,
    }


def asama2_snapshot(workspace, hedef):
    hedef.mkdir(
        parents=True,
        exist_ok=False
    )

    for isim in SOURCE_FILES:
        shutil.copy2(
            workspace / isim,
            hedef / isim
        )

    return hedef


def asama2_snapshot_geri(snapshot, workspace):
    for isim in SOURCE_FILES:
        shutil.copy2(
            snapshot / isim,
            workspace / isim
        )


def asama2_pencere(kaynak, anchor, once=1800, sonra=3600):
    pos = kaynak.casefold().find(
        anchor.casefold()
    )

    if pos < 0:
        return ""

    bas = max(
        0,
        pos - once
    )
    son = min(
        len(kaynak),
        pos + len(anchor) + sonra
    )

    return kaynak[bas:son]


def asama2_baglam(workspace, spec, step):
    if step in {"helper_add", "route_add"}:
        if step == "helper_add":
            focus = {
                "name": spec["name"] + " - helper ekleme",
                "target": "jarvis_tools.py",
                "keywords": spec["tool_keywords"] + [spec["helper"]],
                "goal": spec["tool_goal"],
            }
        else:
            focus = {
                "name": spec["name"] + " - route ekleme",
                "target": "jarvis_tools.py",
                "keywords": [
                    "araci_calistir",
                    spec["action"],
                    spec["helper"],
                    "action",
                    "args",
                    "sonuc",
                ],
                "goal": (
                    f"Yalnizca {spec['action']} route'unu mevcut "
                    f"{spec['helper']} helper'ina bagla."
                ),
            }
    else:
        focus = {
            "name": spec["name"] + " - TOOL entegrasyonu",
            "target": "jarvis_tools.py",
            "keywords": [
                "arac_aciklamalari",
                "Kullanabilecegin yerel Jarvis araclari",
                spec["action"],
                "args",
                "return",
            ],
            "goal": spec["assistant_goal"],
        }

    eski_context_limit = MAX_CONTEXT_CHARS
    eski_index_limit = MAX_INDEX_CHARS
    eski_node_limit = MAX_NODE_CHARS
    eski_node_sayisi = MAX_SELECTED_NODES

    globals()["MAX_CONTEXT_CHARS"] = 5600
    globals()["MAX_INDEX_CHARS"] = 2100
    globals()["MAX_NODE_CHARS"] = 3000
    globals()["MAX_SELECTED_NODES"] = 4

    try:
        baglam = kod_baglami_olustur(
            workspace,
            focus
        )
    finally:
        globals()["MAX_CONTEXT_CHARS"] = eski_context_limit
        globals()["MAX_INDEX_CHARS"] = eski_index_limit
        globals()["MAX_NODE_CHARS"] = eski_node_limit
        globals()["MAX_SELECTED_NODES"] = eski_node_sayisi

    kaynak = dosya_oku(
        workspace / focus["target"]
    )

    ekstra = []

    if step == "helper_add":
        anchors = [
            "def sonuc(",
        ]

        if spec["action"] in {
            "app_status",
            "list_running_apps",
        }:
            anchors.append("def calisan_surecler")

        if spec["action"] == "app_status":
            anchors.append("def surec_eslesmesi_bul")

        if spec["action"] == "file_metadata":
            anchors.append("def yerel_hedef_bul")

        if spec["action"] in {
            "disk_info",
            "known_folders",
        }:
            anchors.append("HOME =")

    elif step == "route_add":
        anchors = [
            "def araci_calistir",
            f"def {spec['helper']}",
            "def sonuc(",
        ]
    else:
        # Assistant entegrasyonunda modele genel test dosyasini degil,
        # yalnizca mevcut arac_aciklamalari() fonksiyonunu goster.
        try:
            arac_fonksiyonu = (
                asama2_fonksiyonlar(kaynak)
                .get("arac_aciklamalari", "")
                .strip()
            )
        except Exception:
            arac_fonksiyonu = ""

        if arac_fonksiyonu:
            baglam["context"] = arac_fonksiyonu[:ASAMA2_CONTEXT_LIMIT]
            baglam["context_chars"] = len(baglam["context"])
            return focus, baglam

        anchors = [
            "def arac_aciklamalari",
            "Kullanabilecegin yerel Jarvis araclari",
        ]

    for anchor in anchors:
        parca = asama2_pencere(
            kaynak,
            anchor,
            once=1200,
            sonra=3000,
        ).strip()

        if not parca:
            continue

        if (
            parca in baglam["context"]
            or any(
                parca in x or x in parca
                for x in ekstra
            )
        ):
            continue

        ekstra.append(parca)

    context = baglam["context"].strip()

    for parca in ekstra:
        kalan = ASAMA2_CONTEXT_LIMIT - len(context)

        if kalan <= 0:
            break

        if len(parca) > kalan:
            parca = parca[:kalan]

        context += (
            "\n\n# --- EK GUVENLI BAGLAM ---\n\n"
            + parca
        )

    baglam["context"] = context
    baglam["context_chars"] = len(context)

    return focus, baglam


def asama2_outer_json(stdout):
    metin = (
        stdout
        or ""
    ).strip()

    if not metin:
        raise RuntimeError(
            "Antigravity stdout bos."
        )

    try:
        veri = json.loads(metin)

        if isinstance(
            veri,
            dict
        ):
            return veri
    except Exception:
        pass

    for satir in reversed(
        [
            x.strip()
            for x
            in metin.splitlines()
            if x.strip()
        ]
    ):
        try:
            veri = json.loads(satir)

            if isinstance(
                veri,
                dict
            ):
                return veri
        except Exception:
            continue

    raise RuntimeError(
        "Antigravity dis JSON cevabi okunamadi."
    )


def asama2_inner_json(response):
    metin = (
        response
        or ""
    ).strip()

    if metin.startswith("```"):
        satirlar = metin.splitlines()

        if satirlar:
            satirlar = satirlar[1:]

        if (
            satirlar
            and satirlar[-1].strip() == "```"
        ):
            satirlar = satirlar[:-1]

        metin = "\n".join(
            satirlar
        ).strip()

    try:
        veri = json.loads(metin)

        if isinstance(
            veri,
            dict
        ):
            return veri
    except Exception:
        pass

    decoder = json.JSONDecoder()

    for i, ch in enumerate(metin):
        if ch != "{":
            continue

        try:
            veri, _ = decoder.raw_decode(
                metin[i:]
            )
        except Exception:
            continue

        if isinstance(
            veri,
            dict
        ):
            return veri

    raise ValueError(
        "GPT-OSS gecerli JSON dondurmedi."
    )


def asama2_agy_cagir(prompt):
    ASAMA2_AI_TEMP.mkdir(
        parents=True,
        exist_ok=True
    )

    if len(prompt) > ASAMA2_MAX_PROMPT:
        raise RuntimeError(
            f"Prompt fazla buyuk: {len(prompt):,} karakter."
        )

    agent_file = (
        Path.home()
        / ".gemini"
        / "config"
        / "agents"
        / ASAMA2_AGENT
        / "agent.md"
    )

    if not agent_file.exists():
        raise FileNotFoundError(
            "Global jarvis-advisor bulunamadi: "
            + str(agent_file)
        )

    cmd = [
        agy_bul(),
        "-p",
        prompt,
        "--agent",
        ASAMA2_AGENT,
        "--model",
        ASAMA2_MODEL,
        "--output-format",
        "json",
        "--sandbox",
    ]

    son_hata = ""

    for ag_deneme in range(2):
        try:
            p = subprocess.run(
                cmd,
                cwd=str(
                    ASAMA2_AI_TEMP
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=AGY_RESPONSE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Antigravity {AGY_RESPONSE_TIMEOUT} saniyede cevap vermedi."
            )

        outer = asama2_outer_json(
            p.stdout
        )

        usage = (
            outer.get("usage")
            or {}
        )

        status = str(
            outer.get(
                "status",
                ""
            )
        ).upper()

        if status == "SUCCESS":
            response = outer.get(
                "response"
            )

            if not isinstance(
                response,
                str
            ):
                raise RuntimeError(
                    "Antigravity response metin degil."
                )

            return (
                asama2_inner_json(
                    response
                ),
                usage,
            )

        error = str(
            outer.get("error")
            or p.stderr
            or "Bilinmeyen Antigravity hatasi."
        )

        total = usage.get(
            "total_tokens",
            0
        )

        son_hata = (
            f"Antigravity ERROR: {error} | token={total}"
        )

        dns = (
            total in {
                0,
                None
            }
            and any(
                x in error.casefold()
                for x in [
                    "no such host",
                    "lookup ",
                    "eligibility check failed",
                    "name resolution",
                    "dns",
                ]
            )
        )

        if dns and ag_deneme == 0:
            durum(
                "AGY_AG",
                (
                    "Token harcanmayan gecici ag/DNS hatasi; "
                    "8 saniye sonra bir kez yeniden denenecek."
                )
            )
            time.sleep(8)
            continue

        break

    raise RuntimeError(
        son_hata
        or "Antigravity basarisiz."
    )


def asama2_token_yaz(usage):
    if not isinstance(
        usage,
        dict
    ):
        return

    parcalar = []

    for etiket, anahtar in [
        ("giris", "input_tokens"),
        ("cikis", "output_tokens"),
        ("dusunme", "thinking_tokens"),
        ("cache", "cache_read_tokens"),
        ("toplam", "total_tokens"),
    ]:
        deger = usage.get(
            anahtar
        )

        if deger is not None:
            parcalar.append(
                f"{etiket}={deger}"
            )

    if parcalar:
        durum(
            "TOKEN",
            "Bu tur: "
            + " | ".join(
                parcalar
            )
        )


def asama2_prompt(
    workspace,
    tur,
    request_id,
    spec,
    step,
    feedback,
    recent
):
    focus, baglam = asama2_baglam(
        workspace,
        spec,
        step
    )

    if step == "helper_add":
        ozel = ""

        if spec["action"] == "app_status":
            ozel = (
                "- Helper mevcut calisan_surecler() ve surec_eslesmesi_bul() "
                "yardimcilarini yeniden kullanmali.\n"
                "- Yeni process tarama kodu, subprocess, psutil, WMI veya shell yazma.\n"
            )
        elif spec["action"] == "list_running_apps":
            ozel = (
                "- Helper mevcut calisan_surecler() sonucunu yeniden kullanmali.\n"
                "- Yeni process tarama kodu, subprocess, psutil, WMI veya shell yazma.\n"
            )
        elif spec["action"] == "disk_info":
            ozel = (
                "- Mevcut shutil ve HOME/Path yapisini kullan; yeni import ekleme.\n"
                "- Yalnizca disk_usage benzeri read-only bilgi kullan.\n"
            )
        elif spec["action"] == "known_folders":
            ozel = (
                "- Yalnizca HOME ve Path ile bilinen klasor yollarini hesapla.\n"
                "- Klasor olusturma/acma/yazma yapma.\n"
            )
        elif spec["action"] == "file_metadata":
            ozel = (
                "- Mevcut yerel_hedef_bul mantigini yeniden kullan.\n"
                "- Icerik okuma yok; yalnizca Path/stat metadata.\n"
            )
        elif spec["action"] == "capabilities":
            ozel = (
                "- Sadece guvenli action adlarini veri olarak dondur.\n"
                "- Baska action calistirma.\n"
            )

        adim = (
            "BU ADIM SADECE HELPER EKLER:\n"
            "- Hedef dosya kesinlikle jarvis_tools.py.\n"
            f"- Tam helper adi: {spec['helper']}\n"
            f"- Tam action adi: {spec['action']}\n"
            f"- Yalnizca BIR yeni top-level helper ekle: {spec['helper']}.\n"
            "- araci_calistir fonksiyonunu BU ADIMDA DEGISTIRME.\n"
            "- Yeni import ekleme.\n"
            "- Var olan read-only yardimcilari yeniden kullan; ayni isi yeniden yazma.\n"
            + ozel
            + "- Gerekli mevcut helperlar gosterilmiyorsa done de; tahmin etme.\n\n"
            "YETENEK AMACI:\n"
            + spec["tool_goal"]
        )
    elif step == "route_add":
        adim = (
            "BU ADIM SADECE ROUTE EKLER:\n"
            "- Hedef dosya kesinlikle jarvis_tools.py.\n"
            f"- Helper zaten mevcut olmalidir: {spec['helper']}\n"
            f"- araci_calistir icine yalnizca {spec['action']} route'unu ekle.\n"
            f"- Route mevcut {spec['helper']} helper'ini cagirmali.\n"
            "- Yeni top-level fonksiyon veya import ekleme.\n"
            "- Helper govdesini degistirme.\n"
            "- Baska action veya guvenlik mantigini degistirme.\n"
            "- Gerekli araci_calistir bolgesi gosterilmiyorsa done de; tahmin etme."
        )
    else:
        adim = (
            "BU ADIM SADECE ASSISTANT/TOOL TANIMINI OGRETIR:\n"
            "- Hedef dosya kesinlikle jarvis_tools.py.\n"
            f"- Yeni action: {spec['action']}\n"
            "- SADECE mevcut def arac_aciklamalari() fonksiyonunu degistir.\n"
            "- Bu fonksiyonun icindeki mevcut arac aciklama metnine yeni action'i ekle.\n"
            "- YENI top-level fonksiyon, class veya import EKLEME.\n"
            "- Baska mevcut fonksiyonu DEGISTIRME.\n"
            "- Helper/runtime implementasyonu YAZMA; helper zaten jarvis_tools.py icinde.\n"
            "- Mevcut 'def arac_aciklamalari()' satirini koru; yeni bir 'def ' satiri ekleme.\n"
            "- Runtime executor veya yeni guvenlik mekanizmasi ekleme.\n"
            "- Kritik guvenlik fonksiyonlarini degistirme.\n"
            "- Action kullanicinin acik istegi olmadan cagrilmamali.\n"
            "- Gosterilen kodda arac_aciklamalari() yoksa done de; tahmin etme.\n\n"
            "ENTEGRASYON AMACI:\n"
            + spec["assistant_goal"]
        )

    recent_text = (
        "\n".join(
            "- " + x
            for x in recent[-6:]
        )
        if recent
        else "Yok."
    )

    prompt = (
        "Sen Jarvis'in kontrollu otonom gelistirme danismanisin.\n\n"
        "Bu ASAMA 2'dir. Asama 1'in calisan guvenlik/test motoru korunuyor.\n"
        "Amac mevcut kodu yeniden tasarlamak degil, BIR yeni read-only "
        "yetenegin SADECE BIR kucuk adimini eklemek.\n\n"
        "DOSYA YAZMA. KOMUT CALISTIRMA. ARAC KULLANMA. INTERNETE CIKMA.\n"
        "Gercek patch, rollback ve testleri yerel Python guvenlik sistemi yapar.\n\n"
        f"TUR: {tur}\n"
        f"REQUEST_ID: {request_id}\n"
        f"YETENEK: {spec['name']}\n"
        f"ACTION: {spec['action']}\n"
        f"ADIM: {step}\n"
        f"HEDEF DOSYA: {focus['target']}\n\n"
        + adim
        + "\n\nONCEKI GERI BILDIRIM:\n"
        + (feedback or "Yok.")
        + "\n\nSON KABUL EDILEN ADIMLAR:\n"
        + recent_text
        + "\n\nKESIN KURALLAR:\n"
        f"- target_file TAM OLARAK {focus['target']} olmali.\n"
        f"- Sadece {focus['target']} icin cevap ver.\n"
        "- En fazla BIR kucuk FIND/REPLACE patch oner.\n"
        "- Tum dosyayi yeniden yazma.\n"
        "- status patch ise find YALNIZCA CONTEXT_BEGIN/CONTEXT_END arasindaki "
        "GOSTERILEN KOD'dan HARFI HARFINE alinmali; IMPORTLAR veya DOSYA "
        "INDEKSI'nden find secme.\n"
        "- find kisa, tam ve dosyada benzersiz bir kaynak parcasi olmali.\n"
        "- Placeholder veya ... kullanma.\n"
        "- Python kodunda tipografik tire/tirnak kullanma; yalnizca normal ASCII - ' \" kullan.\n"
        "- helper_add adiminda replace icinde beklenen yeni helper fonksiyonunu TAM ve parse edilebilir halde bulundur.\n"
        "- Gosterilmeyen kodu degistirme.\n"
        "- Yeni shell, PowerShell, CMD, subprocess, network, credential, silme, "
        "tasima, yeniden adlandirma, dosya yazma, GUI tiklama veya klavye "
        "otomasyonu ekleme.\n"
        "- shutdown/restart/lock/kapatma/silme guvenligini zayiflatma.\n"
        "- Cemil ana Godot projesine dokunma.\n"
        "- Ana Jarvis'e otomatik terfi ekleme.\n"
        "- --dangerously-skip-permissions kullanma.\n"
        "- Yetenek bu adimda zaten dogruysa done kullan.\n"
        "- done ise find ve replace bos string olsun.\n"
        f"- request_id TAM OLARAK {request_id} olmali.\n"
        "- CEVAP YALNIZCA JSON NESNESI olsun; Markdown yazma.\n\n"
        "JSON SEKLI:\n"
        "{\n"
        f'  "request_id": "{request_id}",\n'
        '  "status": "patch veya done",\n'
        f'  "target_file": "{focus["target"]}",\n'
        '  "summary": "kisa ozet",\n'
        '  "reason": "kisa gerekce",\n'
        '  "find": "mevcut parca veya bos",\n'
        '  "replace": "yeni parca veya bos"\n'
        "}\n\n"
        f"DOSYA BOYUTU: {baglam['source_chars']} karakter\n"
        f"GONDERILEN GERCEK KOD: {baglam['context_chars']} karakter\n\n"
        "IMPORTLAR:\n"
        + baglam["imports"]
        + "\n\nDOSYA INDEKSI:\n"
        + baglam["index"]
        + "\n\nGOSTERILEN KOD:\n"
        "<<<CONTEXT_BEGIN>>>\n"
        + baglam["context"]
        + "\n<<<CONTEXT_END>>>"
    )

    return prompt, focus, baglam


def asama2_fonksiyonlar(kaynak):
    tree = ast.parse(
        kaynak
    )

    sonuc_map = {}

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):
            sonuc_map[
                node.name
            ] = (
                ast.get_source_segment(
                    kaynak,
                    node
                )
                or ""
            )

    return sonuc_map


def asama2_readonly_kapi(eski, yeni, spec, step):
    eklenen = "\n".join(
        yeni_eklenen_satirlar(
            eski,
            yeni
        )
    ).casefold()

    bulunan = [
        p
        for p in ASAMA2_YENI_SATIR_YASAK
        if p.casefold() in eklenen
    ]

    if bulunan:
        return (
            False,
            "Yasak yeni read-only disi kalip: "
            + ", ".join(bulunan)
        )

    eski_funcs = asama2_fonksiyonlar(eski)
    yeni_funcs = asama2_fonksiyonlar(yeni)

    eklenen_funcs = set(yeni_funcs) - set(eski_funcs)
    degisen = {
        ad
        for ad in (set(eski_funcs) & set(yeni_funcs))
        if eski_funcs[ad] != yeni_funcs[ad]
    }

    if step == "helper_add":
        if eklenen_funcs != {spec["helper"]}:
            return (
                False,
                (
                    "helper_add adiminda yalnizca "
                    f"{spec['helper']} yeni fonksiyonu eklenebilir. "
                    "Yeni fonksiyonlar="
                    + ", ".join(sorted(eklenen_funcs))
                ),
            )

        if degisen:
            return (
                False,
                (
                    "helper_add mevcut fonksiyonlari degistiremez. Degisen="
                    + ", ".join(sorted(degisen))
                ),
            )

    elif step == "route_add":
        if eklenen_funcs:
            return (
                False,
                (
                    "route_add yeni top-level fonksiyon ekleyemez. Yeni="
                    + ", ".join(sorted(eklenen_funcs))
                ),
            )

        if degisen != {"araci_calistir"}:
            return (
                False,
                (
                    "route_add yalnizca araci_calistir fonksiyonunu degistirebilir. "
                    "Degisen=" + ", ".join(sorted(degisen))
                ),
            )

        dispatcher = yeni_funcs.get("araci_calistir", "")

        if spec["action"] not in dispatcher:
            return False, "Yeni action araci_calistir icine eklenmedi."

        if spec["helper"] not in dispatcher:
            return False, "Yeni route beklenen helper'i cagirmiyor."

        if spec["helper"] not in yeni_funcs:
            return False, "Route eklenmeden once helper workspace'te yok."

    else:
        if eklenen_funcs:
            return (
                False,
                (
                    "assistant_integration yeni top-level fonksiyon ekleyemez. Yeni="
                    + ", ".join(sorted(eklenen_funcs))
                ),
            )

        if degisen != {"arac_aciklamalari"}:
            return (
                False,
                (
                    "assistant_integration yalnizca arac_aciklamalari "
                    "fonksiyonunu degistirebilir. Degisen="
                    + ", ".join(sorted(degisen))
                ),
            )

        arac_metni = yeni_funcs.get("arac_aciklamalari", "")

        if spec["action"] not in arac_metni:
            return (
                False,
                "Yeni action arac_aciklamalari fonksiyonuna eklenmedi.",
            )

    return True, ""


def asama2_step_tamam_mi(workspace, spec, step):
    if step in {"helper_add", "route_add"}:
        kaynak = dosya_oku(
            workspace / "jarvis_tools.py"
        )

        funcs = asama2_fonksiyonlar(kaynak)

        if spec["helper"] not in funcs:
            return False

        if step == "helper_add":
            return True

        dispatcher = funcs.get("araci_calistir", "")

        return (
            spec["action"] in dispatcher
            and spec["helper"] in dispatcher
        )

    kaynak = dosya_oku(
        workspace / "jarvis_tools.py"
    )

    try:
        funcs = asama2_fonksiyonlar(kaynak)
    except Exception:
        return False

    arac_metni = funcs.get("arac_aciklamalari", "")

    return spec["action"] in arac_metni


def asama2_smoke(workspace, spec):
    kod = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "import jarvis_tools;"
        "r=jarvis_tools.araci_calistir(sys.argv[2],{},confirmed=False);"
        "print('__S2__'+json.dumps(r,ensure_ascii=False,default=str))"
    )

    try:
        p = subprocess.run(
            [
                sys.executable,
                "-c",
                kod,
                str(workspace),
                spec["action"],
            ],
            cwd=str(
                workspace
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
    except Exception as e:
        return False, str(e)

    if p.returncode != 0:
        return (
            False,
            (
                p.stderr.strip()
                or p.stdout.strip()
            )
        )

    for satir in p.stdout.splitlines():
        if satir.startswith(
            "__S2__"
        ):
            try:
                veri = json.loads(
                    satir[
                        len("__S2__"):
                    ]
                )
            except Exception as e:
                return False, str(e)

            if not isinstance(
                veri,
                dict
            ):
                return False, "Action sonucu dict degil."

            if veri.get(
                "confirmation_required"
            ) is True:
                return False, "Read-only action onay istiyor."

            return True, str(
                veri.get(
                    "message",
                    "smoke basarili"
                )
            )

    return False, "Smoke JSON sonucu bulunamadi."


def asama2_rapor(
    session_info,
    source_info,
    turns,
    completed,
    failed,
    rejected,
    main_hash_before,
    stop_reason
):
    main_ok, main_farklar = (
        hashler_ayni_mi(
            ROOT,
            main_hash_before
        )
    )

    rapor = {
        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
        "stage": 2,
        "architecture":
            "stage1_engine_model_plus_deterministic_integration",
        "model":
            ASAMA2_MODEL,
        "agent":
            ASAMA2_AGENT,
        "ai_workspace":
            str(
                ASAMA2_AI_TEMP
            ),
        "source_stage1_workspace":
            str(
                source_info[
                    "workspace"
                ]
            ),
        "source_stage1_accepted_changes":
            source_info[
                "accepted"
            ],
        "source_stage1_turns":
            source_info[
                "turns"
            ],
        "total_ai_turns":
            turns,
        "completed_capabilities":
            completed,
        "failed_capabilities":
            failed,
        "rejected_turns":
            rejected,
        "main_files_unchanged":
            main_ok,
        "main_changed_files":
            main_farklar,
        "workspace":
            str(
                session_info[
                    "workspace"
                ]
            ),
        "automatic_promotion":
            False,
        "stop_reason":
            stop_reason,
    }

    yol = (
        session_info[
            "session"
        ]
        / "stage2_report.json"
    )

    yol.write_text(
        json.dumps(
            rapor,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return yol



def asama2_kod_noktalama_temizle(metin):
    """
    Model bazen Python koduna tipografik Unicode noktalama sokabiliyor.
    Kod alanlarinda bunlari guvenli ASCII karsiliklarina cevir.
    Turkce harfleri veya normal Unicode metni degistirme.
    """
    if not isinstance(metin, str):
        return metin

    tablo = str.maketrans({
        "\u2010": "-",  # hyphen
        "\u2011": "-",  # non-breaking hyphen
        "\u2012": "-",  # figure dash
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2212": "-",  # minus sign
        "\u00a0": " ",  # non-breaking space
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    })

    return metin.translate(tablo)


def asama2_beklenen_helperi_ayikla(kod, helper_adi):
    """
    Model replace alaninda daha genis bir parca dondurse bile yalnizca
    beklenen top-level helper fonksiyonunu ayikla.
    """
    if not isinstance(kod, str):
        return ""

    kod = asama2_kod_noktalama_temizle(kod)

    # Once tum replacement modulu parse etmeyi dene.
    adaylar = [kod]

    # Replacement bir mevcut blok + yeni helper seklindeyse helper'dan
    # baslayan kuyrugu da ayrica dene.
    isaret = "def " + helper_adi
    pos = kod.find(isaret)

    if pos >= 0:
        kuyruk = kod[pos:]
        adaylar.append(kuyruk)

        # Sonraki top-level def'e kadar olan parcayi da dene.
        sonraki = kuyruk.find("\ndef ", len(isaret))
        if sonraki > 0:
            adaylar.append(kuyruk[:sonraki + 1])

    for aday in adaylar:
        try:
            tree = ast.parse(aday)
        except SyntaxError:
            continue

        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == helper_adi
            ):
                parca = ast.get_source_segment(aday, node) or ""
                return parca.strip()

    return ""


def asama2_helper_patch_sabitle(veri, workspace, spec, step):
    """
    helper_add icin modelin FIND secimine bagimliligi kaldir.
    Modelden yalnizca beklenen helper govdesini al; mevcut dispatcher'i
    degistirmeden helper'i onun hemen onune deterministik ekle.
    """
    if (
        step != "helper_add"
        or not isinstance(veri, dict)
        or str(veri.get("status", "")).casefold() != "patch"
    ):
        return False

    helper = spec["helper"]

    kaynak = dosya_oku(
        workspace / "jarvis_tools.py"
    )

    try:
        funcs = asama2_fonksiyonlar(kaynak)
    except Exception:
        funcs = {}

    if helper in funcs:
        return False

    helper_kodu = asama2_beklenen_helperi_ayikla(
        veri.get("replace", ""),
        helper
    )

    if not helper_kodu:
        return False

    anchor = "def araci_calistir("

    if kaynak.count(anchor) != 1:
        return False

    veri["find"] = anchor
    veri["replace"] = (
        helper_kodu.rstrip()
        + "\n\n\n"
        + anchor
    )

    durum(
        "HELPER_KILIDI",
        (
            f"{helper} helper'i model FIND'inden bagimsiz olarak "
            "araci_calistir oncesine deterministik yerlestirilecek."
        )
    )

    return True


ASAMA2_ASSISTANT_ARGS = {
    "app_status": '{"app":"uygulama adi"}',
    "list_running_apps": '{}',
    "disk_info": '{}',
    "known_folders": '{}',
    "file_metadata": '{"query":"dosya veya klasor"}',
    "capabilities": '{}',
}


ASAMA2_ASSISTANT_ACIKLAMA = {
    "app_status": (
        "Bir uygulamanin calisip calismadigini read-only sorgular. "
        "Yalnizca kullanici acikca sorarsa kullan."
    ),
    "list_running_apps": (
        "Calisan uygulama/process adlarini read-only listeler. "
        "Yalnizca kullanici acikca isterse kullan."
    ),
    "disk_info": (
        "Disk toplam/kullanilan/bos alan bilgisini read-only verir. "
        "Yalnizca kullanici disk alanini acikca sorarsa kullan."
    ),
    "known_folders": (
        "Temel kullanici klasorlerinin yollarini read-only verir. "
        "Yalnizca kullanici bu yolları acikca sorarsa kullan."
    ),
    "file_metadata": (
        "Belirli bir dosya veya klasorun metadata bilgisini read-only verir. "
        "Dosya icerigini okumaz; yalnizca kullanici acikca isterse kullan."
    ),
    "capabilities": (
        "Jarvis'in kullaniciya sunabildigi temel yetenekleri read-only listeler. "
        "Yalnizca kullanici Jarvis'in neler yapabildigini acikca sorarsa kullan."
    ),
}


def asama2_assistant_patch_yerel(workspace, spec, request_id):
    """
    Assistant/TOOL aciklamasi yaratıcı bir kod uretim isi degildir.
    Model FIND/REPLACE hatalarini ve gereksiz token tuketimini kaldirmak icin
    mevcut arac_aciklamalari() fonksiyonunu yerel controller deterministik
    olarak gunceller. Patch yine normal AST/read-only/test/rollback kapilarindan
    gecmek zorundadir.
    """
    kaynak = dosya_oku(
        workspace / "jarvis_tools.py"
    )

    funcs = asama2_fonksiyonlar(kaynak)
    eski_func = funcs.get(
        "arac_aciklamalari",
        ""
    )

    if not eski_func:
        raise ValueError(
            "jarvis_tools.py icinde arac_aciklamalari() bulunamadi."
        )

    action = spec["action"]

    if action in eski_func:
        return {
            "request_id": request_id,
            "status": "done",
            "target_file": "jarvis_tools.py",
            "summary": f"{action} arac aciklamasinda zaten mevcut.",
            "reason": "Yerel deterministik kontrol mevcut entegrasyonu buldu.",
            "find": "",
            "replace": "",
        }

    args_metni = ASAMA2_ASSISTANT_ARGS.get(
        action,
        "{}"
    )
    aciklama = ASAMA2_ASSISTANT_ACIKLAMA.get(
        action,
        spec.get("assistant_goal", "Read-only Jarvis araci.")
    )

    # Mevcut fonksiyon tek bir triple-quoted arac listesi donduruyor.
    # Kapanis tirnagini bulup yeni action blogunu hemen onune ekle.
    kapanis = eski_func.rfind('"""')

    if kapanis < 0:
        raise ValueError(
            "arac_aciklamalari() icinde beklenen triple-quoted metin bulunamadi."
        )

    blok = (
        "\n\n"
        + action
        + "\nargs:\n"
        + args_metni
        + "\n\n"
        + aciklama
        + "\n"
    )

    yeni_func = (
        eski_func[:kapanis]
        + blok
        + eski_func[kapanis:]
    )

    # Yerel uretilen patch de ayni standart FIND/REPLACE motorundan gecsin.
    return {
        "request_id": request_id,
        "status": "patch",
        "target_file": "jarvis_tools.py",
        "summary": f"{action} arac aciklamasina yerel ve deterministik eklendi.",
        "reason": (
            "Assistant entegrasyonu model FIND secimine bagli degil; "
            "yalnizca arac_aciklamalari() degistiriliyor."
        ),
        "find": eski_func,
        "replace": yeni_func,
    }


def asama2_step(
    session_info,
    main_hash_before,
    protected_baseline,
    seen_patch_hashes,
    spec,
    step,
    tur,
    feedback,
    recent
):
    workspace = (
        session_info[
            "workspace"
        ]
    )

    main_ok, farklar = (
        hashler_ayni_mi(
            ROOT,
            main_hash_before
        )
    )

    if not main_ok:
        raise RuntimeError(
            "Ana Jarvis dosyalari degisti: "
            + ", ".join(
                farklar
            )
        )

    backup = tur_yedegi_olustur(
        workspace,
        session_info[
            "iterations"
        ],
        tur
    )

    request_id = (
        "JARVIS-S2-"
        + uuid.uuid4().hex[
            :12
        ].upper()
    )

    prompt, focus, baglam = (
        asama2_prompt(
            workspace,
            tur,
            request_id,
            spec,
            step,
            feedback,
            recent
        )
    )

    durum(
        "JARVIS",
        (
            f"Tur {tur} | "
            f"{spec['name']} | "
            f"{step}"
        )
    )

    durum(
        "TOKEN",
        (
            "Gonderilen gercek kod baglami: "
            f"{baglam['context_chars']:,} karakter"
        )
    )

    if step == "assistant_integration":
        durum(
            "PROMPT",
            "GPT-OSS cagrisi yok; yerel deterministik entegrasyon."
        )
        durum(
            "YEREL_ENTEGRASYON",
            (
                f"{spec['action']} -> "
                "jarvis_tools.py / arac_aciklamalari()"
            )
        )

        try:
            veri = asama2_assistant_patch_yerel(
                workspace,
                spec,
                request_id
            )
        except Exception as e:
            workspace_geri_yukle(
                backup,
                workspace
            )
            return False, "ENTEGRASYON_RED", str(e), None

        usage = {}
    else:
        durum(
            "PROMPT",
            f"{len(prompt):,} karakter"
        )

        durum(
            "ANTIGRAVITY",
            "GPT-OSS yeni guvenli yetenek adimini inceliyor..."
        )

        try:
            veri, usage = (
                asama2_agy_cagir(
                    prompt
                )
            )
        except Exception as e:
            workspace_geri_yukle(
                backup,
                workspace
            )
            return False, "HATA", str(e), None

        asama2_token_yaz(
            usage
        )

    # Hedef dosyayi model secmez. Her adimin hedefi yerel controller tarafindan
    # sabittir. Model target_file alanini yanlis yazsa bile baska bir dosyaya
    # yonelme yetkisi kazanmaz; controller beklenen hedefi zorunlu kilar.
    if isinstance(veri, dict):
        model_hedef = str(veri.get("target_file", "")).strip()

        if model_hedef != focus["target"]:
            durum(
                "HEDEF_KILIDI",
                (
                    f"Model hedefi '{model_hedef}' yok sayildi; "
                    f"yerel hedef={focus['target']}"
                )
            )

        veri["target_file"] = focus["target"]

        # Modelin kod alanlarinda olusan tipografik Unicode noktalama,
        # Python AST'ye gitmeden once yerel olarak normalize edilir.
        for alan in ("find", "replace"):
            if isinstance(veri.get(alan), str):
                temiz = asama2_kod_noktalama_temizle(
                    veri[alan]
                )
                if temiz != veri[alan]:
                    durum(
                        "KOD_NORMALIZE",
                        (
                            f"{alan} alanindaki tipografik Unicode "
                            "kod noktalama karakterleri ASCII'ye cevrildi."
                        )
                    )
                veri[alan] = temiz

        # helper_add'de modelin FIND secimi guvenilir bir kontrol noktasi
        # degildir. Beklenen helper fonksiyonu ayiklanabiliyorsa patch'i
        # deterministik bir yerel anchor'a sabitle.
        asama2_helper_patch_sabitle(
            veri,
            workspace,
            spec,
            step
        )

    # Stage 2'de helper_add ve route_add icin semantik guvenlik kapilari
    # zaten cok daha dar: helper_add yalnizca tek yeni helper ekleyebilir,
    # route_add ise yalnizca araci_calistir'i degistirebilir. Bu nedenle
    # modelin FIND parcasi prompttaki dar context penceresinin disinda kalmis
    # olsa bile, hedef dosyada HARFI HARFINE mevcutsa gereksiz yere reddetme.
    # Assistant_integration model FIND kullanmaz; yerel controller exact
    # arac_aciklamalari() fonksiyonunu deterministik olarak patch eder.
    dogrulama_context = baglam["context"]

    if (
        step == "assistant_integration"
        and isinstance(veri, dict)
        and str(veri.get("status", "")).casefold() == "patch"
    ):
        # FIND yerel controller tarafindan workspace'teki gercek
        # arac_aciklamalari() fonksiyonundan alinmistir.
        dogrulama_context = veri.get("find", "")

    if (
        isinstance(veri, dict)
        and str(veri.get("status", "")).casefold() == "patch"
        and step in {"helper_add", "route_add"}
    ):
        find_adayi = veri.get("find", "")

        if isinstance(find_adayi, str) and find_adayi.strip():
            if find_adayi not in dogrulama_context:
                hedef_kaynak = dosya_oku(
                    workspace / focus["target"]
                )

                if find_adayi in hedef_kaynak:
                    durum(
                        "BAGLAM_ESNEK",
                        (
                            "FIND dar prompt context'inde yok ama hedef "
                            "dosyada birebir bulundu; Stage 2 kapsam kapilari "
                            "ile dogrulamaya devam ediliyor."
                        )
                    )
                    dogrulama_context = (
                        dogrulama_context
                        + "\n\n# --- STAGE2 EXACT TARGET FALLBACK ---\n"
                        + find_adayi
                    )

    try:
        model_cevabini_dogrula(
            veri,
            request_id,
            focus[
                "target"
            ],
            dogrulama_context
        )
    except Exception as e:
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "JSON_RED",
            str(e),
            None,
        )

    if (
        str(
            veri[
                "status"
            ]
        ).casefold()
        == "done"
    ):
        if asama2_step_tamam_mi(
            workspace,
            spec,
            step
        ):
            return (
                True,
                "ZATEN_VAR",
                (
                    veri[
                        "summary"
                    ]
                    or "Zaten mevcut."
                ),
                None,
            )

        workspace_geri_yukle(
            backup,
            workspace
        )

        return (
            False,
            "DEGISIKLIK_YOK_RED",
            (
                "Model done dedi ama gerekli "
                "entegrasyon workspace'te yok."
            ),
            None,
        )

    hedef = (
        workspace
        / veri[
            "target_file"
        ]
    )

    eski = dosya_oku(
        hedef
    )

    try:
        uygulama = patch_uygula(
            veri,
            workspace,
            protected_baseline,
            seen_patch_hashes
        )
    except Exception as e:
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "GUVENLIK_RED",
            str(e),
            None,
        )

    yeni = dosya_oku(
        hedef
    )

    guvenli, neden = (
        asama2_readonly_kapi(
            eski,
            yeni,
            spec,
            step
        )
    )

    if not guvenli:
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "READONLY_RED",
            neden,
            None,
        )

    test_ok, test_msg = (
        tam_test(
            workspace
        )
    )

    if not test_ok:
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "TEST_RED",
            test_msg,
            None,
        )

    if not protected_ayni_mi(
        workspace,
        protected_baseline
    ):
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "GUVENLIK_RED",
            "Kilitli kritik kod degisti.",
            None,
        )

    if not asama2_step_tamam_mi(
        workspace,
        spec,
        step
    ):
        workspace_geri_yukle(
            backup,
            workspace
        )
        return (
            False,
            "ENTEGRASYON_RED",
            "Patch uygulandi ama beklenen action/helper entegrasyonu yok.",
            None,
        )

    main_ok, farklar = (
        hashler_ayni_mi(
            ROOT,
            main_hash_before
        )
    )

    if not main_ok:
        workspace_geri_yukle(
            backup,
            workspace
        )
        raise RuntimeError(
            "Ana Jarvis butunlugu bozuldu: "
            + ", ".join(
                farklar
            )
        )

    return (
        True,
        "KABUL_ADIM",
        (
            veri[
                "summary"
            ]
            or "Adim kabul edildi."
        ),
        {
            "target":
                uygulama[
                    "target"
                ],
            "added":
                uygulama[
                    "added_lines"
                ],
            "removed":
                uygulama[
                    "removed_lines"
                ],
            "test":
                test_msg,
        },
    )


def asama2_main():
    kaynaklari_kontrol_et()

    main_hash_before = (
        kaynak_hashleri(
            ROOT
        )
    )

    source_info, source_test = (
        asama2_stage1_kaynagini_sec()
    )

    session_info = (
        asama2_oturumu_olustur(
            source_info[
                "workspace"
            ]
        )
    )

    workspace = (
        session_info[
            "workspace"
        ]
    )

    protected_baseline = (
        protected_snapshot(
            workspace
        )
    )

    seen_patch_hashes = set()

    baslik(
        "JARVIS ASAMA 2 - ASAMA 1 TABANLI YENI GUVENLI YETENEKLER"
    )

    durum(
        "TABAN",
        str(
            source_info[
                "workspace"
            ]
        )
    )

    durum(
        "TABAN_TEST",
        source_test
    )

    durum(
        "TABAN_RAPOR",
        (
            f"Kabul={source_info['accepted']} | "
            f"Tur={source_info['turns']}"
        )
    )

    durum(
        "MODEL",
        ASAMA2_MODEL
    )

    durum(
        "AGENT",
        (
            ASAMA2_AGENT
            + " | tools=KAPALI"
        )
    )

    durum(
        "AI_WORKSPACE",
        str(
            ASAMA2_AI_TEMP
        )
    )

    durum(
        "TOKEN",
        (
            "Antigravity Jarvis klasorunde calismiyor; "
            "yalnizca secilen kod baglami gider."
        )
    )

    durum(
        "MIMARI",
        (
            "Asama 1 FIND/REPLACE + rollback + test motoru korunuyor; "
            "helper_add ve route_add GPT-OSS; assistant_integration yerel deterministik."
        )
    )

    durum(
        "GUVENLIK",
        (
            "Yalnizca read-only yeni yetenekler; "
            "kritik fonksiyonlar kilitli."
        )
    )

    durum(
        "ANA_JARVIS",
        "Otomatik terfi KAPALI."
    )

    durum(
        "DURDUR",
        "Ctrl+C"
    )

    durum(
        "WORKSPACE",
        str(
            workspace
        )
    )

    baseline_ok, baseline_msg = (
        tam_test(
            workspace
        )
    )

    if not baseline_ok:
        raise RuntimeError(
            "Asama 2 baslangic workspace'i saglam degil: "
            + baseline_msg
        )

    durum(
        "TEST",
        baseline_msg
    )

    total_turns = 0
    rejected = 0
    completed = []
    failed = []
    recent = []
    stop_reason = (
        "Asama 2 yol haritasi tamamlandi."
    )

    try:
        for i, spec in enumerate(
            ASAMA2_YETENEKLER,
            start=1
        ):
            print()

            durum(
                "YETENEK",
                (
                    f"{i}/{len(ASAMA2_YETENEKLER)} | "
                    f"{spec['name']} | "
                    f"action={spec['action']}"
                )
            )

            cap_backup = (
                session_info[
                    "capability_backups"
                ]
                / (
                    f"{i:02d}_"
                    + spec[
                        "action"
                    ]
                )
            )

            asama2_snapshot(
                workspace,
                cap_backup
            )

            cap_failed = False
            feedback = ""

            for step in [
                "helper_add",
                "route_add",
                "assistant_integration",
            ]:
                step_ok = False

                for deneme in range(
                    1,
                    ASAMA2_MAX_RETRY + 1
                ):
                    total_turns += 1
                    print()

                    durum(
                        "ADIM",
                        (
                            f"{step} | "
                            f"deneme {deneme}/"
                            f"{ASAMA2_MAX_RETRY}"
                        )
                    )

                    (
                        ok,
                        etiket,
                        mesaj,
                        detay
                    ) = asama2_step(
                        session_info,
                        main_hash_before,
                        protected_baseline,
                        seen_patch_hashes,
                        spec,
                        step,
                        total_turns,
                        feedback,
                        recent
                    )

                    if ok:
                        step_ok = True

                        durum(
                            etiket,
                            mesaj
                        )

                        if detay:
                            durum(
                                "PATCH",
                                (
                                    f"{detay['target']} | "
                                    f"+{detay['added']} "
                                    f"/ -{detay['removed']} satir"
                                )
                            )

                            durum(
                                "TEST",
                                detay[
                                    "test"
                                ]
                            )

                        recent.append(
                            (
                                f"{spec['action']} "
                                f"{step}: "
                                f"{mesaj}"
                            )
                        )

                        recent = (
                            recent[
                                -8:
                            ]
                        )

                        break

                    rejected += 1

                    durum(
                        etiket,
                        mesaj
                    )

                    durum(
                        "GERI_AL",
                        "Bu turun patch'i tamamen geri alindi."
                    )

                    feedback = (
                        "Onceki deneme reddedildi: "
                        + mesaj
                        + ". Tek, kucuk, read-only ve "
                        "gosterilen koddan birebir FIND kullan."
                    )

                    time.sleep(
                        TUR_ARASI_BEKLEME
                    )

                if not step_ok:
                    cap_failed = True
                    break

            if cap_failed:
                asama2_snapshot_geri(
                    cap_backup,
                    workspace
                )

                failed.append(
                    spec[
                        "action"
                    ]
                )

                durum(
                    "YETENEK_GERI_AL",
                    (
                        f"{spec['action']} tam entegre olamadi; "
                        "bu yetenege ait tum adimlar geri alindi."
                    )
                )

                continue

            test_ok, test_msg = (
                tam_test(
                    workspace
                )
            )

            if not test_ok:
                asama2_snapshot_geri(
                    cap_backup,
                    workspace
                )

                failed.append(
                    spec[
                        "action"
                    ]
                )

                durum(
                    "YETENEK_RED",
                    test_msg
                )

                continue

            smoke_ok, smoke_msg = (
                asama2_smoke(
                    workspace,
                    spec
                )
            )

            if not smoke_ok:
                asama2_snapshot_geri(
                    cap_backup,
                    workspace
                )

                failed.append(
                    spec[
                        "action"
                    ]
                )

                durum(
                    "YETENEK_RED",
                    (
                        "Read-only smoke testi: "
                        + smoke_msg
                    )
                )

                continue

            completed.append(
                spec[
                    "action"
                ]
            )

            durum(
                "YENI_YETENEK",
                spec[
                    "action"
                ]
            )

            durum(
                "SMOKE",
                smoke_msg
            )

            durum(
                "TEST",
                test_msg
            )

            durum(
                "ANA_JARVIS",
                "Degistirilmedi."
            )

            time.sleep(
                TUR_ARASI_BEKLEME
            )

    except KeyboardInterrupt:
        stop_reason = (
            "Kullanici Ctrl+C ile durdurdu."
        )

        print()

        durum(
            "DURDUR",
            (
                "Ctrl+C alindi; Asama 2 "
                "guvenli bicimde kapatiliyor..."
            )
        )

    finally:
        diff_path = (
            diff_kaydet(
                session_info
            )
        )

        report_path = (
            asama2_rapor(
                session_info,
                source_info,
                total_turns,
                completed,
                failed,
                rejected,
                main_hash_before,
                stop_reason
            )
        )

        main_ok, farklar = (
            hashler_ayni_mi(
                ROOT,
                main_hash_before
            )
        )

        baslik(
            "JARVIS ASAMA 2 DURDU"
        )

        durum(
            "TUR",
            str(
                total_turns
            )
        )

        durum(
            "YENI_YETENEK",
            (
                ", ".join(
                    completed
                )
                if completed
                else "0"
            )
        )

        durum(
            "BASARISIZ_YETENEK",
            (
                ", ".join(
                    failed
                )
                if failed
                else "0"
            )
        )

        durum(
            "RED",
            str(
                rejected
            )
        )

        durum(
            "WORKSPACE",
            str(
                workspace
            )
        )

        durum(
            "DIFF",
            str(
                diff_path
            )
        )

        durum(
            "RAPOR",
            str(
                report_path
            )
        )

        if main_ok:
            durum(
                "ANA_JARVIS",
                (
                    "Guvende. Ana dosyalar "
                    "degistirilmedi."
                )
            )
        else:
            durum(
                "UYARI",
                (
                    "Ana dosyalarda beklenmedik fark: "
                    + ", ".join(
                        farklar
                    )
                )
            )

        durum(
            "TERFI",
            (
                "Otomatik terfi KAPALI. "
                "Yeni yetenekler test workspace'inde."
            )
        )


if __name__ == "__main__":

    asama2_main()