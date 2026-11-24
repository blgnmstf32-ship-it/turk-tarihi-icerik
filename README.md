# Türk Tarihi — ücretsiz sinematik belgesel Reels otomasyonu v0.8

20 özgün uzman rolü ile dört ek 3D rolü, kaynaklı Türk tarihi konularını 60–75 saniyelik dikey belgesel taslağına dönüştürür. Roller aynı Python yürütücüsündeki görev modülleridir; 24 bağımsız AI çalışanı değildir.

## Varsayılan video biçimi

- 60–75 saniye, 9:16, 1080×1920, 30 fps ve 10–12 sahne.
- En az 10 tarihî alan/eser/harita/minyatür/arşiv görseli. Önce lisans ve kaynak bilgisi alınabilen ücretsiz Wikimedia Commons medyası aranır. Yetersiz sonuçta açıkça etiketlenmiş temsili sahne kullanılır ve görsel kalite kapısı başarısız olarak işaretlenir.
- Remotion: yavaş sinematik yakınlaşma ve kaydırma, yumuşak sahne geçişi, hareketli Türkçe altyazı ve sırayla sözcük vurgusu.
- FFmpeg: anlatım ve özgün/ücretsiz ambiyans miksajı, H.264/AAC MP4 sonlandırma.
- Anlatım yönü: doğal ve merak uyandıran belgesel tonu; net telaffuz, dönüm noktalarında canlı ama ölçülü vurgu, tempoda çeşitlilik ve anlamlı duraklar.
- İnsan ses kaydı varsa önceliklidir. Ücretsiz çevrimdışı Piper yedek sesidir ve sentetiktir; tek başına gerçek insan anlatımı doğallığı sağlamaz.
- Google Chirp 3 HD ve Azure Speech seçilebilir, fakat iki bulut sağlayıcı da varsayılan olarak kapalıdır. Ücretli yedek geçişi yoktur; maliyet sınırı sıfırdır.
- faster-whisper ile yerel altyazı kontrolü ve PySceneDetect ile sahne kontrolü isteğe bağlı `requirements-*-audit.txt` dosyalarında bulunur; indirilen modeller/ağ kullanımı varsayılan olarak kapalıdır.
- Wikimedia lisans/atıfları `MEDIA_ATTRIBUTION.md` dosyasına yazılır. Görsel yetersizse açık etiketli temsili canlandırma kullanılır; gerçek fotoğraf diye gösterilmez.
- Hata ve kullanıcı geri bildirimi `output/observer/*.jsonl` içine yerel kaydedilir; anahtarlar gizlenir.
- Instagram Insights için salt okunur kapalı iskelettir. Otomatik yayın özelliği açılmaz.
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

- 20 özgün rol + 4 3D rol tanımı: `config/agents.json`
- Proje ve güvenlik talimatları: `AGENTS.md`
- Varsayılan üretim ayarları: `config/settings.json`
- Ayrıntılı video standardı: `VIDEO_KALITE_STANDARTLARI.md`

## İçerik yönetimi ve haftalık karar raporu

- 20 özgün rol ve dört 3D üretim rolü korunmuştur. AI Genel Yayın Yönetmeni bunları içerik araştırması, strateji ve sonuç raporuyla koordine eder. Rol modülleri tek Python sürecindeki otomasyonlardır; bağımsız LLM ajanları değildir.
- Konu Avcısı kamuya açık Google Trends Türkiye RSS'i ile `config/research_sources.json` içindeki tarih kanallarının son YouTube RSS başlıklarını tarar. RSS rakip izlenme sayısını vermez; sistem bunu performans kanıtı gibi sunmaz.
- İçerik Stratejisti dört kategori için fikirleri trend eşleşmesi, rakip başlık kapsamı ve varsa kendi geçmiş performansına göre göreli 0–100 endekste sıralar. Bu endeks başarı olasılığı değildir. Fikir değerlendirmesi her öneri için dayanak, karşı sav ve tarih doğruluğu kapısı verir.
- Her üretim sonunda `output/auto/editorial/EDITORIAL_DECISION_REPORT.md` ve `.json` oluşur. Öneriler görsel, 3D, ses, montaj, üretim süresi ve ücretli API maliyet varsayımı taşır.
- Üretim raporları `AI_AGENT_EXECUTION_REPORT.json` içinde gerçek LLM çağrısı yapılan rolleri yazar. LLM varsayılan kapalıdır; açmak için `config/settings.json` içindeki `editorial_intelligence.free_llm_enabled`, ilgili açık environment opt-in'i ve anahtar gerekir. Yalnızca `openrouter/free` kullanılır, ücretli yedeğe geçilmez.
- Instagram Insights adaptörü salt okunur ve kapalı başlar. Yetkili Meta token/erişim, medya eşlemesi ve `instagram_insights_enabled` ayarı olduğunda Reels görüntüleme, erişim, paylaşım ve ortalama izlenme süresi ölçülerini alır; hesap düzeyindeki takip değişimini ayrı tutar. Ölçümler `data/performance.jsonl` dosyasına yerel kaydedilir ve sonraki önerilere girer.

Bağımsız haftalık rapor için:

```bash
python -m scripts.editorial_board --out output/editorial
python -m scripts.performance_learning --out output/editorial
```
