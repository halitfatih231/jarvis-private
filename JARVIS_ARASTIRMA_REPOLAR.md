# Jarvis'in aklını ve yeteneklerini geliştirecek açık kaynak araştırması (2026-10-05)

Amaç: Jarvis'e hazır, ücretsiz ve yerel çalışan parçalar eklemek. Her öneri Jarvis'in bugünkü yapısına göre değerlendirildi:
kurallar → yerel Qwen → Gemini → Claude, ve "onaysız zarar yok" güvenlik kuralı.
Hiçbiri henüz kurulmadı. Hepsi PC'de kurulur ve denenir.

## Kısa sonuç

Jarvis üç yerde zayıf. Bulduklarım bu üç yere göre ayrıldı:

| Zayıf yer | Bugün | En iyi bulgu |
|---|---|---|
| **Göz ve el** (ekranı görmek, tıklamak) | Yalnızca Not Defteri okunuyor, tuşla yazılıyor | **Windows-MCP / Windows-Use** (UI Automation ağacı, MIT) |
| **Anlama** (cümleyi doğru işe çevirmek) | Elle yazılmış kurallar + istenirse model | **Cümle-gömme + SetFit niyet sınıflandırıcı** (kurallarla model arası yeni katman) ve **zeyrek** (Türkçe ek çözümleme) |
| **Kulak ve ses** | Yok (yalnızca yazı) | **Silero VAD + faster-whisper (Türkçe turbo) + openWakeWord + Piper TTS** |

## 1. Göz ve el: bütün programları görmek ve kullanmak

### Windows-MCP (CursorTouch) ve Windows-Use (Jeomon), en önemli bulgu
- Windows'un erişilebilirlik altyapısı (UI Automation) ile ekrandaki her düğmeyi, kutuyu ve yazıyı adıyla ve konumuyla okur.
  Ekran görüntüsüne ve görüntü modeline gerek yok. Hızlı ve ücretsiz.
- MIT lisanslı, Python 3.10+, Windows 7–11. Windows-MCP, Claude Desktop'ta eklenti olarak da yayımlanmış.
- **Jarvis için anlamı:** "Word'de kaydet düğmesine bas", "Chrome'daki sekmelerin adları ne", "Ayarlar'da Bluetooth'u aç"
  gibi işler mümkün olur. Bugünkü `jarvis_screen_read` yalnızca Not Defteri'ni okuyabiliyor; bu bütün programlara yayılır.
- **Nasıl alınır:** Kodun tamamını değil, yalnızca "pencerenin öğe ağacını çıkar" kısmının fikrini alırız. Jarvis'e
  `jarvis_ui_tree.py` (salt okuma) eklenir. Tıklama ise güvenlik listesine girer: kaydet/sil/gönder gibi düğmeler EVET ister.

### Microsoft UFO² / UFO³ (MIT)
- Microsoft'un Windows ajanı. Bir ana ajan işi parçalara böler, her program için bir uzman ajan çalışır.
  Hem tıklama hem programın kendi API'si (Word için COM gibi) kullanılır.
- **Jarvis için anlamı:** Doğrudan kurmak ağır. Ama F adımının (adım adım planlayıcı) tasarımı için en iyi örnek:
  "önce API varsa onu kullan, yoksa tıkla" ilkesi Jarvis'e çok uyar. Word'e yazmak için tuş basmak yerine COM ile belgeye
  doğrudan yazmak hem daha hızlı hem daha güvenilir.

### Playwright (ve onu modelle süren browser-use)
- Tarayıcıyı programla yönetir: sayfadaki yazıyı okur, kutuya yazar, bağlantıya tıklar.
- **Jarvis için anlamı:** Bugün tarayıcıda klavye kısayollarıyla çalışılıyor. Playwright ile "bu sayfayı özetle",
  "ilk üç sonucu oku" ve "formdaki kutuyu doldur" güvenilir olur. browser-use bunu modelle yapıyor; önce Playwright'ın kendisi yeter.

### OmniParser (sonraya)
- Ekran görüntüsündeki düğmeleri görüntü modeliyle bulur. UI Automation'ın göremediği oyun veya özel programlar için.
  Ağır, GPU ister. Şimdilik gerek yok.

## 2. Anlama: aklın asıl geliştiği yer

