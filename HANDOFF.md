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
