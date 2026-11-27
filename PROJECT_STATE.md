# Proje durumu

26 Kasım 2026. Türkçe tarih ve güzellik Reels taslakları için son doğrulanmış medya tabanı `26c3b2055ab856f5018bc9b850118c1d929b95d0`. Devralırken güncel `main` dalını esas al. Bu commit, aşağıdaki medya kanıtlarının üretildiği sürümdür.

## Korunan altyapı

| Alan | Durum |
| --- | --- |
| Uzmanlar | Tarih ve güzellik için 20'şer ana rol. Tarih yapılandırmasında ayrıca dört yardımcı 3D görev modülü bulunur. Genel Yayın Yönetmeni konuya göre uzman seçer. |
| Multi-LLM | Gemini → Cloudflare Workers AI → OpenRouter Free. Ortak önbellek, kota, sınırlı tekrar ve başarısız görev kuyruğu korunur. Cloudflare yazılım sınırı 9.000 nöron/gün, OpenRouter sınırı 40 deneme/gün. NVIDIA NIM ve Groq kapalı. [Yönlendirme ayrıntıları](config/MULTI_LLM.md) |
| Editoryal öğrenme | Her pilotta render öncesinde 5 açılış ve 3 senaryo değerlendirildi. Eşik 85/100. Piri Reis 86, güzellik 100 aldı. Bu puan editoryal indekstir. Kaynak, lisans ve insan onayı ayrı kapılardır. [Araştırma](config/REELS_ARASTIRMASI.md) · [Kurallar](config/reels_playbook.json) |
| Ses ve görsel | Tarihte onaylı Charon, güzellikte onaylı Sulafat. Güzellikte mevcut Nano Banana görseli, tarihte 10 arşiv görseli ve atıfları kullanıldı. Piper kullanılmaz. |
| Render ve denetim | Remotion, HyperFrames, Three.js, GSAP, Blender, FFmpeg, Faster Whisper Small CPU INT8, Earshot, CC0 uisfx, OpenCV ve PySceneDetect iki pilotta ilgili işlerde doğrulandı. Real SFX tasarımından yararlanıldı. Üst depo betikleri çalıştırılmadı. [Araçlar ve lisanslar](media_pilot/ARACLAR.md) · [İsteğe bağlı araçlar](config/MOTION_TOOLKIT.md) · [Animasyon](config/EDITORIAL_ANIMATION.md) |
| Yayın ve maliyet | Otomatik Instagram paylaşımı kapalı, insan onayı zorunlu, ücretli servisler kapalı. İki markalı günlük seri üretim yetkilendirilmedi. Mevcut haftalık tarih taslak takvimi ayrı bir akıştır. |

## Kayıtlı medya doğrulaması

[Actions 45828936221](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221) üç başarılı iş içerir. 128 medyasız Python testi ve 15 medya testi toplam **143/143** geçti. JavaScript **2/2**, Remotion tip kontrolü başarılı. Render iki Linux CPU işinde, 4 mantıksal çekirdek ve yaklaşık 16 GiB RAM ile yapıldı. Render adımı yalnız yerel döngü arayüzüne erişebildi. İki rapor 0 ücretli çağrı ve otomatik yayın kapalı sonucunu verir. Her final MP4'ün SHA-256 özeti arşivdeki `FINAL_QA.json` ile eşleşti. İki final de 1080×1920, 30 fps, H.264/AAC ve `human_review_required` durumundadır.

| Ölçüm | Tarih · Piri Reis | Güzellik · Nemlendirici için doğru an |
| --- | ---: | ---: |
| Süre | 67,60 sn | 71,80 sn |
| Ana render duvar saati / CPU süresi / tepe süreç ağacı RSS | 285,00 sn / 288,79 CPU-sn / 4.090 MiB | 133,75 sn / 339,47 CPU-sn / 1.805 MiB |
| Özel sahneler | HyperFrames kolajı 17,46 sn, kesintisiz Three.js/GSAP Atlas kamerası, 2 yerel 2.5D kâğıt katmanı | Blender cilt kesiti 36,28 sn ve 96 kare, İki Three.js/GSAP makro sahnesi 14,41 ve 14,80 sn |
| Türkçe ASR kelime hata oranı, önce → sonra | %7,75 → %7,04 | %4,17 → %4,17 |
| Ortalama altyazı başlangıç farkı, önce → sonra | 96,0 → 66,4 ms, 25/25 eşleşme | 16,2 → 17,9 ms, 47/47 eşleşme |
| Gerçek ses tepesi, önce → sonra | −1,23 → −4,19 dBTP | −0,81 → −1,27 dBTP |
| PySceneDetect belirgin kesmeler, önce → sonra | 2 → 4 | 5 → 5 |
| OpenCV örnek kare keskinlik göstergesi | 2.473,882, aynı | 1.440,492, aynı |
| VMAF | Ölçülmedi, libvmaf yok | Ölçülmedi, libvmaf yok |

