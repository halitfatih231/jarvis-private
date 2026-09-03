# -*- coding: utf-8 -*-

import json
import os
import re
import subprocess
import unicodedata

from collections import deque
from datetime import datetime
from pathlib import Path

import jarvis_tools


# ============================================================
# TEMEL AYARLAR
# ============================================================

HOME = Path.home()
JARVIS_KLASORU = HOME / "Jarvis"

AGY = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "agy"
    / "bin"
    / "agy.exe"
)

MEMORY_FILE = JARVIS_KLASORU / "jarvis_memory.json"
HISTORY_FILE = JARVIS_KLASORU / "jarvis_history.jsonl"

SON_MESAJ_SAYISI = 20
MAX_HAFIZA = 100


# ============================================================
# DURUM
# ============================================================

bekleyen_onay = None

# Son gercek yerel arac islemi.
# "Onu kapat" gibi komutlarda kullanilir.
son_arac_baglami = None


# ============================================================
# EVET / HAYIR
# ============================================================

EVET_KELIMELERI = {
    "evet",
    "evet onayliyorum",
    "onayliyorum",
    "onayla",
    "tamam",
    "tamamdir",
    "yap",
    "devam et",
}


HAYIR_KELIMELERI = {
    "hayir",
    "hayir yapma",
    "iptal",
    "iptal et",
    "vazgec",
    "vazgectim",
    "bosver",
    "bos ver",
}


# ============================================================
# ANTIGRAVITY
# ============================================================

if not AGY.exists():

    print("HATA: Antigravity bulunamadi:")
    print(AGY)

    raise SystemExit


# ============================================================
# NORMALIZASYON
# ============================================================

def norm(metin):

    metin = str(
        metin
    ).casefold()

    metin = metin.translate(
        str.maketrans({
            "ı": "i",
            "ş": "s",
            "ğ": "g",
            "ü": "u",
            "ö": "o",
            "ç": "c",
        })
    )

    metin = unicodedata.normalize(
        "NFKD",
        metin
    )

    metin = "".join(
        karakter
        for karakter in metin
        if not unicodedata.combining(
            karakter
        )
    )

    metin = re.sub(
        r"[^a-z0-9\s._:\\/-]",
        " ",
        metin
    )

    metin = re.sub(
        r"\s+",
        " ",
        metin
    )

    return metin.strip()


# ============================================================
# HAFIZA
# ============================================================

def varsayilan_hafiza():

    return {
        "preferred_address": "Fatih hocam",
        "facts": [],
        "file_aliases": {},
    }