### Yeni ara katman: cümle-gömme + niyet sınıflandırıcı (SetFit), en çok önerdiğim
- Bugün bir cümle ya kurala uyuyor ya da modele (yavaş, ücretli) gidiyor. Arada bir katman yok.
- **SetFit**, az örnekle eğitilen bir sınıflandırıcı. Elimizde zaten yaklaşık 440 etiketli Türkçe cümle var
  (turkish_eval 257, holdout 40, desktop 88, desktop holdout 58). Bunlarla "bu cümle hangi işe benziyor" diye
  milisaniyeler içinde, internetsiz ve ücretsiz karar veren küçük bir model eğitilebilir.
- Türkçe için hazır temel modeller var: `multilingual-e5` (Türkçe NLI ile ince ayarlı `e5-tr-nli`),
  Türkçe ince ayarlı `bge-m3`, ve Türkçe gömme kıyas seti TR-MTEB.
- **Güvenlik:** Sınıflandırıcı yalnızca *öneri* yapar. Emin değilse "şunu mu demek istedin?" diye sorar.
  Tehlikeli işler yine EVET ister.
- **Bulutta yapılabilir:** Eğitim ve ölçüm burada yapılır. Doğruluk mevcut eval setleriyle ölçülür ve "0 WRONG" şartı korunur.

### zeyrek: Türkçe ek çözümleme (MIT)
- Zemberek'in Python sürümü. "kapatmayı unuttum" → kapat + -mA + -yI, "açmasın" → aç + olumsuz.
- **Jarvis için anlamı:** Olumsuzluk ve geçmiş zaman kurallarım (`_NEG_*`, `_PAST_FORM`) elle yazılmış ve kırılgan.
  Bunları kök ve ek bilgisiyle yazmak hem daha sağlam hem daha genel olur. Alfa sürümü olduğu için önce yalnızca
  "ikinci görüş" olarak kullanılmalı: kural ve zeyrek farklı derse kayda geçer, daha sonra kural düzeltilir.
- Üstüne kurulu nöral bir sürüm de var (Aksu, BERTurk tabanlı); şimdilik gerek yok.

### Yerel model değişikliği
- Bugün yerel model `jarvis-local` (Qwen). Seçenekler:
  - **Qwen3 8B / 14B:** araç çağırmada güçlü (araç seçimi F1 0.93 / 0.97). Türkçesi orta.
  - **Gemma 4 E4B:** küçük, 140+ dil, **ses girişi de alıyor**. Türkçe için denemeye değer.
  - **Trendyol-LLM-8B-T1:** Qwen3-8B üzerine Türkçe akıl yürütme için eğitilmiş. Türkçe sohbet için güçlü aday.
- **Öneri:** Bir model seçmeden önce bizim kendi eval setlerimizle (anlama katmanı açık) üçünü yan yana ölçelim.
  Ölçüm betiğini bulutta hazırlarım, sen PC'de çalıştırırsın.

### Hafıza
- **mem0** (anlamca arama yapan hafıza) ve **Letta/MemGPT** (tam ajan çalışma ortamı) incelendi.
- Bugünkü sade JSON hafızası şimdilik doğru seçim. Letta Jarvis'in yerine geçmeye çalışır, çok ağır.
- Hafıza büyüyünce (yüzlerce not) yukarıdaki gömme modeliyle "anlamca en yakın notları getir" eklenir.
  Ayrı bir kütüphaneye gerek kalmaz.

## 3. Kulak ve ses: "Jarvis" deyince dinlemesi

