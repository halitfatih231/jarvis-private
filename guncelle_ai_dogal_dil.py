# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import shutil

jarvis = Path(__file__).with_name("jarvis.py")
metin = jarvis.read_text(encoding="utf-8")

if "def ai_dogal_dil_fallback(komut):" in metin:
    print("AI dogal dil sistemi zaten eklenmis.")
    raise SystemExit


# ============================================================
# 1. AI DOGAL DIL YORUMLAYICISI
# ============================================================

hedef = "def komutu_isle(komut):"

if hedef not in metin:
    print("HATA: komutu_isle() bulunamadi.")
    raise SystemExit


ai_kodu = r'''
def ai_dogal_dil_fallback(komut):
    """
    Mevcut Jarvis kurallari komutu anlayamazsa Claude'a yalnizca
    kullanicinin niyetini cozdurur.

    Claude bilgisayarda dogrudan islem yapmaz.
    Islemi Jarvis'in izin verilen fonksiyonlari gerceklestirir.
    """

    komut = str(komut).strip()

    if not komut:
        return True

    prompt = f"""
Sen Windows'ta calisan Jarvis isimli yerel asistana ait
SADECE dogal dil niyet yorumlayicisisin.

Kullanicinin Turkce cumlesini anla.

SADECE gecerli JSON dondur.
Markdown, aciklama veya kod blogu kullanma.

Izin verilen eylemler:

ac
kapat
ara
arastir
bul
sil
godot_test_ac
higgsfield_durum
higgsfield_maliyet
higgsfield_video_uret
sohbet
bilinmiyor

JSON bicimi:

{{
  "eylem": "eylem",
  "hedef": "temizlenmis hedef veya bos",
  "yanit": "yalnizca sohbet ise kisa Turkce cevap, digerlerinde bos"
}}

Kurallar:

1. "Merhaba Jarvis bana kisisel bilgi kayit formunu acar misin"
   gibi cumle:
   eylem = ac
   hedef = kisisel bilgi kayit formu

2. Hedeften Turkce ekleri ve gereksiz nezaket kelimelerini temizle.
   Ornek:
   "tez dosyami acar misin" -> hedef "tez"
   "Chrome'u acar misin" -> hedef "chrome"

3. Program, dosya veya klasor acma taleplerinin hepsi "ac" olsun.

4. Bir programi kapatma istegi "kapat" olsun.

5. Google/internet aramasi "ara" olsun.

6. Konu hakkinda bilgi toplayip ozetleme istegi "arastir" olsun.

7. Dosya veya klasoru sadece bulma istegi "bul" olsun.

8. Silme istegi "sil" olsun.
   Silme islemi daha sonra Jarvis tarafinda tekrar onaylanacaktir.

9. Cemil/Godot test projesini acma istegi "godot_test_ac" olsun.

10. Higgsfield hesap/durum sorgusu "higgsfield_durum" olsun.

11. Higgsfield maliyet sorgusu "higgsfield_maliyet" olsun.

12. Higgsfield video uretme istegi "higgsfield_video_uret" olsun.
    Kredi harcamasi Jarvis tarafinda ayrica onaylanacaktir.

13. Kullanici sadece konusuyor, soru soruyor veya sohbet ediyorsa
    "sohbet" kullan ve "yanit" alaninda kisa, dogal Turkce cevap ver.

14. Emin degilsen "bilinmiyor" kullan. Tahmin etme.

KULLANICI CUMLESI:
{komut}
"""

    try:
        sonuc = subprocess.run(
            [
                "cmd",
                "/c",
                "claude",
                "-p"
            ],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )

    except subprocess.TimeoutExpired:
        print(
            "Jarvis: Dogal dil yorumlama zaman asimina ugradi."
        )
        return True

    except Exception as e:
        print(
            "Jarvis: Claude dogal dil hatasi:",
            e
        )
        return True

    if sonuc.returncode != 0:
        hata = (
            sonuc.stderr.strip()
            or sonuc.stdout.strip()
        )

        print(
            "Jarvis: Claude dogal dil yorumlayicisi calismadi:",
            hata
        )
        return True

    ham = sonuc.stdout.strip()

    if not ham:
        print(
            "Jarvis: Komutu yorumlayamadim."
        )
        return True

    # Claude nadiren ```json ... ``` dondururse temizle.
    ham = re.sub(
        r"^```(?:json)?\s*",
        "",
        ham,
        flags=re.I
    )

    ham = re.sub(
        r"\s*```$",
        "",
        ham
    ).strip()

    # JSON disinda fazladan metin olursa yalnizca ilk nesneyi al.
    eslesme = re.search(
        r"\{.*\}",
        ham,
        flags=re.S
    )

    if eslesme:
        ham = eslesme.group(0)

    try:
        veri = json.loads(
            ham
        )

    except Exception:
        print(
            "Jarvis: AI yanitini anlayamadim."
        )
        return True

    eylem = norm(
        veri.get(
            "eylem",
            "bilinmiyor"
        )
    )

    hedef_raw = str(
        veri.get(
            "hedef",
            ""
        )
    ).strip()

    yanit = str(
        veri.get(
            "yanit",
            ""
        )
    ).strip()

    # --------------------------------------------------------
    # AC
    # --------------------------------------------------------

    if eylem == "ac":

        if not hedef_raw:
            print(
                "Jarvis: Neyi acmami istedigini anlayamadim."
            )
            konus(
                "Neyi açmamı istediğini anlayamadım."
            )
            return True

        program = program_adi_bul(
            hedef_raw
        )

        if program:
            program_ac(
                program
            )
            return True

        return dogal_ac_komutu(
            hedef_raw
        )

    # --------------------------------------------------------
    # PROGRAM KAPAT
    # --------------------------------------------------------

    if eylem == "kapat":

        program = program_adi_bul(
            hedef_raw
        )

        if program:
            program_kapat(
                program
            )
        else:
            print(
                "Jarvis: Kapatilacak programi bulamadim."
            )
            konus(
                "Kapatılacak programı bulamadım."
            )

        return True

    # --------------------------------------------------------
    # GOOGLE ARA
    # --------------------------------------------------------

    if eylem == "ara":

        if hedef_raw:
            google_ara(
                hedef_raw
            )
        else:
            konus(
                "Ne aramamı istediğini anlayamadım."
            )

        return True

    # --------------------------------------------------------
    # ARASTIR
    # --------------------------------------------------------

    if eylem == "arastir":

        if hedef_raw:
            web_arastir(
                hedef_raw
            )
        else:
            konus(
                "Neyi araştırmamı istediğini anlayamadım."
            )

        return True

    # --------------------------------------------------------
    # DOSYA / KLASOR BUL
    # --------------------------------------------------------

    if eylem == "bul":

        if not hedef_raw:
            konus(
                "Neyi bulmamı istediğini anlayamadım."
            )
            return True

        dosyalar = dosya_bul(
            hedef_raw,
            en_fazla=5
        )

        klasorler = klasor_bul(
            hedef_raw,
            en_fazla=5
        )

        if not dosyalar and not klasorler:
            print(
                f"Jarvis: '{hedef_raw}' bulunamadi."
            )
            konus(
                "Aradığın dosya veya klasörü bulamadım."
            )
            return True

        print(
            "Jarvis: Bulduklarim:"
        )

        for p in dosyalar:
            print(
                " -",
                p
            )

        for p in klasorler:
            print(
                " -",
                p
            )

        adet = len(
            dosyalar
        ) + len(
            klasorler
        )

        konus(
            f"{adet} eşleşme buldum."
        )

        return True

    # --------------------------------------------------------
    # SIL
    # --------------------------------------------------------

    if eylem == "sil":

        if hedef_raw:
            # Mevcut fonksiyon EVET/HAYIR onayi ister.
            dosya_sil_komutu(
                hedef_raw
            )
        else:
            konus(
                "Hangi dosyayı silmemi istediğini anlayamadım."
            )

        return True

    # --------------------------------------------------------
    # GODOT TEST
    # --------------------------------------------------------

    if eylem == "godot_test_ac":
        godot_test_projesini_ac()
        return True

    # --------------------------------------------------------
    # HIGGSFIELD
    # --------------------------------------------------------

    if eylem == "higgsfield_durum":
        hf_status()
        return True

    if eylem == "higgsfield_maliyet":
        hf_cost_test()
        return True

    if eylem == "higgsfield_video_uret":
        # Mevcut hf_video_uret fonksiyonunda kredi onayi korunur.
        hf_video_uret()
        return True

    # --------------------------------------------------------
    # SOHBET
    # --------------------------------------------------------

    if eylem == "sohbet":

        if not yanit:
            yanit = (
                "Seni anladım ama buna verecek "
                "uygun bir cevap oluşturamadım."
            )

        print(
            "Jarvis:",
            yanit
        )

        konus(
            yanit
        )

        return True

    print(
        "Jarvis: Ne yapmak istedigini tam olarak anlayamadim."
    )

    konus(
        "Ne yapmak istediğini tam olarak anlayamadım."
    )

    return True


'''


