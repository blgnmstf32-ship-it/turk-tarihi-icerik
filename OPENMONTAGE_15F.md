# 15F · OpenMontage ve profesyonel sahne incelemesi

28 Kasım 2026. Başlangıç `f0bfd3904c0f63c5082b8bb065855f460d547ecf`. OpenMontage'ın uzak varsayılan dalı `2e003e65fa99a0f329478a2c1cdcf26bc481933a`. Önceki karşılaştırma da aynı revizyondaydı. Bu çalışma bölüm ve beceri envanterini mevcut 163 Registry kaydıyla karşılaştırıp eksik inceleme adımlarını bağladı. [Sabit kaynak ve beceri indeksi](https://github.com/OpenMontageInc/OpenMontage/blob/2e003e65fa99a0f329478a2c1cdcf26bc481933a/skills/INDEX.md)

## Kategori karşılaştırması

Git dosya sayımı 6 çekirdek, alt dizinler dahil 37 yaratıcı, 11 meta, 103 aşama yönergesi ve 92 doğrudan `SKILL.md` verdi. Üst depoda ayrıca 12 üretim YAML'ı, bir framework smoke tanımı ve alt dizin dahil 6 stil YAML'ı var. Tablodaki gruplar beceri indeksi, kurulu beceri adları ve ilgili sabit kaynak dosyalarına dayanır. Aynı tekniği farklı katmanlardan gelen adlarla tekrar saymadık.

| Upstream kategorileri | Mevcut Registry ve 15F kararı |
| --- | --- |
| Çekirdek ve kompozisyon, FFmpeg, Remotion, HyperFrames, altyazı, WhisperX, renk | Kodlama, ses, animasyon ve kalite adaptörleri mevcut. Dikey kadraj, dinamik altyazı ve ses/renk eşikleri korundu. |
| Sinematik, video düzenleme ve işleme, sahne tespiti, kısa form, klip | Kurgu sürekliliği ve örnek kare denetimi mevcut. Kanıta zamanında kesilen ayrıntı planı ve yanal hareketle derinlikte kanıtı açma eklendi. |
| 3B grafik ve dünya, animasyon ve karakter, Manim, Canvas/SVG, GSAP/Lottie, hareketli grafik, tipografi ve veri görselleştirme | Yerel render ve grafik paketleri mevcut. Hareketi okunur durumlara ayırma, aşamalı veri gösterimi, sabit ölçek ve etiket görünürlüğü eklendi. Yeni rig veya render altyapısı kurulmadı. |
| Görsel kullanım, ürün videosu, stil, ışık ve iyileştirme | Gerekçeli ışık, silüet ve malzeme kontrolü mevcut. Planlar arası pozlama/beyaz dengesi ve gerçeğe uygun cilt dokusu incelemesi eklendi. İyileştirme modelleri ve yeni stil paketi kurulmadı. |
| Hikâye, belgesel montajı, B-roll, stok ve arşiv | Öykü, kaynak ve hak kapıları mevcut. Klip alt aralığı, tarih/yer ve dosya bazlı hak ile bağlam görüntüsü/iddia kanıtı ayrımı eklendi. |
| Ses, müzik, efekt, konuşma, avatar, yüz, dublaj | Onaylı sesler, foley, konuşma önceliği ve senkron mevcut. Efekti görünür olaya bağlama ve arşiv sesini sonradan eklenen sesten ayırma eklendi. Yeni ses veya yüz sağlayıcısı kurulmadı. |
| Meta, referans analizi, geri bildirim, kontrol noktası, taste direction, çalışma zamanı seçimi | Sekiz OpenMontage ve altı CineCode kaydı mevcut. Kare aralıklı referans çekim günlüğü, plan sürelerinin medyanı ve gözlem kapsamı eklendi. |
| Üretim rotaları ve ek aileler | Açıklayıcı, animasyon, karakter animasyonu, sinematik ve belgesel için ilgili teknikler yukarıda. Talking head, avatar, hibrit, klip, podcast, ekran demo ve yerelleştirme rotalarının motorları açılmadı. Web yakalama, tasarım sistemleri, ticari model istemleri, harici indirme, anahtar kurma ve otomatik yayın kapsam dışında. |

Sekiz özgün `openmontage-15f:` bilgisi 20 tarih ve 20 güzellik uzmanıyla görev bazında eşleşir. Eski `openmontage:` ve `cinecode:` notları korunur. Toplam 171 Registry kaydı. [Yeni eşleşmeler](config/media_craft_notes.json)

## Yerel bağlama ve doğrulama

