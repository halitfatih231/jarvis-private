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
