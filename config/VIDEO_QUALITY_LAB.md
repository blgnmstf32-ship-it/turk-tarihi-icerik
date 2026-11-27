# Viral analiz ve video kalite laboratuvarı

İki markada aynı kalite raporu sözleşmesi kullanılır. Teknik bölüm mevcut çıktıda gerçekten ölçülmüş sayısal sonuçları, editoryal bölüm mevcut 5 açılış / 3 senaryo puanlamasını ve kaynak incelemesini, Instagram bölümü ise yerel gerçek Meta Insights arşivindeki 48–96 saatlik gözlemleri gösterir. Editoryal eşik **85/100**. Bu puan bir viral olma olasılığı veya Instagram performans ölçümü değildir. Insight oranı için aynı marka, metrik başına en az beş farklı Reels ve geçerli payda gerekir. Yayına hazırlık için insan onayı gerekir.

## Araç incelemesi

Tabloda adı geçen projeler incelendi. Lisanslar depo kodu içindir. Model ağırlıkları, veri setleri, videolar ve dış hizmet izinleri ayrıca değerlendirilir. Bu etapta yeni paket, model, MCP sunucusu, ajan betiği veya dış ağ bağlantısı eklenmedi. Süre ve donanım karşılaştırmaları belgelerdeki gereksinimlere dayanır. Araçların tüketim veya hız ölçümü bu aşamanın kapsamı dışındadır.

