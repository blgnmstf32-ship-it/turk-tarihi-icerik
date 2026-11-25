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

Konu Avcısı, İçerik Stratejisti, Tarih Doğruluk Denetçisi ve AI Genel Yayın Yönetmeni sırayla dört ücretsiz model görüşü verir. İlk iki rol, altı kategorideki ilk 10 adayı beşer başlık halinde değerlendirir. Her aday için özgün bir anlatım açısı, gerekçe, incelenecek kaynak ve açık araştırma sorusu verir. Karar raporu değerlendirme kapsamını gösterir. Tarihî iddialar için kaynak okuması ve insan incelemesi gerekir.

AI Genel Yayın Yönetmeni seçilen video için mevcut 20 uzmandan en çok ikisini görevlendirir. Gelen önerileri kaynak listesiyle ve birbirleriyle karşılaştırır. Uzman görüşleri taslak raporunda kalır, doğrulanmış senaryoyu doğrudan değiştirmez. Dört 3D görevi kurallı üretimle yürür. `AI_AGENT_EXECUTION_REPORT.json` her rolün LLM durumunu, gerçek modeli, HTTP denemelerini ve ilgili kurallı görevin çalışıp çalışmadığını gösterir. Yerel uzman çağrıları için `ENABLE_20_LLM_AGENTS=1` ayarlanır. GitHub Actions uzman adımını mevcut `ENABLE_FREE_LLM=1` ayarına göre açar. Elle çalıştırırken `require_specialists` seçeneği uzman ve yönetmen karşılaştırmasını doğrular.

Instagram Insights salt okunur ve varsayılan olarak kapalıdır. Yetkili bağlantı veya yerel geçmiş sağlanırsa gerçek izlenme, izlenme süresi, paylaşım ve etkileşim ölçümleri ayrı analiz edilir. Erişilemeyen metrikler boş kalır. `EDITORIAL_DECISION_REPORT.md/.json` ve `AI_AGENT_EXECUTION_REPORT.json` çalışma sonucunu saklar.

### Dört gerçek model çağrısını doğrulama

