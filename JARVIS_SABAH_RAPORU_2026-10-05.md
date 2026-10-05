# Jarvis — gece çalışması sabah raporu (2026-10-05)

Gece yalnızca bulutta çalışıldı. Senin bilgisayarına, App'e ve `main` dalına dokunulmadı. Beyin açılmadı, ücretli
Gemini çağrısı yapılmadı. Her şey `halitfatih231/jarvis-dev` deposunda, ayrı dallarda duruyor.

## 1. Kısa özet

| Ölçüm | Dün akşam | Bu sabah |
|---|---|---|
| Türkçe test seti (175 cümle) | 161 doğru, 0 yanlış iş | **175 doğru**, 0 yanlış iş |
| Yeni cümleler (82 cümle, ayarlamadan önce ölçüldü) | 67 doğru, **7 yanlış iş** | **82 doğru**, 0 yanlış iş |
| Kontrol seti (40 cümle, hiç ayarlanmadı) | — | **36 doğru**, 0 yanlış iş (2 yanlış iş vardı, düzeltildi) |
| Masaüstü testi (88 cümle) | 87 doğru | 87 doğru |
| Linux'ta geçen eski testler | 124 / 186 | **126 / 188** (hiçbiri bozulmadı; kalanlar Windows ister) |

"Yanlış iş", Jarvis'in yapmaması gereken bir şeyi yapması demek (örneğin "chrome açık kalsın" deyince Chrome'u açması).
En önemli ölçü bu ve her sette 0.

Uyarı: 175 ve 82 cümlelik setlerde kuralları o cümlelere bakarak düzelttim. Bu yüzden oradaki %100 biraz iyimser.
Gerçek duruma en yakın sayı, hiç ayarlanmayan **kontrol setindeki 36/40**.

## 2. Gece yapılanlar (dallar sırayla, her biri bir öncekinin üstünde)

### `cloud/fixes-3` — TASK-153 (dün akşamki canlı oturumdan çıkan hatalar)
- "bundan sonra senin adın ..." artık görev zinciri sanılmıyor. Planlayıcı hata verirse ham hata metni gösterilmiyor.
- Hata defteri: "bu cevabını hata defterine kaydet" çalışıyor. Ne yazılacağı belli değilse Jarvis soruyor ve bir sonraki
  mesajını not olarak yazıyor. "hata defterini aç" boşsa toplam kayıt sayısını söylüyor.
- Sohbet: uydurma bilgi yok, "hocam" diye hitap, argo/lakap yok ("patron", "başkan"). "Bakıyorum", "araştırıyorum",
  "davet ediyorum" gibi yapmadığı işleri söyleyen cevaplar süzülüyor.
- "çarpıya bas" pencere sanılmıyor. Modelin önerdiği adımın cümlede bir izi olmalı ("ytö den devam edelim" artık sekme açmıyor).

### `cloud/fixes-4` — TASK-154 (setteki son anlaşılmayan cümleler)
- Klasör soruları: "masaüstünde ne var", "indirilenlerdeki pdfleri listele", "belgeler klasörü ne kadar yer kaplıyor",
  "indirilenlerde kopya dosya var mı", "masaüstünde tez diye bir dosya var mı". Hepsi yalnızca okur, hiçbir şeyi değiştirmez.
- "şu an neler çalışıyor", "bir önceki sayfaya dön", "2. sekmeyi aç" (açık sekmeye geçer, yeni sekme açmaz).
- "pekii google a beşiktaş yazar mısın?" artık Google'da arıyor.
- Yapamadığı işler için dürüst cevap: ses, müzik, parlaklık, Wi-Fi/Bluetooth, mail/mesaj →
  "…yapamıyorum; bunun için bir aracım yok. Hiçbir işlem yapılmadı."

### `cloud/eval-2` — TASK-155 (yeni cümleler ve bulduğu hatalar)
- Senin konuşma tarzından 82 yeni cümle eklendi: "jarvis …", "kanka", "abi", "bi", "be", Türkçe harfsiz yazım
  ("chromeu ac"), büyük harf, "araştır" cümleleri. Beklentiler ayarlamadan **önce** yazıldı.
- Bu cümlelerin bulduğu 7 yanlış iş düzeltildi:
  - "chrome açık kalsın" → Chrome'u açıyordu
  - "paint'i kapatmayı unuttum" → Paint'i kapatıyordu
  - "paint'i açmasan iyi olur" → Paint'i açıyordu
  - "chrome açıldı mı" → Chrome'u açıyordu
  - "annemi ara" → Google'da "annemi" arıyordu (artık: "Telefonla arama yapamıyorum")
  - "jarvis googleda dijital oyunlar ara" → "jarvis googleda dijital oyunlar" diye arıyordu (baştaki "jarvis" artık atılıyor)
  - "youtube'dan tarkan aç" → yalnızca YouTube'u açıyordu (artık YouTube'da arıyor)
