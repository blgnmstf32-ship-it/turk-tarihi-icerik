# Ücretsiz editoryal model yönlendirmesi

Genel Yayın Yönetmeni ve iki markanın uzmanları aynı metin katmanını kullanır. Sıra Gemini, Cloudflare Workers AI ve OpenRouter Free. NVIDIA NIM ve Groq erişim onayına kadar kapalıdır. Bu sağlayıcıların ortam anahtarları tek başına çağrı açmaz.

| Sağlayıcı | Model seçimi | Kota ve maliyet denetimi |
| --- | --- | --- |
| Gemini | Flash, Flash Lite ve Gemma mevcut uzman eşlemesini kullanır. | Faturalandırmasız proje onayı ve model bazında RPM, TPM, RPD. Kullanılabilir gerçek kota Google AI Studio projesine bağlıdır. Ücretli görsel projesiyle aynı anahtar reddedilir. |
| Workers AI | Gemma 4 26B A4B birincil. Qwen3 30B A3B FP8, Gemma kullanılamazsa ikinci rotadır. GLM 4.7 Flash yalnız tanılama testine alınır. | Hesap abonelikleri Billing Read isteğiyle doğrulanır. Workers Free 10.000 nöron/gün (00.00 UTC). İki markaya ortak yazılım sınırı 9.000 nöron ve oturum başına 8 deneme. Belirsiz veya ücretli bir abonelikte inference kapalı kalır. |
| OpenRouter | Mevcut ücretsiz model listesi ve `openrouter/free`. | İki markaya ortak 40 deneme/gün, mevcut birleştirilmiş çalıştırma sınırı ve sıfır fiyat parametreleri. |

Cloudflare hesabının kendi kota limiti, bu depo dışında harcanan nöronları da kapsar. Yerel defter gönderimden önce ihtiyatlı bir nöron rezervi yazar. Sağlayıcı token tüketimini döndürürse tahmini gerçek nöron ayrı tutulur. Zaman aşımına uğramış veya ölçülemeyen isteğin rezervi korunur. Hesap doğrulaması yetki gerektirir. Workers AI model çalıştırma ve en az Billing Read izinleri yeterlidir. Ödeme veya abonelik değiştirme iznine gerek yoktur.

Gemini 429, Cloudflare yapılandırılmışsa bu oturumda Google çağrılarını durdurur. 503, zaman aşımı veya geçersiz gövde için Gemini bir kez daha denenir. Cloudflare her görevde model başına bir deneme yapar. Geçici hata yalnız ilgili modeli 60 saniye soğumaya alır. İki ücretsiz model de başarısızsa mevcut sınırlı OpenRouter rotası devreye girer. Türkçe metin denetimi, Cloudflare rotası açıkken yönlendirilen yanıtların diline dair yerel bir sezgisel kontrol sağlar. Mevcut rol şemaları ve kaynak doğrulaması ayrıca uygulanır.

Başarılı görüşler marka, rol ve girdi özetiyle ortak SQLite dosyasında tutulur. İşlenen görev bütün rotalarda başarısız olursa nedeni ve görev kimliği kuyruğa yazılır. Aynı girdiyle yeniden çalıştırma başarısız görevi yeniden dener ve başarılı görüşleri önbellekten alır. Editoryal kurul aynı Actions çalıştırmasının yeniden denemesinde ilk girdi anlık görüntüsünü kullanır. İş akışları aynı eşzamanlılık grubunda ve Actions önbellek anahtarında buluşur. GitHub önbelleğinin silinmesi veya sert biçimde kesilen bir çalıştırma kaydedilmemiş yerel defter girişlerini kaybettirebilir. Sağlayıcı seviyesindeki ücretsiz plan, Cloudflare için gerekli son maliyet kapısıdır.

## LiteLLM Router değerlendirmesi

LiteLLM'in MIT SDK'sı görev rotaları, yeniden deneme, geçiş ve hız sınırlarını destekler. Birden çok süreçte ortak otomatik durum için Redis seçeneği sunar. Mevcut depo ortak SQLite, OpenRouter sıfır fiyat kapısı, Türkçe rol şemaları ve iş girdisi kimliğiyle devam mekanizmasını zaten içeriyor. İkinci bir yönlendirme ve kota katmanı eklememek için LiteLLM kurulmadı. Resmî SDK paket listesinde OpenAI, HTTPX, tokenizers, tiktoken, aiohttp ve boto3 gibi ek bağımlılıklar bulunuyor. Sağlayıcı gecikmesine etkisi burada ölçülmedi. Mart 2026'da bildirilen PyPI tedarik zinciri olayı da kararın güvenlik değerlendirmesine girdi.

- [LiteLLM paket bildirimi](https://github.com/BerriAI/litellm/blob/main/pyproject.toml)
- [LiteLLM Router belgeleri](https://docs.litellm.ai/docs/router/learn/reliability)
- [LiteLLM PyPI olay duyurusu](https://github.com/BerriAI/litellm-docs/blob/main/blog/security_update_march_2026/index.md)
- [Cloudflare Workers AI fiyat ve kota tablosu](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Cloudflare Qwen3 30B A3B FP8](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/)
- [Cloudflare abonelik API'si ve Billing Read](https://developers.cloudflare.com/api/resources/accounts/subresources/subscriptions/methods/get/)
- [Google Gemini API fiyatları](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenRouter ücretsiz modeller](https://openrouter.ai/collections/free-models/)

## Doğrulama

`python -m scripts.quality_checks` çevrim dışı çalışır ve medya üreten testleri sayıp ayrı tutar. **Multi-LLM · Ücretsiz metin ve sağlayıcı geçişi** Actions iş akışı Gemini 429 yanıtını yerel olarak simüle eder. Gemma, tarih ve güzellik için iki zorunlu Türkçe editoryal görevle denenir. Qwen ve GLM tanılamaları ayrı sonuçlanır. İsteğe bağlı modeldeki hata doğrulanmış Gemma sonucunu değiştirmez. Rapor şema, olguya bağlılık, kanıt sınırı, kısa giriş, yanıt süresi, gerçek API çağrıları ve token bilgisi döndüyse nöron tahminini kaydeder. Sağlık veya tarih konusunda yeni bir olgu doğrulandığı varsayılmaz.
