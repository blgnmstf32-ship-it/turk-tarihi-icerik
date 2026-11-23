# Türk Tarihi sinematik belgesel Reels standardı v0.7

## Varsayılan üretim ölçüleri

- Süre: 60–75 saniye; süre tutmazsa metni yeniden yaz, konuşmayı hızlandırıp yavaşlatarak zorla sığdırma.
- Dikey 9:16, 1080×1920, 30 fps, 60–75 saniye ve 10–12 sahne; Remotion sahne kompozisyonu/altyazıyı, FFmpeg ses miksajını ve H.264/AAC son çıktıyı üretir.
- En az 10 ayrı sahne, net sahne kesmeleri, yavaş yakınlaşma/kaydırma, sinematik renk dengesi ve izleyici arayüzü güvenli alanında altyazı.
- Altyazılar cümle/ifade zamanına oturur; konuşma ilerledikçe sözcükler sırayla vurgulanır. Sözcük zamanları forced alignment değil, cümle içi yaklaşık ilerlemedir.

## Görsel standardı ve kaynak

- İlk tercih, Wikimedia Commons'tan lisansı ve atfı kaydedilmiş arkeolojik alan, eser, harita, tarihî minyatür veya açık lisanslı arşiv görüntüsüdür. Kaynak adı, yazar, lisans ve dosya sayfası `MEDIA_ATTRIBUTION.md` içinde saklanır.
- Gerçek fotoğraf mevcut değilse tarihsel gerçekliği iddia etmeyen, açıkça **TEMSİLÎ CANLANDIRMA** olarak etiketlenmiş görsel kullan. Görsel sahnenin tarihî ayrıntılarını doğrulanmış gibi sunma.
- En az 10 farklı görsel yoksa teknik kalite kapısı geçmez. Ücretsiz Commons sonuçları yetersiz olduğunda atıf/lisans uydurma veya ücretli servise düşme; temsili görsel kullan ve gerçekçi görsel şartının karşılanmadığını raporla.

## Anlatım ve ses

- Türkçe belgesel anlatıcısı: merak uyandıran ve yakın giriş; kişi, tarih ve yer adlarında net telaffuz; dönüm noktalarında canlı vurgu; tempoda kontrollü çeşitlilik ve anlamlı duraklar. Bağırma ve düz okuma yok.
- İnsan anlatıcı kaydı tercih edilir. Ücretsiz çevrimdışı Piper yalnız yedek TTS'dir ve sentetik olarak açıkça tanımlanır; insan sesi doğallığı iddia edilemez.
- Konuşma anlaşılır olmalı, müzik/ambiyans anlatıcının altında kalmalı; gerçek ses dinleme ve insan kalite onayı gerekir.
- Örnek `180010.mp4` ekran kaydında ses akışı bulunmadığından anlatıcı ses tonu için kaynak değildir; yalnızca görsel belgesel yaklaşımı referans alınmıştır.

## Tarih, maliyet ve yayın

- En az iki güvenilir kaynakla tarih doğrulaması; doğrulanmamış rakam, alıntı, taktik veya neden-sonuç iddiası yok.
- Yalnızca açık lisans koşullarına uyan görseller ve telif güvenli/özgün ses kullanılır. Kaynak atıflarını eksiksiz sakla.
- Ücretli API, ücretli TTS veya ücretli görsel/video servisi varsayılan olarak kapalıdır. Kullanıcı açıkça izin vermeden açma veya ücretli yedeğe yönelme.
- İnsan tarih, görsel ve ses incelemesi tamamlanmadan `ready` deme. Instagram otomatik paylaşımı kapalıdır; yayın için ayrıca açık insan onayı gerekir.

`python -m scripts.release_check ...` yalnız teknik koşulları kontrol eder; kaynak, lisans ve sanat kalitesi onayı yerine geçmez.
