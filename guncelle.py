# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import py_compile

p = Path("jarvis.py")

if not p.exists():
    raise SystemExit("HATA: jarvis.py bu klasörde bulunamadı.")

text = p.read_text(encoding="utf-8")

if "def hf_json(" not in text:
    raise SystemExit(
        "HATA: Önceki Higgsfield sürümü bulunamadı. "
        "Güncelleme durduruldu."
    )

if (
    "def hf_video_uret(" in text
    and '"higgsfield video uret"' in text
):
    print(
        "Jarvis zaten Higgsfield video üretim "
        "komutunu içeriyor."
    )
    raise SystemExit(0)

backup = Path("jarvis_yedek_video_oncesi.py")
shutil.copy2(p, backup)

VIDEO_KODU = r'''
def hf_json_icinden_deger_bul(veri, anahtarlar):
    if isinstance(veri, dict):
        for anahtar in anahtarlar:
            deger = veri.get(anahtar)

            if deger not in (None, "", []):
                return deger

        for deger in veri.values():
            bulunan = hf_json_icinden_deger_bul(
                deger,
                anahtarlar
            )

            if bulunan not in (None, "", []):
                return bulunan

    elif isinstance(veri, list):
        for oge in veri:
            bulunan = hf_json_icinden_deger_bul(
                oge,
                anahtarlar
            )

            if bulunan not in (None, "", []):
                return bulunan

    return None


def hf_video_url_bul(veri):
    if isinstance(veri, dict):
        for anahtar in (
            "result_url",
            "output_url",
            "video_url",
            "min_result_url",
        ):
            deger = veri.get(anahtar)

            if (
                isinstance(deger, str)
                and deger.startswith(
                    ("http://", "https://")
                )
            ):
                return deger

        for deger in veri.values():
            bulunan = hf_video_url_bul(deger)

            if bulunan:
                return bulunan

    elif isinstance(veri, list):
        for oge in veri:
            bulunan = hf_video_url_bul(oge)

            if bulunan:
                return bulunan

    elif isinstance(veri, str):
        alt = veri.lower()

        if (
            veri.startswith(
                ("http://", "https://")
            )
            and (
                ".mp4" in alt
                or ".mov" in alt
                or ".webm" in alt
            )
        ):
            return veri

    return None


def hf_video_url_indir(url):
    try:
        url_adi = Path(
            unquote(
                urlparse(url).path
            )
        ).name

        if not url_adi:
            url_adi = (
                "Higgsfield_Seedance_"
                + time.strftime(
                    "%Y%m%d_%H%M%S"
                )
                + ".mp4"
            )

        if not Path(url_adi).suffix:
            url_adi += ".mp4"

        hedef = benzersiz_yol(
            INDIRMELER
            / guvenli_ad(url_adi)
        )

        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with (
            urlopen(
                req,
                timeout=120
            ) as resp,
            open(
                hedef,
                "wb"
            ) as f
        ):
            shutil.copyfileobj(
                resp,
                f
            )

        print(
            "Jarvis: Video indirildi:",
            hedef
        )

        return hedef

    except Exception as e:
        print(
            "Jarvis: Video indirilemedi:",
            e
        )

        return None


def hf_video_uret():
    print()

    print(
        "Jarvis: Seedance 2.5 "
        "video üretim modu."
    )

    print(
        "Jarvis: Çözünürlük: 480p"
    )

    print(
        "Jarvis: En-boy oranı: 16:9"
    )

    print(
        "Jarvis: Şimdilik referans medya "
        "olmadan T2V üretimi kullanılıyor."
    )

    prompt = input(
        "Jarvis: Promptu yaz:\n> "
    ).strip()

    if not prompt:
        print(
            "Jarvis: Prompt boş. "
            "İşlem iptal edildi."
        )

        return

    sure_raw = input(
        "Jarvis: Süre kaç saniye? "
        "(boş bırakırsan 5): "
    ).strip()

    if not sure_raw:
        sure = 5

    else:
        try:
            sure = int(sure_raw)

        except ValueError:
            print(
                "Jarvis: Süre tam sayı olmalı. "
                "İşlem iptal edildi."
            )

            return

    if sure <= 0:
        print(
            "Jarvis: Süre sıfırdan "
            "büyük olmalı."
        )

        return

    parametreler = [
        "--prompt",
        prompt,
        "--duration",
        str(sure),
        "--resolution",
        "480p",
    ]

    print()

    print(
        "Jarvis: Önce maliyeti "
        "hesaplıyorum. "
        "Bu adım kredi harcamaz."
    )

    maliyet_data, hata = hf_json([
        "generate",
        "cost",
        "seedance_2_5",
        *parametreler,
    ])

    if hata:
        print(
            "Jarvis: Maliyet "
            "hesaplanamadı:"
        )

        print(hata)

        return

    kredi = (
        maliyet_data.get("credits")
        if isinstance(
            maliyet_data,
            dict
        )
        else None
    )

    if kredi is None:
        print(
            "Jarvis: Maliyet çıktısını "
            "okuyamadım."
        )

        print(
            json.dumps(
                maliyet_data,
                ensure_ascii=False,
                indent=2
            )
        )

        return

    print()

    print(
        "Jarvis: Model: Seedance 2.5"
    )

    print(
        "Jarvis: Süre:",
        sure,
        "saniye"
    )

    print(
        "Jarvis: Çözünürlük: 480p"
    )

    print(
        "Jarvis: En-boy oranı: 16:9"
    )

    print(
        "Jarvis: Tahmini maliyet:",
        kredi,
        "kredi"
    )

    onay = norm(
        input(
            "Jarvis: Üretimi başlatayım mı? "
            "(EVET/HAYIR): "
        )
    )

    if onay != "evet":
        print(
            "Jarvis: İptal edildi. "
            "Video üretimi başlatılmadı."
        )

        return

    print()

    print(
        "Jarvis: ONAY ALINDI."
    )

    print(
        "Jarvis: Kredi harcayan üretim "
        "işi başlatılıyor..."
    )

    uretim_data, hata = hf_json([
        "generate",
        "create",
        "seedance_2_5",
        *parametreler,
        "--wait",
        "--wait-timeout",
        "20m",
        "--wait-interval",
        "5s",
    ], timeout=1500)

    if hata:
        print(
            "Jarvis: Higgsfield "
            "üretim hatası:"
        )

        print(hata)

        return

    job_id = hf_json_icinden_deger_bul(
        uretim_data,
        (
            "id",
            "job_id"
        )
    )

    video_url = hf_video_url_bul(
        uretim_data
    )

    if job_id:
        print(
            "Jarvis: Job:",
            job_id
        )

    if (
        not video_url
        and job_id
    ):
        print(
            "Jarvis: Sonuç URL'si için "
            "işi tekrar kontrol ediyorum..."
        )

        bekleme_data, bekleme_hata = hf_json([
            "generate",
            "wait",
            str(job_id),
            "--timeout",
            "20m",
            "--interval",
            "5s",
            "--quiet",
        ], timeout=1500)

        if not bekleme_hata:
            video_url = hf_video_url_bul(
                bekleme_data
            )

    if (
        not video_url
        and job_id
    ):
        liste_data, liste_hata = hf_json([
            "generate",
            "list"
        ])

        if (
            not liste_hata
            and isinstance(
                liste_data,
                list
            )
        ):
            for x in liste_data:
                if (
                    isinstance(x, dict)
                    and str(
                        x.get("id")
                    ) == str(job_id)
                    and x.get("status")
                    == "completed"
                    and x.get(
                        "result_url"
                    )
                ):
                    video_url = x[
                        "result_url"
                    ]

                    break

    if not video_url:
        print(
            "Jarvis: Üretim tamamlanmış "
            "olabilir fakat sonuç URL'sini "
            "otomatik bulamadım."
        )

        if job_id:
            print(
                "Jarvis: Job ID:",
                job_id
            )

        return

    print(
        "Jarvis: Video tamamlandı."
    )

    print(
        "Jarvis: Sonuç indiriliyor..."
    )

    hedef = hf_video_url_indir(
        video_url
    )

    if hedef:
        print(
            "Jarvis: Higgsfield üretim "
            "akışı tamamlandı."
        )
'''

