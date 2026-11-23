# Codex proje talimatları: Türk Tarihi

Bu proje tarihî, eğitici ve kaynaklı Türkçe Instagram içeriği üretir. `config/agents.json` içindeki **20 uzman rolünü** koru. Bunlar ilk aşamada `scripts/run.py` içinde tek ücretsiz yürütücüdeki 20 iş modülüdür; bağımsız AI ajanı olduklarını iddia etme.

## Sırasıyla uygula
1. Önce resmî veya akademik kaynakları bul; kaynağı açmadan yeni bir iddiayı doğrulanmış olarak işaretleme.
2. `data/topics.json` içine konuyu, üç somut olguyu, kronolojiyi, dönemi ve kaynak URL'lerini ekle.
3. Büyük iddialar, tartışmalı tarihler, tartışmalı etnik tanımlar, tarihî alıntılar ve nedensellik için ek kaynak iste/araştır.
4. Sahte alıntı, uydurma savaş diyalogu, çarpıtılmış tarihî fotoğraf, telif ihlali ve sahte kronoloji üretme.
5. `python -m scripts.run --topic KONU-ID --out output/...` ile taslak üret.
6. `python -m unittest discover -s tests -v` çalıştır.
7. Üretim için **0 ücretli API hedefi** koru; ücretli API çağrılarını kullanıcı onayı olmadan etkinleştirme.
8. Instagram'da yayın yapma; insan onayı, Meta uygulaması, token ve doğrulanmış kamuya açık medya URL'si olmadan yayın kapısını açma.

## Üslup
Doğru, tarafsız, merak uyandırıcı, özlü. Kökenleri, dönemleri, devletleri ve bireyleri birbirine karıştırma. Tarihî yeniden canlandırmaları açıkça etiketle. Her gönderide kaynakları sakla ve uygun yerde paylaş.

## Maliyet
Çoklu uzman görevini mümkün olduğunca aynı yürütmede işle. Ödeme gerektiren modeller ve paralel subagent'lar yalnızca ölçülmüş iyileştirme ve önceden belirlenmiş bütçeyle açılsın.

## MUTLAK VİDEO KALİTE KAPISI (öncelikli)

- Sessiz yazı slaytlarını bitmiş Reels olarak sunma. Önizlemeyi asla `reel.mp4` veya `ready` olarak etiketleme.
- Varsayılan taslak 60–75 saniye, 9:16, 720×1280 ve 30 fps olmalı; Remotion sahne/altyazı hareketini, FFmpeg konuşma ve ses miksajını üretmeli.
- En az 10 ayrı sahne ve her cümleyle ilgisi bulunan görsel gerekir. Mümkünse doğrulanmış açık lisanslı tarihî fotoğraf, eser, alan, harita veya arşiv görseli kullan; canlandırmaları gerçek arşiv görüntüsü gibi gösterme.
- Altyazı konuşmaya zamanlanmalı ve kelime/ifade vurgusuyla hareket etmelidir. Anlatı Türkçe, coşkulu ama ölçülü belgesel tonunda olmalıdır.
- Piper sentetiktir; insan anlatıcısı doğallığı sağladığını iddia etme. Üretilen ses düz veya robotik duyulursa teknik test geçse bile taslak yayın kalitesini geçmez.
- Gerçek kaynak doğrulaması yapılmadan savaş sayıları, komutan alıntıları ve kesin taktik iddiaları ekleme.
- Ücretli video/ses modeli gerekiyorsa kullanıcı izni olmadan çağrı yapma.
- `python -m scripts.release_check ...` teknik kontrolleri ve ardından insan görsel/ses kalitesi onayını gerektir.

## v0.6 belgesel video biçimi
- Varsayılan üretim: `python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto`.
- Bütün 20 görev modülü her içerikte 60–75 saniyelik dikey tarih belgeseli için çalışır. Rol sayısı bağımsız/ücretli 20 AI ajanı olduğu anlamına gelmez.
- Kurgu Remotion ile 30 fps dikey kompozisyon, yavaş sinematik kamera hareketi, sahne geçişleri ve kelime/ifade vurgulu hareketli altyazı üretir; FFmpeg anlatım, müzik ve son H.264/AAC MP4 karışımını yapar.
- En az 10 ayrı görsel sahne kullan. Öncelik, Wikimedia Commons üzerinden lisans/atıf verisi doğrulanmış kamu malı veya ticari kullanıma açık tarihî eser, arkeolojik alan, nesne, harita ve arşiv görüntüleridir. Dosya başına yazar, lisans ve kaynak sayfası `MEDIA_ATTRIBUTION.md` içine yazılır. Gerçek fotoğraf olmayan canlandırmaları görsel üzerinde **TEMSİLÎ CANLANDIRMA** olarak belirt; görseli arşiv fotoğrafı diye sunma.
- Konuşma yönü: doğal Türkçe belgesel anlatıcısı; merak uyandıran sakin giriş, olgular net ve ölçülü, dönüm noktalarında canlı vurgu, kısa anlamlı duraklar. Bağırma, düz okuma ve habersiz ses efekti yapma.
- Gerçek insan kaydı varsa onu tercih et. Ücretsiz çevrimdışı Piper yalnızca yedek TTS'dir; sentetik sesi doğal insan sesi diye tanımlama. Kullanıcı örneği `180010.mp4` ses kanalı içermediğinden bu örneğin ses tonuna dair talimat çıkarma; yalnız görsel kurgu yaklaşımını referans al.
- Gerçek ses kaydı/Piper süresi 60–75 saniye değilse metni yeniden yaz; konuşmayı hızlandırıp/yavaşlatıp süreye zorla sığdırma.
- `scripts/instagram_publish.py` yalnızca açık insan onayı ve manuel çağrıyla çalıştırılabilir. GitHub `instagram-production` environment kurulu olmadan devreye almayın.
- Ücretli API ve ücretli görsel/ses servislerini kullanıcı izni olmadan etkinleştirme. Wikimedia Commons sorguları ücretsiz ve anahtarsız medya aramasıdır; dış LLM anahtarı yoksa hiçbir LLM çağrısı yapma.
- İnsan onayı, kaynak/lisans kontrolü ve ses/görüntü dinlemesi tamamlanmadan taslağı yayına hazır sayma. Instagram otomatik yayınını açma.