Ortalama altyazı farkı ASR zamanlarıyla karşılaştırıldı. OpenCV göstergesi estetik puan değildir. PySceneDetect yalnız sabit eşikte bulduğu kesmeleri sayar. Her marka için özgün çizimli 5 saniyelik Remotion animasyonu ayrı çıktı olarak oluştu. Piri Reis 2.5D katmanları elle tasarlandı. Depth Anything V2 çıkarımı ve dış GeoJSON harita katmanı bu çalıştırmada kullanılmadı.

- [Tarih Actions paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121762543) · [Güzellik Actions paketi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik/actions/runs/45828936221/artifacts/15121002356)
- İki pakette `FINAL_QA.json`, `PERFORMANCE.json`, tam MP4 ve `ONCE_SONRA.mp4` bulunur. Tarih paketinde arşiv atfı ve ayrı HyperFrames klibi de vardır. Actions saklama süresi 14 gündür.

## Açık işler

- İki pilotun insan editör tarafından görüntü, telaffuz, ses dengesi, tarihsel doğruluk ve güzellik iddiaları açısından son onayı.
- Günlük 3 tarih ve 2 güzellik Reels ile 20 hikâyenin birlikte gerçek yük deneyi. Ölçülen montaj, foley ve miks süreleriyle, aynı girdi tipleri için tek koşucuda yaklaşık 21 dakika hesaplanır. Bu tahmin araştırma, kaynak indirme, yeni anlatım, tekrarlar ve incelemeyi kapsamaz. Hikâye ölçümü marka başına tek yerel tasarım örneğidir.
- VMAF ancak libvmaf destekli bir makine ve hizalı referans bulunduğunda ölçülebilir. Freesound ticari işte kapalıdır. İsteğe bağlı araçların durumu ve lisansları [katalogda](config/MOTION_TOOLKIT.md) kayıtlıdır.
- Actions giriş paketlerinin süresi dolmadan onaylı dosyalar, özetleri ve kaynak/izin kayıtları kalıcı erişimde tutulmalı. Uygulama adımları [HANDOFF.md](HANDOFF.md) içindedir.

## Skill ve gizli bilgi güvenliği

26 Kasım 2026. [Skill Security Actions](.github/workflows/skill_security.yml), PR'larda ve `main` dalına gönderimlerde üretimden ayrı çalışır. Cisco Skill Scanner 2.3.2, Git'e kayıtlı `SKILL.md` paketlerini statik ve davranışsal analizle denetler. Depo kuralları yaygın dış bağlantı komutlarını, özyinelemeli silme ve kabuğa borulanan komutları ek olarak engeller. Gitleaks 8.30.1, geçerli commit'ten erişilen Git geçmişini tarar. NVIDIA SkillEvaluator 1.2.1 değerlendirildi. Statik taramaları mevcut kontrollerle örtüştüğü ve canlı değerlendirme ayrı sağlayıcılar ile çalışma ortamı gerektirdiği için eklenmedi.

Taramalar ve altı güvenlik testi ağsız Linux ağ alanında çalışır. Skill dosyaları veri olarak okunur. Üretim API anahtarları tarayıcılara verilmez. Beş eski Actions önbellek etiketi, içerikleri doğrulandıktan sonra yalnız ilgili geçmiş eşleşmenin kimliğiyle istisna edildi. Statik denetim tek başına bir Skill'in güvenliğini garanti etmez.

