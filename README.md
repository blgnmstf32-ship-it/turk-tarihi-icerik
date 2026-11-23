# Türk Tarihi — 20 Görevli Düşük Maliyetli İçerik Fabrikası

**Sürüm 0.3 — kaynaklı taslaklar + ses/görsel varlıkları sağlandığında video montajı. Otomatik seslendirme veya sinematik AI sahnesi üretimi ve Instagram yayını henüz bağlı değil.**

Bu proje Türk tarihinden kaynak bağlantısı bulunan bilgileri Instagram için **1080×1350 gönderi**, **3 adet 720×1280 sahne**, **yayınlanmaması gereken sessiz slayt önizlemesi**, **seslendirme metni**, **caption**, **storyboard**, **kaynakça** ve **20 görev kayıtlı üretim raporu** olarak hazırlar.

**ÖNEMLİ: Önceki sessiz slayt videosu kullanıcı kalite beklentisini karşılamadı; video artık açıkça `SESSIZ_SLAYT_ONIZLEME_YAYINLAMA.mp4` adıyla etiketlenir. Üretim kaydında `ready_for_instagram: false` ve `mp4: null` olur. Yayınlanabilir Reels oluşturulduğu iddia edilmez.**

**20 ajan, bu sürümde 20 ayrı yapay zekâ modeli ya da eş zamanlı sohbet değildir. **20 işlevsel uzman modülü** aynı ucuz Python iş akışı içinde çalışır. İlk sürüm hiçbir ücretli API çağrısı yapmaz. İçerik özgün, ücretsiz tipografik şablonla oluşturulur; sahnelerde gerçekçi savaş hareketi/AI video üretimi **henüz yoktur**.

## Sesli Reels üretimi: ÜCRETSİZ kurgu aşaması

`scripts/create_reel.py` en az **5 birbirinden farklı ve kullanma hakkı olan tarihî görsel**, **20–60 saniyelik Türkçe seslendirme** ve **gerçek senkronlu SRT altyazı** dosyasını alıp 9:16 MP4 hazırlar. Kamera kaydırması/zoom ve altyazı yakma FFmpeg ile ücretsiz yapılır. Bu araç görüntüleri ya da sesi kendi başına uydurmaz veya üretmez; kalite için önce gerçek medya gerekir.

```bash
python -m scripts.create_reel \
  --scenes media/malazgirt/scenes \
  --voice media/malazgirt/speech.wav \
  --subtitles media/malazgirt/subtitles.srt \
  --out output/malazgirt/reel.mp4

python -m scripts.release_check \
  --video output/malazgirt/reel.mp4 \
  --voiceover media/malazgirt/speech.wav \
  --subtitles media/malazgirt/subtitles.srt \
  --scenes media/malazgirt/scenes
```

**Uyarı:** `release_check.py` ses kanalını kontrol eder, gerçek insan konuşması olup olmadığını veya tarihî doğruluğu otomatik doğrulamaz. Bir yayının uygunluğuna insan karar verir.

## İş akışı

```text
Kaynaklı konu arşivi (data/topics.json)
           |
  1–5: Konu ve kaynak kayıt denetimi
           |
  6–10: Senaryo, açıklama, seslendirme
           |
  11–15: Poster, sahneler, MP4 (Pillow + FFmpeg)
           |
  16–20: QA, telif notu, insan onayı, rapor
           |
   GITHUB ACTIONS ARTIFACT (7 gün)
           |
    İNSAN TARAFINDAN GÖZDEN GEÇİR
           |
  Instagram'a manuel yükle (API entegrasyonu sonraki aşama)
```

Her aşama aynı GitHub Actions işinde çalışır. Sunucu kiralamaya gerek yoktur. Github Actions özel depoda hesabın planının dahil olan ücretsiz kotasını kullanabilir. Kodlar, taslak içerik fikirleri ve kaynak URL'leri depoda durur; **Instagram kimlik bilgilerini ve tokenları depoya koymayın**.

## Kullanım

Python 3.11+ ve FFmpeg kurulu bir terminalde:

```bash
python -m pip install -r requirements.txt
python -m scripts.run --topic malazgirt-1071 --out output/malazgirt
python -m unittest discover -s tests -v
```

`--skip-video` ile yalnızca görsel, metin ve sahne üretilebilir. Konuyu boş bırakırsanız o haftanın sıradaki içeriği seçilir.

### Telefonla GitHub kurulumu

