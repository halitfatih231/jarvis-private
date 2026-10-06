# Jarvis: durum ve devir notu (2026-10-06)

Bu dosya bulutta yapılan son işleri ve bundan sonra ne yapılacağını özetler. Kredi biterse buradan devam edilir.

## Nerede ne var

- **Kod:** `halitfatih231/jarvis-dev`, dal **`cloud/windows-ci`** (en yeni; önceki bulut dallarının hepsini içerir).
- **App'e dokunulmadı.** `E:\Jarvis\UI` (App ile ortak) değişmedi. Yeni arayüz `Dev\ui` içinde.
- **Birleştirme rehberi:** jarvis-dev içinde `docs/BIRLESTIRME_VE_DENEME.md`.
- **Önizleme (örnek cevaplarla):** https://claude.ai/artifact/EY4KRaTJdHzGBezYcpgFPX

## Bu turda yapılanlar

| İş | Sonuç |
|---|---|
| Windows testleri (GitHub Actions) | Her gönderimde gerçek Windows'ta çalışıyor; son tamamlanan koşular yeşil |
| MASSIVE tr-TR (16.520 cümle) taraması | Zararlı eylem 0; üç yanlış okuma düzeltildi |
| Common Voice tr (52.857 cümle) taraması | Sıradan cümleler artık araç çalıştırmıyor; zararlı eylem 0 |
| Komut derlemi (1.478 Jarvis cümlesi) | 1466 tam, 10 güvenli, 2 eksik, **0 yanlış** |
| "Beni yarın ara" | Artık web araması yapmıyor |
| **"Jarvis Çekirdek" arayüzü** | Sıfırdan yazıldı (aşağıda) |
| Dosya listeleri | Simge + ad + boyut; tam yol üzerine gelince görünür |

### Jarvis Çekirdek arayüzü

- Canlı çekirdek: hazır (mavi), düşünüyor, çalışıyor, onay (amber), dikte (mor), hata (kırmızı), bağlantı yok.
  Sesli konuşma için `setLevel()` hazır; henüz bağlı değil.
- Güvenlik kapısı: "Onayla ve yap" / "İptal et". **Enter hiçbir zaman onaylamaz**, Esc iptal eder.
- Ctrl+K komut paleti, yazarken öneri (Tab), geçmiş (↑), kısa komutlar (`/yardım`, `/defter`, `/hafıza`, `/tema`...).
- Düzenli cevaplar (listeler, etiket-değer, kaynaklar), görev akışı paneli, ayarlar, telefon görünümü.
- İnternetten hiçbir şey yüklemez. Sunucu `.js` dosyalarını sabit türle gönderir (Windows kayıt defteri sorunu).
- Bulutta gerçek çekirdekle denendi: yetenekler, güvenlik kapısı ve iptal, masaüstü listesi çalıştı; tarayıcı hatası yok.
  **Gerçek Windows'ta elle henüz denenmedi.**

## Sohbetin geri kalanı (bu turdan önce konuşulanlar)

### Araştırma: Jarvis'i daha akıllı yapacak repolar ve yapay zekâlar
- Ayrıntılar: bu depoda **`JARVIS_ARASTIRMA_REPOLAR.md`** (2. tur). Başlıklar: hemen işe yarayacak 5 bulgu, üç katmanlı anlama
  düzeni, tarih/saat anlama, ekranı görme ve kullanma, "yapamıyorum" denen işler, ses, hafıza, tez/akademik işler, güvenlik,
  benzer projeler, yol haritası.
- Ana sonuç: aklın asıl geliştiği yer **anlama**. Cümleyi doğru işe çeviren küçük bir **niyet sınıflandırıcı** + kurallar,
  daha büyük bir modelden daha çok fayda sağlar. Bunun için Hugging Face erişimi gerekiyor (bulutta kapalı).

### OmniRoute işe yarar mı?
- Ne yapar: birçok model sağlayıcısını tek adrese bağlar, biri çökünce sıradakine geçer.
- **Karar: şimdilik hayır.** Akıl getirmez (eksik olan anlama). Jarvis zaten kurallar → Qwen → Gemini → Claude sırasıyla
  yedeğe geçiyor. Ücretsiz sağlayıcılar metni saklayabilir; bu, "özel metin modele gitmez" kuralına aykırı. Bir sunucu ve
  anahtar kopyası daha ekler. Claude Code'u OmniRoute'a bağlamak da beni akıllandırmaz, zayıf modele düşme riski getirir.

### Cümle setleri (yaklaşık 70.000 cümle)
| Set | Cümle | Lisans | Nereden |
|---|---|---|---|
| MASSIVE tr-TR | 16.520 | CC BY 4.0 | Amazon S3 |
| Common Voice tr | 52.857 | CC0 | sabit commit `2d46358…` |
| xSID tr | 800 | CC BY-SA | GitHub |

