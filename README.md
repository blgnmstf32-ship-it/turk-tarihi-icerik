# TARİHİN BİLİNMEYEN GERÇEKLERİ

20 özgün uzman rolü ile dört ek 3D rolü, Türk ve dünya tarihinden kaynaklı konuları 60–75 saniyelik dikey belgesel taslağına dönüştürür. Roller aynı Python yürütücüsündeki görev modülleridir; 24 bağımsız AI çalışanı değildir.

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

Actions > **Tarihin Bilinmeyen Gerçekleri · Haftalık rapor ve Reels** > Run workflow. Örnek konu `antikythera-disli`. Boş bırakılırsa son rapordan kaynak ve anlatım dosyası bulunan bir aday seçilir.

Başarılı üretim `tarihin-bilinmeyen-gercekleri-N` artifact'inde `REVIEW_REQUIRED_REEL.mp4` dosyasını saklar. Bu taslak inceleme içindir; kendi kendine Instagram'da yayınlanmaz.

Yerel kurulum:

```bash
npm ci
npm run typecheck
python -m pip install -r requirements.txt 'piper-tts>=1.3,<2.0'
python -m scripts.auto_produce --topic antikythera-disli --out output/auto --model-cache .cache/piper
```

## Ajan rolleri ve kalite standardı

- 20 özgün rol + 4 3D rol tanımı: `config/agents.json`
- Proje ve güvenlik talimatları: `AGENTS.md`
- Varsayılan üretim ayarları: `config/settings.json`
- Ayrıntılı video standardı: `VIDEO_KALITE_STANDARTLARI.md`

## Haftalık yayın yönetimi

`data/editorial_ideas.json` Türk ve dünya tarihinden 10 başlangıç önerisi ve altı kategori tutar. Her fikir için ilk üç saniye, kaynak bağlantıları, kanıt sınırı, izlenme hipotezi, görsel yaklaşım ve iş süresi kaydedilir. `data/topics.json` içinde kaynakları ve 60–75 saniyelik anlatımı hazırlanmış konular render adayıdır. Eski arşiv konuları açık kimlikle seçilebilir.

Konu Avcısı Google Trends Türkiye, tarih kanallarının YouTube akışları ve Crossref üzerinden yeni araştırma ipuçları toplar. RSS varsa izlenme sayısını ekler. İsteğe bağlı `YOUTUBE_DATA_API_KEY` görünür izlenme, beğeni ve yorum sayaçlarını resmî API üzerinden alır. Erişilemeyen paylaşım sayıları boş kalır. Raporda her sayaç için kaynak ve alınma zamanı gösterilir. Eski sayaç gözlemleri tarihli ve ayrı tutulur. YouTube rakip ölçüleri Instagram Reels ölçüleriyle birleştirilmez.

Haftalık rapor her salı 12.17 Türkiye saati için planlanır. Yerelde:

```bash
python -m scripts.editorial_board --out output/editorial
python -m scripts.performance_learning --out output/editorial
```

### Ücretsiz gerçek LLM

GitHub Actions için `OPENROUTER_API_KEY` adında bir depo secret'ı ve `ENABLE_FREE_LLM=1` adında bir depo değişkeni gerekir. Yerelde aynı isimlerle ortam değişkeni kullanılır. Proje ayarı ücretsiz modeli destekler. Anahtar veya opt-in yoksa rapor hangi alanın eksik olduğunu gösterir.

Konu Avcısı, İçerik Stratejisti, Tarih Doğruluk Denetçisi ve AI Genel Yayın Yönetmeni, sırasıyla birbirinin görüşüne yanıt veren dört ayrı `openrouter/free` isteği alır. Gerçek model ve çağrı durumu raporlanır. Yeni fikirlerin bağlantıları taranmış kaynak kayıtlarıyla eşlenir ve araştırma kuyruğuna gider. Doğrulanmış anlatımlar otomatik olarak değiştirilmez. Ücretsiz rota hata verirse ücretli yedek yoktur. 20 rolün isteğe bağlı model önerileri ayrıca `ENABLE_20_LLM_AGENTS=1` ister ve haftalık workflow'da kapalıdır. Dört 3D rolü üretim otomasyonudur.

Instagram Insights salt okunur ve varsayılan olarak kapalıdır. Yetkili bağlantı veya yerel geçmiş sağlanırsa gerçek izlenme, izlenme süresi, paylaşım ve etkileşim ölçümleri ayrı analiz edilir. Erişilemeyen metrikler boş kalır. `EDITORIAL_DECISION_REPORT.md/.json` ve `AI_AGENT_EXECUTION_REPORT.json` çalışma sonucunu saklar.
