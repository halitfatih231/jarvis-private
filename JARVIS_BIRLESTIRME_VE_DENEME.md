# Bulut işlerini PC'ye alma ve deneme rehberi (2026-10-05)

Bu rehber, bulutta yazılan her şeyi Windows'taki Dev'e almak ve denemek içindir. Hem sen hem PC'deki Claude oturumu adım adım
izleyebilir. **App'e dokunulmaz.** App'e taşıma en sonda ve yalnızca senin açık onayınla yapılır.

## 0. Bilinmesi gerekenler

- Bulut dalları birbirinin üstüne kuruldu. `cloud/safety` en yenisi ve **öncekilerin hepsini içeriyor**: `main`'in üstünde
  18 commit, 43 dosya. Yalnızca bu tek dalı almak yeterli.
- Yerel **TASK-151** (anlama korumaları) ve başlatıcı değişikliği repoda yok. Bulut onları hiç görmedi. Birleştirmede
  çakışma çıkabilir.
- Bulutta hiçbir şey gerçek Windows'ta denenmedi. Linux'ta 197 testin 135'i geçiyor; kalanlar Windows ister ve `main`'de de
  Linux'ta geçmiyor.

## 1. Birleştirme (PC'deki Claude oturumu yapabilir)

```powershell
# Jarvis repo klasöründe
git status                                   # yerel TASK-151 değişiklikleri commit edilmemişse önce onları kaydet:
git checkout -b local/task-151
git add -A
git commit -m "TASK-151 (yerel): anlama korumaları + başlatıcı"

git fetch origin cloud/safety
git checkout -b birlesik origin/cloud/safety
git merge local/task-151
```

Çakışma beklenen yerler ve ne yapılacağı:

| Dosya | Neden | Ne yapılmalı |
|---|---|---|
| `Dev/jarvis_understand.py` | TASK-151'in korumaları ve bulutun TASK-153 "cümlede iz" kuralı aynı yere dokunuyor | **İkisini de tut.** Bir model adımı ikisinden de geçmeli |
| `Dev/jarvis_core.py` | İki taraf da `_handle_core` başına ekleme yaptı | İki bloğu sırayla tut. Dikte/yazma ve hafıza blokları araştırmadan önce kalmalı |
| `Dev/_milestone_user_visible_regression.py` | İki taraf da test listesine ekleme yaptı | İki listeyi birleştir |
| `Management/CLAUDE_REPORT.md` | Rapor sonuna ekleme | İki girişi de tut |

## 2. Otomatik denemeler (sırayla, hepsi geçmeli)

```powershell
python Dev\_task164_safety_sweep_test.py     # güvenlik sözü: tek mesajla taşıma/silme/kapatma yok
python Dev\turkish_eval.py                   # beklenen: 257 cümle, WRONG 0
python Dev\turkish_eval.py --holdout         # beklenen: WRONG 0 (36/40 civarı)
python Dev\desktop_eval.py                   # beklenen: WRONG 0
python Dev\_milestone_user_visible_regression.py
```

Bir şey kırılırsa: o testin çıktısını bana getir (ya da PC'deki Claude'a ver). **Kırmızı testi atlama ya da silme.**

## 3. Dev'i yeniden başlat

`Stop_Jarvis_Dev.cmd`, ardından `Start_Jarvis_Dev.cmd`. Tek bir sunucunun (8766) dinlediğini kontrol et.

## 4. Elle deneme listesi (Dev'de, sırayla)

Her satırı dene ve sonucu işaretle. Beklenen olmazsa hemen yaz: **"bu cevabını hata defterine kaydet"**.

### Güvenlik (önce bunlar)
| Söyle | Beklenen |
|---|---|
| `chrome açık kalsın` | Hiçbir şey olmaz |
| `paint'i kapatmayı unuttum` | Hiçbir şey olmaz |
| `tamam` (bekleyen bir soru varken) | Onay sayılmaz |
| Masaüstünde deneme.txt oluştur, sonra `masaüstünde deneme diye bir dosya var mı` → `onu belgelere taşı` | **Önce soru sorar.** `hayır` → hiçbir şey taşınmaz. Tekrar sor → `evet` → taşır |

### Dikte (TASK-160)
| Söyle | Beklenen |
|---|---|
| `not defterini aç ve merhaba yaz` | Not Defteri açılır, "merhaba" yazılır |
| `not defterine ğüşıöç ĞÜŞİÖÇ yaz` | Türkçe harfler doğru çıkar |
| `not defterine bir şiir yaz` | Kısa bir şiir yazılır, cevapta da görünür |
| `dikte başlat` → `birinci satır` → `paint'i kapat` → `dikte bitti` | İki satır yazılır, Paint **kapanmaz** |
| Dikte sırasında başka pencereye tıkla, sonra bir şey yaz | "Pencere değişti, durdum" der, dikte kapanır |

### Doğrulama (TASK-162)
| Söyle | Beklenen |
|---|---|
| `paint'i aç` | "paint açıldı." (pencere göründükten sonra) |
| `word'ü aç` | Yavaş açılsa da en çok 8 sn içinde cevap verir |
| Paint'te bir şey çiz, kaydetme → `paint'i kapat` | "Kaydedilsin mi?" penceresi açık kalırsa "kapattım" demez, bunu söyler |

### Hafıza (TASK-161)
| Söyle | Beklenen |
|---|---|
| `bunu hatırla: tez danışmanım Ayşe Hoca` → `neleri hatırlıyorsun` | Not listede görünür |
| `ytö kaynaklarını araştır` | "yabancı dil olarak Türkçe öğretimi" ile arar, kaynak verir |
| `youtube aç` → `bir daha yap` | YouTube'u yeniden açar |
| Jarvis'i kapatıp aç → `neleri hatırlıyorsun` | Not hâlâ duruyor (`E:\Jarvis\Data\memory\memory.json`) |

### Anlama (TASK-153…159)
| Söyle | Beklenen |
|---|---|
| `jarvis googleda dijital oyunlar ara` | "dijital oyunlar" aranır |
| `paint açıp youtube aç` | İkisi de açılır |
| `önce paint aç sonra hesap makinesini aç` | Sırayla açılır |
| `masaüstünde ne var` | Masaüstü listelenir |
| `sesi kıs` | "Ses ayarını değiştiremiyorum… Hiçbir işlem yapılmadı." |
| `annemi ara` | "Telefonla arama yapamıyorum" |
| `bilgisayarı kapatır mısın` | EVET ister (deneme için `hayır` de) |

### Araştırma (TASK-152)
| Söyle | Beklenen |
|---|---|
| `yabancı dil olarak Türkçe öğretimi kaynaklarını araştır` | Kaynaklı cevap; `E:\Jarvis\Data\research\usage.json` bugünün sayısı 1 |
| `ytö kaynaklarını detaylı araştır` | Claude ile derin araştırma |

## 5. Sonra

- Bulunan her hata için: deftere yaz, bana getir. Ben önce hatayı yeniden üreten bir test yazar, sonra düzeltirim.
- 2–3 gün sorunsuz kullanımdan sonra App'e taşıma listesi hazırlanır. Taşıma yalnızca senin onayınla yapılır.