[OpenRouter Keys](https://openrouter.ai/settings/keys) üzerinden bir anahtar oluşturun. Depoda **Settings → Secrets and variables → Actions** altında `OPENROUTER_API_KEY` adlı secret ile `ENABLE_FREE_LLM` adlı `1` değerli değişkeni tanımlayın. Anahtar editoryal ve uzman adımlarına verilir. İstek fiyatı sıfırla sınırlandırılır. Başlangıçta ücretsiz Nemotron 3 Nano Omni denenir. Yedek seçenekler ücretsiz Gemma 4 modelleri ve `openrouter/free` rotasıdır. 429 döndüren rota dinlendirilir ve bir rolün çalıştığı rota sonraki rol için tercih edilir. Dört görüşten biri tamamlanmazsa etkinleştirilmiş iş akışı teşhis raporunu kaydeder ve başarısız olur.

Yerel deneme için anahtarı kabuğa gizli girin:

```bash
read -rsp 'OpenRouter API key: ' OPENROUTER_API_KEY
export OPENROUTER_API_KEY
ENABLE_FREE_LLM=1 python -m scripts.editorial_board --out output/editorial --require-llm
unset OPENROUTER_API_KEY
```

### İsteğe bağlı Gemini Türkçe belgesel sesi

Gemini 3.8 Flash TTS, Charon sesi ve Türkiye Türkçesi belgesel yönlendirmesiyle bütün senaryoyu tek seferde okur. Tempoyu, vurguyu ve durakları model belirler. Yerel faster-whisper altyazıyı gerçek konuşma zamanlarına eşler. Ses 60–75 saniye aralığına veya ilk üç saniye açılışına uymuyorsa üretim durur ve metin incelemesi gerekir.

[AI Studio API Keys](https://aistudio.google.com/api-keys) üzerinden **faturalandırma hesabı bağlanmamış Free Tier projesinin** anahtarını kullanın. Proje sahibi, AI Studio'da ücretsiz katmanı kontrol ettikten sonra her çalıştırmada bunu onaylar. API anahtarı projenin faturalandırma durumunu istemciye bildirmez. Proje ücretsiz kotada kaldığında 0 USD. Google'ın 24 Kasım 2026 tarihli [fiyat tablosunda](https://aistudio.google.com/docs/pricing#gemini-3.8-flash-tts) ücretli katman 31 Aralık 2026'ya kadar 1 milyon metin giriş token'ı için 0,50 USD ve 1 milyon ses çıkış token'ı için 9 USD. 60–75 saniye ses çıkışı yaklaşık 0,0135–0,0169 USD, metin girişi ayrıca. Google 1 Ocak 2027'den itibaren ücretli birim fiyatların iki katına çıkacağını belirtiyor. Ücretsiz kota ve erişim AI Studio projesine bağlıdır. Bu entegrasyonun ücretli modu yoktur.

```bash
python -m pip install -r requirements.txt -r requirements-audio-audit.txt
export HF_HOME="$PWD/.cache/huggingface"
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
read -rsp 'Free Tier Gemini API key: ' GEMINI_API_KEY
export GEMINI_API_KEY
python -m scripts.auto_produce --topic antikythera-disli --out output/gemini \
  --voice-provider gemini_tts --confirm-gemini-free-project
python -m scripts.verify_production --out output/gemini --topic antikythera-disli
unset GEMINI_API_KEY
```

API kota, erişim veya yanıt hatasında durur. GitHub Actions'ta Gemini denemek için faturalandırılmamış Free Tier proje anahtarını `GEMINI_API_KEY` secret'ı olarak ekleyip **Run workflow** ekranında `confirm_gemini_free_project` kutusunu seçin. Zamanlanmış üretim Piper kullanır. Ücretsiz katmana yalnız yayınlanabilir nitelikte, hassas bilgi içermeyen senaryo gönderin.

### GitHub yazma erişimi

`Resource not accessible by integration` için [GitHub App kurulumunu](https://github.com/settings/installations) açın. Doğru hesabı ve `blgnmstf32-ship-it/turk-tarihi-icerik` deposunu seçin. Uygulama kurulumu depoya erişmeli ve `Contents: Read and write` izni bulunmalı. `.github/workflows/` değişikliklerini de aktaracak erişimde `Workflows: Read and write` iznini doğrulayın. ChatGPT GitHub bağlantısını bu kurulumla yeniden yetkilendirin. Kurulum izinleri uygulama tarafından sunulmuyorsa, repo sahibi terminalinde GitHub CLI ile yetkilendirilmiş Git aktarımı kullanabilir:

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
git fetch origin
git push origin HEAD:main
```

Komutlar bu projenin güncel yerel kopyasında çalıştırılır. Uzak `main` ilerlemişse önce değişiklikleri birleştirin. Gönderimden sonra GitHub'daki commit kimliğini ve ilk Actions sonucunu kontrol edin. Instagram yayını için ayrı insan onayı gerekir.

Dört editoryal görüş, uzmanlar ve yönetmen birlikte çalıştırma başına sekiz, UTC günü başına kırk üretim isteğiyle sınırlıdır. Başarısız istekler de sayılır. Geçici OpenRouter hatalarında bir değerlendirme en fazla üç kez denenir. OpenRouter kalan kotayı bildiriyorsa daha düşük sınır uygulanır. Uzun `Retry-After` değerinde yeni istekler durur. Başarılı yanıtlar aynı girdilerle tekrar kullanılabilir. GitHub Actions, başarısız değerlendirmelerden sonra da yanıtları ve istek sayacını saklar.
## Piri Reis ses karşılaştırması

Actions → **Piri Reis · Gemini Charon ve Piper** → **Run workflow**. AI Studio'da
`GEMINI_API_KEY` anahtarının faturalandırma hesabı bağlanmamış Free Tier
projesine ait olduğunu kontrol edin ve onay kutusunu işaretleyin. Canlı adım
Charon için bir istek yapar. Kota, erişim ya da ses doğrulama hatasında durur.

Bu deneme mevcut Piri Reis senaryosunu ve aynı sahneleri iki ayrı MP4'e işler.
Her sürüm kendi konuşmasına zamanlanmış altyazı kullanır. İndirme paketindeki
`SES_KARSILASTIRMA.json` son MP4'lerdeki Türkçe konuşma ve altyazı zamanlamasını,
ölçülen durakları ve temiz anlatıcı sesindeki perde aralığını gösterir.
Telaffuz ve anlatım doğallığı için videolar ayrıca dinlenmelidir. İki çıktı da inceleme taslağıdır.
