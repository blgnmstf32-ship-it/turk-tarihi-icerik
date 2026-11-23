# En düşük maliyetli üretim yaklaşımı v0.6

## Varsayılan giderler

- Ücretli AI/ses/görsel API servisi: kapalı; otomatik ücretli yedek yok.
- Ses: yerel ücretsiz Piper Türkçe modeli; ses sentetiktir. Daha doğal sonuç için kullanıcı/insan anlatıcı kayıtlarını dosya başına sağlayabilir.
- Görsel: önce açık lisanslı Wikimedia Commons medyası ve atıf bilgisi. Yetersiz sonuçta ücretli servis çağrılmaz; temsili çizim kullanılır ve gerçekçi görsel şartı karşılanmadı diye rapor edilir.
- Kurgu: Remotion ve FFmpeg. Remotion renderı ücretsiz lisans seçeneğiyle çalıştırılacak şekilde ayarlanmıştır; lisans koşulları hesabın/kuruluşun uygunluğuna göre uygulanır.
- GitHub Actions dakikaları ve depolama kullanımı GitHub planı/kotasına bağlıdır. Yerel bilgisayar çalıştırması Actions dakikalarını kullanmaz.

## Maliyeti düşük tutan varsayılanlar

1. 720×1280 ve 30 fps dikey çıktı.
2. Tek çalıştırmada 10 sahne ve bir kaynaklı senaryo.
3. Model indirmesini Actions cache içinde sakla.
4. Ücretsiz kaynak ve çevrimdışı TTS kullan; kota bittiğinde ücretli modele geçme.
5. Aynı içerik için tekrar üretimi insan kararıyla yap.
6. Instagram otomatik yayınını kapalı tut; her taslak insan incelemesinde kalsın.

20 rol, 20 ayrı abonelik ya da bağımsız ücretli ajan değildir; aynı akışta tanımlı iş modülleridir. Açık LLM rol çağrıları isteğe bağlı ve varsayılan kapalıdır.
