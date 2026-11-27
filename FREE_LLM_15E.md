# 15E · Ücretsiz metin sağlayıcıları

28 Kasım 2026. Başlangıç `c3ed478d5f043022693911ed0b587d382cbe0b57`.

## Aday karşılaştırması

Kota ve lisans bilgisi sağlayıcıların yayımladığı koşulları gösterir. Model lisansı, barındırma şartları ve içeriğin telif veya sağlık onayı ayrı yükümlülüklerdir.

| Sağlayıcı | Ücretsiz kota ve ticari kullanım koşulları | Bu projedeki kanıt ve karar |
| --- | --- | --- |
| Gemini Developer API | Uygun modellerde Free Tier giriş ve çıkış maliyeti sıfır. RPM, TPM ve RPD model ve proje katmanına bağlı. Google üretilen içeriğin sahipliğini talep etmiyor. Ücretsiz hizmette bölgeye göre girdi ve çıktılar hizmet geliştirmede kullanılabilir. [Fiyat](https://ai.google.dev/gemini-api/docs/pricing) · [Kota](https://ai.google.dev/gemini-api/docs/rate-limits) · [Şartlar](https://ai.google.dev/gemini-api/terms) | Bu koşuda anahtar mevcuttu, faturalandırmasız proje onayı yoktu. 0 çağrı. Türkçe, JSON ve süre ölçülmedi. Mevcut onay kapılı yol korundu. |
| Cloudflare Workers AI | Workers Free günde 10.000 nöron. Proje tavanı 9.000. Gemma 4 26B ağırlıkları Apache-2.0. Workers ve model şartları geçerli. Cloudflare eğitim amacıyla müşteri içeriğini açık rıza olmadan kullanmadığını belirtiyor. [Fiyat](https://developers.cloudflare.com/workers-ai/platform/pricing/) · [Veri kullanımı](https://developers.cloudflare.com/workers-ai/platform/data-usage/) · [Gemma 4 lisansı](https://huggingface.co/google/gemma-4-26B-A4B-it) | Hesap Workers Free aboneliğiyle doğrulandı. 2/2 canlı JSON ve 2/2 görev geçişi. Mevcut yedek korunuyor. |
| OpenRouter Free | Ücretsiz varyantlar için 20 istek/dk ve kredili yükseltme olmadan 50 istek/gün. Başarısız denemeler kotaya sayılır. Proje tavanı 40/gün. Her istekte sıfır fiyat sınırı. Seçilen Nemotron modeli ticari kullanıma açık NVIDIA lisansına tabi. Yönlendirilen model ve sunucunun veri koşulları ayrıca geçerli. [Kota](https://openrouter.ai/docs/api_reference/limits) · [Şartlar](https://openrouter.ai/terms) · [Nemotron model kartı ve lisansı](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16) | 2/2 canlı JSON ve 1/2 görev geçişi. Tarih açılışı 3–16 sözcük ölçütünü karşılamadı. Mevcut son yedek korunuyor. |
| GroqCloud | GPT-OSS 20B için yayımlanan Free Plan sınırı 30 RPM, 1.000 RPD, 8.000 TPM ve 200.000 TPD. Hesap panosu belirleyici. Model Apache-2.0, barındırma Groq Services Agreement'a tabi. Yerleşik strict JSON Schema desteği belgeli. [Kota](https://console.groq.com/docs/rate-limits) · [JSON](https://console.groq.com/docs/structured-outputs) · [Şartlar](https://console.groq.com/docs/legal/services-agreement) · [Model lisansı](https://github.com/openai/gpt-oss) | Yeni adaylar içinde öncelikli. Bu projeye ait doğrulanmış Free Plan erişimi yok. 0 çağrı. Türkçe, JSON ve süre ölçülmedi. Kapalı. |
| Mistral | Free mode kotası hesap panosuna bağlı. Resmî destek bu modu değerlendirme ve prototipleme için konumlandırıyor. API plan koşulları açık ağırlık lisansından ayrı. Ücretsiz üretim kapasitesi ve hesabın veri şartları doğrulanmadı. [Kota](https://docs.mistral.ai/admin/billing-usage/usage-limits) · [Planlar](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them) · [Şartlar](https://legal.mistral.ai/terms/get-started/) | Erişim yok. 0 çağrı, kalite ve süre ölçülmedi. Kapalı. |
| Cerebras Inference | Resmî sayfada sürekli Free Tier bulunmuyor. Yeni hesaba küresel yayımlanan koşul doğrulanmış ödeme yöntemi gerektiren 30 günlük tek seferlik 5 USD deneme kredisi. Model lisansı barındırma sözleşmesinden ayrı. [Kota ve deneme](https://inference-docs.cerebras.ai/support/rate-limits) | Sürekli sıfır maliyet hedefini karşılamıyor. 0 çağrı ve canlı ölçüm yok. |
| Cohere | Deneme anahtarı ayda 1.000 çağrı ile sınırlı. Endpoint başına ek RPM sınırları var. Deneme değerlendirme için. Canlı üretim anahtarı ücretli ve SaaS şartlarına tabi. [Kota](https://docs.cohere.com/docs/rate-limits) · [Üretime geçiş](https://docs.cohere.com/docs/going-live) | 0 çağrı. Türkçe, JSON ve süre ölçülmedi. Üretim hattına alınmadı. |
| Hugging Face Inference Providers | Güncel fiyat tablosu Free hesap için aylık dahil kredi göstermiyor. Eski 0,10 USD bilgisi güncel plan tablosuyla uyuşmuyor. Kullanım ayrıca model ve sunucuya özgü. [Güncel fiyat](https://huggingface.co/docs/inference-providers/main/pricing) | Ücretsiz günlük üretim kotası yok. 0 çağrı. |
| GitHub Models | GitHub, Inference API dahil hizmetin 30 Temmuz 2026'da emekliye ayrıldığını bildiriyor. [GitHub Docs](https://docs.github.com/en/github-models) | Uygun ücretsiz yedek yok. 0 çağrı. |

## FreeLLMAPI kararı

MIT lisanslı `144f54bf429559c8e5ef704a77cb85eca12788f2` kaynak revizyonunda sağlayıcı kataloğu, anahtar saklama, kota takibi ve tek istemci adresi incelendi. Katalogdaki toplamlar proje hesabının hakkını veya her modelin ticari iznini kanıtlamıyor. Üretim mevcut doğrudan istemcileri, fiyat ve plan kapılarını, sınırlı yeniden denemeleri ve paylaşılan kota defterini kullanıyor. İkinci proxy, anahtar deposu, sağlayıcı geçişi ve MCP eklenmedi. Karşılaştırma giriş noktası mevcut istemcileri tekrar kullanır. [Sabit kaynak](https://github.com/tashfeenahmed/freellmapi/tree/144f54bf429559c8e5ef704a77cb85eca12788f2)

## Canlı Actions ölçümü

Standart Ubuntu Actions koşucusu, 28 Kasım 01.55 Türkiye saati. İki sağlayıcıda aynı tarih ve güzellik girdileri, 768 çıkış tokeni tavanı. Kodsuz JSON nesnesi, tam alan sözleşmesi ve Türkçe metin sinyali zorunlu. Altı otomatik ölçüt kısa açılışı, verilen olguyu, kanıt sınırını, ek sayısal iddia bulunmamasını, geçerli kanıt kimliğini ve şemayı kapsar. Bu küçük örnek, insan okuması veya tüm 40 uzman rolünü kapsayan kalite ölçümü yerine geçmez. [Canlı ölçüm ve JSON artefaktı](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/46079472737)

| Model | Tarih | Güzellik | Türkçe ve geçerli çıplak JSON | Editoryal ölçütler | Üretim isteği |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cloudflare Gemma 4 26B | 1.857 ms | 2.717 ms | 2/2 | 12/12 | 2 × HTTP 200 |
| OpenRouter Nemotron 3 Nano Omni 30B Free | 885 ms | 1.036 ms | 2/2 | 11/12 | 2 × HTTP 200 |
| Gemini 3.1 Flash-Lite | — | — | Ölçülmedi | Ölçülmedi | 0 |

Süre, istemci duvar saatidir. İlk OpenRouter süresi kota okumasını içerir. Cloudflare abonelik kontrolü 1 ayrı HTTP 200 ve zaman tablosu dışında. Gerçek kullanım Cloudflare 407 giriş ve 151 çıkış tokeni, proje hesabıyla tahmini 9 nöron (63 nöron ayrıldı). OpenRouter 168 çıkış tokeni, bu raporda giriş tokeni eksik. Toplam 4 üretim çağrısı, 2 salt okunur kota veya plan isteği, ücretli API çağrısı 0. Yeni medya üretimi veya Instagram paylaşımı yapılmadı.

`free_provider_comparison.py` yeni adaylara bağlanmaz. Ücretsiz Gemini onayı ve ücretli görsel anahtarından ayrım zorunlu. Cloudflare yalnız doğrulanmış Workers Free hesabında çalışır. OpenRouter mevcut sıfır fiyat ve kota geçidini kullanır. Önbellek yanıtı canlı başarıya sayılmaz. İş akışı yalnız depo sahibinin main dalındaki manuel çalıştırmasıyla açılır. Üretim takvimiyle eşzamanlı çağrı engellenir ve aynı kota dosyaları paylaşılır. Dışarıya verilen rapor model yanıtı, istem metni veya anahtar içermez. [Karşılaştırma işi](.github/workflows/free_provider_comparison.yml)
