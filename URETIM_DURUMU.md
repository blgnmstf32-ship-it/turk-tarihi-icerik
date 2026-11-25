# İki markalı üretim · sürüm devri

Temel sürüm, PR #1'in birleşim commit'i olan `9e15886`. PR'nin kalite iş akışı #77, 70 Python testi ve Remotion tip kontrolüyle geçti.

## Doğrulama akışı

- **Gemini · Model, bütçe ve Nano Banana doğrulaması** manuel çalışır. Önce faturalandırmasız anahtar ile Flash, Flash-Lite ve Gemma'yı doğrudan dener. Piri Reis kolu SHA doğrulamalı Charon sesini, 3D Atlas sahnesini, MP4'ü ve 10 kaynaklı sessiz hikâye kartını üretir. Hikâyelerin bu pilot sürümü yerel illüstrasyondur.
- Piri Reis doğrulaması geçerse, açık seçenek seçildiğinde tek bir Nano Banana 2 Lite Batch görseli istenir. Gönderimden önce ortak Git bütçe dalına rezervasyon yazılır. Çakışan rezervasyon ve başarısı belirsiz istek yeniden satın alınmaz. Batch beklerse aynı iş kimliğiyle tekrar sorgulanır.
- Çalışma raporlarında sağlayıcı erişimi, cache kullanımı ve çağrı sayıları ayrı kaydedilir. Google'ın proje limitleri AI Studio panelinden kontrol edilir. Kodun yerel eşikleri sağlayıcı tarafından garanti edilen kotalar değildir.
- Ücretli Nano Banana anahtarı yalnız görsel adımına verilir. Proje sahibi Google faturalandırmasını, harcama ve uyarı ayarlarını ayrıca kontrol eder. Uygulamadaki 18 USD fren yalnız bu kayıt defterinden geçen istekleri kapsar.
- 30 gün × 35 yeni görsel × $0,0168 = $17,64 yalnız görsel çıktısı. 768 giriş ve 64 ek metin token'ı için ayrılan muhafazakâr payla yaklaşık $17,7912. 31 günlük aynı hacim bu tahminle $18,38424 olur. Reddedilen veya belirsiz istekler de rezervasyonda kalır.
- Instagram otomatik paylaşımı kapalı ve insan incelemesi zorunludur.

## Hedef ve açık işler

Tarih 12.00, 16.00 ve 19.00; bakım 13.00 ve 20.00. Plan saati Europe/Istanbul. İki marka ve anlatıcıları `config/brand_profiles.json` içinde tanımlı. Güzelliğin başlangıç kadrosu ayrı dosyada. Tarih pilotu 1 Reels + 10 hikâyedir. Yeni markanın tam prodüksiyon akışı, beş Reels ve yirmi hikâyelik günlük tam paket, harici performans hesabı, üretim Batch zamanlayıcısı, sahne başına kalıcı görsel önbelleği ve uzun vadeli otomatik kaynak araştırması canlı entegrasyon testinden sonra tamamlanır. Tarih için mevcut haftalık çalışma açık kalır. Instagram yayınlama açılmaz.

## Güzellik inceleme örneği

`python -m scripts.beauty_studio --out output/iki-marka` 10 adet kaynaklı, sessiz yerel illüstrasyon kartı ve iki ayrı plan üretir. `--use-llm` açıkça seçilirse bakım kadrosundan gerekli rolleri aynı seçici koordinatöre yollar. Sessiz kartlar Nano Banana çıktısı olarak raporlanmaz. Model dosyasında cilt katmanları ve kıl yapısı şematik ve ölçek dışıdır. `blender -b -noaudio --threads 2 --python-exit-code 1 --python scripts/beauty_model.py -- --out output/iki-marka/bakim/3d --frames 30 --width 432` gerçek geometriden hareketli kamera kareleri üretir. Modelde üçüncü taraf varlık yoktur.

## Meta API hazırlığı

- Reels için `media_type=REELS`, `video_url`, açıklama ve isteğe bağlı `cover_url`. Hikâyeler için ayrı `media_type=STORIES` akışı ve görsel/video URL'si. Her gönderi `media_publish` öncesinde ayrı medya kapsayıcısına ihtiyaç duyar.
- Meta profesyonel hesap, doğru giriş türü, yayın izni ve Meta'nın okuyabildiği medya URL'si ister. Canlı hesap türü, izinler ve kapsayıcı oluşturma test edilmedi. Gönderim anahtarları bu pilot iş akışlarına geçirilmez.
- Takvim yerelde tutulur. Meta yayını ve yorum sabitlemesi bu aşamada taslak operasyonudur. İncelenen yorum API'sinde sabitleme ve ilk üst düzey yorumu gönderme doğrulanmadı.
- [Meta yayın belgeleri](https://developers.facebook.com/documentation/instagram-platform/content-publishing)
- [Meta medya oluşturma alanları](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media)
- [Meta yorum işlevleri](https://developers.facebook.com/documentation/instagram-platform/comment-moderation)
