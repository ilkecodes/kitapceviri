# Dil profilleri

Her ajan, kitap.json'daki `dil` alanına karşılık gelen bölümü okur. Örnek sayfalar işlendikçe buraya yeni notlar eklenir.

## urduca
- **Yön:** sağdan sola (`yon: rtl`)
- **Okuma:** Urduca genelde nestalik ile yazılır. Harfler eğimli iner, kelimeler iç içe geçebilir. ٹ ڈ ڑ ں ے ھ gibi Urducaya özgü harfleri Arapça karşılıklarıyla karıştırma (ے / ی, ہ / ه / ھ farkına dikkat). Farsça ve Arapça alıntıları olduğu gibi bırak.
- **Çeviri:** Arapça/Farsça kökenli kelimelerin Türkçede yerleşik bir karşılığı varsa onu kullan (ilim, hikmet, kitap). Yoksa anlamı ver. Şiir ve beyitleri satır yapısını koruyarak çevir. Yer adları için Türkçede yerleşik yazımı kullan (Lahor, Delhi, Keşmir).

## uygurca_modern
- **Yön:** sağdan sola (`yon: rtl`)
- **Okuma:** Arap harfli Uygur alfabesi (UEY). Ünlüler açıkça yazılır (ا ە و ۇ ۆ ۈ ې ى). Kelime başındaki ئ hemzesini koru.
- **Çeviri:** Uygurca Türkçeye yakın bir dil ve bu bir tuzak. Benzeyen kelimeleri otomatik olarak Türkçe karşılığına çevirme, anlam kaymalarına dikkat et (aynı kökten gelip farklı anlam kazanmış kelimeler). Cümleyi kelime kelime değil, anlam olarak aktar.

## uygurca_eski
- **Yön:** soldan sağa, Latin transkripsiyon (`yon: ltr`)
- **Okuma:** Uygur alfabesi dikey yazılır: yukarıdan aşağı, sütunlar soldan sağa. Transkripsiyonu Türkolojide yerleşik Latin transkripsiyon sistemiyle ver. Emin olmadığın her harfi [?] ile işaretle. Bu yazıda harf karışması çok sık (özellikle a/e, o/u, ö/ü, s/š, d/t); temkinli ol.
- **Çeviri:** Dinî terimler (Budist, Maniheist) için mutlaka sözlükçeye öneri ekle. Bu kitabın bütün sayfaları her durumda Türkolog kontrolünden geçecek.

## arapca
- **Yön:** sağdan sola (`yon: rtl`)
- **İki dilli sayfalar:** Hint alt kıtası baskılarında Arapça asıl metin çoğu zaman bir sütunda, Urduca (ya da Farsça) tercüme öbür sütundadır. `kitap.json`'daki `kaynak_duzen` hangi sütunun okunacağını söyler. **Sadece o sütunu oku.** Tercüme sütununu, sayfa başlığını (eser adı, yazar adı), filigranı ve site damgalarını (ör. maktabah.org) okuma.
- **Okuma (birebir):** Baskıda ne varsa onu yaz. Hemze, şedde, hareke **ekleme**; baskıda yoksa yok. Baskı hatalarını **düzeltme** (بالاستباط yazıyorsa بالاستباط yaz). Hint-Fars baskı geleneğindeki yazımları koru: noktasız son ى (فى، الى), الصلوة، السموات, ک/ك farkı. Noktalı harfler (ب ت ث ن ي, ج ح خ, د ذ, ر ز, س ش, ص ض, ط ظ, ع غ, ف ق) en sık hata kaynağıdır; özellikle litografi baskılarda nokta kaymış ya da silinmiş olabilir: gördüğünü yaz, emin değilsen `[?kelime]`.
- **Başlıklar:** Baskıda vurgulu yazılmış bölüm başlıkları (تحقيق، معرفة عظيمة، مشهد آخر، زيادة إيضاح gibi) `baslik` bloğu olarak verilir.
- **Kitap sayfa numarası:** Sayfanın üstündeki basılı sayfa numarasını (Arapça-Hint rakamı olabilir: ٤٣) `kitap_sayfa` olarak bildir.
- **Edisyon:** `references/edisyon-kurallari.md`.
- **Çeviri:** Ayet ve hadisler için `references/alinti-kurallari.md`. Klasik tasavvuf ve kelam ıstılahı (tedellî, tecellî, berzah, misâl, Hazîretü'l-Kuds, Şahs-ı Ekber, latîfe, nefs-i nâtıka...) Türkçeye çevrilmez, ıstılah olarak korunur; ilk geçtiği yerde bir kez kısaca açıklanır. Hangi ıstılahın nasıl yazılacağı yazar sözlükçesindedir.

## Bilinmeyen dil
Tespit edilen dil bu listede yoksa ana oturum kullanıcıya haber verir ve iş durur. Profil eklenmeden toplu işleme başlanmaz.
