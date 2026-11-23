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
- Yayınlanabilir MP4 için Türkçe doğal seslendirme, anlatıma göre en az 5 ayrı tarihî canlandırma/harita sahnesi, senkron altyazı, ambiyans ve telif güvenli ses, 9:16 en az 720×1280 görsel zorunludur.
- Gerçek kaynak doğrulaması yapılmadan savaş sayıları, komutan alıntıları ve kesin taktik iddiaları ekleme.
- Daha iyi kalite için ücretli video/ses modeli gerekiyorsa, maliyetini önceden göster ve açık izin almadan ücretli çağrı yapma.
- `python -m scripts.release_check ...` teknik kontrolleri ve ardından insan görsel/ses kalitesi onayını gerektir.

## v0.4 ücretsiz sesli taslak prodüksiyonu
- Yeni görev: `python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto`
- Ücretsiz Piper Türkçe TTS; ses modeli indirilip gerçek TTS olmalı, deney amaçlı ton/ses dosyası konuşma olarak gösterilmez.
- `scripts/illustrate.py` çizimleri temsili canlandırmadır; gerçek tarihî fotoğraf/sinema videosu gibi sunulmaz.
- `scripts/instagram_publish.py` yalnızca açık insan onayı ve manuel çağrıyla çalıştırılabilir. GitHub `instagram-production` environment kurulu olmadan devreye almayın.
- API anahtarları yalnız GitHub Secret ortamında saklanır; `OPENROUTER_API_KEY` yoksa hiçbir LLM çağrısı yapma.
- Ses ve SRT'nin eşleşmesi teknik kontrollerden geçse bile kelime bazlı otomatik hizalama yoktur.
