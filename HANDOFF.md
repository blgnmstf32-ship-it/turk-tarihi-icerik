# Çalışmayı devralma

Bu teslim, iki markanın doğrulanmış medya tabanını ve yeniden kullanım koşullarını kaydeder. [PROJECT_STATE.md](PROJECT_STATE.md) test sayıları, ölçümler ve açık işleri içerir.

## Başlangıç noktası

1. GitHub'daki güncel `main` dalını ve son commit'i kontrol et. `26c3b20`, medya kanıtının commit'idir. Daha yeni belge veya birleşim commit'i varsa güncel `main` üzerinden devam et.
2. Bu oturumdaki medya kanıtı [Actions 45828936221](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221). Başarılı kontrolü belgelerden dolayı yeniden başlatma. Normal Push/PR kalite akışı medya dışı Python testlerini, JS ve tip kontrolünü kapsar. Tam medya iş akışı `media-final-qa` dalında kendi YAML dosyası değiştiğinde veya manuel tetiklendiğinde çalışır. [Kalite akışı](.github/workflows/tests.yml) · [Medya akışı](.github/workflows/media_final_qa.yml)
3. `config/settings.json` içinde otomatik paylaşım kapalı ve insan onayı zorunludur. Kullanıcı yeni aşamayı açana kadar ücretli servis, yeni medya, yeni araç kurulumu ve günlük seri üretim bekler.

## Girdi ve çıktı yerleri

| Girdi veya kanıt | Konum |
| --- | --- |
| Piri Reis Charon WAV ve onay kaydı | `data/GEMINI_CHARON.wav` ve depo içindeki onay kaydı |
| Piri Reis 10 Wikimedia arşiv görseli, altyazı, atıflar ve önceki MP4 | [Actions 45649575775](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45649575775), `tarihin-bilinmeyen-gercekleri-4` |
| Güzellik önceki MP4 ve zamanlı altyazı | [Actions 45702177750](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45702177750), `beauty-reel-kuru-cilt-2` |
| Sulafat kaydı, Nano Banana görseli ve makbuzları | [Actions 45654042857](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45654042857), `beauty-sulafat-and-nano-assets` |
| Son ölçümler, her marka için final ve önce–sonra | [Tarih paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121762543) · [Güzellik paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121002356) |

Arşiv süresi dolduysa önce onaylı yedeği ve SHA-256 kayıtlarını bul. Eksik kaynağı raporla. Yeni ücretli görsel veya ses isteğiyle kendiliğinden ikame etme. Varlıklarla birlikte lisans, atıf ve kullanım hakkı kayıtlarını koru. Render işine sağlayıcı anahtarı verme.

## Kod haritası

- `scripts.final_media_qa` onaylı girdileri denetler, pilotları hazırlar ve karşılaştırma ölçümlerini yazar. `FINAL_QA.json` kalite sonuçları ve çıktı özetini, `PERFORMANCE.json` aşama bazında duvar saati, CPU süresi ve tepe süreç ağacı RSS değerlerini tutar.
- `scripts.auto_produce` tarih hattı, `scripts.beauty_reel` güzellik montajıdır. Tarih hattında `scripts.create_reel` Remotion görüntü ara çıktısını üretir. Anlatım ve müzik nihai FFmpeg miksine eklenir.
- `config/agents.json`, `config/beauty_agents.json`, `config/reels_playbook.json` ve `config/MULTI_LLM.md` uzmanları, editoryal eşikleri ve ortak ücretsiz sağlayıcı yönetimini açıklar.
- `media_pilot/ARACLAR.md`, `config/MOTION_TOOLKIT.md` ve `config/EDITORIAL_ANIMATION.md` lisans kayıtları, yerel araçlar, seçime bağlı modüller ve geri dönüş davranışını açıklar.

## Sonraki oturumda

1. Yeni render başlatmadan önce mevcut tam pilotları insan gözü ve kulağıyla incele. Piri Reis'te atıfları, temsili sahne etiketlerini ve altyazıyı kontrol et. Bakım videosunda cilt kesitinin temsili ölçeğini, iddiaların kaynak sınırlarını ve ses dengesini kontrol et.
2. Onaylı girdileri ve kaynak kayıtlarını koru. Sonraki kapasite deneyi ayrıca yetkilendirildiğinde 5 Reels ve 20 hikâyenin birlikte tamamlanma süresini, başarısızlıkları ve marka başına kaynak tüketimini ölç. Tek hikâye deneyiyle tam paket geçti sonucu verme.
3. Mevcut CPU derlemesinde libvmaf yoksa VMAF sonucunu boş bırak. Referans hizası doğrulanırsa gerçek ölçümü kaydet. Onay gelene kadar günlük otomasyonu ve Instagram paylaşımını devreye alma.

## Güvenlik denetimini devralma

