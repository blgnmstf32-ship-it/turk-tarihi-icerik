# Çalışmayı devralma

Bu teslim, iki markanın doğrulanmış medya tabanını ve yeniden kullanım koşullarını kaydeder. [PROJECT_STATE.md](PROJECT_STATE.md) test sayıları, ölçümler ve açık işleri içerir.

## Başlangıç noktası

1. GitHub'daki güncel `main` dalını ve son commit'i kontrol et. `26c3b20`, medya kanıtının commit'idir. Daha yeni belge veya birleşim commit'i varsa güncel `main` üzerinden devam et.
2. Bu oturumdaki medya kanıtı [Actions 45828936221](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221). Başarılı kontrolü belgelerden dolayı yeniden başlatma. Normal Push/PR kalite akışı medya dışı Python testlerini, JS ve tip kontrolünü kapsar. Tam medya iş akışı `media-final-qa` dalında kendi YAML dosyası değiştiğinde veya manuel tetiklendiğinde çalışır. [Kalite akışı](.github/workflows/tests.yml) · [Medya akışı](.github/workflows/media_final_qa.yml)
3. `config/settings.json` içinde otomatik paylaşım kapalı ve insan onayı zorunludur. Kullanıcı yeni aşamayı açana kadar ücretli servis, yeni medya, yeni araç kurulumu ve günlük seri üretim bekler.

## Girdi ve çıktı yerleri

| Girdi veya kanıt | Konum |
| --- | --- |
| Piri Reis Charon WAV ve onay kaydı | `data/GEMINI_CHARON.wav` ve depo içindeki onay kaydı |
| Piri Reis 10 Wikimedia arşiv görseli, altyazı, atıflar ve önceki MP4 | [Actions 45649575775](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45649575775), `tarihin-bilinmeyen-gercekleri-4` |
| Güzellik önceki MP4 ve zamanlı altyazı | [Actions 45702177750](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45702177750), `beauty-reel-kuru-cilt-2` |
| Sulafat kaydı, Nano Banana görseli ve makbuzları | [Actions 45654042857](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45654042857), `beauty-sulafat-and-nano-assets` |
| Son ölçümler, her marka için final ve önce–sonra | [Tarih paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121762543) · [Güzellik paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121002356) |

Arşiv süresi dolduysa önce onaylı yedeği ve SHA-256 kayıtlarını bul. Eksik kaynağı raporla. Yeni ücretli görsel veya ses isteğiyle kendiliğinden ikame etme. Varlıklarla birlikte lisans, atıf ve kullanım hakkı kayıtlarını koru. Render işine sağlayıcı anahtarı verme.

## Kod haritası

- `scripts.final_media_qa` onaylı girdileri denetler, pilotları hazırlar ve karşılaştırma ölçümlerini yazar. `FINAL_QA.json` kalite sonuçları ve çıktı özetini, `PERFORMANCE.json` aşama bazında duvar saati, CPU süresi ve tepe süreç ağacı RSS değerlerini tutar.
- `scripts.auto_produce` tarih hattı, `scripts.beauty_reel` güzellik montajıdır. Tarih hattında `scripts.create_reel` Remotion görüntü ara çıktısını üretir. Anlatım ve müzik nihai FFmpeg miksine eklenir.
- `config/agents.json`, `config/beauty_agents.json`, `config/reels_playbook.json` ve `config/MULTI_LLM.md` uzmanları, editoryal eşikleri ve ortak ücretsiz sağlayıcı yönetimini açıklar.
- `media_pilot/ARACLAR.md`, `config/MOTION_TOOLKIT.md` ve `config/EDITORIAL_ANIMATION.md` lisans kayıtları, yerel araçlar, seçime bağlı modüller ve geri dönüş davranışını açıklar.

## Sonraki oturumda

1. Yeni render başlatmadan önce mevcut tam pilotları insan gözü ve kulağıyla incele. Piri Reis'te atıfları, temsili sahne etiketlerini ve altyazıyı kontrol et. Bakım videosunda cilt kesitinin temsili ölçeğini, iddiaların kaynak sınırlarını ve ses dengesini kontrol et.
2. Onaylı girdileri ve kaynak kayıtlarını koru. Sonraki kapasite deneyi ayrıca yetkilendirildiğinde 5 Reels ve 20 hikâyenin birlikte tamamlanma süresini, başarısızlıkları ve marka başına kaynak tüketimini ölç. Tek hikâye deneyiyle tam paket geçti sonucu verme.
3. Mevcut CPU derlemesinde libvmaf yoksa VMAF sonucunu boş bırak. Referans hizası doğrulanırsa gerçek ölçümü kaydet. Onay gelene kadar günlük otomasyonu ve Instagram paylaşımını devreye alma.
