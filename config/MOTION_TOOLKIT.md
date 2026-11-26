# İsteğe bağlı hareket ve medya araçları

Varsayılan üretim motoru, sesler, viral öğrenme ve paylaşım ayarları korunur. Bu kayıt araç önerisi verir. Kaynak, model ve varlık izinleri ayrı doğrulanır. Haricî beceriler, paket kurulum betikleri, MCP uçları ve yapay ses/görsel servisleri ajanlara yüklenmez.

| Proje | İnceleme ve kullanım sınırı |
|---|---|
| [Motion Skills](https://github.com/iart-ai/motion-skills) | Ana depo 19 bağımsız paketin dizini. MIT kodu ve teknik fikirler; örnek medya, font, müzik ve marka varlıkları ayrı. `npx skills add` ile uzaktan yükleme, iArt MCP ve ücretli önizleme kapalı. |
| [Animation Skills](https://github.com/Hmzbo/animation-skills) | Depo MIT. Manim, Motion Canvas, Three.js ve WGPU fikirleri kullanılabilir. Remotion ve GSAP’ın kendi lisans koşulları geçerli. Kurucu aracı ajan dizinine dosya kopyalıyor; kurucu veya örnek render çağrısı kullanılmaz. |
| [Motion Canvas Skills](https://github.com/jmwdpk/motion-canvas-skills) | Beceri paketi Apache-2.0. Çerçeveleme, easing ve zaman çizelgesi kullanılır. HTTP/WS geliştirme aracı ve ikinci render altyapısı eklenmez. Kullanılan font ve medya ayrı lisans ister. |
| [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) | Kod Apache-2.0. [Small ONNX](https://huggingface.co/onnx-community/depth-anything-v2-small/blob/main/onnx/model_quantized.onnx) Apache-2.0 ve yayımlanmış SHA-256 ile sınırlı. Base, Large ve Giant CC BY-NC 4.0 ağırlıkları kullanılmaz. ONNX Runtime MIT, NumPy BSD-3-Clause, Pillow HPND. |
| [Parallax Studio](https://github.com/longweekendlabs/parallax-studio) | MIT masaüstü yazılımı. Ayrık derinlik ve sınırlı kamera hareketi tekniği uygun. PySide6 koşulları ve otomatik seçilen poz, maske ve derinlik ağırlıkları farklı olduğundan uygulama kurulmaz. |
| [AnimeFX](https://www.npmjs.com/package/@voltwake/animefx/v/4.0.2) | GitHub kaynağı bu oturumda erişilemedi. Yayımlanmış 4.0.2 tarball ve bütünlük kaydı incelendi. MIT, gömülü Anime.js MIT ve Paper shader bileşenleri için ayrıca Apache-2.0 lisans/NOTICE. İlk aşama sade efektleri mevcut zaman çizelgesine uyarlar. Shader, CDN ve galeri görselleri kullanılmaz. |
| [Manim Community](https://github.com/ManimCommunity/manim) | MIT. İsteğe bağlı yerel Cairo, Pango ve FFmpeg dağıtımlarının lisansları ayrıca geçerli. Örnek font veya eğitim görseli paketlenmez. Yalnız depodaki denetlenmiş yerel sahne çalıştırılabilir. |
| [Theatre.js](https://github.com/theatre-js/theatre) | Çekirdek Apache-2.0. Studio AGPL-3.0; diğer paketler için paket bazında lisans denetimi gerekir. Uzmanlara anahtar kare planı aktarılır; ikinci editör kurulmaz. |
| [rembg](https://github.com/danielgatis/rembg) | Kod MIT. Ağırlık kaynağı otomatik indirmeye bırakılmaz. U2Net ailesi ve dönüştürülmüş ONNX varlıkları için ayrı izin kaydı gerekir. ONNX Runtime/Pillow koşulları ayrıca geçerlidir. |
| [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) / [Historical Basemaps](https://github.com/aourednik/historical-basemaps) | İstemci BSD-3-Clause. Tarihî veri deposu GPL-3.0, tekil haritalar için dönem, içerik kaynağı ve türev dağıtım şartı ayrıca incelenir. Uzaktan karo/glyph veya belirsiz dönem verisi gerekmez. |
| [Poly Haven](https://polyhaven.com/our-api) | API sunucu kodu AGPL-3.0. Barındırılan API'nin güncel koşulları ticari kullanımı ücretsiz kılıyor ve canlı API entegrasyonu için kaynak gösterme istiyor. Model/doku/HDRI varlıkları ayrıca CC0. API kullanılırsa “Powered by Poly Haven” görünür. |
| [VMAF](https://github.com/Netflix/vmaf) | Kod BSD-2-Clause-Patent. FFmpeg lisansı kullanılan derlemeye bağlı. Yalnız FFmpeg ile gelen varsayılan VMAF modeli ve dilim eşleşmiş yerel referans değerlendirilir; özel ağırlık yüklenmez. |
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) | MIT veya Apache-2.0 kod. Model arşivi, kullanılan CPU ikilisi ve Python/Rust çalıştırma zinciri ayrı onaya tabi. Gürültü teyidi ve onaylı yerel ağırlık olmadan çalışmaz. |
| [glTF Transform](https://github.com/donmccurdy/glTF-Transform) | MIT. Draco, Meshopt, KTX ve diğer isteğe bağlı kodlayıcıları bu modül kullanmaz. Model, doku ve yazar hakları optimizasyonla değişmez. |

## Kalıcı teknikler

- Editör ve sanat yönetmeni bir sahnede tek odak, okunaklı güvenli alan, durak ve üç saniyelik ilk görsel vaadi seçer. Hareket, görsel kanıtı açar ve okuma sırasında sakinleşir.
- Kurgu uzmanı giriş, okuma tutuşu ve çıkışı kareye bağlar. Kapak, altyazı ve ilk plan aynı sözü verir. Demo varlıkları ve sahte ürün sonucu kullanılmaz.
- 3B uzmanı derinlikte küçük kaydırma, katmanların aşırı esnemesini önleyen sınırlar ve örtülme kontrolü kullanır. Harita üzerinde kaynak ve dönem görünür, tarihî sınır yaklaşık olduğu yerde belirtilir.
- Bilimsel veya eğitici Manim diyagramı ölçeği, varsayımı ve şema niteliğini görünür kılar. Harici sis, shader ve rastgele döngüler yerine tekrar üretilebilir zaman kullanılır.
- Aynı sahneye tek render motoru seçilir. VMAF, konuşma temizliği ve GLB optimizasyonu yalnız gerektiğinde seçilen ayrı adımlardır.

Kaynak güvenliği için becerilerin metni veri olarak okunur. Otomatik indirme, ortam değişkeni veya kimlik bilgisi isteyen adımlar, geliştirme sunucusu, örnek medya ve kurulum araçları kullanılmaz. Model ve veri dosyaları yalnız yerel, içerik özeti ve izin kaydıyla kabul edilir.

## Uygulama girişleri

`python -m scripts.motion_cli guidance tarih --role 13` sanat yönetmeni önerilerini listeler. Genel Yayın Yönetmeni marka yaklaşımını ve uygun uzman seçeneklerini görür. Araç önerisi, çalıştırma yetkisi vermez. Kod, harici becerilerin yönergelerini çalıştırmak yerine `motion_skill_index.json` içindeki kısa, yerel teknik açıklamaları kullanır.

| Giriş | İsteğe bağlı çalışma biçimi |
|---|---|
| `motion_cli atlas GEOJSON RECEIPT --year YEAR` | WGS84, lisans, hash ve dönem kontrolü. Aynı sadeleştirilmiş sınırlar ağsız MapLibre stiline ve Three.js Atlas katmanına gider. Mevcut Atlas sahnesinde operatör `--atlas-geojson`, `--atlas-receipt` ve `--atlas-year` ile açıkça seçer. |
| `motion_cli catalogue models --file INDEX.json` | Yerel katalog verisini model, doku veya HDRI seçkisine çevirir. `--live` açıkça seçilirse yalnız resmî ücretsiz metadata uç noktası kullanılır. Varlık dosyası yazılmaz ve erişim anahtarı gönderilmez. |
| `motion_cli depth` ardından `motion_cli parallax` | Doğrulanmış Small modeli CPU üzerinde göreli derinlik çıkarır. İkinci adım aynı özgün görsele bağlı iki yakın katman üretir. Remotion için `--parallax-dir` onaylı ilk sahneyle hash eşleştirir. Küçük piksel kaydırması ve düz temel görüntü örtülme deliklerini sınırlar. |
| `auto_produce --opening-effect lines-reveal` veya `mask-reveal` | AnimeFX 4.0.2 efektlerinin yerel zaman çizelgesine uyarlaması. HyperFrames için `media_pilot/design.mjs` üçüncü konumsal argüman olarak aynı efekt adını alır. Her iki motor aynı süre kaydını okur. |
| `motion_cli alpha` | Başka bir ağırlık indirmeden, açıkça onaylanmış yerel U2NetP ONNX kaydı ile alfa maskesi hazırlama. |
| `motion_cli manim barrier OUTPUT` veya `mechanism` | İki denetlenmiş şemadan birini yerel Cairo ile işler. Özel Python sahnesi veya ağdan tema alamaz. İncelenen Manim program sürümü 0.22.1. |
| `motion_cli vmaf REFERENCE ENCODED --aligned` | Video dosyalarını değiştirmeden VMAF JSON ölçümünü hesaplar. Görsel girdiler ve FFmpeg derlemesinde libvmaf gerekir. |
| `motion_cli denoise ... --noise-confirmed` | Yalnız mevcut 48 kHz WAV ve onaylı yerel model arşivi. Filtrelenmiş ses ayrı kalır, orijinal ses veya onay kaydı değişmez. |
| `motion_cli glb SOURCE RECEIPT OUTPUT` | Kendi dokuları içinde taşıyan yerel GLB için `dedup` ve `prune`. İncelenen CLI sürümü 4.5.1. |

Operatör JSON kaydında `sha256`, `source`, `license`, `attribution` ve `commercial_use_reviewed: true` alanlarını doldurur. Atlas kaydı `year`, rembg ONNX kaydı `model_family: "u2netp"` ister. Gerekli isteğe bağlı bağımlılıklar ana iş akışına kurulmaz. VMAF ve DeepFilterNet için derleme/model bulunabilirliği yerel makineye bağlıdır. Günlük render ve Instagram yayın akışlarının tetikleyicileri değişmez.

## Otomatik seçim ve geri dönüş

Her iki markanın mevcut Reels üretim akışı, konuya göre yerel bir efekt seçer. Tarihte keşif ve mekanizma konularında, bakımda katman şeması başlığında satır açılışı kullanılır. Diğer konular mevcut kurguyla devam eder. Onaylı atlas veya derinlik dosyası isteğe bağlıdır. Bu katman ya da efekt başarısız olduğunda mevcut kurgu yeniden denenir. Rapor seçimi ve geri dönüşü ayrı gösterir.

VMAF isteğe bağlı, önceden hizalanmış referansla `--vmaf-reference` ve `--vmaf-aligned` seçenekleriyle çalışır. Referans, FFmpeg veya libvmaf yoksa sonuç `not_measured` olur ve puan alanı yazılmaz. Diğer araçlar gerektiğinde, yerel önkoşulları karşılayan operatör komutlarıyla kullanılır.