- Bunlar **güvenlik taraması** için kullanıldı: Jarvis sıradan bir cümleyle zararlı iş yapıyor mu? Sonuç: hiç yapmıyor.
- Veri setleri repoya konmadı. CI her koşuda indiriyor (`massive_sweep.py`; Common Voice için `--strict --every 4`).
- "Jarvis için kaç cümle gerekir?" sorusunun cevabı: genel cümleler güvenliği ölçer ama Jarvis'in **kendi işlerini** öğretmez.
  Bunun için iş başına etiketli cümle gerekiyor. 440 etiketli cümleden **1.478**'e çıkıldı (`command_corpus.py`); hedef ~5.000.

### Anlama düzeltmeleri (Dev/jarvis_router.py, jarvis_desktop_intent.py)
- Uygulama adı kelime başında olmalı ("ayarlar" bulanık eşleşmez).
- "Beni yarın ara", "polisi ara" gibi telefon cümleleri web araması yapmaz.
- "Boş yere", takvim/alarm/not uygulaması soruları disk ya da program durumu sanılmaz.
- Kibar arama ("… arar mısın"), "… gider misin", "tıklar mısın", "normal boyuta getir", "tekrar eden dosyaları bul",
  "en büyük klasörler", "bütün pencereleri indir" artık anlaşılıyor.
- Kaydırma yalnızca cümle tamamen kaydırma kelimelerinden oluşuyorsa çalışır.
- Cümle sonundaki nokta/ünlem atılır ("?" kalır).

### Ölçümler (son durum)
| Ölçüm | Sonuç |
|---|---|
| turkish_eval | 257/257 tam, WRONG 0 |
| turkish holdout | 36/40, WRONG 0 |
| desktop_eval / holdout | 87/88 ve 56/58, WRONG 0 |
| Komut derlemi | 1466/1478, WRONG 0 |
| MASSIVE + Common Voice | zararlı eylem 0 |
| Windows CI | tam regresyon yeşil |

### Windows testleri nasıl kuruldu
- `.github/workflows/windows-tests.yml`: windows-latest, Python 3.12. `E:` sürücüsü depoya bağlanır, model/ajan/beyin kapalı.
- `JARVIS_CI=1` yalnızca bu bilgisayara özel iki kontrolü atlar. İlk koşudaki 5 hata düzeltildi
  (zaman bütçesi, Excel testi, Python yolu).

### Diğer belgeler
- `JARVIS_SABAH_RAPORU_2026-10-05.md`, `JARVIS_DEVIR_NOTU_2026-10-04.md`, `JARVIS_YETENEK_INCELEMESI.md`,
  `JARVIS_BIRLESTIRME_VE_DENEME.md` (bu depoda).
- jarvis-dev içinde `Management/CLAUDE_REPORT.md`: her TASK'ın kaydı (WINCI, 166, 167, 168).

## Bilgisayarda denemek için

PC'deki Claude oturumuna yapıştırılacak metin:

> Jarvis repo klasöründe `docs/BIRLESTIRME_VE_DENEME.md` rehberini izle. Dal olarak `origin/cloud/windows-ci` al.
> App'e dokunma. Yerel commit edilmemiş değişiklik varsa önce ayrı bir dala kaydet. Çakışmada iki tarafı da koru.
> Rehberdeki otomatik testleri çalıştır; kırmızı test olursa atlama, çıktıyı bana göster.
> Sonra `Stop_Jarvis_Dev.cmd` ve `Start_Jarvis_Dev.cmd` çalıştır.

Ardından tarayıcıda `127.0.0.1:8766` adresini aç ve bir kez **Ctrl+F5**'e bas.

İlk denenecekler:

1. `neler yapabilirsin`
2. `masaüstünde ne var` (liste simgeli görünmeli, yol üzerine gelince çıkmalı)
3. `bilgisayarı kapat` → kapı açılmalı → **İptal et** (ya da Esc)
4. `not defterini aç ve toplantı saat üçte yaz` → solda görev akışında iki adım
5. Ctrl+K → "sekme" yaz

## Açık işler (öncelik sırasıyla)

1. **Bilgisayarda birleştirme + elle deneme** (yukarıdaki adımlar). Sorun çıkarsa: "bu cevabı hata defterine kaydet".
2. **App'e taşıma:** yalnızca senin açık onayınla.
3. **Komut derlemini ~5.000 cümleye büyütmek** (şu an 1.478).
4. **Hugging Face erişimi:** bulutta kapalı. Niyet sınıflandırıcı için gerekli.
5. **Adım F (planlayıcı):** onay bekliyor.
6. **Ses (adım G) ve konuşma animasyonu:** senin kararın. Arayüzde `listening` / `speaking` durumları ve `setLevel()` hazır.
7. Bulut kredisi son günü: **7 Ekim** (`/claim-credit`).

## Kurallar (değişmedi)

- App'e dokunulmaz. Taşıma/silme yalnızca açık **EVET** ile yapılır. `main`'e gönderilmez.
- Özel metin modellere gönderilmez. API anahtarı sohbete yazılmaz.
- Veri setleri repoya konmaz. Bulutta ücretli Gemini çağrısı yapılmaz.

## Son kayıt

- Son gönderim: `d96c033` (TASK-168c, dosya listesi görünümü).
