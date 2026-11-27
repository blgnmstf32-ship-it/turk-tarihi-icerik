# 15D · Graphify, ECC ve token ölçümü

Kaynak depo `blgnmstf32-ship-it/turk-tarihi-icerik`. Başlangıç `f77323bbd9a07bb20235795e37032a4283933209`. [Graphify 0.9.121](https://github.com/Graphify-Labs/graphify/tree/0f22ae762e3e3d0b689fc7ad2b8192740628413b) Apache-2.0 ve pakette ayrıca belirtilen MIT bildirimleriyle. [ECC](https://github.com/affaan-m/ECC/tree/4adeee6732a12d1540f49a4d50a38ce8c97f9a53) MIT. Kaynak kodu ve paketler ayrı değerlendirildi.

## Ölçüm

| Navigasyon yolu | Beş sorgunun toplam çıktısı | Sorgu sürelerinin medyanları toplamı | Doğru kaynak yolları ve satırlar |
| --- | ---: | ---: | ---: |
| Belirlenmiş kaynak dosyalarını tam oku | 22.124 token | 0,088 ms | 8/8 |
| Önceden bilinen simgelerle hedefli `git grep` | 357 token | 18,111 ms | 8/8 |
| Graphify sorgusu, derinlik 1, yaklaşık 500 token bütçe | 2.747 token | 1.198,751 ms | 8/8 |

Tam kaynak okumaya göre azalma **%87,6**. Hedefli arama aynı sekiz konumu **2.390 token daha az** kullanarak buldu. Graphify çıktısı komşu simgeleri de getirdi. Örnekler Scene Director, Video Kalite Laboratuvarı, Tool Router, Registry ve sahne onarımı. Ölçümde `tiktoken 0.14.0 / o200k_base` kullanıldı. Sorgu süreleri her örnekte üç yeni çağrının medyanıdır. Çıkarım 5,137 sn, grafik 1.529.801 bayt. İndirme ve ilk kurulum ölçüme dahil değildir. Doğruluk, kaynak konumu doğruluğudur. API faturası, Work kotası ve model oturumunun tamamı bu ölçümün kapsamı dışındadır.

## Güvenlik ve çalışma biçimi

Graphify, Git'te kayıtlı ve izinli uzantıya sahip normal uygulama dosyalarının salt okunur kopyalarını inceler. Yapılandırma, ortam dosyaları, medya, bağımlılık klasörleri, belgeler ve sembolik bağlar alınmaz. Python ve diğer uygulama dosyaları çalıştırılmaz. Linux CI ağ ve kimlik bilgileri gerektiren hazırlığı, ağsız `--code-only` çıkarımdan ayırır. Çıkarım ve sorguda `GRAPHIFY_BACKEND=none` ve `GRAPHIFY_QUERY_LOG_DISABLE=1` kullanılır. PyPI tekerlekleri ve tokenizer sözlüğü SHA-256 ile sabitlenir. Sonuç depo, tam commit, sürüm ve SHA-256 ile doğrulanır. Araç kurulumları mevcut üretim sanal ortamından ayrıdır.

## ECC incelemesi

| Yetenek | Karar ve proje karşılığı |
| --- | --- |
| Memory Vault | Yerel Markdown, kapsam ve güven sınırı sağlıyor. `PROJECT_STATE.md` ve `HANDOFF.md` aynı devir ihtiyacını karşılıyor. Oturum geçmişi veya ikinci bellek deposu eklenmedi. |
| Continuous Learning | Oturum gözlemcisi kalıcı çalışma örüntüsü yazabiliyor. Eldeki doğrulanmış editoryal öğrenme ve test kanıtı korundu. Harici gözlemci ve otomatik kural terfisi kapalı. |
| AgentShield | Ajan ayarları, izin, hook, MCP ve sır taraması sunuyor. ECC kendi belgesinde önceden denetlenmiş ayrı çalıştırıcı istiyor. Mevcut Cisco Skill Scanner, Gitleaks ve iş akışı izin denetimi kullanılıyor. |
| Token Optimization | Küçük ve görev odaklı bağlam ilkesi Graphify sorgu bütçesi ve mevcut kayıpsız log düzeniyle uygulandı. Kanıt, kaynak ya da sağlık uyarısı elenmez. |
| Code Reviewer ve Architect | Kritik akışı kaynak satırından doğrulama, değişiklik yarıçapını ve alternatif yolu gözden geçirme ilkeleri alındı. Yeni uzman ve harici ajan profili eklenmedi. |
| TDD Guide ve Build Error Resolver | Bozulma kanıtını, test çıkış kodunu ve ham tanıyı koruma ilkesi mevcut sözleşmelerle örtüşüyor. Otomatik düzeltici ve yeni test altyapısı kurulmuyor. |

Work ortamında aynı CLI çalıştırıldı. Codex ve Gemini CLI için üst kaynak yerel kurulum ve ortak kod gezintisini belgeliyor. Entegrasyon bu proje için ortak komut satırı ve `AGENTS.md` kuralını kullanır. Etkileşimli Gemini modeli, ECC hook/MCP, GPU ve harici LLM yürütmesi kapsamda açılmadı. [Graphify kullanım belgeleri](https://docs.graphify.com/reference/overview) · [ECC uyarlama kılavuzu](https://github.com/affaan-m/ECC/tree/4adeee6732a12d1540f49a4d50a38ce8c97f9a53/docs)

## Kalıcı özel arşiv

28 Kasım 2026. [Kişisel GitHub arşivi](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik-graph) PRIVATE. Anonim REST sorgusu 404 döndürdü. [İlk gerçek koşuda](https://github.com/blgnmstf32-ship-it/turk-tarihi-icerik-graph/actions/runs/46078854325) CPU çıkarımı ve yazma işi başarıyla tamamlandı. `c3ed478d5f043022693911ed0b587d382cbe0b57` dizinindeki açılmış grafiğin SHA-256 değeri `78d6796962ec03182b1005802db78b9a6f11ac90853340beed3ae03e46a3527a`.

Arşiv her gün 03.17 Türkiye saati için planlanır. Özel depodan elle de çalıştırılabilir. Kaynak main dalındaki yeni ilk ebeveyn commit'leri sırayla ve koşu başına en çok 12 tane işlenir. Her commit bağımsız gzip ve provenance dosyası alır. Var olan içerik üzerine yazılmaz. `LATEST` son tamamlanan commit'i gösterir. Çıkarım kaynak projeyi çalıştırmadan, ağ ve sırlar kapalı olarak yapılır. Ayrı yazma işi yalnız arşiv deposunun kısa ömürlü GitHub Actions yetkisini kullanır. Sabitlenen Graphify çıkarıcısı güncellenirken özel işin sabit referansı ayrıca incelenir.

Geniş mimari sorularında Graphify, bilinen simge veya dosya için Git Grep kullanılır. İki yol da kritik bulguyu gerçek kod satırına bağlar.
