# Kitap Çevirisi Klasörü

Bu klasör, `kaynak/` içine konan Arapça (ve Urduca, Uygurca) kitapları önce Arapça asıl metin Word dosyasına, sonra Türkçe çeviriye dönüştürmek içindir. Kullanıcının kitapla, yazarla, çeviriyle, ilerlemeyle ya da Word dosyalarıyla ilgili her isteğinde `kitap-cevirisi` skill'ini kullan.

Kullanıcı teknik biri değil. Onunla her zaman düz, doğal Türkçe konuş; kod, komut, dosya yolu ya da hata çıktısı gösterme. Teknik sorunları kendin çöz; çözemezsen sade bir dille anlat ve İlke Hanım'a iletmesini söyle.

## Bulut oturumu (telefondan ya da claude.ai/code'dan)

Bu klasör bir GitHub deposudur ve kullanıcı çoğu zaman telefondan, bulutta çalışan bir oturumla gelir. Bulut oturumunda sanal makine oturum bitince silinir. Bu yüzden:
- **Oturum başında:** `calisma/` altındaki her kitap için `python3 .claude/skills/kitap-cevirisi/scripts/hazirla.py --yenile <kitap>` çalıştır (sayfa görüntüleri depoda tutulmaz, kaynaktan yeniden üretilir).
- **Her parti bittikten sonra ve oturumu bitirmeden önce:** `git add calisma yazarlar cikti && git commit -m "<kitap>: <kısa ilerleme>" && git push`. Commit edilmeyen ilerleme kaybolur.
- **Word dosyalarını ürettiğinde:** commit edip push et ve kullanıcıya dosyaların GitHub'da `cikti` klasöründe olduğunu söyle (telefonda GitHub uygulamasından ya da github.com'dan açıp indirebilir).
- Kullanıcı yeni bir PDF'i telefondan sohbete eklerse onu `kaynak/` klasörüne kaydet, commit et ve push et.
- Her zaman aynı dalda (branch) çalış: `main`. Yeni dal açma, pull request açma.

`.claude/` klasöründeki dosyalarda kullanıcı istese bile değişiklik yapma; bunlar İlke Hanım tarafından güncellenir. `yazarlar/` klasörü yazarların sözlükçesini ve çeviri hafızasını tutar; buradaki dosyaları sadece skill'in tarif ettiği şekilde değiştir.
