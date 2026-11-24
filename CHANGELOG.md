# Değişiklikler
## 0.9

- Türk ve dünya tarihi için Tarihin Bilinmeyen Gerçekleri konsepti, altı kategori ve on kaynaklı pilot fikir.
- Erişilebilen rakip sayaçları, akademik kaynak taraması, ücretsiz LLM ile sıralı rol görüşleri ve haftalık Reels taslak seçimi.
- Kaynaklı Antikitera anlatımı, 3D dişli şeması ve ilk üç saniye ölçümü.


## v0.8 — İçerik yönetimi ve performans öğrenmesi
- AI Genel Yayın Yönetmeni koordinasyon raporu: ücretsiz trend/rakip RSS araştırması, dört içerik kategorisi için gerekçeli öneriler, kanıta dayalı rol değerlendirmesi ve tahmini ücretsiz üretim planı.
- İçerik Stratejisti, 20 özgün rolü koruyarak karşılaştırmalı puanlama ve belirsizlik/karşı görüş açıklaması üretir.
- Salt okunur Instagram Insights için kapalı başlayan Reels/account ölçüm adaptörü; yerel kategori öğrenme kayıtları ve raporu.
- Her rolün LLM çağrısı ile deterministik otomasyon durumunu ayrı raporla; ücretsiz LLM için açık ayar ve ortam opt-in'i, ücretli yedek yok.
- GitHub Actions'a haftalık editoryal rapor, tam video üretim/doğrulama ve artifact saklama adımları eklendi.

## v0.5 — 23 Kasım 2026

- Malazgirt anlatımı daha kısa, konuşma diline yakın cümlelere ayrıldı; tarih ve adlar seslendirme için yazıyla açıldı.
- Piper seslendirmesi ayrı cümle parçalarında, küçük tempo farkları ve planlı duraklarla üretildi. Sentetik ses olduğu açıkça belirtilir.
- Altyazı zamanları tahminî kelime sayımından değil, gerçek ses cümlesi sürelerinden alınır.
- Beş sade sahne yerine 10 farklı özgün çizim; daha çeşitli kompozisyon ve hareketli kamera kullanılır.
- Ücretli servisler kapalı, Instagram otomatik paylaşımı kapalı ve insan onayı zorunlu kalır.
# v0.6 — Cinematic documentary format

- Changed defaults to 60–75 second, 30 fps vertical documentary Reels.
- Added Remotion scene compositing, soft transitions, slow camera motion, animated phrase captions and active-word emphasis; FFmpeg remains responsible for the final voice/music mix and MP4 encoding.
- Added free Wikimedia Commons photo/artifact/site/map discovery with license metadata and attribution. The workflow reports a quality-gate miss and uses explicitly labeled reconstructions when ten licensed visuals cannot be found.
- Rewrote all 20 role descriptions and project instructions for the documentary workflow.
- Added natural, emphatic Turkish narrator direction while keeping Piper as an explicitly synthetic free fallback.
- Preserved paid-service-off, Instagram-auto-publish-off, human-approval-required settings.

# v0.7.0 — Free-first documentary pipeline hardening

- Updated default video output to 1080×1920, 30 fps, 60–75 seconds and 10–12 scenes while preserving all existing 20 editorial roles.
- Added fail-closed Google Chirp 3 HD/Azure Speech selection, disabled AI image adapter, optional local faster-whisper/PySceneDetect audits, local redacted task/feedback logging and read-only disabled Instagram Insights scaffolding.
- Removed the CI FFmpeg package installation stall; checks the runner's preinstalled FFmpeg and retains manual human publication gates.
- No cloud billing, paid provider, or Instagram auto-publishing is enabled.

