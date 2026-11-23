# Türk Tarihi — 20 Rol ile Ücretsiz İçerik Taslağı / Sesli Reels v0.5

**Durum:** 20 iş modülü korunur. Üretim akışı 10 farklı özgün tarihî illüstrasyonu, çevrimdışı Türkçe Piper seslendirmesini, cümle bazlı durak/tempo düzenini, ses parçası sürelerine hizalı altyazıyı, özgün müziği ve hareketli kamera montajını birleştirerek **insan incelemesine sunulan** dikey Reels MP4 üretir. Piper sesi sentetiktir; vurgu ve ritim iyileştirmesi onu insan kaydı yapmaz. Yayın öncesi dinleme ve tarih kontrolü zorunludur.

Bu 20 rol, **20 ayrı bulutta çalışan ücretli veya otonom LLM ajanı değildir**. Ücretsiz Python iş akışı içinde görev tanımlarıdır. İsteğe bağlı `OPENROUTER_API_KEY` ile `openrouter/free` modelinden bir yaratıcı metin önerisi alınabilir; bu öneriler doğrulanmadan yayın dosyasına girmez. GitHub Models 2026'da emekli edilmiştir, kullanılmaz.

## Maliyet ve güvenlik
- Ücretli AI API kullanımı: **0 TL** varsayılan; ücretsiz kota ve kullanım koşulları değişebilir.
- GitHub Actions: depoya/hesaba uygulanan kota ve faturalandırma kuralları geçerli.
- Türkçe Piper TTS: çevrimdışı, açık kaynak model; ilk seferde indirir. Ses kalitesi ve ses modeli lisansını kontrol edin.
- Görsel: kodla oluşturulmuş 10 özgün, stilize tarihî canlandırma ve yavaş kamera hareketi (gerçek fotoğraf veya video değildir).
- Ses: çevrimdışı Piper, cümle cümle üretim, değişen hafif tempo ve planlı duraklar; altyazılar her ses cümlesinin gerçek süresinden hesaplanır.
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
- [Sesli anlatım ve sahne üretimi](scripts/auto_produce.py)

## Özellikle yapılmayanlar
- Başka hesaplardan görüntü indirme veya içerik çalma.
- Hatalı tarihî bilgi yayma.
- Kullanıcı onayı olmadan ücretli araç veya Instagram otomatik yayınını açma.
- 20 bağımsız AI ajanı varmış gibi gösterme.

### 20 ayrı LLM çağrısı (isteğe bağlı)
`config/agents.json` yirmi uzman rol içerir. `scripts/ai_agents.py`, açıkça etkinleştirilirse OpenRouter `openrouter/free` üzerinden **her rol için bir ayrı AI çağrısı** yapabilir. Kurulmuş olması otomatik etkin olduğu anlamına gelmez; hizmetin ücretsiz kotası ve ayrı anahtar gerekir. Varsayılan sıfır API anahtarıyla yalnız deterministik görev yürütücü çalışır.