| Araç | Değerlendirme ve karar | Kod lisansı / kaynak |
| --- | --- | --- |
| QC Video | Python/FFmpeg toplu taraması. Kare aralığıyla kusur kaydı yararlı. Siyah/donmuş kareler doğrudan mevcut FFmpeg filtreleriyle ele alındı. | [MIT](https://github.com/ddfzhh/qc-video/blob/main/LICENSE) |
| VidLint | Node.js ve FFmpeg. Siyah kare, donma ve sessizlik mevcut yerel bileşenlerle büyük ölçüde örtüşüyor. Işığa duyarlılık uyarıları ayrı bir yöntem ve test seti gerektiriyor. | [MIT](https://github.com/ai2922/vidlint) |
| Video Evaluator | 45ck uygulaması. Medya kabulü ve kanıta dayalı storyboard incelemesi mevcut Scene Director ile örtüşüyor. Dış medya alma ve ajan araçları kurulmadı. | [MIT](https://github.com/45ck/video-evaluator/blob/main/LICENSE) |
| VBench | Üretilmiş video karşılaştırma paketi. Yüksek hesap yükü olan model temelli görevler ve ek ağırlıklar içeriyor. Yerel kalite eşiklerinin yerine kullanılmayacak. | [Apache-2.0](https://github.com/Vchitect/VBench/blob/master/LICENSE) |
| ImageHash | CPU üzerinde algısal hash. 64 bit fark hash'i ve Hamming uzaklığı sözleşmeye alındı. Mevcut OpenCV ile ölçülen değerler yeterli. | [BSD-2-Clause](https://github.com/JohannesBuchner/imagehash) |
| PaddleOCR | Gerçek videoya gömülü bilinmeyen yazı için CPU/GPU OCR adayı. Model indirmesi ve ayrı kullanım şartları incelenmeli. Bilinen şablonda mobil yerleşimi Playwright ölçer. | [Apache-2.0](https://github.com/PaddlePaddle/PaddleOCR) |
| WhisperX | Ayrı zorunlu hizalama modeliyle kelime zamanları sunar. Yerel CPU desteği var. Türkçe hizalama modeli ve ağırlık lisansı ayrı doğrulanmalı. Mevcut Faster Whisper ve SRT karşılaştırması korundu. | [BSD-2-Clause](https://github.com/m-bain/whisperX) |
| Netflix VMAF | Sıkıştırma karşılaştırması için hizalı referans ve `libvmaf` gerekir. Mevcut isteğe bağlı FFmpeg entegrasyonu korunur. Uygun ölçüm kaydı bulunmadığında puan üretilmez. | [VMAF lisansı ve patent izni](https://github.com/Netflix/vmaf/blob/master/LICENSE) |
| Watch Video Skill | Romarayt uygulaması. Sahneye göre kare ve altyazı örnekleme yararlı. Mevcut CineCode bilgisi, FFmpeg ve Faster Whisper bu görevi kapsıyor. İndirme ve dış ajan akışı eklenmedi. | [MIT](https://github.com/romarayt/codex-watch-video-skill) |
| Marketing Skills | İçerik ve analitik ayrımı ile ölçüm bağlamı mevcut Instagram bilgi kayıtlarında ve `reels_benchmarks` içinde var. Yeni izleme betiği, reklam aracı ya da takipçi tahmini eklenmedi. | [MIT](https://github.com/coreyhaines31/marketingskills/blob/main/LICENSE) |

[Siyah kare, donmuş kare ve ses filtrelerinin FFmpeg belgeleri](https://ffmpeg.org/ffmpeg-filters.html)

## Kullanım ve kanıt

```bash
python -m scripts.video_quality_lab --plan output/SCENE_PLAN.json --out output
```

- `--evidence` operatörün mevcut yerel ölçüm raporlarından hazırladığı JSON'u alır. Belge alanları `plan_sha256`, isteğe bağlı `asset_sha256`, `observations` ve `source_reviews`. Plan özeti Scene Director raporundaki özettir. Ölçüm satırında `collector`, `values` ve isteğe bağlı `frames: [başlangıç, bitiş)` bulunur. Geçiş satırında zaman aralığına ek olarak `transition_id` belirtilebilir. Tüm Reels'i ölçmeden aralığı atlamayın. Farklı varlıkların ölçümlerini aynı kayıtta birleştirmeyin.
- `--existing-mp4` yalnız mevcut yerel MP4'te FFmpeg siyah/donmuş kare filtresini çalıştırır. Boyut, ortalama FPS ve toplam kare Scene Plan ile eşleşmelidir. Dosya üretilmez. Filtre adayları editörün kararma veya bilinçli durağan plan kararını gerektirir. Operatör teyitli kusuru ölçüm JSON'una ilgili aralıkla kaydeder. Bu yol bu etapta yalnız verisiz komut sözleşmesiyle test edildi.
- `--topic` aynı metni ve kaynakları taşıyan konu JSON'uyla mevcut editoryal değerlendirmeyi çalıştırır. `source_reviews` her sahne için `scene_id`, `status` (`verified` / `unverified`), `source_numbers` ve pasajı açıklayan `finding` alanlarını alır. Kaynak URL'sinin plan içinde bulunması kendi başına doğrulama sayılmaz.
- `--performance` yerel Insights JSONL dosyasını okur. Meta'ya istek göndermez. Eksik gözlem için `insufficient_real_data` döner.
- `--state` ve `--previous-report` aynı planın önceki Scene Director kaydını kullanır. Aralığı bilinen kusurlar ve onlara bitişik geçişler yeniden değerlendirilir. Yeri belirsiz genel kusurlar inceleme listesine düşer. Önceki rapor yoksa sahne kimlikleri öneri olarak kalır. Laboratuvar gerçek render işlemi başlatmaz.

| Kontrol | Operatörün beslediği ölçüm / politika |
| --- | --- |
| İlk üç saniye | FFmpeg + Faster Whisper, ilk kullanılabilir görüntü en geç kare 15, ilk kelime kare 90'dan önce. Açılışın vaadi ayrıca editoryal puanda. |
| Anlatım temposu | Yerel Faster Whisper 95–180 kelime/dk. Sahne örneği yalnız kendi aralığını kapsar. |
| Görsel tekrar | OpenCV ile seçilmiş karelerde 64 bit dHash, asgari Hamming uzaklığı 6. Bilinçli tekrarlar insan incelemesi gerektirir. |
| Altyazı senkronu | Faster Whisper ve SRT, eşleştirme en az %90 ve başlangıç sapmasının 95. yüzdeliği en çok 350 ms. |
| Mobil okunabilirlik | Playwright DOM, güvenli bölgede sıfır taşma ve en az 4,5:1 metin kontrastı. DOM kanıtı video içindeki yazının OCR testi değildir. |
| Siyah/donmuş kare | FFmpeg aday ölçümü, siyah kare aralığı en az 0,25 sn, donma en az 1 sn. Onaylanmış beklenmedik kare sayısı sıfır olmalı. |
| Ses dengesi | FFmpeg Loudnorm ve ayrı ses kanalları, −19 ila −13 LUFS, en fazla −1 dBTP ve anlatım sırasında müzikten en az 8 dB önde. Tek başına final miksinin LUFS değeri ayrımı kanıtlamaz. |
| Sahne geçişleri | PySceneDetect ve editör kaydı, beklenmeyen kesme yok, eşleştirilen sınırda en çok 6 kare fark. Bilinçli yumuşak geçişler gerekçelendirilir. |
| Kaynak doğruluğu | Sahne iddiasıyla eşleşen okunmuş pasaj ve insan kararı. Sağlık iddiaları ve tarihsel yorumlar ayrı doğrulanır. |

`VIDEO_QUALITY_LAB.json` içinde `pass`, `fail`, `partial`, `needs_review` ve `not_measured` teknik durumları vardır. Eksik kanıt olumlu sonuç sayılmaz. Dış ölçüm satırları güvenilen yerel operatör girdisidir. Faster Whisper, OpenCV, Playwright, ses kanalı ve PySceneDetect kanıtlarını bu sürüm kendiliğinden toplamaz. Tarih ve güzellik üretim girişleri değişmedi. Bu laboratuvar iki hat için isteğe bağlı kalite adımıdır.