Önerilen tamamen yerel zincir (2026'da standart hale gelmiş düzen):

| Parça | Seçim | Not |
|---|---|---|
| Uyandırma kelimesi | **openWakeWord** | "Jarvis" için kendi modelimiz yaklaşık 1 saatte eğitilebilir. Sürekli dinler ama hiçbir şey kaydetmez |
| Konuşma algılama | **Silero VAD** | Konuşmanın bittiğini anlar, kesmeden bekler |
| Sesten yazıya | **faster-whisper** + Türkçe ince ayarlı `whisper-large-v3-turbo` | Türkçe hata oranı yaklaşık %12–19. CPU'da da çalışır |
| Yazıdan sese | **Piper** (Türkçe sesler: dfki, fahrettin, fettah, Cem) | Hızlı, CPU'da gerçek zamanlı. Daha doğal ses gerekirse sonra Kokoro/XTTS |

- G adımındaki "Win+H mı, mikrofon düğmesi mi, yerel Whisper mı" sorusunun cevabı: **yerel Whisper**. Ses PC'den çıkmaz.
- Güvenlik: Sesle gelen tehlikeli komutlar da yazıyla gelenler gibi EVET ister. Yanlış duyulmuş "sil" kimseyi yakmaz.

## 4. MCP: Jarvis'i başka araçlara bağlamak
- Windows 11 MCP'yi yerleşik destekliyor; dosya ve pencere yönetimi MCP sunucusu olarak açılıyor. Kayıtta yaklaşık 2000 sunucu var
  (takvim, e-posta, tarayıcı, dosya).
- **Jarvis için anlamı:** Jarvis bir MCP *istemcisi* olursa her yeni yetenek için kod yazmak gerekmez. Örneğin Google Takvim'e
  bağlanmak bir ayar işi olur.
- Risk: Her sunucu yeni bir kapı açar. Yalnızca seçilmiş, salt okuma ağırlıklı sunucular eklenmeli; yazma işleri EVET listesine girer.

## Önerilen sıra

| Sıra | İş | Nerede | Onay gerekir mi |
|---|---|---|---|
| 0 | Mevcut bulut işini PC'de birleştirip denemek (`BIRLESTIRME_VE_DENEME.md`) | PC | Hayır |
| 1 | **Niyet sınıflandırıcı (SetFit)**: kurallarla model arası ücretsiz, hızlı akıl katmanı | Bulutta yazılır, PC'de denenir | Hayır (yalnızca öneri yapar, varsayılan kapalı) |
| 2 | **UI Automation ile ekran okuma**: her programı görmek (salt okuma) | Bulut + PC | Hayır |
| 3 | zeyrek'i "ikinci görüş" olarak eklemek | Bulut | Hayır |
| 4 | Yerel model kıyası (Qwen3 / Gemma 4 / Trendyol) | Betik bulutta, ölçüm PC'de | Model değişikliği senin kararın |
| 5 | Sesli Jarvis (openWakeWord + VAD + Whisper + Piper) | PC | Evet: mikrofon sürekli açık olacak |
| 6 | F adımı planlayıcısı (UFO fikirleriyle) + tıklama | Bulut + PC | **Evet** |
| 7 | MCP istemcisi | Bulut + PC | Evet: hangi sunucular |

## Kaynaklar
- Windows-Use: https://github.com/Jeomon/Windows-Use
- Windows-MCP: https://mcpservers.org/servers/CursorTouch/Windows-MCP
- Microsoft UFO: https://github.com/microsoft/UFO, makale: https://arxiv.org/html/2504.14603v1
- Agent S: https://github.com/sbc-learn/Agent-S
- zeyrek: https://zeyrek.readthedocs.io/, https://pypi.org/project/zeyrek
- TR-MTEB: https://research.itu.edu.tr/en/publications/tr-mteb-a-comprehensive-benchmark-and-embedding-model-suite-for-t/
- e5-tr-nli: https://huggingface.co/thealper2/intfloat-multilingual-e5-base-tr-nli
- Türkçe bge-m3: https://huggingface.co/nezahatkorkmaz/turkce-embedding-bge-m3
- SetFit örneği (multilingual-e5): https://huggingface.co/nlp-team-issai/setfit-me5-large-instruct-v3
- Türkçe Whisper turbo: https://huggingface.co/selimc/whisper-large-v3-turbo-turkish
- Whisper Türkçe doğruluk: https://vexascribe.com/how-accurate-is-whisper
- openWakeWord: https://pypi.org/project/openwakeword/0.4.0/
- Yerel sesli asistan zinciri: https://localaimaster.com/blog/local-speech-to-speech-assistant
- Piper Türkçe: https://huggingface.co/dcx514ai/piper_tts_turkish_high, Piper ve Kokoro karşılaştırması: https://www.promptquorum.com/ko/power-local-llm/piper-vs-kokoro-tts
- Yerel araç çağırma modelleri: https://insiderllm.com/guides/function-calling-local-llms/, https://localaimaster.com/blog/best-ollama-models-tool-calling
- Gemma 4: https://aiworld.eu/story/google-has-released-gemma-4
- Türkçe modeller listesi: https://github.com/kesimeg/awesome-turkish-language-models, Türkçe yerel model değerlendirmesi: https://arxiv.org/html/2609.28007
- mem0 ve Letta: https://vectorize.io/articles/mem0-vs-letta
- browser-use / Playwright: https://www.morphllm.com/comparisons/playwright-vs-puppeteer
- Windows 11 MCP: https://winaero.com/model-context-protocol-mcp-support-announced-for-windows-11