yeni = metin.replace(
    hedef,
    ai_kodu + "\n" + hedef,
    1
)


# ============================================================
# 2. ESKI "ANLAYAMADIM" FALLBACK'INI AI ILE DEGISTIR
# ============================================================

eski_parca = '''    print(
        "Jarvis: Bu komutu henüz anlayamadım."
    )

    return True
'''

if eski_parca not in yeni:
    # Dosyada UTF-8 goruntuleme farki olabilecegi icin
    # daha saglam regex ile son fallback'i bul.
    desen = (
        r'    print\(\s*'
        r'"Jarvis: Bu komutu hen[^"]*"\s*'
        r'\)\s*'
        r'return True'
    )

    eslesme = re.search(
        desen,
        yeni,
        flags=re.S
    )

    if not eslesme:
        print(
            "HATA: Eski anlayamama bolumu bulunamadi."
        )
        raise SystemExit

    yeni = (
        yeni[:eslesme.start()]
        + '''    return ai_dogal_dil_fallback(
        komut
    )'''
        + yeni[eslesme.end():]
    )

else:
    yeni = yeni.replace(
        eski_parca,
        '''    return ai_dogal_dil_fallback(
        komut
    )
''',
        1
    )


# ============================================================
# 3. SYNTAX TESTI + YEDEK + KAYIT
# ============================================================

compile(
    yeni,
    str(jarvis),
    "exec"
)

zaman = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

yedek = jarvis.with_name(
    f"jarvis_yedek_ai_dogal_dil_oncesi_{zaman}.py"
)

shutil.copy2(
    jarvis,
    yedek
)

jarvis.write_text(
    yeni,
    encoding="utf-8"
)

print("TAMAM: AI dogal dil fallback Jarvis'e eklendi.")
print("CLAUDE: sadece komut anlasilmadiginda devreye girer")
print("DOGAL TURKCE: aktif")
print("SOHBET: aktif")
print("SILME ONAYI: korunuyor")
print("HIGGSFIELD KREDI ONAYI: korunuyor")
print("YEDEK:", yedek)
print("TEST: python jarvis.py")