# Türk Tarihi Instagram İçerik Fabrikası v0.4 — Sıfır ücretli API

## Gerçekte neler var?
- `config/agents.json` içindeki **20 fonksiyonel rol**, tek Python sürecinde işler. Bunlar henüz 20 bağımsız LLM değildir.
- `scripts.auto_produce` otomatik: kaynaklı konu arşivi → taslak → 5 farklı özgün stilize canlandırma çizimi → **Piper Türkçe seslendirme** → SRT → özgün atmosferik enstrümantal ses → FFmpeg 9:16 video.
- İsteğe bağlı OpenRouter `openrouter/free` modeli, sadece **alternatif senaryo ÖNERİSİ** üretir; doğrulanmamış öneri doğrudan videoya girmez. GitHub Models kullanılmaz (2026'da kapatıldı).
- Altyazı zamanlaması **cümle bazında tahminidir**, doğrulanmış kelime hizalaması değildir.
- Çizimlerde gerçek tarihî görüntüler/foto-gerçekçi sahneler yoktur; 5 ayrı orijinal illüstrasyon vardır. Tam sinematik video için ayrıca lisanslı kayıt veya görsel/video modeli gerekir.
- **Instagram'a otomatik yayın yok**. İnsan tarih/telif/yaratıcılık onayı zorunlu. `OPENROUTER_API_KEY` zorunlu değildir. Ücretli AI API çağrıları sıfır.

## GitHub'a kurulum
Repo: `https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik`
Bu ZIP içindeki dosyaları repo köküne, mevcut dosyaların üzerine **değişiklikleri birleştirerek** yükle. `.github/workflows/produce.yml` eski sessiz taslak akışının yerine geçer. GitHub Work/Codex ile kod incelemesi, PR ve test yap. Hiçbir gizli anahtarı depoya commit etme.

GitHub > Actions > **Türk tarihi ücretsiz sesli Reels taslağı** > Run workflow. Konu `malazgirt-1071`. Çıktı `tarih-sesli-reels-taslagi-...` adlı artifact içinde `REVIEW_REQUIRED_REEL.mp4` olacaktır **yalnızca sesli üretim ve teknik kontrol başarılıysa**.

Salı ve cuma 12:17 TR saatinde taslak üretimi zamanlanmıştır; GitHub gecikme yapabilir.

İlk çalıştırmada Piper'ın yaklaşık onlarca MB Türkçe modeli indirilir, paket ve modelin güncel lisanslarına dikkat et. Ücretsiz altyapı ve kota şartları değişebilir. Kodun depoda olması yeterli değildir; **Actions'da başarılı bir çalışma gözlenmelidir**. İlk çalışma başarısızsa logları değerlendir.

## İsteğe bağlı LLM öneri ajanı
OpenRouter'dan ücretsiz kotaya sahip API anahtarı alınırsa GitHub > Settings > Secrets and variables > Actions > New repository secret kısmında `OPENROUTER_API_KEY` adıyla saklanır. Bu anahtar **varsayılan olarak zorunlu değil**. Koda yalnız `openrouter/free` yönlendiricisi yazılmıştır; fiyatlı model fallback'i yoktur. Yanlış tarihî bilgi yayımlamak yerine öneriler incelemeye bırakılır.

## Gelişim yolu
1. v0.4: otomatik illüstrasyon, çevrimdışı Türkçe TTS, ses yatağı ve MP4 (CI üzerinden çalışma **henüz doğrulanmadıysa** yayın hazır demeyin).
2. v0.5: lisans onaylı tarihî tablo/fotoğraf veritabanı, daha dramatik özgün sahneler, sahne seçimi; gerektiğinde ücretli görüntü modeli ve bütçe sınırı.
3. v0.6: Meta Instagram profesyonel hesabıyla doğrulanmış API, ayrı yayın onayı ekranı, güvenli token, paylaşım raporu. Instagram erişim belirteci ve kullanıcı onayı olmadan aktivasyon yapılmaz.

## Kaynaklar
- Piper: https://github.com/OHF-Voice/piper1-gpl
- Türkçe ses modeli: https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/dfki/medium
- OpenRouter ücretsiz yönlendirici: https://openrouter.ai/openrouter/free

## Instagram yayın bağlantısı (bilerek kapalı)
`instagram_publish_manual.yml` dosyası kod olarak hazırdır; kendiliğinden çalışmaz. Meta profesyonel hesap/API yetkisi, yayınlanacak MP4 için herkese açık HTTPS barındırma, `IG_ACCESS_TOKEN`, `IG_USER_ID`, GitHub `instagram-production` onay ortamı ve `approval/approved.json` dosyasında gerçek içerik onayı olmadan kullanılamaz. `approval/approved.json` varsayılan **false**. Bu sürümde hiçbir paylaşım yapılmadı.

Resmî Meta iki aşamalı container + media_publish akışına göre scaffold yazıldı; API sürümü ve onay/izinlerin canlı kurulum sırasında güncelliği yeniden kontrol edilmelidir.

## İsteğe bağlı gerçek 20 LLM görev yürütücüsü
`OPENROUTER_API_KEY` GitHub Secrets'a eklendiğinde ve Actions repository variable olarak `ENABLE_20_LLM_AGENTS=1` ayarlandığında `scripts/ai_agents.py` **20 ayrı ücretsiz model çağrısı** yapar. Ön tanımlı `0` olduğunda ayrı LLM çağrısı yok, yalnız 20 kod modülü çalışır. İlgili bağımsız rol önerileri `AI_AGENTS_STATUS.json` içinde saklanır ve tarihî doğruluk onayı olmadan videoya sokulmaz. Ücretsiz kotanın dolması hâlinde ajan hatayı kaydeder, **ücretli modele otomatik geçiş yapmaz**.
