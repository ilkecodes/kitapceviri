# Sayfa düzenleri ve katmanlar

Kaynaklar aynı düzende gelmez. Modern bir matbu, iki dilli bir Hint baskısı, bir şerh ya da hâşiyeli bir yazma çok farklı görünür. Hatta bir kitabın içinde düzen değişebilir (mukaddime tek sütun, metin iki sütun). Bu yüzden okuma **sütun** mantığıyla değil **katman** mantığıyla yapılır: Sayfadaki her blok ne olduğuna göre etiketlenir, kitabın ayarında hangi katmanların alınacağı yazar.

## Katmanlar

| Katman | Ne | Nasıl tanınır |
|---|---|---|
| `matn` | Asıl eserin metni | Ana metin; şerhli baskılarda çoğu zaman kırmızı, kalın, üstü çizili ya da parantez içinde |
| `serh` | Şerhin metni | Matnı açıklayan, ondan sonra ya da etrafında gelen metin; çoğu zaman قوله، أقول، أى gibi ifadelerle başlar |
| `hasiye` | Kenar notları, talikat | Sayfa kenarında, çoğu zaman eğik ya da farklı yönde; "منه"، "صح"، "ح" gibi işaretler |
| `tashih` | Kenardaki düzeltme | Metindeki bir işarete bağlı, sonunda "صح" olan kenar yazısı; asıl metne ait bir eksiği tamamlar |
| `tercume` | Başka dile çeviri | İki dilli baskılarda öbür sütun ya da paragraf (Urduca, Farsça, Türkçe) |
| `dipnot` | Baskının kendi dipnotları | Sayfa altında, çizgiyle ayrılmış |
| `ust_bilgi` | Sayfa başlığı, sayfa numarası, filigran, kütüphane mührü, site damgası | Okunmaz (sayfa numarası `kitap_sayfa` olarak bildirilir) |
| `takip` | Takip kelimesi (reklam) | Yazmalarda sağ sayfanın altında, bir sonraki sayfanın ilk kelimesi |
| `kayit` | Ferağ kaydı, temellük, vakıf kaydı, mühür yazısı | Okunur ama ayrı tutulur; çeviriye girmez, Arapça edisyonda ayrı bir bölümde verilebilir |

## Sık görülen düzenler

| Düzen | `kaynak_duzen` örneği | `katmanlar` |
|---|---|---|
| Tek sütun matbu | "Tek sütun Arapça metin, altta baskının dipnotları." | `["matn", "dipnot"]` |
| İki sütun, iki dil | "Sağ sütun Arapça asıl, sol sütun Urduca tercüme." | `["matn"]` |
| Paragraf paragraf iki dil | "Her Arapça paragrafın altında Urduca tercümesi var; Arapça paragraflar daha iri ve harekeli." | `["matn"]` |
| Şerh | "Matn kırmızı ve parantez içinde, şerh siyah; ikisi iç içe akıyor." | `["matn", "serh"]` ya da sadece `["matn"]` |
| Hâşiyeli yazma | "Nesih, sayfada 19 satır; kenarlarda talik hâşiyeler ve tashih notları; sağ sayfaların altında takip kelimesi." | `["matn", "tashih", "hasiye"]` |

Hangi katmanların alınacağı **esere** bağlıdır. Bir şerhi çeviriyorsak matn ve şerh birlikte alınır; şerhli baskıdan sadece matnı istiyorsak şerh atlanır. Bu karar örnek taramada kullanıcıya sorulur.

## Okuyucu için kurallar
- Her bloğun `katman` alanı vardır.
- `katmanlar` listesindeki katmanları **eksiksiz** oku. Listede olmayanları okuma, ama `takip` ve `kayit` katmanlarını her zaman kısa olarak yaz (kontrol için kullanılırlar).
- `tashih` katmanındaki kenar düzeltmesi, metindeki işaretli yere ait bir eksiği tamamlıyorsa, bunu metnin içine **koyma**. Ayrı blok olarak yaz, `bagli_oldugu` alanına ilgili kelimeyi not et. Edisyon aşaması bunu dipnotla metne yerleştirir.
- Sayfanın düzeni kitabın tarifindeki düzenden farklıysa (mukaddime, tablo, başka bir risale, farklı yazı), `duzen_farki` alanına bir cümleyle yaz.
