# Türk Tarihi — 20 Rol ile Ücretsiz İçerik Taslağı / Sesli Reels v0.4

**Durum:** 20 iş modülü kuruludur; yeni sistem 5 farklı özgün tarihî illüstrasyonu, çevrimdışı Türkçe Piper seslendirmesini, kısa metinleri, tahmini zamanlı altyazıları ve özgün müziği birleştirerek **insan onayına sunulacak** bir dikey Reels MP4 üretecek şekilde geliştirilmiştir. Kodun GitHub Actions üzerinde **başarıyla çalıştığı henüz doğrulanmadıkça** gerçek yayın sistemi hazır sayılmaz.

Bu 20 rol, **20 ayrı bulutta çalışan ücretli veya otonom LLM ajanı değildir**. Ücretsiz Python iş akışı içinde görev tanımlarıdır. İsteğe bağlı `OPENROUTER_API_KEY` ile `openrouter/free` modelinden bir yaratıcı metin önerisi alınabilir; bu öneriler doğrulanmadan yayın dosyasına girmez. GitHub Models 2026'da emekli edilmiştir, kullanılmaz.

## Maliyet ve güvenlik
- Ücretli AI API kullanımı: **0 TL** varsayılan; ücretsiz kota ve kullanım koşulları değişebilir.
- GitHub Actions: depoya/hesaba uygulanan kota ve faturalandırma kuralları geçerli.
- Türkçe Piper TTS: çevrimdışı, açık kaynak model; ilk seferde indirir. Ses kalitesi ve ses modeli lisansını kontrol edin.
- Görsel: kodla oluşturulmuş özgün, stilize tarihî canlandırmalar (fotoğraf gerçekliğinde AI video değil).
- **Yayın kapalı**: Instagram API kimlik bilgileri eklenmedi, otomatik paylaşım tetiklenmez, `approval/approved.json` dosyası `false` olarak kalır.
- Modelin ileri geri tarihî yorum veya yanlış üretilen çizim yapabilmesi nedeniyle insan kaynak kontrolü şart.

## Başlatma
GitHub deposunda Actions > **Türk tarihi ücretsiz sesli Reels taslağı** > Run workflow. Konu kimliği olarak `malazgirt-1071` seç.

Başarıyla çalışan bir iş `tarih-sesli-reels-taslagi-N` adlı artifact üretir. İçindeki `REVIEW_REQUIRED_REEL.mp4`, konuşmalı otomatik taslaktır; kalite kontrol ve tarihî kaynak onayı olmadan paylaşma.

Yerel kullanımı: `pip install -r requirements.txt 'piper-tts>=1.3,<2.0'`, `ffmpeg` kur, sonra `python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto`.

## Belgeler
- [Kurulum ve yetki gereksinimleri](KURULUM_v04.md)
- [20 görev tanımı](config/agents.json)
- [Kalite kapısı](AGENTS.md)
- [Orijinal sesli anlatım ve sahne üretimi](scripts/auto_produce.py)

## Özellikle yapılmayanlar
- Başka hesaplardan görüntü indirme veya içerik çalma.
- Hatalı tarihî bilgi yayma.
- Kullanıcı onayı olmadan ücretli araç veya Instagram otomatik yayınını açma.
- 20 bağımsız AI ajanı varmış gibi gösterme.

### 20 ayrı LLM çağrısı (isteğe bağlı)
`config/agents.json` yirmi uzman rol içerir. `scripts/ai_agents.py`, açıkça etkinleştirilirse OpenRouter `openrouter/free` üzerinden **her rol için bir ayrı AI çağrısı** yapabilir. Kurulmuş olması otomatik etkin olduğu anlamına gelmez; hizmetin ücretsiz kotası ve ayrı anahtar gerekir. Varsayılan sıfır API anahtarıyla yalnız deterministik görev yürütücü çalışır.
