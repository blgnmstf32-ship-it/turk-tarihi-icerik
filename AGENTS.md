# Codex proje talimatları: Türk Tarihi

Bu proje tarihî, eğitici ve kaynaklı Türkçe Instagram taslakları üretir. `config/agents.json` içindeki ilk **20 uzman rolünü aynen koru**; sonlarına 4 Three.js görev modülü eklenmiştir. Bunlar tek ücretsiz yürütmede çalışan iş modülleridir; bağımsız LLM ajanı olduklarını iddia etme. 3D LLM çağrısı varsayılan olarak kapalıdır.

## Sırasıyla uygula
1. Önce resmî veya akademik kaynakları bul; kaynağı açmadan yeni bir iddiayı doğrulanmış olarak işaretleme.
2. `data/topics.json` içine konuyu, üç somut olguyu, kronolojiyi, dönemi ve kaynak URL'lerini ekle.
3. Büyük iddialar, tartışmalı tarihler, tartışmalı etnik tanımlar, tarihî alıntılar ve nedensellik için ek kaynak iste/araştır.
4. Sahte alıntı, uydurma savaş diyalogu, çarpıtılmış tarihî fotoğraf, telif ihlali ve sahte kronoloji üretme.
5. `python -m scripts.run --topic KONU-ID --out output/...` ile taslak üret.
6. `python -m unittest discover -s tests -v` çalıştır.
7. Üretim için **0 ücretli API hedefi** koru; ücretli API çağrılarını kullanıcı onayı olmadan etkinleştirme.
8. Instagram'da yayın yapma; insan onayı, Meta uygulaması, token ve doğrulanmış kamuya açık medya URL'si olmadan yayın kapısını açma.
9. Savaş konularında `scripts/three_scene.py` ile kuşbakışı Three.js savaş haritası; şehir/fetih konularında şehir uçuşu veya kuşatma sahnesi planla. Ana Remotion + FFmpeg montajı aynı kalır.
10. 3D sahneleri kısa tut (sahne başı yaklaşık 7–9 saniye, video başına en çok 3). Temsili canlandırma olarak etiketle; taktik ayrıntıyı kaynak olmadan kesin tarihî gerçek gibi gösterme.
11. 3D WebGL renderı hata verirse aynı Remotion kurgusunu 3D kapalı yeniden üret ve `three_d` raporunda `fallback_2d_after_3d_failure` olarak kaydet.
12. Ücretsiz prosedürel Three.js/React Three Fiber kullan. Blender isteğe bağlıdır; zorunlu bağımlılık yapma. Ücretli 3D üretim servislerini açma.

## Üslup
Doğru, tarafsız, merak uyandırıcı, özlü. Kökenleri, dönemleri, devletleri ve bireyleri birbirine karıştırma. Tarihî yeniden canlandırmaları açıkça etiketle. Her gönderide kaynakları sakla ve uygun yerde paylaş.

## Maliyet
Çoklu uzman görevini mümkün olduğunca aynı yürütmede işle. Ödeme gerektiren modeller ve paralel subagent'lar yalnızca ölçülmüş iyileştirme ve önceden belirlenmiş bütçeyle açılsın.

## MUTLAK VİDEO KALİTE KAPISI (öncelikli)

- Sessiz yazı slaytlarını bitmiş Reels olarak sunma. Önizlemeyi asla `reel.mp4` veya `ready` olarak etiketleme.
- Varsayılan taslak 60–75 saniye, 9:16, 1080×1920 ve 30 fps olmalı; Remotion sahne/altyazı hareketini, FFmpeg konuşma ve ses miksajını üretmeli.
- En az 10 ayrı sahne ve her cümleyle ilgisi bulunan görsel gerekir. Mümkünse doğrulanmış açık lisanslı tarihî fotoğraf, eser, alan, harita veya arşiv görseli kullan; canlandırmaları gerçek arşiv görüntüsü gibi gösterme.
- Altyazı konuşmaya zamanlanmalı ve kelime/ifade vurgusuyla hareket etmelidir. Anlatı Türkçe, coşkulu ama ölçülü belgesel tonunda olmalıdır.
- Piper sentetiktir; insan anlatıcısı doğallığı sağladığını iddia etme. Üretilen ses düz veya robotik duyulursa teknik test geçse bile taslak yayın kalitesini geçmez.
- Gerçek kaynak doğrulaması yapılmadan savaş sayıları, komutan alıntıları ve kesin taktik iddiaları ekleme.
- Ücretli video/ses modeli gerekiyorsa kullanıcı izni olmadan çağrı yapma.
- `python -m scripts.release_check ...` teknik kontrolleri ve ardından insan görsel/ses kalitesi onayını gerektir.