- [Skill Security Actions](.github/workflows/skill_security.yml) önce hash'leri sabitlenmiş Linux araçlarını ayrı koşucu dizinine hazırlar. Ardından denetimi ve [altı regresyon testini](scripts/skill_security_contracts.py) dış ağ kapalı ve boşaltılmış ortamla yürütür. Cisco'nun LLM ve bulut bileşenleri ile NVIDIA'nın canlı değerlendirmesi devre dışıdır. Gitleaks açık kaynak CLI olarak çalışır.
- [Denetleyici](scripts/skill_security.py) Git'e kayıtlı Skill paketlerinden geçici bir tarama kopyası alır ve sembolik bağları reddeder. Raporda kural kimlikleri, dosya ve satır bilgileri kullanılabilir. Kod parçalarını ve olası anahtar değerlerini Actions loglarına veya PR yorumlarına aktarma.
- Yeni bir Skill'i eklerken önce metnini, yardımcı dosyalarını ve lisansını incele. PR kontrolünü görmeden Skill'i ya da kurulum betiğini çalıştırma. Cisco'nun yüksek ve kritik bulguları, depo komut politikası ve Gitleaks eşleşmeleri işi durdurur. Kurulum veya tarayıcı hatasında sonuç eksik kabul edilir. Açık kaynak sayfasına verilmiş bir bağlantı tek başına ağ komutu sayılmaz.
- [Gitleaks geçmiş istisnaları](config/gitleaks-history.ignore) doğrulanmış beş önbellek etiketiyle sınırlıdır. Yeni bir eşleşmede önce kaynağı incele. Gerçek anahtarsa iptal et ve erişimini yenile. Sırf kontrolü geçirmek için genel kural veya klasör istisnası ekleme.
- Güvenlik araçlarını güncellerken sürüm ve hash kayıtlarını birlikte kontrol et. Güvenlik testleri medya iş akışından bağımsızdır. Medya değişmedikçe 15 medya testinin son kanıtı Actions 45828936221'dir.

## Bağımlılık ve Actions denetimini devralma

- [Dependency Security](.github/workflows/dependency_security.yml) iş akışı PyPI ve npm açık kayıtlarını kullanır. Proje paketlerine ait Python wheel'leri yalnız çözümleme için okunur ve npm kurulum betikleri çalıştırılmaz. Üretim secret'ı bu işlere eklenmez. Ağ veya tarayıcı hatası başarılı tarama sayılmaz.
- [İzin denetimi](scripts/dependency_security.py) workflow düzeyinde salt okuma ve iş düzeyinde gerekçeli iki yazma alanı arar. Bir işin izin ihtiyacı değişirse önce tetikleyiciyi ve dal koşulunu incele. [Altı denetim testi](scripts/dependency_security_contracts.py) yetki yükseltme, gizli bilgi aktarımı ve onaysız paket kaynağı durumlarını kapsar.
- Dependabot önerileri PR olarak gelir. Medya veya üretim bağımlılığı değişirse birleştirmeden önce uyumluluk kontrolü yap. Denetim araçlarının karma sabitli dosyalarını güncellerken tekrarlanabilir wheel kurulumu ve ilgili tarama işini birlikte doğrula.
- İki yerel Skill açık dağıtım izni içermez. İzin doğrulanmadan açık kaynak lisansı atama. Bu kapsamda otomatik Instagram yayını açılmadı ve yeni medya üretilmedi.

## Terminal ve bağlam verimliliğini devralma

- Önce kısa Git durumunu al. Aynı devir belgelerini oturuma birden fazla kez eklemek gerekirse `python -m scripts.context_output notes PROJECT_STATE.md HANDOFF.md ...` kullan. Birebir aynı dosyaların tüm kaynak yolları görünür. Kopyalar arasındaki en küçük fark ayrı bölüm olarak kalır.
- Gerçek test çıkış koduyla `python -m scripts.context_output unittest LOG --exit-code KOD` çalıştır. Actions'ta `offline-quality-logs` paketinde hem ham hem önizleme dosyasını açabilirsin. Hata veya eksik bitiş kaydında tam log korunur. Önizleme aracı arızalanırsa ham log gösterilir ve iş başarısız olur.
- Sağlık uyarısı, kaynak/URL ve sayısal ölçüm kaybında değişikliği kabul etme. [Çıktı testlerini](scripts/context_output_contracts.py) medyasız çalıştır. Yerel token ölçümlerini yalnız ölçülmüş metin ve tokenizer ile birlikte bildir. Üretim ortamındaki kota ve faturalandırma için bu oranları kullanma.
- RTK veya Context Mode için global hook ve MCP kurulumu yapılmadı. GitHub Actions ve Work zaten yerel Python önizlemesini çalıştırır. Yeni bir ortamda Codex/Gemini CLI eklenti desteğini ayrıca doğrula.

## Skill Registry kullanımı

