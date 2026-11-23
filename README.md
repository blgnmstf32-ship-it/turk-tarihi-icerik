# Türk Tarihi — ücretsiz sinematik belgesel Reels otomasyonu v0.6

20 uzman rol, kaynaklı Türk tarihi konularını 60–75 saniyelik dikey belgesel taslağına dönüştürür. Roller aynı ücretsiz Python yürütücüsündeki iş modülleridir; 20 bağımsız/ücretli AI çalışanı değildir.

## Varsayılan video biçimi

- 60–75 saniye, 9:16, 720×1280, 30 fps.
- En az 10 tarihî alan/eser/harita/minyatür/arşiv görseli. Önce lisans ve kaynak bilgisi alınabilen ücretsiz Wikimedia Commons medyası aranır. Yetersiz sonuçta açıkça etiketlenmiş temsili sahne kullanılır ve görsel kalite kapısı başarısız olarak işaretlenir.
- Remotion: yavaş sinematik yakınlaşma ve kaydırma, yumuşak sahne geçişi, hareketli Türkçe altyazı ve sırayla sözcük vurgusu.
- FFmpeg: anlatım ve özgün/ücretsiz ambiyans miksajı, H.264/AAC MP4 sonlandırma.
- Anlatım yönü: doğal ve merak uyandıran belgesel tonu; net telaffuz, dönüm noktalarında canlı ama ölçülü vurgu, tempoda çeşitlilik ve anlamlı duraklar.
- İnsan ses kaydı varsa önceliklidir. Ücretsiz çevrimdışı Piper yedek sesidir ve sentetiktir; tek başına gerçek insan anlatımı doğallığı sağlamaz.
- İnsan anlatımı için programın ürettiği `VOICE_RECORDING_GUIDE.txt` dosyasındaki satırları ayrı dosyalara `01.wav`, `02.wav` … şeklinde kaydedip `--voice-recordings kayit-klasoru` seçeneğiyle verin. Böylece altyazılar her cümlenin gerçek ses süresine oturur.

## Maliyet ve yayın kapıları

- Ücretli API ve ücretli medya servisleri kapalıdır; otomatik yayına ücretli yedek yoktur.
- Instagram otomatik paylaşımı kapalıdır; insan onayı zorunludur.
- Wikimedia Commons medya araması ücretsiz ve anahtarsızdır. Görsel dosyalarının atfı `MEDIA_ATTRIBUTION.md` içine eklenir.
- Her videoda kaynak, lisans, tarih doğruluğu, ses doğallığı ve görsel uygunluğu insan tarafından incelenmelidir.

## Üretim

Actions > **Türk tarihi ücretsiz sesli Reels taslağı** > Run workflow. Konu kimliği örneği: `malazgirt-1071`.

Başarılı üretim `tarih-sesli-reels-taslagi-N` artifact'inde `REVIEW_REQUIRED_REEL.mp4` dosyasını saklar. Bu taslak inceleme içindir; kendi kendine Instagram'da yayınlanmaz.

Yerel kurulum:

```bash
npm ci
npm run typecheck
python -m pip install -r requirements.txt 'piper-tts>=1.3,<2.0'
python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto --model-cache .cache/piper
```

## Ajan rolleri ve kalite standardı

- 20 rol tanımı: `config/agents.json`
- Proje ve güvenlik talimatları: `AGENTS.md`
- Varsayılan üretim ayarları: `config/settings.json`
- Ayrıntılı video standardı: `VIDEO_KALITE_STANDARTLARI.md`
