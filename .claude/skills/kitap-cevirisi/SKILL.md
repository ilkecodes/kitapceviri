---
name: kitap-cevirisi
description: Taranmış ya da PDF halindeki Arapça (ve Urduca, Uygurca) kitapları okuyup denetleyerek önce Arapça asıl metin Word'üne, sonra ayet/hadis referanslı Türkçe çeviri Word'üne dönüştürür; yazar düzeyinde ıstılah sözlükçesi ve çeviri hafızası tutar. Kullanıcı "çevir", "devam et", "kitap ne durumda", "Word'ü ver", "yeni yazar", bir düzeltme ya da yeni bir PDF eklediğini söylediğinde kullan.
---

# Kitap Çevirisi

`kaynak/` klasörüne konan PDF kitaplardan iki Word dosyası üretilir:
1. **Arapça asıl metin:** Baskıdan okunmuş, denetlenmiş, yazım standardına göre düzenlenmiş; her düzeltme dipnotlu.
2. **Türkçe çeviri:** Yazarın ıstılah sözlükçesine ve önceki çevirilerine uygun; ayetler Diyanet mealiyle, hadisler standart numaralı kaynak dipnotlarıyla.

Ara çalışma `calisma/<kitap>/` altında, yazar bilgisi `yazarlar/<yazar>/` altında durur. Her sayfanın durumu ayrı bir dosyada tutulur; iş istenildiği an bırakılıp "devam et" ile sürdürülebilir.

## Kullanıcıyla iletişim (en önemli kural)

Kullanıcı teknik biri değil. Kod görmek ya da anlamak istemiyor.
- Her zaman düz, doğal Türkçe konuş. Dosya yolu, JSON, betik adı, komut, hata çıktısı gösterme.
- Arka planda ne yaptığını anlatma; sonucu söyle: "Kitabı hazırladım, 141 sayfa; 3'ü boş."
- Teknik sorunu kendin çöz. Çözemezsen sade bir dille anlat, "bunu İlke Hanım'a iletin" de ve hata ayrıntısını `calisma/hata-notlari.md` dosyasına yaz.
- Kullanıcıya **sadece onun karar vermesi gereken şeyleri** sor: dil ve sütun tespiti doğru mu, tutarsız bir ıstılah nasıl yazılsın, deneme çevirisi uygun mu. Soruları toplu sor, tek tek değil.
- İlerlemeyi kısa ver: "Asıl metin: 60/141 sayfa. 2 sayfa uzman kontrolü bekliyor."

## Betikler

