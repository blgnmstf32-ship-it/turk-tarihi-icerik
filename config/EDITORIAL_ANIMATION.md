# Yerel editoryal animasyon

Konu ve marka aynı seçim kuralından geçer. Tarihte mevcut 3B şehir, savaş, mekanizma ve Atlas sahneleri için geniş ve sürekli kamera yolu seçilir. Basılı kaynak ve arşiv konularında sıcak kâğıt kolajı, sözlü anlatılarda çizimli defter rehberi önerilir. Güzellikte cilt katmanları ve bariyer için makro kamera, ambalaj ve içerik listeleri için gül tonlu etiket kolajı, bakım rutinlerinde çizimli damla rehberi kullanılır. Başka konularda mevcut kurgu sürer.

Seçim, Genel Yayın Yönetmeni ve ilgili sahne, sanat, kurgu, 3B ve denetim rollerinin girdisine eklenir. Yerel kurallar yeni model çağrısı gerektirmez. LLM tavsiyesi araç yükleme, üçüncü taraf bağlantısı çalıştırma veya yayın onayı vermez. Viral öğrenme rehberi ve kaynak denetimi mevcut sırada uygulanır.

- Kamera, her 3B çekim içinde kesintisiz ilerler. Three.js konum ve odak eğrilerini örnekler, GSAP tek bir yumuşatma eğrisi uygular. Aynı kare farklı sırada istendiğinde aynı değer hesaplanır. Tarihî harita ve güzellik anatomisi için mevcut temsili gösterim uyarıları korunur.
- Kâğıt kolajı yerel HTML, CSS ve GSAP zaman çizelgesiyle hazırlanır. Dosyadaki metin, kaçış uygulanarak HTML'e aktarılır. Fotoğraf varsa yerel JPEG, ticari kullanım kaydı, kaynak, atıf ve dosya özeti kontrol edilir. Tarih akışı kendi indirdiği Commons fotoğraflarından açık lisanslı bir alt küme kullanabilir. Diğer durumlarda dosya almadan özgün kâğıt desenleri çalışır. HyperFrames yalnız yerelde kurulu doğrulanmış araç ve tarayıcı bulunduğunda ek klip hazırlar. Üretimde servis anahtarları bu sürece aktarılmaz. Ek klip eksik veya geçersizse temel kurgu sürer.
- İki özgün karakter, vektör şekli, kareye bağlı hareket, göz kırpma ve pozlarla çizilir. Tarih için defter ve güzellik için damla tasarımı vardır. Remotion'daki `EditorialCharacter` kompozisyonu iki markayı da destekler. Tarih ana akışı sözlü anlatıda bunu otomatik katman olarak kullanır. Mevcut sabit güzellik pilotunun cilt konusu makro kamerayı seçer.

## Dış kaynak ve lisans incelemesi

| Proje / incelenen commit | Değerlendirme ve uygulama |
| --- | --- |
| Lemo Opuscar `439b98a` | `core/render/events.mjs` gibi çekirdek araçlar ve `styles/archive-lighttable/demo/timeline.js` gibi geliştiriciye ait demo kodu MIT kapsamında ticari kullanım için değerlendirilebilir. Zaman çizelgesini resim ve ses varlıklarından ayırma ile kaynaklı belge katmanlama teknikleri incelendi. Dokümanlar ve belirtilen istemler CC BY-NC 4.0 kapsamındadır. Lisans, kişinin kendi ticari filmi için ek kullanım izni verir ve dokümanın ticari ürüne eklenmesi gibi daha geniş yeniden dağıtımı ayrıca düzenler. Demolardaki üçüncü taraf varlıklar ve bazı sesler kendi koşullarına tabidir. İş akışına dış dosya aktarılmadı. [Lisans](https://github.com/lemomo-ai/lemo-opuscar/blob/439b98af08b04400f8fd8a8dd19cd773c0c96532/LICENSE) |
| OneTake `4e024be` | PolyForm Noncommercial 1.0.0. Kesintisiz kamera fikri, mevcut Three.js ve GSAP ile bağımsız uygulandı. Kod, görsel, şablon ve ticari kullanımı kısıtlı diğer dosyalar alınmadı. [Lisans](https://github.com/feitangyuan/onetake/blob/4e024be4c6c696b260f39a35aee6bd56d303b679/LICENSE) |
| Collage B-Roll `a1a4ee2` | Depo kodu MIT. Kâğıt, raster doku ve fotoğraf katmanı fikri bağımsız uygulandı. Kaynak betiklerdeki Gemini/Veo, depolama, yükleme ve indirme adımları kullanılmadı. [Lisans ve kaynak](https://github.com/pyang5166/gbro-collage-broll/tree/a1a4ee2e2abf7d44e460026b706d0c72c2cf8a91) |
| Claude Animation Base `0ac8bf2` | Depo MIT. Sahne zamanına bağlı pozlar ve ayrı çizim katmanları incelendi. Clawd karakteri, ad, marka ve örnek varlıklar alınmadı. p5.js LGPL 2.1 ve p5.brush MIT olarak değerlendirildi. Mevcut Remotion/SVG hattı ihtiyacı karşıladığı için ikisi de bağımlılık olarak eklenmedi. [Depo lisansı](https://github.com/JohnHeibel/ClaudeAnimationBase/blob/0ac8bf2b31942376cb6b8c4074715595d512acd2/LICENSE) · [p5.js](https://p5js.org/copyright/) · [p5.brush](https://github.com/acamposuribe/p5.brush) |

GSAP, pilotla aynı `3.14.2` sürümünde Remotion'a bağlandı. GSAP Standard License geçerlidir. Mevcut HyperFrames `0.9.90`, Three.js ve Remotion sürümleri korunur. Üçüncü taraf depoların kurulum ve render betikleri çalıştırılmadı. [GSAP lisansı](https://gsap.com/standard-license/)

## Medyasız doğrulama

`python -m scripts.quality_checks` Python seçim ve temel kurguya dönüş yolunu denetler. `node --experimental-strip-types --test tests/editorial_animation.test.mjs` altı kamera eğrisini ve HyperFrames HTML sözleşmesini açmadan veya render etmeden test eder. `npm run typecheck` Remotion tiplerini doğrular. Medya testleri standart test dizininde kalır.
