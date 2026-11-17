# Ayet ve hadis alıntıları

**Temel kural: Hiçbir ayet numarası, hadis kaynağı ya da meal hafızadan yazılmaz.** Alıntıyı ajan bulur, doğrulamayı `alinti.py` betiği veri setlerine karşı yapar. Ajan bir referansı "biliyor" olsa bile onu yazmaz; betik bulamadıysa alıntı "bulunamadı" olarak kalır ve uzman kontrolüne düşer.

## Alıntı türleri

| Tür | Nasıl tanınır | Ne yapılır |
|---|---|---|
| **Ayet (tam)** | قال تعالى، قوله تعالى، كما قال الله، لقوله عز من قائل vb. ile ya da tanınan bir ayet lafzı ile gelir; ayetin tamamını ya da büyük kısmını aktarır | Türkçede **meal metni aynen** konur, dipnot: `Ra'd 13/39.` |
| **Ayet (kısmi)** | Ayetin bir parçası | Çevirmen parçayı mealin ifadesine uygun çevirir, dipnot: `Hac 22/52.` |
| **İktibas** | Yazar ayetin bir ifadesini kendi cümlesine yedirmiş, alıntı işareti yok | Çeviri yazarın cümlesini çevirir, dipnot: `Krş. İbrâhîm 14/11.` |
| **Hadis** | قال النبى، قال رسول الله، فى الحديث، كما ورد vb. | Çevirmen hadisi çevirir (veri setindeki Türkçe karşılığa bakarak), dipnot: `Müslim, nr. 199.` |
| **Hadise işaret** | Yazar hadisin bir ifadesine değiniyor (ör. "عضّ عليها بنواجذك") | Dipnot: `Krş. ...` (betik bulabildiyse) |
| **Kutsî hadis, dua, kelâm-ı kibâr** | | Hadis gibi işlenir; bulunamazsa sadece işaretlenir |

## Doğrulama sonuçları

| `eslesme.durum` | Anlamı | Türkçe metinde |
|---|---|---|
| `dogrulandi` | Lafız veri setinde birebir bulundu | Referans dipnotu |
| `dogrulandi` + `kisa: true` | 3-5 kelimelik kısa alıntı birebir bulundu | Referans dipnotu; birden çok eşleşme olabilir, `ayrica` listesine bak |
| `yakin` | Lafız birebir tutmuyor ama çok yakın (yazar başka bir rivayetten ya da mana ile aktarmış olabilir) | Dipnot `Krş. ...`; sayfa kontrol listesine düşer |
| `bulunamadi` | Veri setinde yok (başka bir kaynaktan olabilir, uydurma olabilir, yanlış tespit olabilir) | Dipnot yok; sayfa kontrol listesine düşer |

Veri setleri: Kur'an (Arapça + Diyanet İşleri meali), Buhârî, Müslim, Ebû Dâvûd, Tirmizî, Nesâî, İbn Mâce, Muvatta (Arapça + Türkçe), Şah Veliyyullah'ın Kırk Hadis'i (Arapça). Bunların dışındaki kaynaklardan (Müsned, Hâkim, Taberânî...) gelen hadisler "bulunamadı" çıkar. Bu, hadisin uydurma olduğu anlamına gelmez.