- [Cisco 2.3.2 ve Apache-2.0 lisansı](https://pypi.org/project/cisco-ai-skill-scanner/2.3.2/) · [NVIDIA 1.2.1 ve Apache-2.0 lisansı](https://github.com/NVIDIA/SkillEvaluator/tree/v1.2.1) · [Gitleaks v8.30.1 ve MIT lisansı](https://github.com/gitleaks/gitleaks/tree/v8.30.1)

## Bağımlılık ve Actions izin güvenliği

26 Kasım 2026. [Dependency Security Actions](.github/workflows/dependency_security.yml) PR, `main` gönderimi ve haftalık tetikleyicide çalışır. Mevcut Cisco ve Gitleaks iş akışı korunur.

| Araç | Depodaki karar |
| --- | --- |
| pip-audit 2.10.1 | Linux/Python 3.12 için, beş uygulama gereksinim dosyasının ortak çözümü ve iki karma sabitli tarayıcı listesi PyPI açık kayıtlarına göre taranır. Uygulama paketleri kurulmaz. Sabit Git revizyonlu Earshot'ın kayıtlı PyPI bağımlılıkları çözülür. Earshot kaynak kodu bu taramanın kapsamında değildir. [PyPA](https://github.com/pypa/pip-audit) |
| npm audit | Ana proje ve `media_pilot` kilitleri, paket kurmadan ve yaşam döngüsü betiği çalıştırmadan npm kayıt hizmetine karşı denetlenir. [npm belgeleri](https://docs.npmjs.com/cli/v11/commands/npm-audit/) |
| Dependabot | Pip, iki npm dizini ve GitHub Actions için haftalık güncelleme PR'ları yapılandırıldı. Karma sabitli iki denetim listesi elle güncellenir. [Ayarlar](.github/dependabot.yml) · [GitHub belgeleri](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) |
| Trivy | Bağımlılık ve gizli bilgi taramaları mevcut araçları tekrar eder. Kapsamda yayımlanan konteyner veya Kubernetes yoktur. Eklenmedi. [Trivy](https://github.com/aquasecurity/trivy) |
| Semgrep CE | Uygulama kodu için SAST sunar. Bu aşamanın kapsamı bilinen bağımlılık açıkları ve Actions izinleri. Harici kural paketi yüklenmedi. [Semgrep](https://github.com/semgrep/semgrep) |
| OpenSSF Scorecard | Depo uygulamalarını ve izinleri puanlar. Bu ihtiyaç, puan yayınlamayan ve yazma yetkisi istemeyen yerel Actions izin denetimiyle karşılandı. Eklenmedi. [OpenSSF Scorecard](https://github.com/ossf/scorecard) |

Başlangıç npm raporunda ana kilitte 16 paket bulgusu, Python raporunda Pillow 12.3.0 için 42 açık kaydı vardı. Remotion ailesi 4.0.547, Zod 4.6.7 ve Pillow en az 13.0.0 sürümüne alındı. Son taramalarda her iki npm kilidi ve seçilen Python bağımlılıklarında bilinen bulgu kalmadı. Uygulama kaynak kodu ve mevcut 40 uzman korunur. Bu aşamada medyasız Python, JavaScript ve tip kontrolü çalıştırıldı. Yeni sürümlerle 15 medya testi ile üretim tekrarına girilmedi.

19 iş akışı izin açısından denetlenir. Kullanılmayan üç işin depo yazma yetkisi kaldırıldı. İki kayıt işinin `contents: write` yetkisi olay ve iş koşuluna bağlı olarak dar kapsamda kalır. Günlük üretim çağrısı adlandırılmış sır alanlarıyla sınırlıdır ve onaylı demo bunları almaz. Bağımlılık işi yalnız okuma izniyle ve sağlayıcı anahtarları olmadan çalışır.

Depo geçmişi ve iki Skill klasöründe açık lisans kaydı bulunamadı. Her iki Skill alanı `LicenseRef-No-License-Granted` olarak kaydedildi. Bu kayıt mevcut lisans durumunu belirtir ve yeni dağıtım izni vermez. [GitHub lisans açıklaması](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) · [Agent Skills alan tanımı](https://agentskills.io/specification#license-field)

## Bağlam ve terminal çıktısı

26 Kasım 2026. [Yerel çıktı aracı](scripts/context_output.py) üçüncü taraf hook, MCP sunucusu, model veya API kullanmadan Python ile çalışır. [Kalite iş akışı](.github/workflows/tests.yml) başarılı unittest kayıtlarını gruplandırır ve tam logu yedi gün saklar. Başarısız ve tamamlanmamış loglar olduğu gibi gösterilir. Kaynaklar, URL'ler, sayısal değer taşıyan satırlar, sağlık uyarıları ve tanılama metni korunur. Aynı devir belgesinin birebir kopyaları yalnız açık dosya listesi üzerinde bir kez gösterilir ve tekrarların dosya yolu kalır.

| Araç | Lisans, platform ve karar |
| --- | --- |
| RTK OSS 1.2.1 | Ölçülen OSS paketi Apache-2.0. Tam sürümün motoru ayrıca BUSL-1.1. Codex ve Gemini CLI hook desteği üretici belgesinde var. Bağımsız CLI, Actions koşucusunda da çağrılabilir. Work içinde SHA-256 doğrulanmış ikiliyi yalnız tekil komutlarda telemetri kapalı denedik. `rtk test` görünümü tanılama, URL, sayısal ölçüm ve sağlık uyarısı bulunan deneme bloklarını göstermedi. Hook kurulmadı. [RTK](https://github.com/rtk-ai/rtk/tree/v1.2.1) |
| Context Mode 2.2.4 | Elastic License 2.0. Ücretsiz yerel MCP ve SQLite araması ile ayrı abonelikli Gateway sunar. Codex ve Gemini CLI entegrasyonları belgelidir. Çalıştırma aracı host kullanıcısının dosya ve ağ yetkileriyle çalışır. Bu depoda veya Work'te MCP, hook ve Gateway kurulmadı. Actions'ta test edilmedi. Belgelenen verimlilik üreticinin iş yüküne aittir. [Context Mode](https://github.com/mksglu/context-mode/tree/v2.2.4) |
| Planning with Files | MIT. Codex ve Gemini CLI desteği var. Markdown devir notları CI içinde de okunabilir. Otomatik yeniden ekleme hook'ları ek bağlam ve kalıcı durum yaratır. Mevcut PROJECT_STATE ve HANDOFF aynı ihtiyacı karşılıyor. [Planning with Files](https://github.com/OthmanAdi/planning-with-files) |
| Graphify | Apache-2.0. Codex/Gemini CLI eklentileri ve Actions'ta çalışabilecek yerel kod ayrıştırması bulunur. Karma belge ve medya dizininde çıkarım sağlayıcı kullanabilir. Kod gezinmesine yarar. Test logu denetimi için eklenmedi. [Graphify](https://github.com/Graphify-Labs/graphify) |
| Caveman | Apache-2.0. Codex ve Gemini CLI'de kısa yanıt tarzı ve yerel proxy seçenekleri belgelenmiş. Actions test logu için gereken birebir kanıt koruma koşulu doğrulanmadı. Proxy ve model yönlendirmesi eklenmedi. [Caveman](https://github.com/JuliusBrussee/caveman) |
| LLMLingua | Kod MIT, kullanılan model ağırlığı ayrıca incelenmeli. Yerel Python kitaplığı Actions'ta çağrılabilir. Bu sürüm için yerleşik Codex/Gemini CLI adaptörü doğrulanmadı. Model tabanlı metin elemesi kelime ve bağlam kaybına yol açabileceğinden kanıt loglarında kullanılmadı. [LLMLingua](https://github.com/microsoft/LLMLingua) |

Yerel ölçüm `88ba142` tabanındaki çalışma kopyasında, aynı girdiler kuyrukta tekrar kullanılarak yapıldı. `tiktoken 0.14.0 / o200k_base` yalnız metin gövdesini saydı. Bu sayım hesap kullanım limitini veya Codex/Gemini'nin gerçek oturum tüketimini ölçmez.

| Örnek | Ham → seçilen görünüm (bayt) | Ham → seçilen görünüm (token) | Token azalması |
| --- | ---: | ---: | ---: |
| Aynı çalışma ağacında `git status` → `git status --short --branch` | 300 → 104 | 71 → 22 | %69,0 |
| Gerçek 128 medyasız unittest kaydı | 22.388 → 4.104 | 5.138 → 986 | %80,8 |
| Önceki PROJECT_STATE ve HANDOFF belgelerinin ikişer kopyası | 34.820 → 17.566 | 9.905 → 4.997 | %49,5 |

Aynı test logunda RTK görünümü 25 token, kısa Git durumu 22 token kullandı. Ayrı bir güvenlik örneğinde yerel araç dört kanıt işaretinin tamamını korudu. RTK'nın doğrudan `test` görünümünde dördü de görünmedi. Altı regresyon testi ve yapay çıkış kodu 7 üzerinden CI kabuğu deneyi uygulandı. Hata çıkış kodu ve iki ham çıktı dosyasının bayt eşitliği doğrulandı. [Tokenizer](https://github.com/openai/tiktoken)

## Uzman beceri ve araç envanteri

26 Kasım 2026. [Skill Registry](config/skill_registry.json) ve [Python okuyucusu](scripts/skill_registry.py), orijinal hareket kataloğu, beceri indeksi, profesyonel medya seçenekleri, Reels rehberi ve iki uzman kadrosunu bir araya getirir. Çözümlenen envanter 113 kayıt içerir. 85 bilgi kaydı, 27 araç kaydı ve bir varlık referansı vardır. Araç grubundaki Freesound kapalıdır. Bilgi grubunda 65 dış hareket becerisinin 40 yerel uyarlaması ve 25 referans kaydı, iki yerel Skill, 11 editoryal yöntem ve yedi kaynak incelemesi bulunur. Tarih ve bakım için 20'şer ana uzman ve tarih için dört yardımcı 3B görev, marka ve sayısal rol kimliğiyle eşleşir. Tarih Genel Yayın Yönetmeni hâlâ ayrı koordinasyon akışındadır.

Kayıtlar görevi, marka ve rol kapsamını, kullanım koşulunu, kod/varlık/ağırlık lisans bilgisini, güvenlik durumunu, donanımı, servis maliyetini, mevcut adaptörü, uygunsa alternatif aracı ve kanıt kapsamını taşır. Ücretsiz maliyet kaydı varsa hizmet ücretini anlatır. Koşucu ve donanım kullanımını kapsamaz. Alternatif, elle değerlendirilen bir kayıt bağıdır. Uzman seçimi aynı araç adları ve izin listesiyle sürer. Python okuyucusu hiçbir adaptörü çalıştırmaz. Uzman isteminde yalnız mevcut göreve ait aynı yöntem ve seçenek metni kullanılır.

Test durumunda eski gerçek CPU çalıştırması, medyasız adaptör sözleşmesi, statik güvenlik taraması, katalog kaydı ve kullanılamayan araç birbirinden ayrılır. Örneğin VMAF son medya koşucusunda kullanılamadı. Depth Anything V2 Small için ağırlık denetimi geçerli, model çıkarımı doğrulanmış olarak görünmez. AnimeFX üst paketinin incelemesi ile yerel açılış adaptörü farklı kimliklere sahiptir. Real SFX kaynak metni ve gerçek yerel ses efekti çalıştırması da ayrı kayıttır. Yeni medya ve canlı sağlayıcı çağrısı bu aşamada yapılmadı.

Agent Skills standardı, klasör adıyla eşleşen bir `name` ve kısa `description` içeren `SKILL.md` ile başlar. YAML alanları ile ayrıntılı açıklamalar ihtiyaç olduğunda okunur. Standart deposunun kodu Apache-2.0, belgeleri CC BY 4.0 lisansındadır. Yerel Skill lisansları önceki kayıtlarıyla korunur. Codex ve Gemini CLI, depo kökündeki `.agents/skills` yolunu belgeler. Mevcut ortak Skill orada kullanılır, eski `.codex/skills` kaydı kendi yerinde korunur. Yeni paket, kopya, sembolik bağlantı, kurulum veya otomatik araç yetkisi eklenmedi. CLI keşfi belgelerden doğrulandı. Bu oturumda etkileşimli CLI oturumu açılmadı. [Standart](https://agentskills.io/specification) · [Standart deposu](https://github.com/agentskills/agentskills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/)

Sekiz medyasız regresyon testi, marka ayrımını, 40 ana uzmanı, hareket kayıtlarını, önceki uzman araç seçenekleriyle eşitliği, kanıt kapsamını, dosya ve komut güvenliğini ve CLI'nin JSON çıktısını denetler. Cisco Skill Scanner, Gitleaks ve ham/özet kalite logu düzeni korunur.

## Google Gemini Skills incelemesi

27 Kasım 2026. Google'ın yayımladığı `google-gemini/gemini-skills` deposu `c4d0c62c1240e08a90546186bf320600ab6a039a` revizyonunda incelendi. Codex paket bildirimi 2.8.0 sürümünü ve kök lisans Apache-2.0 kapsamını gösterir. Bu lisans depo içeriğine aittir. Gemini hizmetinin kota, fiyat ve veri koşulları ayrıdır. Depo Google tarafından yayımlanır ancak README, resmî ürün desteği sunulmadığını belirtir. [Sabit kaynak](https://github.com/google-gemini/gemini-skills/tree/c4d0c62c1240e08a90546186bf320600ab6a039a) · [Lisans](https://github.com/google-gemini/gemini-skills/blob/c4d0c62c1240e08a90546186bf320600ab6a039a/LICENSE)

| İncelenen paket | Karar ve tarama sonucu |
| --- | --- |
| `gemini-api-dev` | API, modele karar verme, yapılandırılmış JSON, bağlam, önbellek, multimodal inceleme, TTS ve görsel üretim için sekiz özgün Türkçe bilgi notu eklendi. Cisco yalnız `MANIFEST_MISSING_LICENSE` bilgi bulgusu verdi. Lisans kökten doğrulandı. SDK kurulum komutları, otomatik model yükseltme, sunucuda konuşma saklama ve yönetilen ajan örnekleri aktarılmadı. |
| `gemini-api-cli` | Üç yüksek Cisco bulgusu (`PIPELINE_TAINT_FLOW` iki, `CORRELATED_NETWORK_EXECUTION_FLOW` bir) ve iki yerel komut kuralı eşleşmesi oluştu. Araç, ağdan kurulum betiğini kabuğa aktarıyor ve mevcut kota/anahtar denetimini kullanmıyor. Kurulmadı veya çağrılmadı. Bu ayrı API istemcisi, etkileşimli Gemini CLI ile aynı program değildir. |
| `gemini-live-api-dev` | Gerçek zamanlı ağ oturumu ve ses akışı mevcut metin incelemesini veya onaylı anlatıcı akışını karşılamıyor. Cisco yalnız eksik frontmatter lisansı bilgi bulgusu verdi. Envantere çalıştırılabilir paket eklenmedi. |
| `gemini-omni-flash-api` | Medya yükleme ve üretim betikleri bulunuyor. Cisco bilgi seviyesinde lisans alanı ve düşük seviyede bildirilmemiş ağ hedefi buldu. Betikler çalıştırılmadı. |

Dört paket ve yardımcı dosyalar ağsız statik taramada yalnız veri olarak açıldı. Gitleaks, incelenen dış dosyalarda bulgu vermedi. Sonuçlar kurulum onayı anlamına gelmez. Yerel depodaki Skill taraması ve geçmiş sızıntı denetimi ayrı sürer.

[Skill Registry](config/skill_registry.json) 121 kayda ulaştı. Yeni sekiz kayıt yalnız bilgi türündedir ve 40 ana uzmanı marka ve görevlerine göre kapsar. Kayıtlarda kaynak revizyonu, lisans kapsamı ve Google belgeleri görünür. Medyasız sözleşme testi bu eşleşmeyi doğrular. Mevcut uzman istemi, sağlayıcı sırası ve önbellek kimliği değişmedi. Gemini, Cloudflare ve OpenRouter kotaları ile Charon ve Sulafat ses akışları önceki yapılandırmadadır. Ücretli anahtar kullanımı ve yayın kapısı registry'den açılamaz.

Google’ın Codex paket yolu kaynakta belgelenir. Gemini CLI, güvenilen çalışma alanında ortak Agent Skills dizinini destekler. Bu depoda dış paket iki istemcide de kurulmadı veya etkinleştirilmedi. GitHub Actions, registry’nin Python okuyucusunu ve yerel güvenlik taramalarını kullanır. Canlı API, eklenti kurulumu, örnek medya üretimi ve dosya yükleme denenmedi. [Google geliştirici belgeleri](https://ai.google.dev/gemini-api/docs/coding-agents) · [Gemini CLI keşfi](https://geminicli.com/docs/cli/using-agent-skills/)

## OpenMontage karşılaştırması

27 Kasım 2026. OpenMontage `2e003e65fa99a0f329478a2c1cdcf26bc481933a` revizyonunda araştırıldı. Mimari belgeler, sinematik işlem tanımı, yönetmen ve gözden geçiren yönergeleri, kontrol noktası ve önbellek kodu ile kompozisyon seçimi incelendi. Aşağıdaki tasarım notları mevcut Türkçe projeye özgüdür. Çalışan Scene Director veya sahne yeniden üretim sistemi bu aşamada eklenmedi. [Sabit kaynak](https://github.com/OpenMontageInc/OpenMontage/tree/2e003e65fa99a0f329478a2c1cdcf26bc481933a)

| Alan | OpenMontage’da görülen | Bizde mevcut ve sonraki tasarım kararı |
| --- | --- | --- |
| Otonom üretim | Kodlama ajanı YAML aşamalarını ve Markdown yönergelerini okuyup Python araçlarını çağırır. Çıktı ve onay kayıtları üzerinden ilerler. | `auto_produce` ve `beauty_reel` belirli iş yollarını yürütüyor. Ajan kabuk yetkisi yerine aşama teslimlerine girdi, sorumlu, çıktı ve kontrol durumu eklemeyi tasarla. |
| Uzman koordinasyonu | Yürütücü yapımcı aşama yönetmenlerine görev verir. İnceleme sonucuna göre kabul, düzeltme veya önceki aşamaya dönüş önerir. | `ai_agents` marka ve role göre seçili uzman önerilerini topluyor. Ortak kota korunarak teslimin tek sahibi ve bağımsız kontrolü belirtilmeli. Aynı kaynak veya görevi her uzman yeniden işlememeli. |
| Sahneye göre araç seçimi | Araç keşfi Python modüllerini içe aktarır. Seçiciler yetenek, erişilebilirlik, maliyet ve kalite sinyallerine göre sağlayıcıları sıralar. | Mevcut `media_tools`, `motion_toolkit` ve registry izin listeleri kullanılır. Bir sahnenin amacı, hazır yerel araç, lisans, süre ve güvenli alternatif önceden yazılabilir. Dinamik dış modül keşfi ve ücretli sağlayıcı seçimi kapsam dışı. |
| Storyboard ve sinematik plan | Senaryo ritimleri kaynak görüntüye, ana kadraja, kamera hareketine ve geçişe bağlanır. Backlot yerel bir izleme panosu sunar. | `reels_editorial` ve `three_scene` konu ve animasyon planı sağlıyor. Eksik olan, her sahne için tek kimlik altında kaynak/iddia, anlatım aralığı, kadraj, hareket, altyazı ve geçiş kaydı. Ayrı pano bu aşamada kurulmadı. |
| Çoklu render | Tek kompozisyon tercihi plan aşamasında belirlenir. Remotion, HyperFrames ve FFmpeg rotaları bilinir. Beklenmedik motor değişimi denetlenir. | Remotion ana kurgu, HyperFrames yerel klip, Blender ve Three.js sahne üretimi ve FFmpeg son miks olarak kalır. `auto_produce` ve `beauty_reel` geri dönüşlerini planlanan ve gerçekleşen yol olarak kaydetmek tasarlanabilir. |
| Görüntü, ses ve animasyon | Varlık ve montaj kayıtları sahne bağı, müzik, geçiş ve senkronu birbirine bağlar. | Mevcut onaylı Charon ve Sulafat, altyazı ve miks akışı korunur. Sahne değişikliklerinin hangi zaman aralıklarını etkilediği aynı zaman çizelgesinde kaydedilebilir. |
| Başarısız üretim | Son geçerli aşamadan devam ve görsel işi ilgili uzmana geri gönderme belgelenmiş. İncelenen revizyonda tüm sahneler için otomatik, genel bir yeniden üretim mekanizması doğrulanmadı. | Yerel 3B→2B geri dönüşü var. Yeni tasarım, yalnız hatalı sahneyi ve etkilenen geçişleri işaretler. Görsel, ses veya lisans değişirse bağlantılı kontroller yeniden yapılır. Yetki veya kaynak sorunu otomatik tekrar edilmez. |
| Önbellek ve kalite | Yeniden üretilebilir tek çıktı araçlarının içerik tabanlı önbelleği ve aşama şema denetimi var. Önbellek makineler arasında eşitlenmiyor. | Onaylı ses özetleri, SQLite editoryal önbellek, `release_check` ve `final_media_qa` var. Eksik olan sahne düzeyinde girdi/ayar/çıktı özeti ve hak ile QA kanıtını birlikte doğrulayan yeniden kullanım kararı. |

### Lisans ve güvenlik kararı

Kök lisans GNU AGPL v3. Bölüm 4–6, lisans kapsamındaki yazılımın dağıtımında bildirimlerin, lisans metninin ve dağıtım biçimine uygun karşılık gelen kaynak kodun sağlanmasını düzenler. Bölüm 13, değiştirilmiş bir sürüm ağ üzerinden kullanıcılarla etkileşiyorsa bu kullanıcılara ilgili sürümün kaynak koduna ücretsiz ve görünür erişim sunulmasını ister. Üçüncü taraf varlıklar, fontlar, medya ve araç bağımlılıkları ayrıca lisans incelemesi gerektirir. Dosya veya kod birleştirmesi için uyumluluk kararı verilmedi. Bu teslimde üst projenin kodu, betiği, şeması, metni, varlığı ve bağımlılığı aktarılmadı. [Üst depo lisansı](https://github.com/OpenMontageInc/OpenMontage/blob/2e003e65fa99a0f329478a2c1cdcf26bc481933a/LICENSE) · [Lisans metni ve bölümler](https://opensource.org/license/agpl-3.0)

Ağsız Cisco taraması örnek olarak dört paket üzerinde çalıştı. `ai-video-gen` ve `create-video` paketlerinde üç orta HTTP POST bulgusu ve toplam 11 yerel ağ komutu eşleşmesi görüldü. Üç bilgi bulgusu eksik Skill lisans alanına ilişkindi. `character-animation-qa` bulgu vermedi. Seçilen dört paket dosyasında Gitleaks bulgusu yoktu. Sabit dış depo revizyonunun sığ geçmiş taramasında 26 kalıp eşleşmesi vardı. Bunlar örnek, test ve bir araç dosyasında görünür. Kimlik bilgisi olarak geçerlilikleri sınanmadı ve bu dosyalar aktarılmadı. Üst depo çalıştırılmadı veya bağımlılıkları kurulmadı. Yerel proje güvenlik iş akışları ayrıca çalışır.

[Skill Registry](config/skill_registry.json) 129 kayıt içerir. `openmontage:` kimlikli sekiz özgün bilgi notu 40 ana uzmana görevlerine göre bağlandı. Kayıtlar sabit kaynak ve lisans kapsamı taşır. Medyasız testler eşleşmeyi ve çalıştırma sınırını doğrular. Mevcut render ve metin sağlayıcı yolları, ücretsiz kota, ses profilleri ve yayın kapısı aynı yapılandırmayı kullanır.

## CineCode karşılaştırması

27 Kasım 2026. `sarpstar/cinecode` deposu `c8a3e7552699360a2b0142c9620882af2069eedb` revizyonunda incelendi. Kaynaklar arasında Quick ve Film Mode yönergeleri, kamera ve kurgu, sahne bitirme, animatik, ses tasarımı, referans analizi, kalite kontrolü ve hook zinciri var. Karşılaştırma statik incelemeye dayanır. CineCode veya üst depo testleri çalıştırılmadı. [Sabit kaynak](https://github.com/sarpstar/cinecode/tree/c8a3e7552699360a2b0142c9620882af2069eedb)

| Konu | CineCode yaklaşımı | Bu projeye eklenen fark |
| --- | --- | --- |
| Quick Mode, Film Mode ve önizleme | Quick tek HTML üzerinde kısa bir kart, seçili kareler ve taslak kullanır. Film, yol haritası, senaryo, stil karesi ve animatikle daha fazla karar doğrular. | Mevcut Remotion ve HyperFrames önizleme yolları için seçim ölçütü kaydedildi. Bilinen biçim ve düşük belirsizlikte iki temsilî inceleme karesi yeterli olabilir. Tempo veya senkron belirsizse daha ayrıntılı zamanlama taslağı seçilir. OpenMontage storyboard ve aşama onayları yeniden tanımlanmadı. |
| Sinematik kamera, 3B ve geçiş | Zaman tabanlı Canvas ve Three.js hareketleri, odağın iki düzlem arasında devri, J/L kesmeler ve yönü/hızı eşleşen hareketli kesmeler kullanır. | Mevcut Three.js ve GSAP yollarındaki kamera zaten kareye göre deterministik. Yeni not, kesmenin iki yanında ekran yönünü, konu konumunu, algılanan hızı ve bulanıklığın sınırını denetler. Yeni kamera motoru veya 3B render yolu eklenmedi. |
| Işıklandırma ve kompozisyon | Işık kaynağı, temas gölgesi, alan derinliği ve sis/parlama sahnenin ihtiyacına göre seçilir. | Blender ve Three.js için gerekçeli ana ışık ve okunur silüet. Remotion ve HyperFrames harita, etiket, altyazı ve ürün grafiğinde okunurluğu düşüren bitirme efektleri kapalı önerilir. |
| Katmanlı ses | Ortam, olay sesi, müzik ve anlatım ayrıdır. Ortam sesi görüntü kesmesinden önce başlayabilir veya sonra devam edebilir. Sahne düzeyi ses sapmaları ayrıca incelenir. | Mevcut FFmpeg miks, ducking ve ses hedefleri korunur. Yeni bilgi notu oda sesi geçişini ve sahne düzeyinde dinlemeyi önerir. CineCode’un −14 LUFS ve −1 dBTP hedefi projeye uygulanmadı. Charon ve Sulafat korunur. |
| Referans video | Süre, ritim, plan uzunluğu, palet ve ses biçimi ayrı ölçülür. Gözlemden bir biçim tercihi çıkarılır. | Hakları uygun mevcut bir referans için zaman kodlu ölçü ile özgün kurgu kararı ayrı yazılır. Optik benzerlik veya popülerlik kanıt sayılmaz. Kaynak kare, ses, metin veya benzer tanınabilir plan kopyalanmaz. |
| Render öncesi kalite | Film Mode animatikte zamanlamayı inceler. Örnek kareler ve taslaktan belirli anları ayıran kısa inceleme, finalden önce yararsız düzeltmeyi azaltır. | Mevcut `reels_editorial` ile `final_media_qa` arasındaki inceleme için kritik kesmenin iki yanı, açılış, en zayıf an ve telefon boyutunda okunurluk notu. Bu aşamada önizleme veya medya üretilmedi. |

Kök `LICENSE` MIT kapsamındadır. MIT, kopya veya önemli bölüm dağıtıldığında telif ve izin metninin korunmasını ister. Lemo Opuscar’dan gelen parçaların ayrı bildirimi ile font, HDRI, müzik, stok ve ekran görüntüsü koşulları ayrıca kontrol edilir. Registry için Türkçe, özgün uyarlamalar yazıldı. CineCode kaynak dosyası, şablonu, fontu veya medya varlığı aktarılmadı. [MIT lisansı](https://github.com/sarpstar/cinecode/blob/c8a3e7552699360a2b0142c9620882af2069eedb/LICENSE) · [Varlık notları](https://github.com/sarpstar/cinecode/blob/c8a3e7552699360a2b0142c9620882af2069eedb/references/assets-and-licences.md)

Ağsız Cisco testi, üst deponun `SKILL.md`, `references`, `scripts`, lisans ve test iş akışı örneğini taradı. 102 bulgunun 32’si yüksek veya kritikti. Yerel komut kuralları ayrıca iki ağ komutu eşleşmesi verdi. Bunlar statik tarama bulgularıdır. Sabit revizyonun sığ Git geçmişi Gitleaks bulgusu vermedi. `UserPromptSubmit`, `PreToolUse` ve `Stop` hook’ları ortamı aktaran Node/Python zinciri ve dosya keşfi içerir. Hook, `guard.py`, ağdan varlık alan betikler ve CDN bağımlı şablonlar kurulmadı. Proje bağımlılık taraması mevcut kendi kilit ve gereksinimleri üzerinde çalışır.

[Skill Registry](config/skill_registry.json) 135 kayda ulaştı. Altı yeni `cinecode:` notu tarih için 14, bakım için 16 ilgili uzmana bağlanır. 40 ana rol ve dört yardımcı 3B görev korunur. Bilgi notları adaptör, ücretli servis veya yayın yetkisi taşımaz. Remotion, HyperFrames, Blender, Three.js, GSAP, Gemini, Cloudflare ve OpenRouter akışları korunur. Scene Director bu aşamada geliştirilmedi.