## Varsayılan belgesel video biçimi
- Varsayılan 1080×1920, 30 fps; 60–75 saniye ve 10–12 ayrı sahnedir.
- Ücretli ses sağlayıcıları seçilebilir adaptörlerdir; varsayılan Piper, bulut ve faturalandırma kapalıdır. Kredi bittiğinde ücretli yedek sağlayıcıya geçiş yasaktır.
- Google Chirp 3 HD/Azure için ayrıca `paid_services_enabled`, `cloud_voice_enabled`, ilgili sağlayıcı `enabled` değeri ve geçerli kimlik bilgisi gerekir. Üretim iş akışları bu ayarları otomatik açmaz.
- Wikimedia Commons görsellerinde lisans adı, kaynak sayfası ve atıf korunur; 10 uygun fotoğraf bulunmazsa yerel temsili görseller kullanılır ve gerçek tarihî fotoğraf diye sunulmaz.
- faster-whisper ve PySceneDetect isteğe bağlı, yerel QA kontrolleridir; varsayılan olarak kapalıdır ve model dosyalarını ağdan indirmez.
- Yerel Task Observer JSONL dosyalarına gizli bilgileri ayıklayarak hata/geri bildirim yazar. Instagram Insights gelecekteki salt-okunur iskelettir; yayınlama uç noktası yoktur.

## v0.7 belgesel video biçimi
- Varsayılan üretim: `python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto`.
- İlk 20 görev modülü korunur; 3D Sahne Planlayıcı, 3D Animasyon Ajanı, 3D Render Ajanı ve 3D Kalite Kontrol Ajanı görevleri sona eklenmiştir. Toplam 24 iş modülü aynı ücretsiz üretim hattında çalışır; dört 3D görevi ek LLM çağrısı başlatmaz.
- `visual_mode: battle_map` savaş başlığında; `visual_mode: siege_city` fetih/şehir başlığında 1–2 kısa prosedürel Three.js sahnesini etkinleştirir. Belirtilmemiş konular için yerel anahtar kelime sınıflandırması vardır.
- Three.js sahneleri `@remotion/three` ile ana Remotion zaman çizelgesine eklenir; Chromium WebGL renderı `--gl=angle` kullanır. Blender bulunmadan da üretim çalışmalıdır.
- 3D render başarısızlığında ana 2D Remotion/FFmpeg akışı yeniden denenir; plan `3D_SCENE_PLAN.json`, sonuç `AUTO_REPORT.json` içine yazılır. Üretilen sahneler temsili canlandırmadır ve insan incelemesi ister.
- Kurgu Remotion ile 30 fps dikey kompozisyon, yavaş sinematik kamera hareketi, sahne geçişleri ve kelime/ifade vurgulu hareketli altyazı üretir; FFmpeg anlatım, müzik ve son H.264/AAC MP4 karışımını yapar.
- En az 10 ayrı görsel sahne kullan. Öncelik, Wikimedia Commons üzerinden lisans/atıf verisi doğrulanmış kamu malı veya ticari kullanıma açık tarihî eser, arkeolojik alan, nesne, harita ve arşiv görüntüleridir. Dosya başına yazar, lisans ve kaynak sayfası `MEDIA_ATTRIBUTION.md` içine yazılır. Gerçek fotoğraf olmayan canlandırmaları görsel üzerinde **TEMSİLÎ CANLANDIRMA** olarak belirt; görseli arşiv fotoğrafı diye sunma.
- Konuşma yönü: doğal Türkçe belgesel anlatıcısı; merak uyandıran sakin giriş, olgular net ve ölçülü, dönüm noktalarında canlı vurgu, kısa anlamlı duraklar. Bağırma, düz okuma ve habersiz ses efekti yapma.
- Gerçek insan kaydı varsa onu tercih et. Ücretsiz çevrimdışı Piper yalnızca yedek TTS'dir; sentetik sesi doğal insan sesi diye tanımlama. Kullanıcı örneği `180010.mp4` ses kanalı içermediğinden bu örneğin ses tonuna dair talimat çıkarma; yalnız görsel kurgu yaklaşımını referans al.
- Gerçek ses kaydı/Piper süresi 60–75 saniye değilse metni yeniden yaz; konuşmayı hızlandırıp/yavaşlatıp süreye zorla sığdırma.
- `scripts/instagram_publish.py` yalnızca açık insan onayı ve manuel çağrıyla çalıştırılabilir. GitHub `instagram-production` environment kurulu olmadan devreye almayın.
- Ücretli API ve ücretli görsel/ses servislerini kullanıcı izni olmadan etkinleştirme. Wikimedia Commons sorguları ücretsiz ve anahtarsız medya aramasıdır; dış LLM anahtarı yoksa hiçbir LLM çağrısı yapma.
- İnsan onayı, kaynak/lisans kontrolü ve ses/görüntü dinlemesi tamamlanmadan taslağı yayına hazır sayma. Instagram otomatik yayınını açma.

