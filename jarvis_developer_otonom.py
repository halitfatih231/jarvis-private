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


if __name__ == "__main__":

    main()