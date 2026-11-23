# Türk Tarihi belgesel Reels otomasyonu v0.7

## İçerik üretim modeli

- `config/agents.json` içindeki 20 görev rolü, tek Python iş akışında çalışır. Bu sayı 20 bağımsız ücretli LLM ajanı demek değildir.
- Varsayılan video: 60–75 saniye, dikey 9:16, 1080×1920, 30 fps.
- Sahne görsellerinde önce Wikimedia Commons'ın açık lisanslı bitmap eserleri, arşiv fotoğrafları, haritaları ve tarihî alan görüntüleri aranır. Yazar, lisans ve kaynak sayfası `MEDIA_ATTRIBUTION.md` içinde saklanır. Yeterli uygun görsel bulunmazsa yerel canlandırmalar kullanılır ve görsel kalite eksiği rapora yazılır.
- Remotion sinematik sahne hareketini ve sözcük vurgulu altyazıları render eder. FFmpeg anlatım/müziği miksler ve H.264/AAC MP4'ü tamamlar.
- Anlatıcı yönü merak uyandıran, doğal ve ölçülü coşkulu Türkçe belgesel tonudur. İnsan kaydı tercih edilir; Piper sentetik ücretsiz yedektir.
- `180010.mp4` örneğinde ses kanalı yoktur; görsel ritim ve altyazı yaklaşımı örnek alınır, konuşma sesi taklit edilmez.

## Ücret ve yayın güvenliği

- Ücretli AI, görsel ve ses API servisleri kapalıdır; ücretsiz kota dolarsa ücretli modele geçiş olmaz.
- Wikimedia Commons'ın anahtarsız, ücretsiz araması dışında harici üretim servisi varsayılan değildir.
- Instagram otomatik paylaşımı kapalı, insan onayı zorunludur. Üretim yalnız incelenecek taslak oluşturur.
- Hiçbir gizli anahtar depoya eklenmemelidir. Varsayılan iş akışı LLM anahtarını kullanmaz; 20 rol yine yerel görev modülleri olarak korunur.
- Actions ve Remotion lisans uygunluğu, hesap/proje koşullarına bağlıdır; ücretli bir özellik etkinleştirmeyin.

## Yerel çalıştırma

```bash
npm ci
npm run typecheck
python -m pip install -r requirements.txt 'piper-tts>=1.3,<2.0'
python -m scripts.auto_produce --topic malazgirt-1071 --out output/auto --model-cache .cache/piper
```

Gerçek anlatıcı kaydı için `VOICE_RECORDING_GUIDE.txt` içindeki her satırı ayrı dosyaya `01.wav`, `02.wav`, … adıyla kaydedin ve `--voice-recordings kayit-klasoru` ekleyin. Piper kullanılmadığında Piper modeli indirilmez.

## İsteğe bağlı yerel QA

`requirements-audio-audit.txt` ve `requirements-video-audit.txt` isteğe bağlıdır. faster-whisper küçük modeli yalnızca kullanıcı isterse bir kez önbelleğe indirilir; otomatik üretim bunu varsayılan olarak indirmez.

```bash
python -m pip install -r requirements-audio-audit.txt -r requirements-video-audit.txt
# Modeli yalnızca bu denetimi kullanmaya karar verirseniz önbelleğe alın:
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
```

## GitHub Actions

Repo: https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik

Actions > **Türk tarihi ücretsiz sesli Reels taslağı** > Run workflow > `malazgirt-1071`. Başarılı çalışma `tarih-sesli-reels-taslagi-N` adlı artifact üretir. Önce workflow testi ve Remotion TypeScript kontrolü çalışır.

Salı ve cuma 12:17 Türkiye saatinde taslak üretimi zamanlanır; GitHub zamanlaması gecikebilir. Bu zamanlama Instagram paylaşımı yapmaz.

## İsteğe bağlı ücretsiz LLM rol çağrıları

`ENABLE_20_LLM_AGENTS=1` ve uygun `OPENROUTER_API_KEY` birlikte verilirse her rol için `openrouter/free` yönlendiricisine bir çağrı yapılır. Varsayılan kapalıdır, bağımsız 20 ajan çalıştığı anlamına gelmez; kota veya hata durumunda ücretli modele geçilmez.

## Güvenlik kapıları

Yayımdan önce tarihî kaynaklar, görsellerin sahneye uygunluğu ve lisansları, sesin doğallığı ve altyazı gözle incelenmelidir. Piper sesi sentetiktir. `approval/approved.json` false kalır; Instagram otomatik yayın akışı bu görevde etkinleştirilmez.