- Toplamı `python -m scripts.skill_registry --summary` ile, bir uzmanın JSON kaydını `python -m scripts.skill_registry --brand tarih --role 13` ile al. GitHub Actions veya başka Python kodu `registry_view("bakim", 20)` ile aynı veri görünümünü okuyabilir. Tam katalog için `registry_view()` kullan.
- Görev metnini ve uzman eşlemesini kendi kaynak kataloğunda güncelle. [Skill Registry yapılandırmasına](config/skill_registry.json) lisans, yerel adaptör, önkoşul, alternatif ve kanıt gibi ek alanları gir. Kimlikler ad alanı, depo ve beceri adından üretilir. İki marka aynı sayısal rolü paylaşabildiğinden tam uzman anahtarını kullan.
- `adapter` mevcut girişin belge kaydıdır. Çalıştırma izni mevcut üretim ve insan onayı kapılarında kalır. `historical_pass` yalnız bağlantılı eski gerçek çalıştırmanın kapsamını gösterir. `adapter_contract_only` medyasız denetimdir. VMAF ölçümü için destekli koşucu ve hizalı referans gerektiğinde yeni kanıtı ayrıca kaydet.
- Yeni ortak Skill için Codex ve Gemini CLI belgelerinde tanımlanan `.agents/skills/<ad>/SKILL.md` yolunu değerlendir. Dosya adı, lisans, içeriğin güvenlik incelemesi ve Cisco/Gitleaks PR sonuçları kontrol edilir. Mevcut eski Codex yolu korunur. Registry, editoryal uzmanlara tam dosyaları veya harici komutları aktarmadan ilgili kayıtları sağlar.
- Yeni video aracı veya Scene Director bu aşamada eklenmedi. Medya, ücretli API ve Instagram yayın akışları bu teslimin dışında kalır.

## Gemini bilgi kayıtları

- `python -m scripts.skill_registry --brand tarih --role 8` veya `--brand bakim --role 16` ile ilgili Gemini notlarını bul. JSON'da `gemini:` kimlikleri bilgi kaydıdır. Adaptörleri boştur ve çalışma yetkisi taşımazlar.
- Kayıtlar sabit Google revizyonuna ve ilgili belgeye bağlanır. Yenileme gerektiğinde upstream değişikliği ağsız Cisco ve Gitleaks kontrolünden geçir. Yalnız görevle ilgili bilgiyi Türkçe özetle. Ham Skill, kurulum komutu, uzak bağlantı, CLI ve SDK seçeneklerini otomatik etkinleştirme.
- Yeni model veya API sürümünü belge örneğinden üretime alma. Ücretsiz hesap erişimi ve mevcut kota kapıları ayrı doğrulanır. Sunucudaki bağlam önbelleği yerel SQLite yanıt önbelleğinden ayrıdır. Tarihte Charon ve bakımda Sulafat için önce onaylı kayıt kullanılır. Görsel ve medya servisi çağrıları önceki onay kapsamına bağlıdır.
- `python -m scripts.quality_checks` sekiz bilgi notunu ve 40 uzman eşleşmesini medyasız doğrular. Codex ve Gemini CLI uyumluluğu bu teslimde belge incelemesidir. Dış paketlerin canlı servis testi bu aşamaya dahil değildir.

## OpenMontage inceleme notlarını devralma