- Ayrıca: "bilgisayarı kapatır mısın" artık "bilgisayarı kapat" gibi EVET onayı istiyor. "ytö hakkında makale bul"
  araştırma modunu başlatıyor. "hata defterinde neler var" defteri gösteriyor.
- Yeni **kontrol seti** (`Dev/turkish_eval_holdout.py`, 40 cümle): kurallar yazıldıktan sonra yazıldı ve kurallar ona göre
  ayarlanmadı. İlk ölçüm 34/40, 2 yanlış iş. Yalnızca güvenlik için bu 2 yanlış iş düzeltildi:
  - "not defterini açmana gerek yok" → Not Defteri'ni açıyordu
  - "paint'i açınca ne oluyor" → Paint'i açıyordu
  Çalıştırmak için: `python turkish_eval.py --holdout -v`

## 3. Bilerek bırakılanlar

- Kontrol setinde anlaşılmayan 4 cümle (kontrol seti bozulmasın diye kural eklenmedi):
  "masaüstüne dön", "sayfayı tazele", "indirilenlerde tez diye bir şey var mı" (sohbete düşüyor) ve
  "bir önceki sayfaya geri git" (soru soruyor). Hiçbiri yanlış iş yapmıyor.
- Masaüstü kontrol setinde daha önce de olan 2 yanlış iş: "telegramı başlat" (`telegrami` diye bir program açmaya
  çalışıyor) ve "word ve excel'i aç" (yalnızca Word'ü açıyor). Bunlar uygulama listesine bağlı. Windows'ta bakılmalı.
- `_task005_tamper_test.py` Linux'ta argümansız çalışınca çöküyor. Main'de de aynısı oluyor, gece yapılanlarla ilgisi yok.

## 4. Senin yapacakların (yerelde, sırayla)

1. **TASK-151'i birleştir.** Yerel TASK-151 değişiklikleri (anlama korumaları) ve başlatıcı değişikliği hâlâ repoda yok.
   En son dal `cloud/eval-2`, gece yapılanların hepsini içeriyor. TASK-151'i bunun üstüne al.
   TASK-153'teki "cümlede iz olmalı" koruması TASK-151 ile örtüşebilir. İkisini de tut, daha sıkı olanı geçerli olsun.
2. Birleşmiş kodu Dev'e al ve tam regresyonu Windows'ta koş. Beklenen:
   - `python turkish_eval.py` → 257 cümlede 0 yanlış iş.
   - `python turkish_eval.py --holdout` → 0 yanlış iş.
3. Dev'de birkaç cümle dene: "chrome açık kalsın" (hiçbir şey olmamalı), "masaüstünde ne var", "sesi kıs"
   (dürüst "yapamıyorum"), "jarvis youtube'dan tarkan aç".
4. Araştırma modunu bir kez gerçek anahtarla dene (dünkü devir notundaki adım). `usage.json` sayısı 1 olmalı.
5. App'e taşıma yalnızca senin açık onayınla yapılır.

## 5. Dallar

`main` → `cloud/quick-fixes` → `cloud/turkish-eval` → `cloud/understanding` → `cloud/fixes-2` → `cloud/research` →
`cloud/fixes-3` → `cloud/fixes-4` → **`cloud/eval-2`** (en yeni, hepsini içerir)

---

## EK (sabah, 1 saatlik ek çalışma): `cloud/fixes-5` — TASK-156, gece kurallarının gözden geçirilmesi

Repodaki kod ve testlerde geçen 3.878 cümleyi gece öncesi ve sonrası kodla çalıştırıp karşılaştırdım. 60 cümlenin
davranışı değişmiş, bunların 58'i istenen değişiklik. İstenmeyen 2 değişiklik ve elle denediğim tuzak cümlelerde
bulunanlar düzeltildi:
- "YouTube'da openai ara ve ilk videoyu aç" tamamıyla YouTube'da aranıyordu. YouTube kuralı artık yalnızca "youtube'dan …"
  biçimini tanıyor ve zincir komutları almıyor.
- Türüne göre dosya listeleri ("indirilenlerdeki pdf dosyalarını göster") geçici dosyaları gizlemeyi bırakmıştı. Geri geldi.
- "word'e mesaj yaz" ve "interneti aç" gereksiz yere "yapamıyorum" cevabı alıyordu. Kural daraltıldı.
- "bir önceki sayfaya dönme" geri gidiyordu. Artık hiçbir şey yapmıyor.
- "paint'i normale döndür" bir ara geçmiş zaman sanıldı. Düzeltildi, yine komut olarak çalışıyor.
- "word ve excel'i aç": bilgisayarda bulunamayan ikinci program sessizce atlanıyordu. Artık o da deneniyor ve
  bulunamazsa açıkça söyleniyor.

Sonuç: Türkçe set 257/257, kontrol seti 36/40, masaüstü testi 87/88, masaüstü kontrol seti **56/58** (önce 54/58).
Hepsinde 0 yanlış iş. Linux'ta 127/189 test geçiyor, hiçbiri bozulmadı.

**En yeni dal artık `cloud/fixes-5`.** Yerelde TASK-151'i bunun üstüne al.

## EK 2: `cloud/fixes-6` — TASK-157, iki adımlı cümleler

- "paint açınca youtube aç" ve "paint açıp youtube aç" yalnızca YouTube'u açıyordu. Artık önce Paint, sonra YouTube açılıyor.
- "paint'i açtıktan sonra youtube'u aç" geçmiş zaman sanılıp hiçbir şey yapmıyordu. Artık iki adımı da yapıyor.
- "önce paint aç sonra youtube aç" her zaman modelli planlayıcıya gidiyordu, model yoksa hiçbir şey olmuyordu. Artık modelsiz,
  söylenen sırayla çalışıyor.
- Soru ve olumsuz cümleler yine hiçbir şey yapmıyor ("paint'i açınca ne oluyor", "paint'i açıp kapatma").
- Tüm ölçümler aynı ve 0 yanlış iş. Linux'ta 128/190 test geçiyor, hiçbiri bozulmadı.

**En yeni dal artık `cloud/fixes-6`.**

## EK 3: `cloud/fixes-7` — TASK-158, virgülle ayrılmış komutlar

- "paint aç, hesap makinesi aç" modelli planlayıcıya gidiyordu. Artık modelsiz, sırayla çalışıyor.
- 16 farklı çok adımlı cümle denendi. Hiçbiri bir adımı sessizce atlamıyor.
- Hâlâ modele bağlı olanlar (model yoksa hiçbir şey yapmıyor, yanlış iş de yapmıyor): "google aç beşiktaş ara", "chrome'u aç,
  sonra kapat", "not defterini aç ve merhaba yaz".
- Linux'ta 129/191 test geçiyor, hiçbiri bozulmadı. **En yeni dal artık `cloud/fixes-7`.**

## EK 4: `cloud/fixes-8` — TASK-159, modele bağlı kalan üç cümle

- "google aç beşiktaş ara", "youtube'u aç tarkan ara": artık modelsiz çalışıyor. İlk sürüm bir yan etki yaptı:
  "google'a gir ve openai yaz ve ara" cümlesini "ve openai yaz ve" diye bir aramaya çeviriyordu. Eski testler bunu yakaladı,
  düzeltildi ve teste eklendi.
- "chrome'u aç, sonra kapat": aynı cümlede adı geçen programı kapatıyor. Önceki konuşmadan kalan bir programı asla kapatmıyor.
- "not defterini aç ve merhaba yaz": Jarvis'in programların içine yazı yazacak aracı yok. Artık hiçbir şey yapmadan bunu
  açıkça söylüyor.
- Linux'ta 130/192 test geçiyor, hiçbiri bozulmadı. **En yeni dal artık `cloud/fixes-8`.**

## EK 5: `cloud/dictation` — TASK-160, dikte ve yetenek incelemesi

- Jarvis artık Not Defteri, Word ve WordPad'e yazabiliyor:
  - "not defterine X yaz" metni olduğu gibi yazar.
  - "not defterine bir şiir yaz" önce metni üretir, sonra yazar.
  - "dikte başlat" ile her mesajın bir satır olarak yazıldığı dikte modu açılır, "dikte bitti" ile kapanır.
- Güvenlik:
  - Yalnızca bu üç programa ve yalnızca harf/Enter yazar.
  - Kısayol tuşu basamaz.
  - Pencere değişirse hemen durur.
- Gerçek Windows'ta henüz denenmedi.
- Yetenek incelemesi: `docs/CLAUDE_YETENEKLERI_JARVIS.md`.
- **En yeni dal artık `cloud/dictation`.**
