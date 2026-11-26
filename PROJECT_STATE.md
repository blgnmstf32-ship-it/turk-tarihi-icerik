# Proje durumu

26 Kasım 2026. Türkçe tarih ve güzellik Reels taslakları için son doğrulanmış medya tabanı `26c3b2055ab856f5018bc9b850118c1d929b95d0`. Devralırken güncel `main` dalını esas al. Bu commit, aşağıdaki medya kanıtlarının üretildiği sürümdür.

## Korunan altyapı

| Alan | Durum |
| --- | --- |
| Uzmanlar | Tarih ve güzellik için 20'şer ana rol. Tarih yapılandırmasında ayrıca dört yardımcı 3D görev modülü bulunur. Genel Yayın Yönetmeni konuya göre uzman seçer. |
| Multi-LLM | Gemini → Cloudflare Workers AI → OpenRouter Free. Ortak önbellek, kota, sınırlı tekrar ve başarısız görev kuyruğu korunur. Cloudflare yazılım sınırı 9.000 nöron/gün, OpenRouter sınırı 40 deneme/gün. NVIDIA NIM ve Groq kapalı. [Yönlendirme ayrıntıları](config/MULTI_LLM.md) |
| Editoryal öğrenme | Her pilotta render öncesinde 5 açılış ve 3 senaryo değerlendirildi. Eşik 85/100. Piri Reis 86, güzellik 100 aldı. Bu puan editoryal indekstir. Kaynak, lisans ve insan onayı ayrı kapılardır. [Araştırma](config/REELS_ARASTIRMASI.md) · [Kurallar](config/reels_playbook.json) |
| Ses ve görsel | Tarihte onaylı Charon, güzellikte onaylı Sulafat. Güzellikte mevcut Nano Banana görseli, tarihte 10 arşiv görseli ve atıfları kullanıldı. Piper kullanılmaz. |
| Render ve denetim | Remotion, HyperFrames, Three.js, GSAP, Blender, FFmpeg, Faster Whisper Small CPU INT8, Earshot, CC0 uisfx, OpenCV ve PySceneDetect iki pilotta ilgili işlerde doğrulandı. Real SFX tasarımından yararlanıldı. Üst depo betikleri çalıştırılmadı. [Araçlar ve lisanslar](media_pilot/ARACLAR.md) · [İsteğe bağlı araçlar](config/MOTION_TOOLKIT.md) · [Animasyon](config/EDITORIAL_ANIMATION.md) |
| Yayın ve maliyet | Otomatik Instagram paylaşımı kapalı, insan onayı zorunlu, ücretli servisler kapalı. İki markalı günlük seri üretim yetkilendirilmedi. Mevcut haftalık tarih taslak takvimi ayrı bir akıştır. |

## Kayıtlı medya doğrulaması

[Actions 45828936221](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221) üç başarılı iş içerir. 128 medyasız Python testi ve 15 medya testi toplam **143/143** geçti. JavaScript **2/2**, Remotion tip kontrolü başarılı. Render iki Linux CPU işinde, 4 mantıksal çekirdek ve yaklaşık 16 GiB RAM ile yapıldı. Render adımı yalnız yerel döngü arayüzüne erişebildi. İki rapor 0 ücretli çağrı ve otomatik yayın kapalı sonucunu verir. Her final MP4'ün SHA-256 özeti arşivdeki `FINAL_QA.json` ile eşleşti. İki final de 1080×1920, 30 fps, H.264/AAC ve `human_review_required` durumundadır.

| Ölçüm | Tarih · Piri Reis | Güzellik · Nemlendirici için doğru an |
| --- | ---: | ---: |
| Süre | 67,60 sn | 71,80 sn |
| Ana render duvar saati / CPU süresi / tepe süreç ağacı RSS | 285,00 sn / 288,79 CPU-sn / 4.090 MiB | 133,75 sn / 339,47 CPU-sn / 1.805 MiB |
| Özel sahneler | HyperFrames kolajı 17,46 sn, kesintisiz Three.js/GSAP Atlas kamerası, 2 yerel 2.5D kâğıt katmanı | Blender cilt kesiti 36,28 sn ve 96 kare, İki Three.js/GSAP makro sahnesi 14,41 ve 14,80 sn |
| Türkçe ASR kelime hata oranı, önce → sonra | %7,75 → %7,04 | %4,17 → %4,17 |
| Ortalama altyazı başlangıç farkı, önce → sonra | 96,0 → 66,4 ms, 25/25 eşleşme | 16,2 → 17,9 ms, 47/47 eşleşme |
| Gerçek ses tepesi, önce → sonra | −1,23 → −4,19 dBTP | −0,81 → −1,27 dBTP |
| PySceneDetect belirgin kesmeler, önce → sonra | 2 → 4 | 5 → 5 |
| OpenCV örnek kare keskinlik göstergesi | 2.473,882, aynı | 1.440,492, aynı |
| VMAF | Ölçülmedi, libvmaf yok | Ölçülmedi, libvmaf yok |

Ortalama altyazı farkı ASR zamanlarıyla karşılaştırıldı. OpenCV göstergesi estetik puan değildir. PySceneDetect yalnız sabit eşikte bulduğu kesmeleri sayar. Her marka için özgün çizimli 5 saniyelik Remotion animasyonu ayrı çıktı olarak oluştu. Piri Reis 2.5D katmanları elle tasarlandı. Depth Anything V2 çıkarımı ve dış GeoJSON harita katmanı bu çalıştırmada kullanılmadı.

- [Tarih Actions paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121762543) · [Güzellik Actions paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121002356)
- İki pakette `FINAL_QA.json`, `PERFORMANCE.json`, tam MP4 ve `ONCE_SONRA.mp4` bulunur. Tarih paketinde arşiv atfı ve ayrı HyperFrames klibi de vardır. Actions saklama süresi 14 gündür.

## Açık işler

- İki pilotun insan editör tarafından görüntü, telaffuz, ses dengesi, tarihsel doğruluk ve güzellik iddiaları açısından son onayı.
- Günlük 3 tarih ve 2 güzellik Reels ile 20 hikâyenin birlikte gerçek yük deneyi. Ölçülen montaj, foley ve miks süreleriyle, aynı girdi tipleri için tek koşucuda yaklaşık 21 dakika hesaplanır. Bu tahmin araştırma, kaynak indirme, yeni anlatım, tekrarlar ve incelemeyi kapsamaz. Hikâye ölçümü marka başına tek yerel tasarım örneğidir.
- VMAF ancak libvmaf destekli bir makine ve hizalı referans bulunduğunda ölçülebilir. Freesound ticari işte kapalıdır. İsteğe bağlı araçların durumu ve lisansları [katalogda](config/MOTION_TOOLKIT.md) kayıtlıdır.
- Actions giriş paketlerinin süresi dolmadan onaylı dosyalar, özetleri ve kaynak/izin kayıtları kalıcı erişimde tutulmalı. Uygulama adımları [HANDOFF.md](HANDOFF.md) içindedir.