## İçerik stratejisi, araştırma ve öğrenme
- `scripts.editorial_board` AI Genel Yayın Yönetmeni koordinasyon katmanıdır. Her üretimde haftalık karar raporu oluşturur; `EDITORIAL_DECISION_REPORT.md/.json` dosyalarını teslim eder.
- `scripts.editorial_research` anahtarsız Google Trends Türkiye RSS'ini ve `config/research_sources.json` içindeki kamuya açık YouTube kanal RSS başlıklarını okur. Rakip başlıkları konu kapsamını gösterir; izlenme sayısı veya rakip Insights verisi göstermez. Kaynak ve toplama zamanı rapora yazılır.
- `scripts.content_strategy` tarih, tarihî gizem, az bilinen olay ve keşif kategorilerini; trend eşleşmesi, rakip başlık kapsamı ve `data/performance.jsonl` ölçümlerini kullanarak göreli 0–100 endeksle sıralar. Bu değer başarı olasılığı değildir; örneklem yoksa başlangıç puanı ve açık belirsizlik yazılır.
- Fikir değerlendirmesi `Konu Avcısı`, `İçerik Stratejisti` ve `Tarih Doğruluk Denetçisi` perspektiflerini, her görüşün dayanak ve karşı savıyla raporlar. Kurallı perspektifleri bağımsız LLM sohbeti diye sunma.
- Haftalık öneriler sıralı fikir, gerekçe, karşı görüş, önerilen görsel/3D/ses/kurgu, tahmini üretim süresi ve ücretli API maliyeti tahminini içerir. 0 TL yalnız ücretli API maliyeti içindir; iş gücü ve donanım maliyeti buna dahil değildir.
- `scripts.performance_learning` gerçek Instagram Insights ölçülerini veya içe aktarılan ölçümleri normalize edip yeterli örneklem olduğunda kategori medyanlarıyla karşılaştırır; `data/performance.jsonl` içine yerel öğrenme kayıtları yazar. Küçük örneklemde sonuç `insufficient_baseline` olur.
- Insights adaptörü salt okunur `GET` çağrısı kullanır. Varsayılan kapalıdır; yalnız hesap sahibi ayarı, `INSTAGRAM_INSIGHTS_ENABLED=1`, uygun token/izin ve medya eşlemesini sağlarsa çağrı yapar. Yayınlama endpoint'i ekleme. Metriklerin bir bölümü hesap, bir bölümü Reels bazında olabilir; erişilemeyen alanı tahmin etme.
- Mevcut 20 rolün görevleri tek Python hattında otomasyon olarak çalışır; bunlar 20 ayrı LLM ajanı demek değildir. Gerçek LLM, yalnız `editorial_intelligence.free_llm_enabled=true`, `ENABLE_FREE_LLM=1`, anahtar ve `openrouter/free` rotasıyla yönetici önerisi için açılır. 20 rolün LLM önerileri ayrıca `ENABLE_20_LLM_AGENTS=1` ister. Ücretli model/fallback çağrısı yasaktır; koşullar eksikse sıfır LLM çağrısı yap.
- LLM önerilerini taslak karar desteği say; tarihî olgu, trend, kaynak veya başarı olasılığı uyduramaz. Her rolün gerçek çağrı durumunu `AI_AGENT_EXECUTION_REPORT.json` içinde açıkça kaydet.
- GitHub Actions üretim workflow'u strateji raporu, Remotion render, FFmpeg ses miksajı, Türkçe konuşma kontrolü ve çıktıları Actions artifact'e kaydetme adımlarını yürütür. Instagram yayın adımı ekleme.