- `python -m scripts.skill_registry --brand tarih --role 11` veya `--brand bakim --role 20` ile ilgili `openmontage:` bilgi kayıtlarını bul. [Karşılaştırma](PROJECT_STATE.md#openmontage-karşılaştırması) kaynakları, açık noktaları ve lisans kararını tutar. Sekiz notun adaptörü boştur.
- Sahne kaydı daha sonra yetkilendirilirse önce bir medyasız taslakta kimlik, başlangıç karesi, süre, konuşma aralığı, görsel kaynak ve hak kaydı, seçilen ve gerçekleşen motor, dosya özetleri, hata nedeni ve inceleme durumunu tanımla. Planı, üretim komutunu, teknik sonucu ve insan onayını ayrı tut.
- Kaldığı yerden devam tasarımında değişen sahneyi ve bağımlılıklarını belirle. Başarılı varlığı yalnız hash, sürüm ve haklar eşleşirse yeniden kullan. Bir görsel değişiminde mevcut Charon ya da Sulafat kaydını ve onaylı altyazıyı koru. Etkilenen kesme ve senkronu yeniden doğrula.
- Kalite doğrulamasında çözünürlük, kare hızı, senkron ve ses düzeyini ayrı ölç. Kaynak, telif ve sağlık iddiası incelemesi ile yayın onayı ayrı kapılardır. Lisans veya sağlayıcı maliyeti engelinde işlem insan incelemesine gider. Bu aşama çalışma notunda kapanır.

## CineCode bilgi kayıtları

- `python -m scripts.skill_registry --brand tarih --role 13` veya `--brand bakim --role 20` ile ilgili `cinecode:` notlarına ulaş. Altı notun kaynakları sabit Git revizyonuna bağlıdır. [Karşılaştırma ve denetim](PROJECT_STATE.md#cinecode-karşılaştırması)
- Açık sahne kararında en az masraflı inceleme düzeyini seç. Kare ile karar verilemiyorsa zamanlama taslağı öner. Kesmenin iki yanını, ana ışığın gerekçesini, telefon boyutu okunurluğunu ve ortam sesinin geçişini zaman koduyla incele. Geçerli ses ve insan onayı kuralları aynı kalır.
- CineCode hook, betik ve şablonları bu notların parçası değildir. İnceleme için sağlanan referans klibi üretim varlığına dönüştürme. Yeni motor, sağlayıcı veya Scene Director ekleme yetkisi bu kayıtlardan gelmez.

## Instagram editoryal bilgi kayıtları

- `python -m scripts.skill_registry --brand tarih --role 6` açılış notunu, `--brand bakim --role 6` izinli rakip karşılaştırması notunu gösterir. Mevcut Reels uzman brifi eşleşen `instagram:` kayıtlarını ekler. Dokuz kaydın adaptörü boştur. [İnceleme ve kaynaklar](PROJECT_STATE.md#instagram-agent-skill-karşılaştırması)
- 5 açılış, 3 senaryo ve 85/100 eşiğiyle devam et. Konuşulan cümle, ekrandaki kısa metin ve ilk kare kanıtını ayrı denetle. Tahmini taslak süresi ile onaylı kayıttan ölçülen süreyi ayrı belirt.
- Rakip gözlemi, editoryal skor ve marka Insights girdisini aynı kanıt olarak kullanma. Oran için kaynağı, aynı yaş penceresini, geçerli paydayı ve örneklemi sakla. Erişilemeyen ölçüm bilinmiyor kalsın.
- `python -m scripts.quality_checks` medyasız sözleşmeleri doğrular. Üst paket bu projeye kurulmadı. Otomatik veri toplama, yorum, DM veya yayın ekleme yetkisi bu bilgi kayıtlarından gelmez.

## Merkezi yönlendirmeyi devralma

- Uzman brifi, `specialist_context(rol, marka, konu)` üzerinden ilgili `skill_notes` metinlerini ekler. Dört üst kaynağın göreve uygun kayıtlarını [Skill Router](scripts/skill_router.py) içindeki görev, sahne ve konu eşleşmelerinden izle. Bir not eklerken önce kayıt kimliği, rol eşleşmesi ve mevcut iki not/640 karakter sınırını kontrol et.
- Yerel araç için `run_tool(RouteContext(...), topic=..., state=...)` çağrısı yapılandırılmış bağlam alır. Arşiv veya katalog incelemesi için çağıranın onayladığı yerel metadata `snapshots` alanına araç kimliğiyle verilir. Ham model cevabı veya önerilen `media_tool` değeri yürütme girdisi olarak kullanılamaz. Ardışık çalıştırmada `selected`, `rejected`, `attempts`, `executed_adapter` ve `result` alanlarını kontrol et.
- Yeni bir bağlama gerektiğinde [Tool Router](scripts/tool_router.py) ve Registry girişi birlikte incelenir. Yalnız mevcut, kısa, güvenli ve doğrulanmış yerel işlem ekle. İşlev veya anahtar semantiği değiştiğinde ilgili önbellek anahtarını sürümle. Render, ücretli servis ve Instagram yayın kapıları kendi yerlerinde kalır.
- [Medyasız sözleşmeler](tests/test_skill_router.py) gerçek yerel dönüşümleri sentetik metin ve metadata ile çalıştırır. Ağsız kalite testi, Cisco, Gitleaks ve bağımlılık denetimlerini normal PR akışında doğrula. [Karar ve kapsam](PROJECT_STATE.md#skill-router-ve-tool-router)

## Scene Director'ı devralma

- `python -m scripts.scene_director --brand tarih --topic piri-reis-kayip-kaynak --out output/scenes/tarih` veya `--brand bakim --topic kuruluk-nemlendirici-zamani --out output/scenes/bakim` ile iki JSON dosyasını üret. Başka onaylı metin için aynı çağrıda `--topic-file` kullan. Tarih `narration`, güzellik `script` dizisini kullanır. Varsayılan zaman çizgisi tahmindir.
- `--overrides` JSON nesnesinin anahtarı 1 tabanlı anlatım satır numarasıdır. İsteğe bağlı `kind`, `source_numbers` ve `assets` alanlarını alır. Varlık kaydı `id`, `kind`, `source_number`, `sha256`, `license`, `attribution` ve doğrulanmış ticari kullanım beyanı taşır. Kaynak bağlamayı doğrulanmış iddia yerine koyma. Medya dosyası açılmaz.
- Bir sorun bildirildiğinde aynı plan ve çıktı dizininde `--failures` ile `{"s03":"renderer_unavailable"}` biçiminde dosya ver. Son raporun kimliği yerel `.scene-state.sqlite3` kaydına bağlıdır. Yeniden değerlendirilen sahneyi ve iki komşu sınırı kontrol et. Yaşayan makbuz, `selected_renderer` değerini plan olarak ve `executed_renderer` değerini `null` olarak saklar. Bu aşamadaki yerel ön ayar çağrısı ayrı alandadır.
- Kurgu değişimi gerekiyorsa ayrı Python ortamında [opsiyonel hash sabitli wheel'i](requirements-scene-otio.txt) kullan ve `--otio` ekle. `SCENE_TIMELINE.otio` içindeki klipler yer tutucudur. Bu dosya üzerinden otomatik medya bağlama veya render tetikleme yoktur. Mevcut Remotion, HyperFrames, Blender ve Three.js girişleri kendi yerinde kalır. [Mimari ve doğrulama](PROJECT_STATE.md#scene-director-ve-kurgu-zaman-çizelgesi)

## Genel güzellik Reels motoru

- Ağsız plan için `python -m scripts.beauty_reel --topic cilt-bariyeri-katmanlari --out output/bakim/bariyer` veya `python -m scripts.beauty_studio --reel-topic lazer-on-gorusme --out output/bakim/lazer` kullan. Katalogda ayrıca `nazik-cilt-bakimi`, `kozmetik-parfum-etiketi`, `nazik-sac-bakimi` ve `gunes-koruyucu-etiketi` var. `--otio` isteğe bağlı kare tabanlı kurgu planı ekler. Önceki pilotun `beauty_reel --assets` ve hikâyelerin `beauty_studio --date` çağrısı korunur.
- `--topic-file` girdisi `id`, `title`, altı kategori anahtarından birini içeren `category`, güvenilir yayıncı URL ve başlıklarını kimliğe bağlayan `sources` nesnesi ve `beats` dizisini alır. Her sahneye Türkçe `text`, kısa `heading`, `purpose` ve `references` kaynak kimlikleri ver. İlk sahne `hook`, son sahne `sources` olmalı. Arada konuya özgü `safety` sahnesi gerekir. [Örnekler ve kabul edilen kategoriler](data/beauty_reel_topics.json)
- Haricî bir görsel gerekiyorsa uygun sahnenin `visual` alanında yerel `file`, `source`, `attribution`, `license`, `sha256` ve `commercial_use_reviewed` alanlarını tut. Lisansın asıl kayıt ve eserle eşleşmesini ve gerektiğinde aynı lisansla paylaşım koşullarını insan doğrular. Görsel beraberinde bir ağ indirmesi gelmez.
- Gelecekte `--bundle PAKET` ile mevcut `SULAFAT.wav`, `CAPTIONS.json`, `REVIEW.json` ve varsa görsellerin eşleşmesini render başlatmadan doğrula. `CAPTIONS.json` dosyasında `language=tr`, `audio_sha256`, `script_sha256` ve bir tabanlı `line`, saniye cinsinden `start`, `end`, `text` alanları taşıyan `cues` dizisi bulunur. Zaman kodları dinlenmiş kayda ait olmalı. `REVIEW.json` dosyasında `voice=Sulafat`, `topic_sha256`, `script_sha256`, `audio_sha256`, `captions_sha256` ve gerçek insan incelemesinden sonra `human_approved`, `source_claims_reviewed`, `health_warnings_reviewed`, `visual_rights_reviewed` alanları gerekir. Konu ve senaryo özetlerini ilk plandaki `beauty` alanından al.
- Yerel renderı yalnız onaylı paket, boş çıktı dosyası hedefi ve mevcut Chromium ile açıkça `--render-approved /yerel/chromium` verildiğinde iste. Üretilen dosyanın biçim ve kapsam kontrolü sonra `BEAUTY_RENDER_REPORT.json` dosyasına yazılır. Bu aşamada verilen örnekler ve CI yalnız plan, yerel adaptör, altyazı metni ve zaman çizelgesini doğruladı. Görüntü kalitesini, telaffuzu ve gerçek altyazı eşleşmesini bir sonraki izinli render oturumunda incele. Instagram gönderimi için bu komut yetki vermez.

## Araştırma ve belge incelemesini devralma

- [Araştırma Registry kayıtları](config/research_registry.json) iki markanın trend ve kaynak uzmanlarına dört kısa yöntem notu taşır. `python -m scripts.skill_registry --brand bakim --role 5` ile kaynak doğrulama, `--role 7` ile trend notlarını gör. `research:trafilatura` yürütülebilir tek yeni bağdır. Başlık ve DOI, içerik üretiminde kullanılmadan önce asıl metne bakılır.
- Yerel HTML aracı gerektiğinde CPython 3.12 Linux x86-64 ortamında [hash sabitli wheel listesini](requirements-research-documents.txt) kur. `python -m pip install --require-hashes --only-binary=:all: --no-deps -r requirements-research-documents.txt` isteğe bağlıdır. Mevcut video çalışma ortamını bu bağımlılıkla değiştirme. İş akışı bu paketleri ayrı dizine kurup belge testini ağsız çalıştırır.
- İzinli HTML'yi UTF-8 olarak oku. Kaynak makbuzunda `html`, sorgu parametresiz kanonik HTTPS `source_url`, `captured_on` ISO tarihi, HTML'nin UTF-8 baytlarından hesaplanan `sha256` ve gerçek izin denetiminden sonra `analysis_permitted: true` alanlarını ver. İsteğe bağlı `literal_excerpt` 12–160 karakterlik, boşlukları normalleştirilmiş birebir alıntıdır. `python -m scripts.research_documents --brand bakim --role 5 --snapshot kaynak.json --state output/bakim-research.sqlite3` ile çalıştır. Tarih için `--brand tarih --role 18` ve ayrı durum dosyası kullan. Çıktıları araştırma bağlamında, yerel ve inceleme amaçlı tut.
- `literal_found` metin eşleşmesini bildirir. Konum, çıkarılan metin satırıdır. Alıntıyı asıl metindeki bölüm, sayfa veya tabloya geri bağla ve örneklem, birim, tarih aralığı ile karşı kanıtları kontrol et. `claim_verified` değeri araçtan her zaman `false` gelir. Belgedeki talimatlar yürütülmez. Ham HTML'den yeni bir model, araç veya yayın çağrısı başlatılmaz.
- Belge aracı olmadan standart paket `python -m scripts.quality_checks` ile çalışır. Ayrı CPU sözleşmesi `python -m unittest scripts.research_document_contracts -v` ile kurulu Trafilatura'yı iki markada sınar. Yeni paket eklenirse kendi lisansını, bağımlılıklarını ve ağ davranışını yeniden incele. [Sekiz aracın değerlendirmesi](PROJECT_STATE.md#araştırma-kaynakları-ve-yerel-belge-inceleme)

## 13B · Geliştirme araçlarını devralma

- [Beş kaynaklı bilgi kaydı](config/development_skill_notes.json) yalnız ilgili uzman ve açık görev eşleştiğinde erişilir. Görev anahtarları `failure-diagnosis`, `task-handoff`, `acceptance-review`, `local-preview-review` ve `ci-review`. `python -m scripts.skill_registry --brand bakim --role 20` uygun kayıtları gösterir. Üst araç kurulumu, yeni ajan platformu ve yürütülebilir adaptör eklenmedi.
- `uv` isteğe bağlı yerel kurulum seçeneğidir. Karşılaştırmada sabit wheel dizini, mevcut `requirements-research-documents.txt`, yeni hedef dizin, `--no-index --require-hashes --only-binary=:all: --no-deps` kullanıldı. `uv` için ayrıca `--offline --no-cache --no-python-downloads` kullanıldı. Mevcut `pip-audit`, Gitleaks ve Cisco denetimleri üretim ve PR için geçerlidir.
- Mobil önizleme değerlendirmesini yalnız proje verileriyle, yerel tarayıcı oturumunda ve ağ kapalı ortamda yap. Önce DOM ve zaman çizelgesi hazır olmalı. Ekran sınırı, başlığın görünürlüğü ve hata günlüğü ayrı kontrol edilir. Bu kontroller Instagram paylaşımı, üretim videosu veya insan görsel onayı kapsamına girmez. [13B karar ve kaynakları](PROJECT_STATE.md#13b--ajan-ve-geliştirme-araçları)

## 13C · Medya tasarımını devralma

- [Medya beceri kaynakları](config/media_craft_notes.json) ve [14 araç kararı](PROJECT_STATE.md#13c--sahne-tasarımı-animasyon-ve-ses-incelemesi) sabit kaynakları gösterir. `craft-review` ve `foley-review`, Scene Director sahnesinin `craft_review.visual_notes` ve `craft_review.foley_notes` alanlarını besler. Bu kayıtları mevcut yerel sahne hazırlığı ve insan tasarım incelemesinde kullan. Dosya indirme, Blender Python/MCP, dış harita ve ses araması için bilgi kayıtlarından yetki çıkarma.
- Bir mevcut videoda duraklama işaretlemek gerekirse önce salt okunur ses seviyeleri ve kaynağa hizalı söz/altyazı aralıklarıyla adayları oluştur. Genel Tool Router çağrısı `RouteContext(brand, 15, "pause-analysis")` ve `snapshots={"media-craft:pause-review": snapshot}` alır. JSON alanları `fps: 30`, `duration_frames`, `alignment: "reviewed_source_frame_alignment"`, `silence`, `narration`, `captions`. Son üçü başlangıç dahil, bitiş hariç özgün kare çiftleridir. Dosya yolu, ses ve zaman çizelgesi adaptöre verilmez.
- `human_review_candidate` yalnız bakılacak yeri gösterir. Sessizlikteki anlatı durakları, kelime sonları, müzik ve altyazı kararı aynı özgün zaman kodunda gözden geçirilir. Bu aşamada kurgu kesme, hız ayarı, altyazı yazma veya yeniden zamanlama yapılmaz. Sözleşmeler `python -m unittest discover -s tests -p test_media_craft.py -v` ile medyasız çalışır.

## Merkezi video kalite laboratuvarını devralma

- `python -m scripts.video_quality_lab --plan output/SCENE_PLAN.json --out output` iki marka için aynı raporu oluşturur. Kanıt alanları, yerel ölçüm girişleri, eşikler ve araç/lisans kararları [VIDEO_QUALITY_LAB.md](config/VIDEO_QUALITY_LAB.md) içinde.
- Kapsamlı teknik inceleme için mevcut ölçüm sonuçlarını `--evidence` ile aktar. `--existing-mp4` mevcut dosyayı yalnız siyah ve donmuş kare adayları için tarar. Ses/kontrast/altyazı/kesme ölçümleri ayrı kanıt ister. VMAF puanı yalnız aynı çıktıya bağlanan hizalı referansla alınır.
- Sınırlı sahne incelemesi için orijinal `--state` ve `--previous-report` değerini kullan. Raporu ayrı bir `--out` dizinine yazarak önceki Scene Director raporunu da saklayabilirsin. Gerçek Instagram gözlemleri geldiğinde yalnız yerel Meta arşiviyle `--performance` kullan.

## Onaylı iki pilotun gerçek render ve kalite raporları

- GitHub Actions `Media final QA · approved assets` işini isteğe bağlı başlat. Tarih, güzellik ve 15 ertelenen medya testini içeren tam Python paketi ayrı işlerde yürür. Medyasız Python paketi ayrıca çalışır. Önceki final dosyaları, onaylı girdi artefaktları ve CPU Whisper modeli sürüm/özet kontrolünden geçer.
- Sonuç artefaktlarında final MP4, kısa önce-sonra MP4, `FINAL_QA.json`, `PERFORMANCE.json`, `TOOL_VERSIONS.json`, `SCENE_PLAN.json`, `SCENE_EXECUTION_REPORT.json`, `SCENE_TIMELINE.otio`, `VIDEO_QUALITY_LAB.json`, `MEASUREMENT_EVIDENCE.json` ve kaynak/altyazı kayıtları bulunur. Yerel tekrar için `python -m scripts.final_media_qa --help`; `--previous` aynı markanın önceki onaylı tam artefakt dizinidir.
- Raporun teknik durumu, editoryal 85/100 eşiği, kaynak incelemesi ve Instagram performans durumunu ayrı oku. Görsel tekrar ve mobil okunabilirlik örnek kare kanıtıdır. Anlatıcı ile karışık ses arasındaki fark, ayrı miks kanallarının birebir seviye dökümü değildir. Aynı planın gerçek medya sorunları önce Scene Director'a yazılır. Otomatik kurtarma yalnız sınırlı görsel kusurları kapsar, diğer sorunlar insan incelemesinde kalır.
- İki markada yerel gerçek MP4 ile kare koruma testi yapıldı. Yeniden render edilen `s04` tarihte 44, güzellikte 60 kareydi. Kapsam dışındaki sırasıyla 1.984 ve 2.094 karenin çözümlenmiş özetleri kaynak MP4 ile eşleşti. Güzellik ASS bindirmesinde tamsayı kare saatini ve sabit 30 fps'yi koru.
- Son tam CPU render ve ölçüm kanıtı [45988740750 numaralı Actions çalıştırması](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45988740750). Önce-sonra süreleri ve iki ayrı artefakt bağlantısı [PROJECT_STATE.md](PROJECT_STATE.md#onaylı-iki-pilotun-üretim-doğrulaması) içinde. İki Reels de insan incelemesi durumunda. Piri Reis altyazı sapmalarını ve bakım pilotunun işaretlenen mobil örneğini değerlendirmeden yayın onayı verme.

## 15A.1 · Sınırlı pilot onarımı

- Son pilot girdisi [Actions 45988740750](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45988740750). `scripts.pilot_scene_repair` doğrulanmış 15A MP4’ünü, kalite raporunu, altyazıyı ve mevcut anlatıcıyı kullanır. Tam pilot renderı yerine yalnız işaretlenen altyazı aralıklarını yeniler. Tarih için onaylı kolaj, güzellik için onaylı görsel yeniden kullanılır. Sağlayıcı anahtarı gerekmez.
- GitHub CPU’da tekrar gerekirse [Approved pilot caption repair](.github/workflows/pilot_scene_repair.yml) manuel başlatılır. İş akışı sabit girdi paketlerini indirir ve Whisper dosya özetlerini denetler. Arşivler yoksa aynı SHA-256’ya sahip onaylı yerel kopyaları `python -m scripts.pilot_scene_repair --help` seçenekleriyle ver. Başarılı mevcut çıktı ve testleri tekrar üretme.
- `SCENE_EXECUTION_REPORT.json` hedef sahneleri, komşu geçişleri ve korunan kareleri taşır. `MEASUREMENT_EVIDENCE.json` mobil örnekleri ve kesme noktalarını, `VIDEO_QUALITY_LAB.json` teknik kapıları doğrular. Final ancak tüm altyazılar eşleştiğinde ve başlangıç sapmaları 350 ms’yi aşmadığında, mobil örnekler ve geçişler geçtiğinde, kapsam dışı kareler ve AAC akışı korunduğunda kabul edilir.
- Son indirme kopyaları `Piri_Reis_15A1.mp4` ve `Nemlendirici_15A1.mp4`. [Proje durumu](PROJECT_STATE.md#15a1--onaylı-pilotların-altyazı-onarımı) ölçümleri ve özetleri kaydeder. İnsan incelemesi sürüyor. Instagram otomatik paylaşımı kapalı.

## 15B · Kapasite koşusunu devralma

- Günlük işletim hedefi iki marka toplamında 2 Reels ve 20 sessiz hikâye. 3 tarih ve 2 güzellik Reels yalnız kapasite iş yüküdür.
- Ayrı bir çıktı diziniyle `python -m scripts.capacity_15b --out output/capacity-15b` çalıştırılabilir. Mevcut Python gereksinimleri, `psutil==7.2.2`, sabit `requirements-scene-otio.txt`, FFmpeg ve ffprobe kullanılır. Koşu onaylı medya ve yayın komutlarını çağırmaz.
- `CAPACITY_15B.json` gerçek PNG, engelli Reels, sessiz MP4 simülasyonu ve API sayaçlarını ayrı tutar. `PERFORMANCE.json` duvar saati, CPU-sn ve örneklenen süreç ağacı RSS değerlerini taşır. Her Reels klasöründe kaynak kaydı, uzman brifi, Scene Director kararı, OTIO ve video kalite raporu bulunur.
- `SILENT_SIMULATION.mp4` 70 saniyelik görsel iş yükü kaydıdır. Eşleşen onaylı Charon veya Sulafat dosyası, onaylı zamanlı altyazı, gerekli görsel hakları ve tam kalite incelemesi geldiğinde normal üretim girişini kullan. Mevcut 15A.1 sahne onarımını ve kalite eşiklerini koru. Instagram otomatik paylaşımı kapalı kalır.

## 15C · Konuşan fotoğraf denemesini devralma

- 15C için adayların kod, ağırlık, kota ve ticari kullanım kayıtları [AVATAR_15C.md](AVATAR_15C.md) içinde. Önce bu raporun CPU sonucu ve girdi özetlerini kontrol et. Ditto denemesi ayrı bir değerlendirme koşusudur. Üretim görevine otomatik motor seçimi eklenmedi.
- Tarih testinde yalnız arşivdeki hak kaydı bulunan Sokollu minyatürü ve mevcut Charon kesiti kullanıldı. Görselde kişi adı, kaynak, modern anlatım ve **YAPAY ZEKÂ TEMSİLİ · TEMSİLÎ CANLANDIRMA** ibareleri yer alır. Sokollu minyatürünü Piri Reis'in portresi olarak sunma. Gerçek kişide görseli ve sesi canlandırmaya yönelik izin kapsamını kaydet.
- Yeniden değerlendirmede her çalıştırılan ağırlığın özetini ve lisansını sabitle. Render girdilerini dış ağsız ve sağlayıcı anahtarsız koşucuya ver. Ücretsiz bir Space ancak uygulamanın erişimi, veri işleme koşulları ve kota uygunluğu doğrulanırsa değerlendirilir.
- Sicil ve yönlendirici kaydı için gerçek medya üzerinde yeterli dudak/fonem eşleşmesi, yüz bütünlüğü, doğal mimik ve baş pozu kanıtı gerekir. 1080×1920 ve 30 fps son medya sözleşmesini, mevcut kalite eşiklerini ve Scene Director'ın sahneye özgü onarımını koru. Ücretli çağrı ve Instagram otomatik paylaşımı kapalı.

## 15D · Kod grafiğiyle devralma

- Önce `git rev-parse HEAD` ile tam commit'i bul. [Graphify kaydında](GRAPHIFY_15D.md) anlatılan commit bağlantılı grafik ve provenance dosyasını kullan. `python graphify_project.py verify --out GRAFIK_DIZINI` içeriği doğrulamıyorsa aynı commit'te yerel ağsız çıkarım al.
- Geniş kaynak okumadan önce `python graphify_project.py query --out GRAFIK_DIZINI --question "modül ve simge"` çalıştır. Sonucun kaynak yolu ve satırını doğrula. Kesilmiş sorgu veya tek kesin simge için hedefli `git grep` kullan. Model sağlayıcı, oturum kayıtçısı, MCP ve hook açma.
- [CPU işi](.github/workflows/graphify.yml) standart Linux koşucusunda kilitlenmiş Python tekerlekleri ve doğrulanmış `o200k_base` sözlüğü kullanır. Kamuya açık işte yalnız sayısal ölçüm raporu yüklenir. Birleşim öncesi kalite, bağımlılık ve içerik güvenlik taramaları da geçmelidir.
- ECC inceleme ilkeleri için [15D raporuna](GRAPHIFY_15D.md) bak. Kurulum betikleri, otomatik Memory Vault ve Continuous Learning akışları mevcut görevlerle çalıştırılmaz.
