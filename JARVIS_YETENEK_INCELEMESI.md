# Claude'un çalışma biçimi — Jarvis'e ne aktarılabilir? (2026-10-05)

Kullanıcının isteği: "Kendine bak, sen çok akıllısın. Yeteneklerin ne? Onları Jarvis'e geçir."

## Önce dürüst bir not

Benim zekâm büyük bir dil modelinden geliyor. O model bir dosya olarak Jarvis'e kopyalanamaz. Ama Jarvis zaten aynı
türden modelleri çağırabiliyor: Claude (katman 3) ve Gemini (katman 2). Yani Jarvis'in "beyni" eksik değil; eksik olan iki şey var:

1. **Modeli kullanma biçimi.** Bir işe nasıl yaklaştığım: önce anlamak, planlamak, yapmak, sonucu kontrol etmek, gerekirse
   düzeltmek, bilmediğimi söylemek.
2. **Araçlar.** Gözler (ekranı/dosyayı okumak) ve eller (yazmak, tıklamak). Model ne kadar akıllı olursa olsun, eli olmayan
   bir şeyi yapamaz.

Aşağıdaki tablo, benim bir işte kullandığım her yeteneği ve Jarvis'teki karşılığını gösteriyor.

## Yetenek tablosu

| # | Yetenek | Ben nasıl yapıyorum | Jarvis'te bugün | Eksik / aktarım |
|---|---|---|---|---|
| 1 | **Bağlamı hatırlamak** | Konuşmanın tamamını görüyorum; "onu", "aynısını", "dünkü dosya" neyi kastediyor biliyorum | Sohbette son 4 tur; komutlarda yalnızca bir önceki mesaj ve son tarayıcı/pencere/dosya bağlamı | **Konuşma hafızası**: son 10 tur + "onu/orayı/aynısını/öbürünü" çözme |
| 2 | **Niyeti anlamak** | Her cümleyi anlamıyla okuyorum, kalıba bakmıyorum | Önce kurallar; model yalnızca şüpheli cümlelerde ve varsayılan olarak KAPALI | Anlama katmanını yerelde açmak (yerel ölçüm 167/168, 0 yanlış). Karar ve maliyet senin |
| 3 | **Yap ve kontrol et** | Bir komut çalıştırıyorum, çıktısını okuyorum, beklediğim olmadıysa düzeltiyorum | Eylemi yapıyor, aracın mesajını aktarıyor; sonucu kendisi kontrol etmiyor | **Eylem sonrası doğrulama**: pencere gerçekten açıldı mı, sekme geldi mi, yazı yazıldı mı? Olmadıysa bir kez başka yol, sonra dürüst cevap |
| 4 | **Görmek** | Dosyaları, test çıktılarını, kodu okuyorum | Ekranı göremiyor; yalnızca pencere başlıklarını ve sekme adlarını biliyor | **Ekranı okumak**: öndeki pencerenin metnini Windows UI Automation ile okumak (yerel kalır). Ekran görüntüsü + görsel model ancak açık izinle |
| 5 | **Yazmak / üretmek** | İstenen metni yazıyorum | **Bugün eklendi (TASK-160)**: Not Defteri / Word / WordPad'e yazma, dikte modu, "bir şiir yaz" deyince önce metni üretip sonra yazma | Sesli dikte (aşağıda) |
| 6 | **Bilgi bulmak** | Web'de arıyorum, kaynak gösteriyorum | Araştırma modu (TASK-152): Gemini + Google, derinde Claude | Gerçek anahtarla bir kez denenmeli |
| 7 | **Bilmediğini söylemek** | Emin değilsem söylüyorum, uydurmuyorum | Sohbet talimatı + "yaptım" süzgeci + "yapamıyorum" cevapları | Ölçmeye devam (yanlış iş sayısı her sette 0) |
| 8 | **Çok adımlı iş** | Bir adımın sonucuna göre sonrakini seçiyorum | Yerel zincir (sırayla, modelsiz) + model planlayıcı (adımları baştan yazar, sonucu görmez) | Planlayıcı her adımın **sonucunu** görsün: "ilk sonucu aç, PDF ise indir" gibi |
| 9 | **Kendini sınamak** | Değişiklikten önce ve sonra ölçüyorum, kontrol seti tutuyorum | Hata defteri var; kendini ölçmüyor | Hata defterinden haftalık özet; kullanıcının düzeltmesinden **kural önerisi** (onayla eklenir) |
| 10 | **Kullanıcıyı tanımak** | Proje notlarını (CLAUDE.md) ve tercihleri okuyorum | Yalnızca kimlik metni | **Tercih dosyası**: "hocam" hitabı, kısaltmalar ("ytö" = yabancı dil olarak Türkçe öğretimi), sık siteler, klasör takma adları |
| 11 | **Tehlikeli işte durmak** | Silme/taşıma gibi işlerden önce soruyorum | EVET onayı, geri alınabilir taşıma | Var. Aynı kural yeni araçlara da uygulanıyor (dikte yalnızca yazı programlarına, kısayol tuşu yok) |

## Bugün yapılan: dikte (TASK-160, dal `cloud/dictation`)

- "not defterine merhaba dünya yaz", "word'e şunu yaz: ...": metin olduğu gibi yazılıyor. İçinde "sonra ara", "neden"
  gibi sözcükler geçse bile komut sanılmıyor.
- "not defterine bir şiir yaz", "not defterini aç ve kısa bir mektup yaz": Jarvis metni önce sohbet modeliyle üretiyor,
  sonra yazıyor ve ne yazdığını cevapta gösteriyor. Özel bilgi içeren istek modele gönderilmiyor.