1. `github.com` hesabınla giriş yap, yeni **Private** repository aç (`turk-tarihi-ajans` gibi).
2. Bu ZIP dosyasını aç. Dosyaları **klasör yapısıyla** depoya yükle. GitHub telefon arayüzünde çoklu klasör yükleme zor olursa GitHub Codespaces tarayıcı editörü veya Codex'in repo bağlantısından yararlan. **ZIP'i tek dosya olarak yüklemek Actions'ı kurmaz.**
3. Repo > **Actions** > **Türk tarihi taslak üretimi** > **Run workflow**.
4. Çalışma sonunda Actions ekranındaki `tarih-yayin-taslagi-...` artifact'ini telefona indir. İçinde post, video ve metinler bulunur.
5. **Kaynakları açıp her cümleyi kontrol et.** Tarihî yanılgı ve telif riski yoksa manuel olarak Instagram'da paylaş.
6. Otomasyon için `.github/workflows/produce.yml` dosyası Salı ve Cuma günleri Türkiye saatiyle **12:17**'de taslak oluşturacak şekilde ayarlanmıştır. GitHub zamanlayıcısı kesin dakika garantisi vermez.

### GitHub'a taşımada önemli ayrıntı

Bu paket üzerinde tüm dosyalar bulunur ancak **GitHub'da yeni depo açma ve dosya yükleme otomatik yapılmadı.** Kaynak kodu GitHub'a yüklenene kadar telefon kapalıyken otomasyon çalışmaz. Hesap bağlantısı ve izinler ayrıca gerekli olabilir.

## İçerik politikası

- Her bilgi en az bir kaynak URL'sine bağlanır; gerçek kaynak metninin insan tarafından okunması zorunludur.
- Kaynak URL'sinin biçimsel kontrolü, URL içeriğinin bağımsız doğrulanması **değildir**.
- Rekonstrüksiyon görselleri 'tarihî canlandırma' olarak tanımlanır; eski fotoğraf veya belge gibi sunulmaz.
- Tarih hakkında farklı yorumlar varsa bağlam notu korunur; belirsizlik gizlenmez.
- Başka kullanıcıların Reels videoları veya telifli arşiv fotoğrafları izinsiz kopyalanmaz.
- Kamuya otomatik yayın **kapalı**; Instagram API, gizli token ve onaylı içerik barındırma bağlantıları eklendikten sonra ayrıca açılabilir.

## Maliyet

- Python, Pillow, FFmpeg: ücretsiz açık kaynak yazılımlar.
- Buradaki 20 modülde: **0 ücretli yapay zekâ çağrısı**.
- GitHub Actions: hesabın ve depo tipinin dahil olduğu ücretsiz kota içinde 0 TL; kotanın aşılması veya depolama/artifact kullanımında ücret doğabilir.
- Gerçekçi hareketli yapay zekâ video, ücretli seslendirme, profesyonel ses/müzik ekleme ve yüksek hacim, sonraki aşamaya bırakıldı.
- Bu sürümün maliyet sınırı `config/settings.json` dosyasında **0 TL ücretli API** olarak sabittir.

## Geliştirme yol haritası

1. **v0.1 (hazır)**: 20 rol, kaynaklı beş konu, post, sessiz slayt önizlemesi (yayınlanamaz), altyazı yerine metin sahneleri, açıklama, arşiv, zamanlama ve testler.
2. **v0.2 (hazır)**: Ses içermeyen örnek video yayın için reddediliyor; yayına geçiş kontrolü var.
3. **v0.3 (hazır, sınırlı)**: Haricî sahne görsellerini, tamamlanmış seslendirmeyi ve SRT dosyasını ücretsiz FFmpeg ile MP4 hâline getiren modül. Otomatik AI sahne ve TTS üretimi sonraki aşamada.
4. **v0.4 (plan)**: Ekonomik AI sahneleri, Türkçe TTS, altyazı senkronlama ve telif güvenli müzik; ayrıca doğrulanmış kaynak kontrolü.
5. **v0.5 (plan)**: Meta'nın profesyonel Instagram API'siyle onaylı yayın; performans takibi ve içerik planlama.

## Yeni prodüksiyon şartı

`YENI_VIDEO_BRIFI_MALAZGIRT.md` ve `VIDEO_KALITE_STANDARTLARI.md` dosyalarını uygula. Sesli anlatım, canlı/illüstratif sahneler ve gerçek montaj tamamlanmadan Reels hazır kabul edilmez. `scripts/release_check.py` yalnızca teknik minimumları kontrol eder, insani kalite değerlendirmesinin yerini almaz.

## Kaynak örnekleri

- TDV İslâm Ansiklopedisi (Malazgirt Muharebesi): https://islamansiklopedisi.org.tr/malazgirt-muharebesi
- TDV İslâm Ansiklopedisi (İstanbul): https://islamansiklopedisi.org.tr/istanbul
- TBMM tarihçe: https://tbmm.gov.tr/history
- Atatürk Araştırma Merkezi (Cumhuriyet): https://atam.gov.tr/cumhuriyetimizin-99-yili-kutlu-olsun/

Dosyadaki örnek cümleler kaynağa dayanarak taslak olarak hazırlanmıştır. Paylaşmadan önce URL'leri açıp teyit etmekten sen sorumlusun.
