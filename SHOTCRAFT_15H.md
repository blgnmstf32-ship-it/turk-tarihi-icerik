# 15H · Video Shotcraft incelemesi

28 Kasım 2026. Proje tabanı `6dea7d5e5233e7bf3dcc1f678a2809e67e8b0a6e`. İncelenen Video Shotcraft aynası `457f3a144b3140bd89970e0fe4a6a692d0f9719d`. `NOTICE` özgün yazar Wei Yihao ve katkıda bulunanları belirtir. Kök `LICENSE` Apache-2.0'dır. Aynanın README dosyası 209 stil bildiriyor. Git envanterinde 10 kategoride 152 çekim kartı ve `demos` altında 202 TSX dosyası sayıldı. [Sabit upstream](https://github.com/digitalpublisher/video-shotcraft/tree/457f3a144b3140bd89970e0fe4a6a692d0f9719d) · [NOTICE](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/NOTICE) · [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Seçim ve mevcut kapsama göre fark

| Yeni kayıt | Uygulama ve fark |
| --- | --- |
| `tabletop-reframe` | Özgün kolajda sabit eğimle taramayı ve cepheye dönüşü ayrı hareket evrelerine koyar. Mevcut yanal derinlik açığa çıkarma ve ürün ayrıntısı bekletme notlarını korur. [Çekim kartı](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/references/shots/camera/overhead-camera-moves.md) |
| `readable-detail-triplet` | Aynı işlemin üç ayrıntısını benzer eksen ve ölçekte sıralayıp sonucu okunur bırakır. Süreklilik gerektiriyorsa vurgu tek sahnede kalır. Flash ve karartma efektleri kullanılmaz. [Ritim kartı](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/references/shots/rhythm/montage-rhythm-moves.md) |
| `svg-path-draw` | Özgün yön ve süreç şemasında kareye bağlı SVG çizgi açılımı, dolgu katmanı ve sabit etiketler kullanır. Mevcut aşamalı grafik ve tohumlu eskiz becerilerinin yanına yön göstergesine özgü reçete ekler. [Animasyon kartı](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/references/shots/ui-entrance/draw-svg-trace.md) |
| `cut-event-drift` | Gözlenen kesme, konuşma/ses olayı ve varsa ritim ızgarasının kare farklarını ayrı değerlendirir. Mevcut geçiş toleransına ve anlatım korumasına dokunmaz. [Ses ritmi rehberi](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/references/music-beat-sync.md) |

Kamera, veri ve efekt grupları mevcut derinlik, şema ve kaynak inceleme yöntemleriyle karşılaştırıldı. Açılış, kapanış, tipografi ve diğer geçişler mevcut giriş/altyazı/kanıt becerilerinin kapsamına büyük ölçüde giriyor. Etkileşim ve arayüz girişleri ürün demosu ağırlıklı. Ritim önerilerinde konuşma ve altyazı önce gelir. Mevcut `video-shotcraft:product-detail-hold` dahil 171 kayıt değerleriyle birebir korundu. Dört ek notla toplam 175 kayıt ve 40 ana uzman vardır.

## Lisans ve güvenlik incelemesi

Upstream `NOTICE`, `LICENSE`, varlık atfı, yönergeler, şablon bağımlılık kilidi ve otomasyon yüzeyleri statik incelendi. Şablon kilidinde `npm audit --package-lock-only --ignore-scripts` 9 yüksek ve 3 orta önem düzeyinde kayda işaret etti. Dağıtılan değişiklik projeye özgün Türkçe notlar, mevcut yerel yönlendirme ve ölçüm raporu kodu ekler. Shotcraft şablonu, TSX demosu, kurucu, tarayıcı yakalama, JianYing betikleri, ses/görsel dosyaları, CI veya bağımlılık aktarımı kapsam dışındadır. Başka marka filmlerinde kaynak gösterimi kullanım izni sağlamaz. Remotion lisansı ve üçüncü taraf ses lisansları ayrı uygulanır. [Upstream atıfları](https://github.com/digitalpublisher/video-shotcraft/blob/457f3a144b3140bd89970e0fe4a6a692d0f9719d/references/shots/ATTRIBUTION.md) · [Remotion lisansı](https://www.remotion.dev/docs/license) · [Mixkit lisansları](https://mixkit.co/license/)

## Kullanım ve kapsam

- Skill Router `shotcraft-review` görevinde roller ile sahne türüne göre en çok iki not seçer. Scene Director seçilen kimlikleri mevcut `scenes[].review_skills` alanına ekler. Video Kalite Laboratuvarı bu notları `editor_review.scenes` altında insan incelemesine taşır. Planın render motoru ve kare sınırları mevcut sözleşmeyle belirlenir. Eski planlar okunur.
- İsteğe bağlı `rhythm_review` kanıtı, `asset_sha256` ve bir `events` listesi taşır. Her kayıt tekil `transition_id`, `observed_cut_frame`, `audio_event_frame` ve kullanılmıyorsa `null` olan `grid_frame` içerir. Kareler planın 30 fps, sıfır tabanlı kare çizelgesindedir. Üç işaretli milisaniye farkı `editor_review.rhythm` alanında verilir. Negatif değer daha erken bir kareyi gösterir. Bu rapor, sağlanan yerel gözlemleri karşılaştırır. Otomatik onarım, teknik eşik ve yayın onayı kendi kurallarıyla çalışır.
- Graphify 0.9.121 aynı proje tabanında ağsız yapısal modda 127 kaynak dosya, 1.366 düğüm ve 4.481 kenar doğruladı. Sorgu sonucu Skill Router, Scene Director ve Kalite Laboratuvarı girişlerine götürdü. Hedefli Git Grep ile kaynak satırları ve eski Shotcraft notu doğrulandı. Yeni medya üretimi ve ücretli API çağrısı 0. Instagram otomatik paylaşımı kapalı.

## Doğrulama

Yerel Python paketi 243/243 geçti. Ayrı karşılaştırmada `6dea7d5` üzerindeki 171 Registry kaydı tüm alanlarıyla birebir eşleşti. 40 ana uzmanın kimliği korundu. Testler iki markada görev ve sahne eşleşmesini, küçük kare farklarının ayrı raporlanmasını, başka medya özetiyle gelen verinin reddini, eski planları ve mevcut yayın kapılarını kapsar.