- **Dikte modu.** Komut: "dikte başlat" ya da "word'e dikte edeceğim".
  - Bundan sonraki her mesaj programa bir satır olarak yazılır. Hiçbiri komut olarak çalıştırılmaz ("paint'i kapat" bile yazılır).
  - "dikte bitti" ile durur. 10 dakika mesaj gelmezse kendiliğinden kapanır.
  - Pencere kapanır ya da değişirse dikte de kapanır.
- **Güvenlik** (`Dev/jarvis_typing.py`, Jarvis'te klavye girdisi gönderen tek yer):
  - Yalnızca Not Defteri, Word ve WordPad'e yazar. Tarayıcıya, komut istemine ya da başka bir pencereye asla yazmaz.
  - Yalnızca harf ve Enter gönderir. Ctrl/Alt/Win kısayolu basamaz; bu yüzden kaydedemez, silemez, bir şey çalıştıramaz.
  - Doğru pencerenin önde olduğunu her 24 karakterde bir yeniden kontrol eder. Başka bir pencereye tıklarsan hemen durur
    ve kaç karakter yazdığını söyler.
  - Tek seferde en çok 4.000 karakter yazar. Metin hiçbir modele gitmez, mesajdan doğrudan pencereye yazılır.
- Bulutta sahte pencere ve klavyeyle test edildi (15 test). **Gerçek Windows'ta henüz denenmedi.** İlk deneme Dev'de:
  "not defterini aç ve merhaba yaz". Türkçe harfler (ğüşıöç) de denenmeli.

## Sesli dikte: senin kararın

Jarvis şu an yalnızca yazıyla konuşuyor. Sesle dikte için üç yol var:

1. **Windows'un kendi sesle yazma özelliği (Win+H).** Hemen kullanılabilir, Jarvis'te değişiklik gerektirmez: Not Defteri'nde
   Win+H'ye basıp konuşursun. Ses Microsoft'a gider.
2. **Jarvis arayüzüne mikrofon düğmesi** (tarayıcının konuşma tanıma özelliği). Kolay eklenir ama ses Google'a gider.
3. **Yerel Whisper modeli.** Ses bilgisayardan çıkmaz, ama ağırdır (indirme ve işlemci/GPU yükü).

Gizlilik açısından en iyisi 3, en kolayı 1.

## Önerilen sıra (sonraki adımlar)

| Adım | Ne | Nerede | Not |
|---|---|---|---|
| A | Dikte + metin üretip yazma | bulut | **Yapıldı** (TASK-160). Windows'ta denenmeli |
| B | Konuşma hafızası + tercih dosyası + kısaltmalar | bulut | **Yapıldı** (TASK-161): kısaltmalar, notlar, "bir daha yap" |
| C | Eylem sonrası doğrulama | bulut (kod) + Windows (deneme) | **Yapıldı** (TASK-162): program açma/kapatma. Windows'ta denenmeli |
| D | Anlama katmanını varsayılan açmak | yerel | Ölçüm var. Karar ve maliyet senin |
| E | Ekranı okumak (UI Automation) | Windows | İlk parça **yapıldı** (TASK-165): Not Defteri okuma + dikte kontrolü |
| F | Planlayıcının adım sonuçlarını görmesi | bulut | C'den sonra |
| G | Sesli dikte | senin seçimine göre | Yukarıdaki üç yol |

Ek (TASK-163): anlama modeli artık daha fazla bağlam görüyor:
- son 3 konuşma turu,
- en son kullanılan program,
- kısaltmaların.

Bu, adım B'nin model tarafı. Özel bilgi içeren turlar ve notlar isteme hiç girmiyor.

## F adımı için tasarım önerisi (senin onayını bekliyor, kodu yazılmadı)

**Bugün:** Planlayıcı tüm adımları baştan yazıyor ("chrome aç, google'a git, X ara, ilk sonuca tıkla") ve sırayla çalıştırıyor.
Bir adım başarısız olursa duruyor. Ama adımın **sonucuna göre** karar veremiyor. Örneğin "ilk sonuç PDF ise indir, değilse
ikinciye bak" gibi bir isteği yerine getiremiyor.

**Öneri:** Her adımdan sonra modele yalnızca o adımın kısa sonucu (sayfa başlığı, sonuç adları, açılan pencere başlığı)
gösterilir. Model bir sonraki adımı seçer ya da "bitti" der. Güvenlik çerçevesi değişmez:

1. **Araç listesi:** Model yine yalnızca bugünkü doğrulanmış listeden seçer. Dosya taşıma/silme yoktur.
   Kritik işler yine EVET ister.
2. **Adım sınırı:** En çok 6 adım ve toplam 60 saniye.
3. **Model yalnızca okur:** Model sayfa içeriğini değil, yalnızca başlıkları görür. Gizli içerik filtresi aynen uygulanır.
4. **İz kuralı:** Her adımın, kullanıcının cümlesinde bir izi olmalıdır (TASK-153 kuralı). "youtube'a da bak" demediysen
   YouTube açılmaz.
5. **Kapatma anahtarı:** Varsayılan KAPALI, `JARVIS_STEPWISE=1` ile açılır. Önce yerelde ölçülür.

**Risk:** Model her adımda seçim yaptığı için yanlış bir tıklama olasılığı artar. Bu yüzden önce kapalı gelir ve önce
salt okunur araçlarla denenir.