KOMUT_KODU = r'''
    if k in {
        "higgsfield video uret",
        "seedance video uret",
        "video uret higgsfield",
    }:
        hf_video_uret()
        return True

'''

marker = (
    "# ============================================================\n"
    "# KOMUTLAR\n"
    "# ============================================================"
)

pos = text.find(marker)

if pos == -1:
    raise SystemExit(
        "HATA: KOMUTLAR bölümü bulunamadı. "
        "Yedek dosya oluşturuldu."
    )

text = (
    text[:pos]
    + VIDEO_KODU
    + "\n\n"
    + text[pos:]
)

komut_baslangici = text.find(
    "def komutu_isle("
)

if komut_baslangici == -1:
    raise SystemExit(
        "HATA: komutu_isle fonksiyonu "
        "bulunamadı."
    )

masaustu_marker = (
    "    # --------------------------------------------------------\n"
    "    # Masaüstü\n"
    "    # --------------------------------------------------------"
)

komut_pos = text.find(
    masaustu_marker,
    komut_baslangici
)

if komut_pos == -1:
    raise SystemExit(
        "HATA: Komut ekleme noktası "
        "bulunamadı."
    )

text = (
    text[:komut_pos]
    + KOMUT_KODU
    + text[komut_pos:]
)

p.write_text(
    text,
    encoding="utf-8"
)

try:
    py_compile.compile(
        str(p),
        doraise=True
    )

except Exception as e:
    shutil.copy2(
        backup,
        p
    )

    raise SystemExit(
        "HATA: Güncellenmiş kod "
        "sözdizimi kontrolünden geçmedi. "
        "Eski jarvis.py geri yüklendi.\n"
        + str(e)
    )

print(
    "TAMAM: jarvis.py güncellendi."
)

print(
    "YEDEK:",
    backup.resolve()
)

print(
    "YENİ KOMUT: higgsfield video üret"
)