def hafiza_dosyalari_hazirla():

    JARVIS_KLASORU.mkdir(
        parents=True,
        exist_ok=True
    )

    if not MEMORY_FILE.exists():

        MEMORY_FILE.write_text(
            json.dumps(
                varsayilan_hafiza(),
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    if not HISTORY_FILE.exists():

        HISTORY_FILE.touch()


def hafiza_yukle():

    try:

        veri = json.loads(
            MEMORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            veri,
            dict
        ):

            raise ValueError

    except Exception:

        veri = varsayilan_hafiza()

    if not isinstance(
        veri.get("facts"),
        list
    ):

        veri["facts"] = []

    if not isinstance(
        veri.get("file_aliases"),
        dict
    ):

        veri["file_aliases"] = {}

    if not veri.get(
        "preferred_address"
    ):

        veri[
            "preferred_address"
        ] = "Fatih hocam"

    return veri


def hafiza_kaydet(
    hafiza
):

    MEMORY_FILE.write_text(
        json.dumps(
            hafiza,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def bilgi_hatirla(
    metin
):

    metin = str(
        metin
    ).strip()

    if not metin:

        return False

    hafiza = hafiza_yukle()

    facts = hafiza.get(
        "facts",
        []
    )

    yeni_norm = norm(
        metin
    )

    for eski in facts:

        if norm(
            eski
        ) == yeni_norm:

            return False

    facts.append(
        metin
    )

    hafiza[
        "facts"
    ] = facts[-MAX_HAFIZA:]

    hafiza_kaydet(
        hafiza
    )

    print(
        "[Hafizaya kaydedildi]",
        metin
    )

    return True


def bilgi_unut(
    sorgu
):

    sorgu = str(
        sorgu
    ).strip()

    if not sorgu:

        return False

    hafiza = hafiza_yukle()

    sorgu_n = norm(
        sorgu
    )

    kalanlar = []
    silinenler = []

    for bilgi in hafiza.get(
        "facts",
        []
    ):

        bilgi_n = norm(
            bilgi
        )

        if (
            sorgu_n in bilgi_n
            or bilgi_n in sorgu_n
        ):

            silinenler.append(
                bilgi
            )

        else:

            kalanlar.append(
                bilgi
            )

    if not silinenler:

        return False

    hafiza[
        "facts"
    ] = kalanlar

    hafiza_kaydet(
        hafiza
    )

    for bilgi in silinenler:

        print(
            "[Hafizadan silindi]",
            bilgi
        )

    return True


def hitap_degistir(
    yeni_hitap
):

    yeni_hitap = str(
        yeni_hitap
    ).strip()

    if not yeni_hitap:

        return False

    hafiza = hafiza_yukle()

    hafiza[
        "preferred_address"
    ] = yeni_hitap

    hafiza_kaydet(
        hafiza
    )

    print(
        "[Hitap guncellendi]",
        yeni_hitap
    )

    return True


# ============================================================
# DOSYA TAKMA ADLARI
# ============================================================

def dosya_takma_adi_kaydet(
    takma_ad,
    hedef
):

    takma_ad = str(
        takma_ad
    ).strip()

    hedef = str(
        hedef
    ).strip()

    if not takma_ad or not hedef:

        return False

    hafiza = hafiza_yukle()

    anahtar = norm(
        takma_ad
    )

    hafiza[
        "file_aliases"
    ][anahtar] = {
        "name": takma_ad,
        "target": hedef,
    }

    hafiza_kaydet(
        hafiza
    )

    print(
        "[Dosya hafizasi]",
        takma_ad,
        "->",
        hedef
    )

    return True


def dosya_takma_adi_sil(
    takma_ad
):

    anahtar = norm(
        takma_ad
    )

    hafiza = hafiza_yukle()

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    if anahtar not in aliases:

        return False

    eski = aliases.pop(
        anahtar
    )

    hafiza[
        "file_aliases"
    ] = aliases

    hafiza_kaydet(
        hafiza
    )

    print(
        "[Dosya hafizasi silindi]",
        eski.get(
            "name",
            takma_ad
        )
    )

    return True


def dosya_takma_adi_coz(
    sorgu
):

    sorgu_n = norm(
        sorgu
    )

    if not sorgu_n:

        return None

    hafiza = hafiza_yukle()

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    # Tam eslesme
    if sorgu_n in aliases:

        hedef = aliases[
            sorgu_n
        ].get(
            "target"
        )

        if hedef:

            print(
                "[Hafizadan dosya]",
                sorgu,
                "->",
                hedef
            )

            return hedef

    # Kismi eslesme
    en_iyi = None

    for (
        anahtar,
        bilgi
    ) in aliases.items():

        if (
            anahtar in sorgu_n
            or sorgu_n in anahtar
        ):

            hedef = bilgi.get(
                "target"
            )

            if not hedef:

                continue

            aday = (
                len(anahtar),
                bilgi.get(
                    "name",
                    anahtar
                ),
                hedef,
            )

            if (
                en_iyi is None
                or aday[0] > en_iyi[0]
            ):

                en_iyi = aday

    if en_iyi:

        _, isim, hedef = en_iyi

        print(
            "[Hafizadan dosya]",
            isim,
            "->",
            hedef
        )

        return hedef

    return None


# ============================================================
# SOHBET GECMISI
# ============================================================

def gecmise_ekle(
    rol,
    metin
):

    metin = str(
        metin
    ).strip()

    if not metin:

        return

    kayit = {
        "time":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "role":
            rol,

        "content":
            metin,
    }

    with HISTORY_FILE.open(
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                kayit,
                ensure_ascii=False
            )
            + "\n"
        )


def son_gecmisi_yukle(
    adet=SON_MESAJ_SAYISI
):

    sonlar = deque(
        maxlen=adet
    )

    try:

        with HISTORY_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            for satir in f:

                satir = satir.strip()

                if not satir:

                    continue

                try:

                    veri = json.loads(
                        satir
                    )

                except Exception:

                    continue

                if isinstance(
                    veri,
                    dict
                ):

                    sonlar.append(
                        veri
                    )

    except Exception:

        pass

    return list(
        sonlar
    )


# ============================================================
# GEMINI HAFIZA BAGLAMI
# ============================================================

def hafiza_baglami_olustur():

    hafiza = hafiza_yukle()

    hitap = hafiza.get(
        "preferred_address",
        "Fatih hocam"
    )

    facts = hafiza.get(
        "facts",
        []
    )

    aliases = hafiza.get(
        "file_aliases",
        {}
    )

    if facts:

        facts_text = "\n".join(
            "- " + str(bilgi)
            for bilgi in facts
        )

    else:

        facts_text = (
            "- Henuz kalici bilgi yok."
        )

    if aliases:

        alias_satirlari = []

        for bilgi in aliases.values():

            alias_satirlari.append(
                "- "
                + str(
                    bilgi.get(
                        "name",
                        ""
                    )
                )
                + " -> "
                + str(
                    bilgi.get(
                        "target",
                        ""
                    )
                )
            )

        alias_text = "\n".join(
            alias_satirlari
        )

    else:

        alias_text = (
            "- Kayitli dosya takma adi yok."
        )

    return f"""
Tercih edilen hitap:
{hitap}

Kalici bilgiler:
{facts_text}

Dosya ve klasor takma adlari:
{alias_text}
""".strip()


def gecmis_baglami_olustur():

    gecmis = son_gecmisi_yukle()

    if not gecmis:

        return "Onceki sohbet kaydi yok."

    satirlar = []

    for kayit in gecmis:

        rol = kayit.get(
            "role",
            ""
        )

        metin = kayit.get(
            "content",
            ""
        )

        ad = (
            "Kullanici"
            if rol == "user"
            else "Jarvis"
        )

        satirlar.append(
            f"{ad}: {metin}"
        )

    return "\n".join(
        satirlar
    )


# ============================================================
# MEMORY KOMUTLARI
# ============================================================

def memory_komutlarini_ayikla(
    cevap
):

    if not cevap:

        return "", []

    desen = (
        r"\[\[MEMORY\]\]"
        r"\s*(\{.*?\})\s*"
        r"\[\[/MEMORY\]\]"
    )

    islemler = []

    for eslesme in re.finditer(
        desen,
        cevap,
        flags=re.DOTALL
    ):

        try:

            veri = json.loads(
                eslesme.group(1)
            )

            if isinstance(
                veri,
                dict
            ):

                islemler.append(
                    veri
                )

        except Exception:

            pass

    temiz = re.sub(
        desen,
        "",
        cevap,
        flags=re.DOTALL
    ).strip()

    return (
        temiz,
        islemler
    )


def memory_islemlerini_uygula(
    islemler
):

    for islem in islemler:

        op = str(
            islem.get(
                "op",
                ""
            )
        ).strip()

        if op == "remember":

            metin = str(
                islem.get(
                    "text",
                    ""
                )
            ).strip()

            if metin:

                bilgi_hatirla(
                    metin
                )

        elif op == "forget":

            sorgu = str(
                islem.get(
                    "query",
                    ""
                )
            ).strip()

            if sorgu:

                bilgi_unut(
                    sorgu
                )

        elif op == "set_address":

            deger = str(
                islem.get(
                    "value",
                    ""
                )
            ).strip()

            if deger:

                hitap_degistir(
                    deger
                )

        elif op == "set_file_alias":

            alias = str(
                islem.get(
                    "alias",
                    ""
                )
            ).strip()

            target = str(
                islem.get(
                    "target",
                    ""
                )
            ).strip()

            if alias and target:

                dosya_takma_adi_kaydet(
                    alias,
                    target
                )

        elif op == "forget_file_alias":

            alias = str(
                islem.get(
                    "alias",
                    ""
                )
            ).strip()

            if alias:

                dosya_takma_adi_sil(
                    alias
                )


# ============================================================
# TOOL JSON AYIKLAMA
# ============================================================

def arac_komutu_ayikla(
    cevap
):

    if not cevap:

        return None

    baslangic_etiketi = "[[TOOL]]"
    bitis_etiketi = "[[/TOOL]]"

    baslangic = cevap.find(
        baslangic_etiketi
    )

    if baslangic == -1:

        return None

    baslangic += len(
        baslangic_etiketi
    )

    bitis = cevap.find(
        bitis_etiketi,
        baslangic
    )

    if bitis == -1:

        return None

    ham_json = cevap[
        baslangic:bitis
    ].strip()

    try:

        veri = json.loads(
            ham_json
        )

    except Exception:

        return None

    if not isinstance(
        veri,
        dict
    ):

        return None

    return veri


# ============================================================
# DOSYA ALIAS COZ
# ============================================================

def arac_argumanlarini_hafizadan_coz(
    action,
    args
):

    if not isinstance(
        args,
        dict
    ):

        return {}

    args = dict(
        args
    )

    hedef_alanlari = {
        "open_local":
            "query",

        "find_local":
            "query",

        "open_parent":
            "query",

        "delete_local":
            "target",

        "rename_local":
            "target",
    }

    if action in hedef_alanlari:

        alan = hedef_alanlari[
            action
        ]

        mevcut = str(
            args.get(
                alan,
                ""
            )
        ).strip()

        if mevcut:

            alias = dosya_takma_adi_coz(
                mevcut
            )

            if alias:

                args[
                    alan
                ] = alias

    if action in {
        "copy_local",
        "move_local",
    }:

        kaynak = str(
            args.get(
                "source",
                ""
            )
        ).strip()

        if kaynak:

            alias = dosya_takma_adi_coz(
                kaynak
            )

            if alias:

                args[
                    "source"
                ] = alias

        hedef = str(
            args.get(
                "destination",
                ""
            )
        ).strip()

        if hedef:

            alias = dosya_takma_adi_coz(
                hedef
            )

            if alias:

                args[
                    "destination"
                ] = alias

    return args


# ============================================================
# KRITIK YEREL GUVENLIK KATMANI
# ============================================================

def olumsuz_kapatma_ifadesi_mi(
    kullanici_metni
):

    q = norm(
        kullanici_metni
    )

    tehlikeli_olmayan_ifadeler = [
        "kapatma",
        "kapatmasin",
        "kapatmayin",
        "kapatmak istemiyorum",
        "kapatma lutfen",
        "sakin kapatma",
        "kapatsam mi",
        "kapatmali miyim",
        "kapatmak zararli",
        "kapatmak sorun",
        "kapatmak gerekir",
        "neden kapat",
    ]

    return any(
        ifade in q
        for ifade in tehlikeli_olmayan_ifadeler
    )


def acik_bilgisayar_kapatma_istegi_mi(
    kullanici_metni
):

    q = norm(
        kullanici_metni
    )

    if olumsuz_kapatma_ifadesi_mi(
        q
    ):

        return False

    ifadeler = [
        "bilgisayari kapat",
        "bilgisayarimi kapat",
        "pc yi kapat",
        "pc kapat",
        "bilgisayari kapatir misin",
        "pc yi kapatir misin",
        "bilgisayari kapat lutfen",
        "pc yi kapat lutfen",
    ]

    return any(
        ifade in q
        for ifade in ifadeler
    )


def acik_yeniden_baslatma_istegi_mi(
    kullanici_metni
):

    q = norm(
        kullanici_metni
    )

    soru_ifadeleri = [
        "yeniden baslatsam mi",
        "yeniden baslatmali miyim",
        "restart atsam mi",
        "restart gerekli mi",
    ]

    if any(
        ifade in q
        for ifade in soru_ifadeleri
    ):

        return False

    ifadeler = [
        "bilgisayari yeniden baslat",
        "bilgisayarimi yeniden baslat",
        "pc yi yeniden baslat",
        "pc yeniden baslat",
        "bilgisayara restart at",
        "pc ye restart at",
    ]

    return any(
        ifade in q
        for ifade in ifadeler
    )


def acik_kilitleme_istegi_mi(
    kullanici_metni
):

    q = norm(
        kullanici_metni
    )

    ifadeler = [
        "bilgisayari kilitle",
        "bilgisayarimi kilitle",
        "pc yi kilitle",
        "pc kilitle",
    ]

    return any(
        ifade in q
        for ifade in ifadeler
    )


def uygulama_adi_metinde_var_mi(
    kullanici_metni,
    app
):

    q = norm(
        kullanici_metni
    )

    app_n = norm(
        app
    )

    if not app_n:

        return False

    return app_n in q


def son_acilan_uygulama():

    global son_arac_baglami

    if not isinstance(
        son_arac_baglami,
        dict
    ):

        return None

    if not son_arac_baglami.get(
        "success"
    ):

        return None

    action = son_arac_baglami.get(
        "action"
    )

    args = son_arac_baglami.get(
        "args",
        {}
    )

    if action != "open_app":

        return None

    if not isinstance(
        args,
        dict
    ):

        return None

    app = str(
        args.get(
            "app",
            ""
        )
    ).strip()

    return app or None


def arac_guvenlik_kontrolu(
    kullanici_metni,
    action,
    args
):

    """
    Gemini TOOL uretse bile son karar burada verilir.

    return:
        (izin, yeni_args, mesaj)
    """

    q = norm(
        kullanici_metni
    )

    args = (
        dict(args)
        if isinstance(
            args,
            dict
        )
        else {}
    )

    # --------------------------------------------------------
    # BILGISAYAR KAPATMA
    # --------------------------------------------------------

    if action == "shutdown_pc":

        if not acik_bilgisayar_kapatma_istegi_mi(
            kullanici_metni
        ):

            return (
                False,
                args,
                (
                    "Bilgisayarı kapatma komutunu çalıştırmadım. "
                    "Bunun için açıkça "
                    "\"bilgisayarı kapat\" demen gerekiyor."
                )
            )

    # --------------------------------------------------------
    # YENIDEN BASLATMA
    # --------------------------------------------------------

    if action == "restart_pc":

        if not acik_yeniden_baslatma_istegi_mi(
            kullanici_metni
        ):

            return (
                False,
                args,
                (
                    "Yeniden başlatma komutunu çalıştırmadım. "
                    "Bunun için açıkça "
                    "\"bilgisayarı yeniden başlat\" demen gerekiyor."
                )
            )

    # --------------------------------------------------------
    # KILITLEME
    # --------------------------------------------------------

    if action == "lock_pc":

        if not acik_kilitleme_istegi_mi(
            kullanici_metni
        ):

            return (
                False,
                args,
                (
                    "Bilgisayarı kilitleme komutunu çalıştırmadım. "
                    "Bunun için açıkça "
                    "\"bilgisayarı kilitle\" demen gerekiyor."
                )
            )

    # --------------------------------------------------------
    # UYGULAMA KAPATMA
    # --------------------------------------------------------

    if action == "close_app":

        if olumsuz_kapatma_ifadesi_mi(
            kullanici_metni
        ):

            return (
                False,
                args,
                "Kapatma işlemini çalıştırmadım."
            )

        app = str(
            args.get(
                "app",
                ""
            )
        ).strip()

        if not app:

            return (
                False,
                args,
                "Hangi uygulamanın kapatılacağı belli değil."
            )

        # "Chrome'u kapat" gibi acik isim varsa izin ver.
        if uygulama_adi_metinde_var_mi(
            kullanici_metni,
            app
        ):

            return (
                True,
                args,
                ""
            )

        # "Onu kapat" sadece son basarili open_app ile eslesirse.
        if q in {
            "onu kapat",
            "onu da kapat",
            "kapat onu",
        }:

            son_app = son_acilan_uygulama()

            if (
                son_app
                and norm(
                    son_app
                ) == norm(
                    app
                )
            ):

                args[
                    "app"
                ] = son_app

                return (
                    True,
                    args,
                    ""
                )

            return (
                False,
                args,
                "“Onu” ile hangi uygulamayı kastettiğiniz kesin değil."
            )

        # Her sey, hepsini, tumunu gibi ifadeleri engelle.
        toplu_ifadeler = {
            "her seyi kapat",
            "hepsini kapat",
            "tumunu kapat",
            "herseyi kapat",
        }

        if q in toplu_ifadeler:

            return (
                False,
                args,
                (
                    "Toplu kapatma yapmadım. "
                    "Hangi uygulamayı kapatacağınızı belirtin."
                )
            )

        # Gemini uygulama tahmin ettiyse ama kullanici adini
        # soylemediyse calistirma.
        return (
            False,
            args,
            (
                f"{app} kapatılmadı. "
                "Uygulamanın adını açıkça söylemeniz gerekiyor."
            )
        )

    return (
        True,
        args,
        ""
    )


# ============================================================
# YALNIZ "KAPAT" ICIN YEREL ENGEL
# ============================================================

def belirsiz_kapatma_komutu_mi(
    kullanici_metni
):

    q = norm(
        kullanici_metni
    )

    return q in {
        "kapat",
        "kapat lutfen",
        "hey jarvis kapat",
        "jarvis kapat lutfen",
    }


# ============================================================
# YEREL DOSYA AC
# ============================================================

def yerel_dosya_ac(
    sorgu
):

    try:

        yol = jarvis_tools.yerel_hedef_bul(
            sorgu
        )

    except Exception as e:

        return {
            "success": False,
            "message":
                (
                    "Dosya arama sistemi "
                    f"hata verdi: {e}"
                ),
            "confirmation_required": False,
        }

    if yol is None:

        return {
            "success": False,
            "message":
                f"{sorgu} bulunamadı.",
            "confirmation_required": False,
        }

    try:

        os.startfile(
            str(yol)
        )

        return {
            "success": True,
            "message":
                f"{yol.name} açıldı.",
            "data": {
                "path":
                    str(yol)
            },
            "confirmation_required": False,
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"{yol.name} açılamadı: {e}",
            "confirmation_required": False,
        }


# ============================================================
# JARVIS ARAC CALISTIR
# ============================================================

def jarvis_aracini_calistir(
    action,
    args
):

    print()
    print(
        "[Jarvis araci:]",
        action
    )

    if args:

        print(
            "[Argumanlar:]",
            args
        )

    try:

        if action == "open_local":

            return yerel_dosya_ac(
                args.get(
                    "query",
                    ""
                )
            )

        return jarvis_tools.araci_calistir(
            action,
            args
        )

    except Exception as e:

        return {
            "success": False,
            "message":
                (
                    "Jarvis aracı çalıştırılırken "
                    f"hata oluştu: {e}"
                ),
            "confirmation_required": False,
        }


# ============================================================
# ONAY SISTEMI
# ============================================================

def onay_beklemeye_al(
    action,
    args,
    arac_sonucu
):

    global bekleyen_onay

    veri = arac_sonucu.get(
        "data"
    )

    if not isinstance(
        veri,
        dict
    ):

        veri = {}

    if action == "delete_local":

        tam_yol = str(
            veri.get(
                "target",
                ""
            )
        ).strip()

        if tam_yol:

            onay_args = {
                "target":
                    tam_yol
            }

        else:

            onay_args = dict(
                args
            )

    else:

        onay_args = dict(
            args
        )

    bekleyen_onay = {
        "action":
            str(
                veri.get(
                    "action",
                    action
                )
            ),

        "args":
            onay_args,

        "message":
            str(
                arac_sonucu.get(
                    "message",
                    "İşlem onay bekliyor."
                )
            ),
    }

    print()
    print(
        "Jarvis:",
        bekleyen_onay[
            "message"
        ]
    )

    print(
        "Jarvis: EVET veya HAYIR yazın."
    )


# ============================================================
# HAZIRLIK
# ============================================================

hafiza_dosyalari_hazirla()


# ============================================================
# GEMINI BASLAT
# ============================================================

print(
    "Jarvis beyni baslatiliyor..."
)

gemini = subprocess.Popen(
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

    cwd=str(
        JARVIS_KLASORU
    ),

    creationflags=getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0
    )
)


if (
    gemini.stdin is None
    or gemini.stdout is None
):

    print(
        "HATA: Gemini baslatilamadi."
    )

    raise SystemExit


# ============================================================
# GEMINI MESAJ
# ============================================================

def mesaj_gonder(
    metin
):

    olay = {
        "event": "user",

        "message": {
            "content":
                metin
        }
    }

    gemini.stdin.write(
        json.dumps(
            olay,
            ensure_ascii=False
        )
        + "\n"
    )

    gemini.stdin.flush()


def text_delta_bul(
    obj
):

    if isinstance(
        obj,
        dict
    ):

        deger = obj.get(
            "text_delta"
        )

        if isinstance(
            deger,
            str
        ):

            return deger

        for v in obj.values():

            bulunan = text_delta_bul(
                v
            )

            if bulunan:

                return bulunan

    elif isinstance(
        obj,
        list
    ):

        for v in obj:

            bulunan = text_delta_bul(
                v
            )

            if bulunan:

                return bulunan

    return None


def gemini_cevap_al():

    delta_toplam = ""

    while True:

        satir = gemini.stdout.readline()

        if not satir:

            raise RuntimeError(
                "Gemini oturumu kapandi."
            )

        try:

            olay = json.loads(
                satir
            )

        except json.JSONDecodeError:

            continue

        parca = text_delta_bul(
            olay
        )

        if parca:

            delta_toplam += parca

        if olay.get(
            "event"
        ) == "result":

            sonuc_veri = olay.get(
                "result",
                {}
            )

            if sonuc_veri.get(
                "status"
            ) != "SUCCESS":

                print(
                    "Jarvis: Gemini hatasi:",
                    sonuc_veri.get(
                        "error",
                        "Bilinmeyen hata"
                    )
                )

                return None

            cevap = str(
                sonuc_veri.get(
                    "response",
                    ""
                )
            ).strip()

            if not cevap:

                cevap = (
                    delta_toplam.strip()
                )

            return cevap or None


# ============================================================
# TOOL SONUCUNU GEMINI'YE BILDIR
# ============================================================

def geminiye_arac_sonucu_bildir(
    action,
    args,
    arac_sonucu,
    durum="completed"
):

    try:

        payload = {
            "type":
                "local_tool_result",

            "status":
                durum,

            "action":
                action,

            "args":
                args,

            "result":
                arac_sonucu,
        }

        bildirim = (
            "[YEREL_SISTEM_BILDIRIMI]\n"
            "Bu bir kullanici mesaji DEGILDIR.\n"
            "Bu Jarvis'in yerel arac sonucudur.\n"
            "Bu bilgiyi baglamda tut.\n"
            "Bu bildirime dayanarak YENI TOOL calistirma.\n"
            "Sadece ACK yaz.\n"
            + json.dumps(
                payload,
                ensure_ascii=False
            )
            + "\n[/YEREL_SISTEM_BILDIRIMI]"
        )

        mesaj_gonder(
            bildirim
        )

        # ACK cevabini tuket.
        gemini_cevap_al()

        return True

    except Exception as e:

        print(
            "[Arac sonucu Gemini'ye aktarilamadi]",
            e
        )

        return False


# ============================================================
# SON ARAC BAGLAMINI KAYDET
# ============================================================

def son_arac_baglamini_guncelle(
    action,
    args,
    arac_sonucu
):

    global son_arac_baglami

    son_arac_baglami = {
        "action":
            action,

        "args":
            dict(
                args
            ),

        "success":
            bool(
                arac_sonucu.get(
                    "success"
                )
            ),

        "message":
            arac_sonucu.get(
                "message",
                ""
            ),
    }


# ============================================================
# ONAY CEVABI
# ============================================================

def bekleyen_onayi_isle(
    kullanici_metni
):

    global bekleyen_onay

    cevap = norm(
        kullanici_metni
    )

    if cevap in EVET_KELIMELERI:

        islem = bekleyen_onay
        bekleyen_onay = None

        if not islem:

            return True

        action = islem.get(
            "action",
            ""
        )

        args = islem.get(
            "args",
            {}
        )

        print()
        print(
            "[Onaylandi:]",
            action
        )

        try:

            arac_sonucu = (
                jarvis_tools.araci_calistir(
                    action,
                    args,
                    confirmed=True
                )
            )

        except Exception as e:

            arac_sonucu = {
                "success": False,
                "message":
                    (
                        "Onaylanan işlem "
                        f"çalıştırılamadı: {e}"
                    ),
                "confirmation_required": False,
            }

        mesaj = str(
            arac_sonucu.get(
                "message",
                "İşlem tamamlandı."
            )
        )

        print()
        print(
            "Jarvis:",
            mesaj
        )

        gecmise_ekle(
            "user",
            kullanici_metni
        )

        gecmise_ekle(
            "assistant",
            mesaj
        )

        son_arac_baglamini_guncelle(
            action,
            args,
            arac_sonucu
        )

        geminiye_arac_sonucu_bildir(
            action,
            args,
            arac_sonucu,
            durum="confirmed_and_completed"
        )

        return True

    if cevap in HAYIR_KELIMELERI:

        islem = bekleyen_onay
        bekleyen_onay = None

        mesaj = (
            "Tamam Fatih hocam, "
            "işlemi iptal ettim."
        )

        print()
        print(
            "Jarvis:",
            mesaj
        )

        gecmise_ekle(
            "user",
            kullanici_metni
        )

        gecmise_ekle(
            "assistant",
            mesaj
        )

        if islem:

            geminiye_arac_sonucu_bildir(
                islem.get(
                    "action",
                    ""
                ),

                islem.get(
                    "args",
                    {}
                ),

                {
                    "success": False,
                    "message":
                        (
                            "Kullanıcı işlemi "
                            "onaylamadı."
                        ),
                    "confirmation_required": False,
                },

                durum="cancelled_by_user"
            )

        return True

    print()
    print(
        "Jarvis: Bu işlem onay bekliyor. "
        "Lütfen EVET veya HAYIR yazın."
    )

    return True


# ============================================================
# NORMAL SOHBET / TOOL TURU
# ============================================================

def jarvis_sor(
    kullanici_metni
):

    gecmise_ekle(
        "user",
        kullanici_metni
    )

    mesaj_gonder(
        kullanici_metni
    )

    cevap = gemini_cevap_al()

    if not cevap:

        return

    (
        temiz_cevap,
        hafiza_islemleri
    ) = memory_komutlarini_ayikla(
        cevap
    )

    memory_islemlerini_uygula(
        hafiza_islemleri
    )

    arac = arac_komutu_ayikla(
        temiz_cevap
    )

    if arac:

        action = str(
            arac.get(
                "action",
                ""
            )
        ).strip()

        args = arac.get(
            "args",
            {}
        )

        if not isinstance(
            args,
            dict
        ):

            args = {}

        args = arac_argumanlarini_hafizadan_coz(
            action,
            args
        )

        # ====================================================
        # SERT YEREL GUVENLIK KAPISI
        # ====================================================

        (
            izin,
            args,
            guvenlik_mesaji
        ) = arac_guvenlik_kontrolu(
            kullanici_metni,
            action,
            args
        )

        if not izin:

            print()
            print(
                "[GUVENLIK ENGELLEDI:]",
                action
            )

            print()
            print(
                "Jarvis:",
                guvenlik_mesaji
            )

            gecmise_ekle(
                "assistant",
                guvenlik_mesaji
            )

            geminiye_arac_sonucu_bildir(
                action,
                args,
                {
                    "success": False,
                    "message":
                        guvenlik_mesaji,
                    "confirmation_required": False,
                },
                durum="blocked_by_local_safety"
            )

            return

        # ====================================================
        # ARACI CALISTIR
        # ====================================================

        arac_sonucu = jarvis_aracini_calistir(
            action,
            args
        )

        # ====================================================
        # ONAY
        # ====================================================

        if arac_sonucu.get(
            "confirmation_required"
        ):

            onay_beklemeye_al(
                action,
                args,
                arac_sonucu
            )

            gecmise_ekle(
                "assistant",
                str(
                    arac_sonucu.get(
                        "message",
                        "İşlem onay bekliyor."
                    )
                )
            )

            return

        mesaj = str(
            arac_sonucu.get(
                "message",
                "İşlem tamamlandı."
            )
        )

        print()
        print(
            "Jarvis:",
            mesaj
        )

        gecmise_ekle(
            "assistant",
            mesaj
        )

        son_arac_baglamini_guncelle(
            action,
            args,
            arac_sonucu
        )

        geminiye_arac_sonucu_bildir(
            action,
            args,
            arac_sonucu
        )

        return

    # ========================================================
    # NORMAL CEVAP
    # ========================================================

    if not temiz_cevap:

        if hafiza_islemleri:

            temiz_cevap = (
                "Hatırladım Fatih hocam."
            )

        else:

            temiz_cevap = (
                "Fatih hocam, cevap oluşturamadım."
            )

    print()
    print(
        "Jarvis:",
        temiz_cevap
    )

    gecmise_ekle(
        "assistant",
        temiz_cevap
    )


# ============================================================
# GEMINI SISTEM TALIMATI
# ============================================================

print(
    "Kalici hafiza yukleniyor..."
)

hafiza_metni = hafiza_baglami_olustur()
gecmis_metni = gecmis_baglami_olustur()

araclar_metni = (
    jarvis_tools.arac_aciklamalari()
)

print(
    "Gemini oturumu isitiliyor..."
)


sistem_talimati = f"""
Sen Jarvis isimli kisisel yapay zeka asistanisin.

Kullaniciya dogal yerlerde "Fatih hocam" diye hitap et.

==================================================
TEMEL DAVRANIS
==================================================

Turkce konus.

Dogal ve kisa cevap ver.

Kullanicinin acikca istemedigi bilgisayar
islemlerini YAPMA.

Normal bilgi sorularini bilgisayar komutu sanma.

==================================================
KRITIK KAPATMA KURALLARI
==================================================

"Kapat" tek basina BELIRSIZDIR.

Kullanici sadece:
"Kapat."
derse HICBIR TOOL kullanma.

Normal cevap:
"Neyi kapatayım Fatih hocam?"

"Her seyi kapat",
"Hepsini kapat",
"Tumunu kapat"
gibi belirsiz toplu komutlarda HICBIR TOOL kullanma.
Ne kapatilacagini sor.

Bilgisayari kapatmak icin kullanici acikca:
"Bilgisayari kapat."
veya
"PC'yi kapat."
demelidir.

"Bilgisayari kapatsam mi?"
sorusunda shutdown_pc KULLANMA.

"Bilgisayari kapatmak zararli mi?"
sorusunda shutdown_pc KULLANMA.

"Chrome'u kapatma."
ifadesinde close_app KULLANMA.

"Chrome'u kapat."
ifadesinde yalnizca Chrome'u kapat.

"Jarvis'i kapat."
ifadesi Windows araci DEGILDIR.
Ana program bunu yerel olarak ele alir.

==================================================
YEREL GUVENLIK
==================================================

Sen yanlis TOOL secsen bile Python tarafinda
ikinci bir guvenlik sistemi vardir.

Bu sistemi asmaya veya dolasmaya calisma.

==================================================
YEREL SISTEM BILDIRIMI
==================================================

[YEREL_SISTEM_BILDIRIMI]
etiketi ile gelen mesaj GERCEK KULLANICI MESAJI
DEGILDIR.

Bu Jarvis'in yerel arac sonucudur.

Bu bildirime cevap olarak sadece:

ACK

yaz.

Yeni TOOL kullanma.

==================================================
KALICI HAFIZA
==================================================

{hafiza_metni}

==================================================
SON SOHBETLER
==================================================

{gecmis_metni}

==================================================
MEMORY FORMATI
==================================================

Hatirla:

[[MEMORY]]{{"op":"remember","text":"BILGI"}}[[/MEMORY]]

Unut:

[[MEMORY]]{{"op":"forget","query":"BILGI"}}[[/MEMORY]]

Hitap:

[[MEMORY]]{{"op":"set_address","value":"YENI HITAP"}}[[/MEMORY]]

Dosya takma adi:

[[MEMORY]]{{"op":"set_file_alias","alias":"TAKMA AD","target":"HEDEF"}}[[/MEMORY]]

Takma adi unut:

[[MEMORY]]{{"op":"forget_file_alias","alias":"TAKMA AD"}}[[/MEMORY]]

Parola, sifre ve API anahtari kaydetme.

==================================================
TOOL FORMATI
==================================================

Gercek bilgisayar islemi gerekiyorsa SADECE:

[[TOOL]]{{"action":"ARAC_ADI","args":{{...}}}}[[/TOOL]]

formatini kullan.

TOOL cevabinda baska metin yazma.

==================================================
MEVCUT ARACLAR
==================================================

{araclar_metni}

Ek arac:

open_local
args:
{{"query":"dosya veya klasor adi"}}

Yerel dosya veya klasoru acar.

==================================================
ORNEKLER
==================================================

Kullanici:
"Chrome'u ac."

Cevap:
[[TOOL]]{{"action":"open_app","args":{{"app":"chrome"}}}}[[/TOOL]]


Kullanici:
"Chrome'u kapat."

Cevap:
[[TOOL]]{{"action":"close_app","args":{{"app":"chrome"}}}}[[/TOOL]]


Kullanici:
"Kapat."

Cevap:
Neyi kapatayım Fatih hocam?


Kullanici:
"Her seyi kapat."

Cevap:
Neyi kapatmamı istediğinizi belirtin Fatih hocam.


Kullanici:
"Bilgisayari kapat."

Cevap:
[[TOOL]]{{"action":"shutdown_pc","args":{{}}}}[[/TOOL]]


Kullanici:
"Bilgisayari kapatsam mi?"

Cevap:
Normal sohbet cevabi ver.
TOOL kullanma.


Kullanici:
"Chrome neden cok RAM kullaniyor?"

Cevap:
Normal sohbet cevabi ver.
TOOL kullanma.


Kullanici:
"Formumu ac."

Cevap:
[[TOOL]]{{"action":"open_local","args":{{"query":"formum"}}}}[[/TOOL]]


Kullanici:
"Deneme klasorunu sil."

Cevap:
[[TOOL]]{{"action":"delete_local","args":{{"target":"Deneme"}}}}[[/TOOL]]

Silme onayini yerel Python sistemi yapar.

==================================================
DIGER GUVENLIK
==================================================

Kalici silme yapma.

Dosya silmede EVET/HAYIR onayi zorunludur.

Hedefteki dosyanin uzerine otomatik yazma.

Kritik Windows sureclerini kapatma.

Ana Cemil Godot projesini degistirme.

Yalnizca Cemil_Jarvis_Test test projesini kullan.

Ucretli Higgsfield islemini kendiliginden baslatma.

Talimati anladigini sadece HAZIR diyerek cevapla.
"""


mesaj_gonder(
    sistem_talimati
)

isitma = gemini_cevap_al()

if not isitma:

    print(
        "HATA: Gemini isitilamadi."
    )

    raise SystemExit


# ============================================================
# DURUM
# ============================================================

mevcut_hafiza = hafiza_yukle()

print()
print("=" * 72)
print("JARVIS SESSIZ + SERT GUVENLIK KATMANI HAZIR")
print("Hitap: Fatih hocam")
print("Beyin: Gemini / Antigravity")
print("Kalici hafiza: AKTIF")
print("Windows araclari: AKTIF")
print("Dosya yonetimi: AKTIF")
print("Silme: EVET/HAYIR + GERI DONUSUM KUTUSU")
print("Tool sonucu -> Gemini: AKTIF")
print("KRITIK TOOL GUVENLIK KAPISI: AKTIF")
print("Belirsiz 'kapat': ENGELLI")
print("Ses: KAPALI")
print("Mikrofon: KAPALI")
print(
    "Kalici bilgi:",
    len(
        mevcut_hafiza.get(
            "facts",
            []
        )
    )
)
print(
    "Dosya takma adi:",
    len(
        mevcut_hafiza.get(
            "file_aliases",
            {}
        )
    )
)
print("Cikis: jarvis kapat")
print("=" * 72)


# ============================================================
# ANA DONGU
# ============================================================

try:

    while True:

        kullanici = input(
            "\nSen: "
        ).strip()

        if not kullanici:

            continue

        # ----------------------------------------------------
        # ONAY BEKLIYOR
        # ----------------------------------------------------

        if bekleyen_onay is not None:

            bekleyen_onayi_isle(
                kullanici
            )

            continue

        q = norm(
            kullanici
        )

        # ----------------------------------------------------
        # JARVIS PROGRAMINI KAPAT
        # ----------------------------------------------------

        if q in {
            "jarvis kapat",
            "jarvisi kapat",
            "jarvis cik",
            "cik",
            "exit",
            "quit",
        }:

            print()
            print(
                "Jarvis: Görüşürüz Fatih hocam."
            )

            gecmise_ekle(
                "assistant",
                "Görüşürüz Fatih hocam."
            )

            break

        # ----------------------------------------------------
        # TEK BASINA "KAPAT" ASLA TOOL'A GITMEZ
        # ----------------------------------------------------

        if belirsiz_kapatma_komutu_mi(
            kullanici
        ):

            mesaj = (
                "Neyi kapatayım Fatih hocam?"
            )

            print()
            print(
                "Jarvis:",
                mesaj
            )

            gecmise_ekle(
                "user",
                kullanici
            )

            gecmise_ekle(
                "assistant",
                mesaj
            )

            continue

        # ----------------------------------------------------
        # TOPLU BELIRSIZ KAPATMA
        # ----------------------------------------------------

        if q in {
            "her seyi kapat",
            "herseyi kapat",
            "hepsini kapat",
            "tumunu kapat",
        }:

            mesaj = (
                "Hangi uygulamayı veya pencereyi "
                "kapatmamı istediğinizi belirtin Fatih hocam."
            )

            print()
            print(
                "Jarvis:",
                mesaj
            )

            gecmise_ekle(
                "user",
                kullanici
            )

            gecmise_ekle(
                "assistant",
                mesaj
            )

            continue

        # ----------------------------------------------------
        # NORMAL TUR
        # ----------------------------------------------------

        jarvis_sor(
            kullanici
        )


except KeyboardInterrupt:

    print()
    print(
        "Jarvis kapatiliyor..."
    )


finally:

    try:

        if gemini.stdin:

            gemini.stdin.close()

    except Exception:

        pass

    if gemini.poll() is None:

        try:

            gemini.terminate()

        except Exception:

            pass