Proje kökünden: `python3 .claude/skills/kitap-cevirisi/scripts/<betik>.py ...` (Windows'ta `python3` yoksa `python`). Çıktılar `ANAHTAR değer` biçiminde, senin okuman için.

| Betik | İş |
|---|---|
| `kontrol.py` | Gerekli paketler kurulu mu |
| `hazirla.py "<pdf>"` | PDF'i sayfa görüntülerine böler, boş sayfaları ayıklar |
| `kirp.py <kitap> <sayfa>` | Okuması zor sayfayı yüksek çözünürlükte parçalara böler |
| `durum.py ozet\|siradaki\|guncelle\|kontrol\|kirpilacak\|metin-dok\|tarama-bitti\|sifirla` | İlerleme ve aşama yönetimi |
| `alinti.py dogrula\|tara\|ozet <kitap>` | Ayet/hadis alıntılarını veri setine karşı doğrular |
| `sozlukce.py liste\|adaylar\|topla\|onayla\|isaretle` | Yazar sözlükçesi |
| `yazar.py olustur\|hafiza-yukle\|hafiza-ekle-kitap\|ornek\|bul\|dok\|istatistik` | Yazar profili ve çeviri hafızası |
| `birlestir.py <kitap> [--asil] [--turkce] [--temiz]` | Word dosyaları |

## Alt-ajanlar ve paralellik

| Ajan | Girdi | Grup büyüklüğü |
|---|---|---|
| `sayfa-okuyucu` | görüntü | 3 sayfa |
| `sayfa-denetci` | görüntü + okuma | 3 sayfa |
| `edisyoncu` | metin | 5 sayfa |
| `alinti-tespit` | metin | 5 sayfa |
| `terim-tarayici` | metin dosyaları | 1 dosya |
| `sayfa-cevirmen` | metin | **art arda** 3 sayfa |
| `ceviri-denetci` | metin | 3 sayfa |
| `redaktor` | metin | 8 sayfa, tek ajan |

Aynı anda en fazla 3 ajan çalıştır (tek mesajda 3 Task çağrısı). Ajanlara sadece şu bilgileri ver: kitap kısa adı, yazar kısa adı, dil, `kaynak_duzen`, `katmanlar`, metin türü, kitaba özel notlar ve sayfa listesi (her sayfa için durum dosyası yolu; okuyucu/denetçi için görüntü yolu ve varsa parçalar). `durum.py siradaki` satırları: `sayfa  görüntü  durum_dosyası  parçalar`. Denetçilere, önceki ajanın dönüş mesajını **iletme**: Bağımsız olmaları gerekiyor.

Her ajan grubu bittikten sonra, **grubun bütün ajanları dönüş yaptıktan sonra**, `durum.py guncelle <kitap>` çalıştır; bir ajan hâlâ çalışırken çalıştırma. `BOZUK ... MESGUL` satırı o sayfanın o an yazıldığını gösterir: sıfırlama, ajanlar bitince `guncelle`'yi tekrar çalıştır. Diğer `BOZUK` satırları gelirse o sayfanın o aşamasını `durum.py sifirla` ile sıfırla ve bir kez daha dene. İkinci kez de bozuksa sayfayı bırak, `calisma/hata-notlari.md`'ye yaz, raporda söyle.

---

## 0. Her oturumun başında
1. `kontrol.py`. `EKSIK` dönerse `KUR:` satırındaki komutu çalıştır; başarısız olursa `KUR_2:` satırını dene. Bulut oturumundaysan `CLAUDE.md`'deki "Bulut oturumu" kurallarına da uy (görüntüleri yenile, her partiden sonra commit + push). Python hiç yoksa: "Bilgisayarda Python kurulu değil; İlke Hanım'ın yardımı gerekiyor" de ve dur.
2. `durum.py kitaplar` ve `kaynak/` klasörü: Hazırlanmamış PDF varsa yeni kitaptır. Devam eden kitap varsa `durum.py ozet <kitap>` → `SIRADAKI_IS`'e göre ilgili adıma geç.

## 1. Yazar profili (yazarın ilk kitabında bir kez)
Bu adım iki durumda yapılır: Yazar `yazarlar/` altında hiç yoksa, ya da varsa ama `yazar.py istatistik <yazar>` hafızada sayfa gösterdiği halde sözlükçede hiç onaylı terim yoksa (o zaman doğrudan 3. maddeden başla).
1. Yazar `yazarlar/` altında yoksa: `yazar.py olustur <yazar> --ad "..." --ad-ar "..."`. Kısa ad Latin harfli ve sade olsun (ör. `veliyyullah`).
2. **Önceki çeviriler:** Kullanıcıya yazarın daha önce çevrilmiş eseri olup olmadığını sor. Varsa Asıl ve Türkçe Word dosyalarını `yazarlar/<yazar>/onceki/` klasörüne koymasını iste. Her çift için: `yazar.py hafiza-yukle <yazar> --asil ... --ceviri ... --eser "..."`. (Sayfa işaretleri `﴿ كتاب ص ١٦ ﴾` / `﴿ s. 16 ﴾` ya da `[ص ١٦]` / `[s. 16]` biçiminde olmalı.)
3. Hafıza doluysa **profil çıkar:** `yazar.py dok <yazar>` → her dosya için bir `terim-tarayici` ajanı (B biçimi; çıktı dosyası `yazarlar/<yazar>/dok/oneriler-<n>.json`). Sonra:
   - `tutarli: true` ve makul olan terimleri `sozlukce.py onayla yazar:<yazar> --kaynak ... --turkce ... --ilk-gecis "..." --tur ...` ile onayla.
   - Tutarsız ya da ajanın yanlış bulduğu terimleri **tek bir listede** kullanıcıya sor ("Önceki çevirilerde المُثُل bir yerde 'meseller', bir yerde 'misâller' yazılmış. Hangisi olsun?"), cevaba göre onayla.
   - `uslup` bulgularını `yazarlar/<yazar>/uslup.md` dosyasına madde madde yaz.

## 2. Yeni kitap
1. Hazırlık:
   - Matbu kitap: `hazirla.py "kaynak/<dosya>.pdf"`
   - Yazma (YEK, Gallica, Princeton vb.): Kullanıcıya kütüphane kaydındaki varak aralığını sor (ör. "24a-25b"). Mecmuanın tamamı geldiyse önce birkaç sayfaya bakıp risalenin hangi PDF sayfalarında olduğunu bul. Sonra `hazirla.py "kaynak/<dosya>.pdf" --sayfalar <ilk>-<son> --varak-bas 24a`.
   - Tek tek görüntü dosyaları geldiyse (bir klasör dolusu JPG): `hazirla.py "kaynak/<klasör>"` (aynı seçenekler geçerli).
   Çıktı: `KITAP`, `BOS_SAYFA`, `METIN_KATMANLI_SAYFA`.
2. **Örnek tarama:** Baştan, ortadan ve sondan 4-5 sayfa görüntüsünü kendin aç ve `calisma/<kitap>/kitap.json`'a yaz:
   - `dil`, `yon`, `uretim`, `tur` (dini_tasavvufi | tarih | edebi | siir | akademik)
   - `kaynak_duzen` ve `katmanlar`: `references/duzenler.md`'ye göre. Kaynaklar farklı düzenlerde gelir (tek sütun, iki dilli sütun ya da paragraf, şerh, hâşiyeli yazma, mecmua). Tarifi gördüğün düzene göre yaz (ör. "İki sütunlu: sağ sütun Arapça asıl metin, sol sütun Urduca tercüme. Üst bilgide eser ve yazar adı var.") ve okunacak katmanları belirle (ör. `["matn"]`). **Şerhli** bir eserde matnın mı, yoksa matn ve şerhin birlikte mi alınacağını kullanıcıya sor.
   - `yardimci_sutun`: okunmayan tercüme katmanının dili (yoksa `null`)
   - `baslik` (asıl dilde), `baslik_ar`, `baslik_tr`, `yazar` (yazarlar/ altındaki kısa ad; yoksa adım 1)
3. Kullanıcıya kısaca söyle ve onaylat: eser, yazar, dil, sütun düzeni, sayfa sayısı, baskı kalitesi. Dil `references/diller.md`'de yoksa desteklenmediğini söyle ve dur. El yazması ya da `uygurca_eski` ise bütün sayfaların uzman kontrolü gerekeceğini açıkça söyle.
4. **Deneme partisi:** İlk 5 metin sayfasını bütün aşamalardan geçir (adım 3'ün tamamı, sonra adım 5'in tamamı; terim taramasını bu 5 sayfa için atla), sonra `birlestir.py <kitap>` ile iki taslak Word üret. Kullanıcıya: "İlk 5 sayfanın Arapça metni ve çevirisi hazır. Bakabilir misiniz? Uygunsa kitabın tamamına geçeyim." Onay gelmeden devam etme. Geri bildirimi `kitap.json` → `notlar`'a ve gerekiyorsa sözlükçeye / `uslup.md`'ye işle.

## 3. Asıl metin (kitabın tamamı, partilerle)
Bir parti = 9 sayfa. Her parti için:
1. **Okuma:** `durum.py siradaki <kitap> okuma --adet 9` → 3 `sayfa-okuyucu` (3'er sayfa) → `guncelle`.
2. **Denetim (QC-1):** `siradaki ... denetim --adet 9` → 3 `sayfa-denetci` → `guncelle`.
3. **Zor sayfalar:** `durum.py kirpilacak <kitap>` listesindeki her sayfa için `kirp.py <kitap> <sayfa>` ve `durum.py sifirla <kitap> <sayfa> okuma`; bu sayfaları okuma + denetimden **bir kez daha** geçir (ajanlar parçaları otomatik kullanır). İkinci seferde de düşük çıkarsa öyle kalır; kontrol listesine düşer.
4. **Edisyon:** `siradaki ... edisyon --adet 10` → 2 `edisyoncu` (5'er sayfa) → `guncelle`.
5. **Alıntı tespiti:** `siradaki ... alinti --adet 10` → 2 `alinti-tespit` → `alinti.py dogrula <kitap>` → `guncelle`.
6. **Düzen ve sıra kontrolü:** `durum.py duzen <kitap>`: Yeni listelenen sayfalara bak. Düzen farkı okumayı etkilemişse (ör. başka bir risaleye geçilmiş, tablo yanlış okunmuş) kitaba not ekle, gerekirse o sayfayı `sifirla ... okuma` ile ek talimatla yeniden okut. Yazmalarda ayrıca `durum.py takip <kitap>`: `UYUMSUZ` satırı, eksik ya da karışık varak demektir. Kullanıcıya kitabın hangi varakları arasında sorun olduğunu söyle; taramayı kontrol etmesini iste.
7. Bir satırlık ilerleme ver ve sonraki partiye kendiliğinden geç. Her partide onay isteme.

Bütün sayfalar `alintilandi` olunca:
- **Emniyet ağı:** `alinti.py tara <kitap>`. Listelenen her satır, ajanın kaçırdığı muhtemel bir alıntıdır: O sayfanın `alintilar` listesine yeni bir kayıt ekle (`id` sıradaki A numarası; `metin` satırdaki ifadeyi edisyon metninden birebir al; `bicim: tam`), sonra `alinti.py dogrula <kitap>`.
- `birlestir.py <kitap> --asil` → kullanıcıya: "Arapça asıl metin hazır. X sayfa uzman kontrolü bekliyor (kitap sayfaları: ...). Çeviriye geçiyorum."

## 4. Terim taraması (çeviriden önce bir kez)
1. `durum.py metin-dok <kitap>` → her dosya için bir `terim-tarayici` (A biçimi; çıktı `calisma/<kitap>/tarama/oneriler-<n>.json`). Ajana mevcut sözlükçeyi (`sozlukce.py liste <kitap> --hepsi`) de ver.
2. Önerileri birleştir. Sözlükçede olmayan, makul ve tartışmasız olanları `onayla`. Tartışmalı olanları (birden çok makul karşılık, yazar için önemli kavram) **tek listede** kullanıcıya sor.
3. `durum.py tarama-bitti <kitap>`.

## 5. Çeviri (partilerle)
Bir parti = 9 sayfa. Her parti için:
1. **Çeviri:** `siradaki ... ceviri --adet 9` → art arda 3'er sayfalık 3 pencere → 3 `sayfa-cevirmen`. Her ajana kendi penceresinden önceki sayfanın yolunu da ver. → `guncelle`.
2. **Sözlükçe:** `sozlukce.py topla <kitap>`:
   - `YENI`, tek öneri, makul → `onayla`. Birden çok öneri → en doğrusunu seç, `onayla`; diğerini kullanan sayfaları `durum.py sifirla <kitap> <sayfa> ceviri`.
   - `CAKISMA` → listelenen sayfaları `sifirla ... ceviri`.
   - `isaretle`, sıfırlanan sayfaları yeniden çevirt.
   - Önemli kararları ilerleme mesajında bir satırla bildir.
3. **Çeviri denetimi (QC-2):** `siradaki ... ceviri_denetim --adet 9` → 3 `ceviri-denetci` → `guncelle`.
4. **Redaksiyon:** `siradaki ... redaksiyon --adet 9` → tek `redaktor`. `GOZLEM` dönerse kuralı `kitap.json` → `notlar`'a ekle (sonraki partilerde çevirmene iletilir).
5. İlerleme ver, devam et. Her 4 partide bir taslak Türkçe Word üret.

## 6. Kitap bittiğinde
1. `durum.py kontrol <kitap>` → `birlestir.py <kitap>` (iki taslak Word).
2. Kullanıcıya: iki dosyanın hazır olduğunu, kaç sayfanın kontrol beklediğini ve bunların **kitap sayfa numaralarını** söyle. Kontrol bekleyen yerler Word'de sarı ile işaretli. Ayrıca "kaynağı bulunamayan" alıntıların sayısını söyle (`alinti.py ozet`).
3. Kullanıcı "son hali" derse `birlestir.py <kitap> --temiz`. Kontrol bekleyen sayfa varsa önce hatırlat.
4. **Öğrenme:** `yazar.py hafiza-ekle-kitap <kitap>` (kontrol bekleyen sayfalar eklenmez). Kitap boyunca biriken `GOZLEM`'leri ve kullanıcı geri bildirimlerinden yazara genel olanları `yazarlar/<yazar>/uslup.md`'ye ekle. Böylece yazarın sonraki kitabı bunlarla başlar.

## 7. Düzeltme istekleri
Sayfa numarası, kullanıcı aksini söylemedikçe **kitabın basılı sayfa numarası ya da yazmanın varak numarasıdır** (Word'deki [s. 43] / [ص ٤٣], yazmada [s. 24b]); durum dosyalarındaki `kitap_sayfa` ile eşleştir.
- Türkçe düzeltme: ilgili sayfanın `ceviri.bloklar` metnini düzelt.
- Arapça okuma hatası: `edisyon.bloklar`'ı düzelt (gerekiyorsa `tashihler`'i güncelle), sonra `sifirla ... alinti` ile o sayfayı alıntı ve çeviri aşamasından yeniden geçir.
- İsim/ıstılah değişikliği: `sozlukce.py onayla` ile güncelle, eski karşılığı içeren sayfaları bul (çeviri metinlerinde ara), `sifirla ... ceviri` ile yeniden çevirt.
- Ardından Word'leri yeniden üret.

**Uyarı:** Word dosyaları her seferinde yeniden üretilir ve yeni ad alır; elle yapılmış Word düzeltmeleri yeni dosyaya taşınmaz. Kullanıcıya düzeltmeleri sana söylemesini öner. Word üzerindeki son elden düzeltmeler en sonda, `--temiz` sürümde yapılmalı.

## Veri kaynakları (kullanıcı sorarsa)
Kur'an metni ve meal: Tanzil (Diyanet İşleri meali). Hadis: Kütüb-i Sitte ve Muvatta, Arapça ve Türkçe, standart numaralarla (fawazahmed0/hadith-api). Meal dosyası `veri/kuran.json.gz` içindedir ve değiştirilebilir.
