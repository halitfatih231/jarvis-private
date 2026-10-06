# Jarvis için derin açık kaynak araştırması (2026-10-05, 2. tur)

Amaç: Jarvis'in aklını ve yeteneklerini hazır, ücretsiz ve olabildiğince yerel parçalarla büyütmek. Her bulgu Jarvis'in bugünkü
yapısına göre değerlendirildi. Bu yapı iki şeyden oluşuyor:
- Katmanlar: kurallar → yerel Qwen → Gemini → Claude.
- Güvenlik kuralı: tek mesajla taşıma, silme veya kapatma yok, gizli metin modele gitmez.

**Hiçbiri henüz kurulmadı.** Bulut ortamından Hugging Face'e erişim kapalı (403). Bu yüzden model indirme ve eğitim işleri
PC'de ya da ağ izni açılınca yapılır. Kod, test ve ölçüm betikleri bulutta yazılabilir.


> **Güncelleme (2026-10-06): ölçüldü.** MASSIVE tr-TR'nin 16.520 cümlesi Jarvis'in kurallarından geçirildi (Hugging Face kapalı
> olduğu için Amazon'un kendi dosyasından indirildi). **Hiçbir cümle zararlı bir iş yaptırmadı** (kapatma, taşıma, silme yok).
> Bulunan zararsız yanlış anlamalar düzeltildi: "crossword başlat" Word'ü açıyordu, "alarm ayarla" Ayarlar'ı, "programımı göster"
> çalışan programları listeliyordu (TASK-166). Tarama artık her push'ta Windows CI'da koşuyor. Niyet sınıflandırıcı için
> gömme modeli Hugging Face ister; o adım erişim açılınca.

---

## A. Hemen işe yarayacak 5 bulgu

| # | Bulgu | Jarvis'e ne katar | Zorluk |
|---|---|---|---|
| 1 | **Amazon MASSIVE veri seti, Türkçe bölümü (tr-TR)** | Profesyonel çevirmenlerin yazdığı yaklaşık 16 bin Türkçe sesli asistan cümlesi. 60 niyete etiketli: alarm, müzik, takvim, hava, e-posta... Bizim yaklaşık 440 cümlemizin 40 katı | Düşük |
| 2 | **UI Automation** (`uiautomation` kütüphanesi, Windows-MCP, Windows-Use) | Her programın düğmesini ve yazısını görmek. Chrome, Word, Electron ve Qt programları dahil | Orta |
| 3 | **Ses, parlaklık ve müzik kontrolü** (`pycaw`, `screen-brightness-control`, Windows medya kontrolü SMTC) | Jarvis'in bugün "değiştiremiyorum" dediği üç işi açar | Düşük |
| 4 | **Ollama yapılandırılmış çıktı** (JSON şeması ile kısıtlı üretim) | Anlama katmanındaki "model bozuk JSON döndürdü" hatalarını kökten bitirir | Çok düşük |
| 5 | **yoktez-mcp + OpenAlex + DergiPark** | Tez araştırman için YÖK Tez ve DergiPark'ta gerçek arama, tez PDF'ini okuma, gerçek DOI'li kaynak | Orta |

---

## B. Anlama (aklın asıl geliştiği yer)

### B1. Üç katmanlı yeni anlama düzeni (önerim)
```
cümle → [normalleştirme] → [kurallar] → [niyet sınıflandırıcı] → [yerel model, JSON şemalı] → [Gemini/Claude]
            yeni                bugün          YENİ, ücretsiz          bugün + şema                bugün
```

**Normalleştirme (yeni)**
- **Türkçe karakter düzeltme (deasciifier):** "masaustunde ne var" → "masaüstünde ne var". Telefondan ya da İngilizce klavyeden
  yazınca kurallar bugün kaçırabiliyor. Kütüphaneler: `NlpToolkit-Deasciifier`, `VNLP Normalizer` (yazım hatası düzeltme de yapar),
  `akana` (gündelik konuşma kısaltmalarını da düzeltir).
- **zeyrek** (MIT): kelimeyi kök ve eklerine ayırır. Olumsuzluk ve geçmiş zaman kurallarım bununla daha sağlam olur.

**Niyet sınıflandırıcı (yeni, en büyük kazanç)**
- Türkçe cümle gömme modeli üstüne **SetFit** ile eğitilir. Modeller: `multilingual-e5`, Türkçe ayarlı `e5-tr-nli`,
  Türkçe `bge-m3`; hepsi TR-MTEB'de ölçülmüş.
- Eğitim verisi iki kaynaktan gelir:
  - **MASSIVE tr-TR:** 16 bin cümle. Genel asistan niyetleri.
  - **Bizim eval setlerimiz:** yaklaşık 440 cümle. Jarvis'e özel işler.
- Milisaniyede, internetsiz ve ücretsiz çalışır. Emin değilse soru sorar. Tehlikeli işlerde yine EVET ister.
- Ölçüt değişmez: bütün setlerde **0 WRONG**.

**Yerel model**
- **Ollama `format` parametresine JSON şeması:** model geçersiz cevap üretemez. Not: Qwen 3.5/3.6'da şema uyumu sorunu
  bildirilmiş, kendi testlerimizle ölçülmeli.
- Model adayları:
  - Qwen3 8B/14B: araç seçimi F1 0.93/0.97.
  - Gemma 4 E4B: 140+ dil, ses girişi var.
  - Trendyol-LLM-8B-T1: Türkçe akıl yürütme.
- **DSPy (GEPA / MIPROv2):** anlama katmanının talimatını bizim eval setlerimizle otomatik iyileştirir. GEPA, başarısız örnekleri
  okuyup talimatı kendisi düzeltiyor. Elle prompt yazmanın yerini alabilir.

### B2. Tarih ve saat anlama
- `dateparser` Türkçeyi destekliyor ("23 saat önce"). "yarın saat 3'te" gibi gelecek ifadeleri zayıf olabilir; kendi test setimizle
  ölçülmeli. Hatırlatıcı ve takvim özellikleri için gerekli.

---

## C. Göz ve el: ekranı görmek ve kullanmak

| Araç | Ne yapar | Not |
|---|---|---|
| **uiautomation** (yinkaisheng, yaklaşık 2.8k yıldız) | Windows UI Automation'ın Python sarmalayıcısı. Win32, WPF, Qt, Chrome ve Electron programlarının öğe ağacını okur | Jarvis'e en kolay eklenecek parça. Pencereyi önce bulup sonra içinde aramak hızlı |
| **Windows-MCP** (CursorTouch) | UI Automation tabanlı hazır MCP sunucusu. Claude Desktop eklentisi olarak yayımlanmış | Kodunu okuyup fikirlerini almak için en iyi örnek |
| **Windows-Use** (Jeomon, MIT) | Aynı yaklaşımla çalışan tam ajan, 13 model sağlayıcısı | Ajan döngüsü örneği |
| **Microsoft UFO² / UFO³** (MIT) | Ana ajan işi böler, her program için uzman ajan. Hem tıklama hem programın kendi API'si | F adımı planlayıcısının tasarım örneği |
| **pywin32 / win32com** | Word'ü COM ile yönetir: belgeye doğrudan yazar, kaydeder, PDF'e çevirir | Word'e tuşla yazmak yerine belgeye doğrudan yazmak. Çok daha güvenilir |
| **python-docx** | Word dosyası oluşturur ve okur. Word açık olmasa da çalışır | "Tezimin 2. bölümünü oku" için |
| **Windows yerleşik OCR** (`winocr`) | Ekran görüntüsünden yazı okur. Türkçe dil paketi kurulabilir | UI Automation'ın göremediği yerler için ücretsiz yedek |
| **Qwen3-VL 2B/4B** (Ollama) | Görüntü anlayan yerel model. 4B için yaklaşık 3.5 GB ekran kartı belleği gerekir. Arayüz öğesi bulmada güçlü | "Ekranda ne var" sorusu için. Ağır, sonraya |
| **Playwright** | Tarayıcıyı programla yönetir: sayfa okuma, form doldurma | Web işlerini klavye kısayollarından kurtarır |

**Dosya bulma:** **Everything (voidtools) + `es` komutu** bütün diskte dosya adını anında bulur. Jarvis'in bugünkü klasör
taramasından kat kat hızlı. `everything-mcp` adında hazır bir Python paketi de var.

---

## D. Bugün "yapamıyorum" denen işler

`jarvis_router._UNSUPPORTED` listesindeki her işin bir çözümü var:

| Bugünkü cevap | Çözüm | Güvenlik |
|---|---|---|
| "Ses ayarını değiştiremiyorum" | **pycaw** (Windows ses API'si): aç, kıs, sessize al | Zararsız, onay gerekmez |
| "Ekran parlaklığını değiştiremiyorum" | **screen-brightness-control** | Zararsız |
| "Müziği kontrol edemiyorum" | **Windows medya kontrolü (SMTC)** `winsdk` / `py-now-playing` ile: durdur, devam, sonraki, "ne çalıyor" | Zararsız |
| "Wi-Fi, Bluetooth... değiştiremiyorum" | Windows Radios API (`winsdk`) | Kapatma işi onay ister: internet kesilirse Jarvis'in bulut katmanları da gider |
| "E-posta veya mesaj gönderemiyorum" | Gmail ve Takvim için yerel MCP sunucuları (OAuth, Masaüstü uygulaması) | **Gönderme her zaman EVET ister**, okuma serbest |
| "Telefonla arama yapamıyorum" | **KDE Connect** (Windows sürümü var): telefon bildirimleri, SMS okuma/gönderme | Gönderme EVET ister. Kurulumu uğraştırır, sonraya |

Ek yeni yetenek olarak **hatırlatıcılar** önerilir: "yarın 10'da hatırlat" denince `Windows-Toasts` ile bildirim gösterilir.
Zamanlama için Windows Görev Zamanlayıcı kullanılır; böylece Jarvis kapalıyken de çalışır.

---

## E. Kulak ve ses

| Parça | En iyi seçim | Not |
|---|---|---|
| Uyandırma | **openWakeWord** | "Jarvis" için kendi modelimiz yaklaşık 1 saatte eğitilir |
| Konuşma algılama | **Silero VAD v5** | 2026'da standart |
| Sesten yazıya | **faster-whisper + Türkçe ayarlı whisper-large-v3-turbo** | Türkçe hata oranı yaklaşık %12–19 |
| | Diğer adaylar: **Qwen3-ASR 1.7B** (Ocak 2026, 30 dil) | Türkçe sonucu yayımlanmamış, bizim ölçmemiz gerekir |
| | NVIDIA Parakeet v3 / Canary v2 | **Türkçe yok** (25 Avrupa dili). Kullanılmaz |
| | Voxtral Mini 3B | Türkçe hata oranı %23. Whisper'dan kötü |
| Yazıdan sese | **Piper** (Türkçe sesler: dfki, fahrettin, fettah, Cem) | Hızlı, CPU'da çalışır |
| | Edge TTS (Microsoft'un çevrimiçi sesleri, ücretsiz) | En doğal Türkçe ses, ama internet ister ve metin Microsoft'a gider |
| Hazır zincir | **huggingface/speech-to-speech** (Temmuz 2026) | Her parçası yerel olanla değiştirilebilir. Mimari örneği olarak bakılmalı |

---

## F. Hafıza ve "her şeyi hatırlayan Jarvis"

- **Bugünkü sade JSON hafızası doğru.** Letta/MemGPT ağır ve Jarvis'in yerine geçmeye çalışır. mem0, hafıza yüzlerce notu
  geçince anlamca arama için düşünülebilir. Ama aynı işi B1'deki gömme modeliyle kendimiz yaparız.
- **screenpipe:** ekranı ve sesi sürekli kaydedip aranabilir hale getirir ("dün okuduğum makale neydi?"). Yerel çalışır, Windows
  OCR ve UI Automation kullanır. Ama ayda yaklaşık 20 GB yer ve %5–10 işlemci kullanıyor, ticari lisansı ücretli. Gizlilik açısından
  da ağır bir karar. **Önerim: şimdilik hayır.**

---

## G. Tez ve akademik işler (sana özel)

- **yoktez-mcp** (MIT): YÖK Tez'de başlık, yazar, danışman, üniversite ve yıl ile detaylı arama yapar. İzinli tezlerin PDF'ini
  sayfa sayfa Markdown olarak okur. Python 3.11+.
- **DergiPark:** yaklaşık 2.5 bin dergi, 728 bin makale. OpenAIRE ve Google Scholar ile entegre.
- **TR Dizin** ve **OpenAlex API** (ücretsiz): gerçek DOI'li kaynaklar. Uydurma kaynak riskine karşı Jarvis'in verdiği her kaynak
  OpenAlex'te doğrulanabilir.
- **Zotero + yerel RAG** (Zotero-RAG-Assistant, rag-paper, thesis-cli): kendi PDF kütüphanende soru sorarsın, cevap sayfa
  numarasıyla gelir. Örnek: "ytö'de kelime öğretimi hangi makalelerde geçiyor". Hepsi Ollama ile yerel çalışır.
- **Önerim:** Jarvis'in araştırma modülüne önce **OpenAlex ile kaynak doğrulama**, sonra **YÖK Tez araması** eklenir.

---

## H. Güvenlik (yetenek arttıkça daha önemli)

- 2024–2026 araştırmalarının ortak sonucu: modeli "kötü talimata uyma" diye eğitmek yetmez. Güvenlik **modelin dışında**,
  kesin kurallarla sağlanmalı. Örnekler: CaMeL (çift model + bilgi akışı takibi), FIDES, Progent. Jarvis bunu zaten yapıyor:
  `CONFIRM_FIRST`, güvenlik taraması, `LOCAL_ONLY_SOURCES`.
- **Yeni risk:** Jarvis ekranı ve web sayfalarını okumaya başlayınca, okunan metindeki gizli talimatlar ("bu dosyaları sil")
  modele ulaşabilir (dolaylı talimat enjeksiyonu).
- **Kural önerisi:** Ekrandan, web'den ya da PDF'ten okunan metin **asla komut olarak çalıştırılmaz**. Yalnızca veri olarak
  gösterilir. Bu metni okuduktan sonra gelen tehlikeli işler her zaman EVET ister. CaMeL'in "çift model" fikrinin sade hali budur.
  Güvenlik taramasına bu kontrol de eklenir.
- **Open.Jarvis** (Windows için yerel öncelikli benzer proje, MIT) bize benzer üç iyi fikir taşıyor:
  - eklenti izin profilleri (güvenli / normal / yönetici),
  - gizlilik modu: açıkken hafıza modele gitmez,
  - URL'de yalnızca http/https: `file://` ve `javascript:` reddedilir.

---

## I. Benzer projeler (fikir almak için)

| Proje | Ne öğrenilir |
|---|---|
| **Open.Jarvis** (Windows, MIT) | Yerel yönlendirme + isteğe bağlı bulut, izin profilleri, gizlilik modu. Jarvis'e en çok benzeyen proje |
| **Leon AI** | Araç, bağlam ve hafıza düzeni. Belirlenmiş iş akışları |
| **PersonalJarvis** | Kodlama araçlarını ve tarayıcıyı yöneten masaüstü ajanı |
| **OpenJarvis (Stanford)** | Kişisel cihazda yapay zekâ, MCP araçları |
| **bertrandmbanwi/Jarvis** | 109 araç, tarayıcı otomasyonu, masaüstü katmanı |

---

## Önerilen yol haritası

| Sıra | İş | Nerede | Onay |
|---|---|---|---|
| 0 | Mevcut bulut işini PC'de birleştir ve dene | PC | — |
| 1 | **Ollama JSON şeması** + **Türkçe karakter düzeltme** (küçük, hızlı kazançlar) | Bulut | Hayır |
| 2 | **Ses / parlaklık / müzik** araçları (pycaw, sbc, SMTC) | Bulut kod + PC deneme | Hayır (zararsız işler) |
| 3 | **Niyet sınıflandırıcı** (MASSIVE tr-TR + bizim setler, SetFit) | Kod bulutta, eğitim PC'de | Hayır (varsayılan kapalı) |
| 4 | **Okunan metin komut değildir** güvenlik kuralı + tarama | Bulut | Hayır |
| 5 | **UI Automation ile her programı okuma** (salt okuma) | Bulut + PC | Hayır |
| 6 | Word'e COM ile yazma, Everything ile dosya bulma | Bulut + PC | Hayır |
| 7 | Tez araçları: OpenAlex doğrulama, YÖK Tez arama | Bulut | Hayır |
| 8 | Hatırlatıcı (Windows bildirimi + Görev Zamanlayıcı) | Bulut + PC | Hayır |
| 9 | Yerel model kıyası + DSPy ile talimat iyileştirme | PC | Model değişikliği senin kararın |
| 10 | Sesli Jarvis (openWakeWord, VAD, Whisper, Piper) | PC | **Evet** (sürekli mikrofon) |
| 11 | F adımı planlayıcı + tıklama | Bulut + PC | **Evet** |
| 12 | Gmail/Takvim, telefon (KDE Connect) | PC | **Evet** (hesap erişimi) |

---

## Kaynaklar
**Anlama:**
- MASSIVE: https://huggingface.co/datasets/AmazonScience/massive, https://amazon.science/blog/amazon-releases-51-language-dataset-for-language-understanding
- zeyrek: https://zeyrek.readthedocs.io/
- Deasciifier: https://pypi.org/project/NlpToolkit-Deasciifier, VNLP: https://vnlp.readthedocs.io/en/latest/main_classes/normalizer.html, akana: https://pypi.org/project/akana/0.1.0/
- TR-MTEB: https://research.itu.edu.tr/en/publications/tr-mteb-a-comprehensive-benchmark-and-embedding-model-suite-for-t/
- e5-tr-nli: https://huggingface.co/thealper2/intfloat-multilingual-e5-base-tr-nli, Türkçe bge-m3: https://huggingface.co/nezahatkorkmaz/turkce-embedding-bge-m3
- SetFit örneği: https://huggingface.co/nlp-team-issai/setfit-me5-large-instruct-v3
- Ollama yapılandırılmış çıktı: https://registry.ollama.ai/blog/structured-outputs, https://devtoollab.com/blog/llm-structured-outputs-guide-2026
- DSPy / GEPA: https://www.morphllm.com/gepa-prompt-optimization, https://futureagi.com/blog/what-is-dspy-2026/
- Yerel araç çağırma modelleri: https://insiderllm.com/guides/function-calling-local-llms/
- Gemma 4: https://aiworld.eu/story/google-has-released-gemma-4
- Türkçe modeller: https://github.com/kesimeg/awesome-turkish-language-models, https://arxiv.org/html/2609.28007
- dateparser: https://dateparser.readthedocs.io/

**Göz ve el:**
- uiautomation: https://awesome.ecosyste.ms/projects/github.com%2Fyinkaisheng%2FPython-UIAutomation-for-Windows
- Windows-MCP: https://mcpservers.org/servers/CursorTouch/Windows-MCP
- Windows-Use: https://github.com/Jeomon/Windows-Use
- UFO: https://github.com/microsoft/UFO, https://arxiv.org/html/2504.14603v1
- Word otomasyonu: https://pydocmaker.readthedocs.io/en/latest/s02_word_examples.html
- winocr: https://pypi.org/project/winocr
- Qwen3-VL: https://registry.ollama.ai/library/qwen3-vl, https://insiderllm.com/guides/vision-models-locally/
- Playwright / browser-use: https://www.morphllm.com/comparisons/playwright-vs-puppeteer
- Everything / es: https://www.voidtools.com/forum/viewtopic.php?p=41538, https://socket.dev/pypi/package/everything-mcp

**Sistem kontrolleri:**
- screen-brightness-control: https://pypi.org/project/screen-brightness-control/0.8.5/
- Windows medya kontrolü: https://learn.microsoft.com/en-us/uwp/api/windows.media.control, https://py-now-playing.readthedocs.io/en/latest/autoapi/py_now_playing/core/index.html
- Windows-Toasts: https://windows-toasts.readthedocs.io/
- KDE Connect: https://itsfoss.com/kde-connect-windows
- Google MCP: https://glama.ai/mcp/servers/antonio-mello-ai/mcp-google
- Windows 11 MCP: https://winaero.com/model-context-protocol-mcp-support-announced-for-windows-11

**Ses:**
- Türkçe Whisper turbo: https://huggingface.co/selimc/whisper-large-v3-turbo-turkish, Whisper doğruluğu: https://vexascribe.com/how-accurate-is-whisper
- Canary / Parakeet: https://arxiv.org/html/2509.14128v1
- Qwen3-ASR: https://www.gladia.io/blog/best-open-source-speech-to-text-models
- openWakeWord: https://pypi.org/project/openwakeword/0.4.0/
- Yerel sesli asistan zinciri: https://localaimaster.com/blog/local-speech-to-speech-assistant
- Piper Türkçe: https://huggingface.co/dcx514ai/piper_tts_turkish_high, Piper ve Kokoro karşılaştırması: https://www.promptquorum.com/ko/power-local-llm/piper-vs-kokoro-tts

**Hafıza:**
- mem0 ve Letta: https://vectorize.io/articles/mem0-vs-letta
- screenpipe: https://screenpi.pe/blog/best-ai-screen-recorder-2026

**Tez ve akademik:**
- yoktez-mcp: https://github.com/saidsurucu/yoktez-mcp
- DergiPark: https://cabim.ulakbim.gov.tr/dergipark/
- TR Dizin: https://trdizin.gov.tr/en/
- Zotero-RAG-Assistant: https://github.com/aahepburn/Zotero-RAG-Assistant, rag-paper: https://glama.ai/mcp/servers/i1ight/ragPaper

**Güvenlik:**
- CaMeL ve dış kurallarla savunma: https://arxiv.org/html/2606.26479v1, https://link.springer.com/article/10.1007/s10015-026-01152-3
- LlamaFirewall: https://arxiv.org/pdf/2505.03574

**Benzer projeler:**
- Open.Jarvis: https://github.com/dmrr35/Open.Jarvis
- Leon: https://github.com/leon-ai/leon
- PersonalJarvis: https://github.com/PersonalJarvis/PersonalJarvis
- OpenJarvis: https://openjarvis.stanford.edu/
- bertrandmbanwi/Jarvis: https://github.com/bertrandmbanwi/Jarvis
