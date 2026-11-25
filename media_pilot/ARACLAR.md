# Profesyonel medya CPU pilotu

İki örnek de önceki GitHub Actions çıktılarından alınan onaylı Charon ve Sulafat kayıtlarını kullanır. MP4'ler 720×1280, 30 fps kısa inceleme örnekleridir. Karşılaştırma videosu aynı anı yan yana gösterir ve yeni ses miksini çalar. Tam boyutlu mevcut Reels üretim hattı, Remotion üç boyutlu sahneleri ve Blender araçları korunur.

`PILOT_REPORT.json` içindeki `tools` ve marka altındaki kalite dosyaları çalışma sürelerini verir. Motor süreleri iki yerel işçiyle aynı kaynak görsel, başlık, çözünürlük ve kare hızında ölçülür. Altyazı ve ses birleştirme ayrı işlemdir. GSAP ve Lottie maliyeti motor süresinin içindedir. Kısa kesit üzerindeki WER, telaffuzun insan tarafından onaylandığı anlamına gelmez ve bütün videonun WER değerini temsil etmez. Senkron ölçümü aynı yerel ASR zamanlarına göre hesaplanır. OpenCV'nin kare farkı ve Laplasyen değeri estetik bir kalite puanı değildir.

| Araç | Sürüm ve lisans | İş akışı |
|---|---|---|
| HyperFrames | 0.9.90 · Apache-2.0 | Yerel HTML sahnesinin CPU alternatifi. Remotion ile aynı sahne girdisi. |
| Faster Whisper | 1.2.1 · MIT; Small model snapshot 536b066 | CPU INT8 Türkçe ASR, kelime eşlemesi ve ses kontrolü. |
| Openverse | REST v1 · adayın özgün lisansı geçerli | Görsel Üretim ve Kaynak Kütüphanesi için CC0, PDM ve CC BY aday taraması. Özgün kaynak onayı gerekiyor. |
| Real SFX | Kaynak incelemesi edbefcb. Betiklerin açık lisansı doğrulanamadı. uisfx 0.4.0 havuzu CC0. | Marka başına kare zamanlı yerel cue listesi ve Real SFX ile gelen ayrı lisanslı uisfx varlık hattı. Üst depo betikleri çalıştırılmaz. |
| Earshot | 1.0.0 / 7a7f7c5 · MIT | Her marka için ayrı CPU foley kütüphanesi. Yerel oluşturulan WAV. Dinleme modeli, MCP ve dış LLM özellikleri kapalı. |
| yt-dlp | 2026.11.23 · Unlicense | Açık izinli, yerel test klibinin SHA-256 doğrulanan indirme testi. Haricî URL, çerez, eklenti ve kullanıcı yapılandırması kullanıma açılmadı. |
| GSAP | 3.14.2 · Standard no-charge licence | HTML başlık girişi, kamera hareketi ve ilerleme çizgisi. Paket yerel yüklenir. |
| Lottie | lottie-web 5.13.0 · MIT | Güzellikte neme ait özgün vektör animasyon. |
| OpenCV | opencv-python-headless 4.13.0.92 · Apache-2.0 | Örnek kareyi açar ve motorlar arasında görüntü farkını ölçer. |
| PySceneDetect | 0.6.7.1 · BSD-3-Clause | Önce ve sonra kesme noktalarını sayar. Tek sahneli kısa motor testinde sıfır kesme normaldir. |
| FFmpeg Loudnorm | Ubuntu 24.04 dağıtım derlemesi, sürüm raporda · lisans derlemeye bağlı | Ardışık iki geçişte EBU R128, hedef −16 LUFS ve −1.5 dBTP. |
| Wikimedia Commons | MediaWiki Action API · dosya başına lisans | Atıflı arama sonuçları. Piri Reis arşiv fotoğrafı CC BY-SA 4.0 ve yeniden çerçevelenen medya aynı lisansla tanımlı. |
| Freesound | Ücretsiz API yalnız ticari olmayan kullanım için | Ticari pilotta kapalı. Ağ çağrısı, ücret ve performans ölçümü yok. |

Pilotun hizmet/API ücreti 0 USD. GitHub Actions standart Linux CPU kullanır. Opsiyonel paketler ayrı iş akışındadır. npm sürümleri bütünlük özetleriyle kilitlenir ve kurulumda yaşam döngüsü betikleri kapalıdır. Haricî ajan becerileri kurulmaz. Model dosyaları SHA-256 ile doğrulanır. Medya işinde servis anahtarları tanımlanmaz; render ve efekt alt süreçleri ortam değişkenleri izin listesiyle çalışır. HyperFrames telemetrisi kapalıdır. Açık lisans gerektiren görseller ve sesler dosya başına kaydedilir, insan incelemesi zorunludur.

Resmî koşullar ve kaynaklar

- [HyperFrames](https://github.com/heygen-com/hyperframes) · [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) · [Openverse](https://api.openverse.org/v1/)
- [Real SFX](https://github.com/Clipwing/skills/tree/edbefcbc3474869e6cc1e8a7ca583b0efd0dab7e/skills/real-sfx) · [Earshot](https://github.com/Leonxlnx/earshot/tree/7a7f7c5c70d4a763a1eca4b3666af7c77e313f97) · [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [GSAP lisansı](https://gsap.com/standard-license/) · [Lottie](https://github.com/airbnb/lottie-web) · [OpenCV](https://opencv.org/license/) · [PySceneDetect](https://www.scenedetect.com/)
- [FFmpeg Loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm) · [Wikimedia yeniden kullanım](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia) · [Freesound API koşulları](https://freesound.org/docs/api/terms_of_use.html)

Uzman önerisinde araç seçimini açmak için yetkili editoryal çalıştırmada `ENABLE_MEDIA_TOOL_REVIEW=1` ayarlanır. Model yalnız ilgili rolün araç listesinden seçim yapabilir. Bu seçenek render, indirme veya paylaşım yetkisi vermez. CPU pilotu kendi araç planlarını marka dosyasına yazar ve o planı yerelde yürütür. Yerel HTML animasyonunun bağımlılıklarını kilitli npm paketlerinden yeniden hazırlamak için `node media_pilot/design.mjs /mutlak/klasor history` ya da `beauty` kullanılır.