- Skill Router, sahne türü ve uzman eşleşmesiyle bağlamı seçer. Bir çağrıda mevcut iki not ve 640 karakter sınırı geçerlidir. Scene Director seçilen bilgi kimliklerini `scenes[].review_skills` altında tutar. Kamera motoru, montaj, anlatıcı ve çekim süreleri mevcut plan sözleşmesinden gelir.
- Video Kalite Laboratuvarı, mevcut Tool Router adaptöründen `editor_review.scenes` için insan incelemesi bekleyen kayıtları döndürür. Mevcut teknik ölçümler, 85/100 editoryal eşik, hatalı sahne ve komşu geçişin yeniden değerlendirilmesi, OpenTimelineIO ve onay kapıları kendi kurallarıyla çalışır. Eski planlar yeni alan olmadan okunur.
- İsteğe bağlı çekim günlüğü `--evidence` JSON dosyasındaki `reference_review` alanından gelir. İnceleme izni açıklaması (`review_permission: true`), referansın SHA-256 özeti, rasyonel `fps`, toplam kare ve `shots` gerekir. Her çekim, bitişi hariç `frames` ve kontrollü `scale`, `motion`, `light`, `transition`, `sound` değerleri taşır. Bilinmeyen gözlem `unknown`. Yerel kullanıcı gözlemleri `reviewed_metadata` olarak raporlanır, gerçek video ölçümü veya varlık kullanım onayı verilmez. Eksik kapsama ayrıca görünür. Çakışan zaman aralığı, dosya yolu ve serbest çalışma talimatı kabul edilmez. [Kanıt sözleşmesi](scripts/video_quality_lab.py)
- Kök lisans AGPL-3.0. Sonuç yalnız özgün Türkçe rehberlik ve kendi Python kodumuzu içerir. Üst depo betiği, yönerge metni, fontu, varlığı, bağımlılığı, hook'u, MCP sunucusu ve çalıştırıcısı aktarılmadı. Üçüncü taraf model ve medya lisansları kendi koşullarına tabidir. [Lisans](https://github.com/OpenMontageInc/OpenMontage/blob/2e003e65fa99a0f329478a2c1cdcf26bc481933a/LICENSE)

## Ücretsiz gerçek stok ve arşiv adayları

Her dosya için kullanım koşulu, asıl yükleyici/kurum, atıf, kişi ve marka izinleri, coğrafi kapsam ve türev kullanım kontrol edilir. Ücretsiz erişim tek başına yayın onayı vermez. Bu tabloda kişisel veya klinik örnek onaylanmadı ve hiçbir video indirilmedi.

| Kaynak | Kullanım kararı ve örnek |
| --- | --- |
| Pexels | Ücretsiz ticari B-roll adayı. Tek başına yeniden dağıtım ve sahte destek yasak. Tanınabilir kişiyi olumsuz/rahatsız edici bağlamda kullanma. El kremi uygulaması, yarar veya tedavi iddiası eklenmeden, varlık hakları ve markalar incelendikten sonra açıklayıcı B-roll olabilir. [Lisans](https://www.pexels.com/license/) · [Varlık 8141586](https://www.pexels.com/video/person-putting-cream-on-her-finger-8141586/) |
| Pixabay | Ticari kurguya dahil edilebilen ücretsiz aday. Bağımsız yeniden satış/dağıtım, logo/marka içeren ticari kullanım ve kişilik hakları kontrolü uygulanır. Çömlek yapımı klibi modern bağlam görüntüsü olarak aday. Tarihî olaya ait kayıt diye sunulamaz. [Lisans](https://pixabay.com/service/license-summary/) · [Varlık 41388](https://pixabay.com/videos/modeling-clay-pottery-craft-art-41388/) |
| Wikimedia Commons | Kamu malı, CC0 ve uygun CC BY/CC BY-SA kayıtlarda ticari kullanım mümkün. Eser sayfası, atıf, türev ve paylaşım koşulları incelenir. Apollo 11 arşiv montajı NASA yapımı ve ABD kamu malı olarak işaretli. Türkiye ve hedef dağıtım alanında haklar ayrıca incelenir. [Yeniden kullanım](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia) · [Apollo 11 kaydı](https://commons.wikimedia.org/wiki/File:Apollo_11_Moonwalk_Montage.webm) |
| NASA | Kurumsal arşiv ve tarihî görüntü adayları. Üçüncü taraf öğeler, logolar, destek izlenimi ve tanınabilir kişi koşulları dosya ve bağlamla değerlendirilir. [Medya koşulları](https://www.nasa.gov/nasa-brand-center/images-and-media/) |
| NARA ve Library of Congress | Arşiv kataloğu ve açık film koleksiyonları kullanılabilir. NARA özel medya, bağışçı ve coğrafi kısıtlar barındırabilir. LoC medya kaydında Rights and Access ile varsa atıf satırı okunur. Çevrimiçi erişim yeniden kullanım izni değildir. [NARA haklar](https://www.archives.gov/research/motion-pictures/permissions) · [LoC serbest yeniden kullanım](https://www.loc.gov/free-to-use/) |
| Internet Archive / Prelinger | Tarihî film keşfi. Toplayıcı genelinde tek ticari lisans varsayılmaz. Belirli yükleme, ses, menşe, ülke ve kullanım koşulu kesinleşirse aday yapılır. [Koleksiyon](https://archive.org/details/prelinger) |

Pexels ve Pixabay için API anahtarı veya otomatik indirme eklenmedi. Mevcut onaylı yerel varlık ve kaynak yolları kullanılır. Lisans kaydı olmayan aday için insan incelemesi beklenir.

## Test kapsamı

Yapısal Graphify 0.9.121 grafiği aynı kaynak commit ve arşiv SHA-256 ile doğrulandı. Ağsız 226 Python testi, iki marka planı, mevcut notların korunması, 40 rol eşleşmesi, birim testinde referans bilgi kabul/ret koşulları ve Tool Router önbelleği doğrulandı. Yeni medya üretmeme sınırı nedeniyle medya dosyası üreten 15 fixture bu aşamada çalıştırılmadı.
