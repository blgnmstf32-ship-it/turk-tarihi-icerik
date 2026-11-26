# Reels araştırması ve editoryal kararlar

Kaynak incelemesi 26 Kasım 2026, İstanbul. Yürütülebilir rehber `reels_playbook.json` içinde. Aşağıdaki tercihler 100 puanlık editoryal modelin girdisidir. Puan iç kalite ölçüsüdür. Reel başarısı izleyici ve dağıtım verisiyle ölçülür.

## Instagram ve akademik dayanak

| Kaynak ve kapsam | Uygulama ve sınır |
|---|---|
| [Meta, Instagram Best Practices](https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/) | Dikkat, Reel süresi, etiketler ve takipçi büyümesi için profesyonel panelde hesap bazlı rehber var. Evrensel süre veya hashtag formülü çıkarma. |
| [Meta, Trial Reels](https://about.fb.com/news/2024/12/trial-reels-try-content-non-followers-first-see-what-perfoms-best/) ve [Edits](https://about.fb.com/news/2025/04/introducing-edits-streamlined-video-creation-app/) | Açılış ve uzunluk gibi bir seferde tek değişkeni incele. İzlenme, etkileşim ve varsa erken atlama oranını gerçek veriden al. Trial Reels paylaşıma açılır, bu projede insan onayı dışında çalışmaz. |
| [Meta, 2026 dağıtım güncellemesi](https://about.fb.com/news/2026/01/2026-ai-drives-performance/) | Meta, ABD'de artan özgün içerik payını raporladı. Kendi çekim, anlatım ve analizi ekle; ABD sonucunu Türkiye kotası veya sabit sıralama ağırlığı olarak kullanma. |
| [Instagram Creators duyurusunun tarihli aktarımı](https://www.theverge.com/news/847739/instagram-hashtag-spam-limit) | 18 Aralık 2025 duyurusunda beş etiket sınırı aktarılıyor. Proje 0–5 ilgili etiketi kabul eder. Türkçe konu terimi açıklama girişine yerleşir. Erişim garantisi veya Instagram arama hacmi çıkarılmaz. |
| [Loewenstein 1994, merak](https://doi.org/10.1037/0033-2909.116.1.75) | İzleyicinin neyi bilmediğini tarif eden somut bir soru kur ve videoda yanıtla. Genel psikoloji bulgusudur. |
| [Berger ve Milkman 2012, paylaşım](https://doi.org/10.1509/jmr.10.0353) | Şaşırtıcı ama kanıtlı ayrıntı ve aktarılabilir pratik fayda test edilir. Makale paylaşımı Instagram'a özgü bir sıralama deneyi değildir. |
| [Guo vd. 2014, video etkileşimi](https://www.oerknowledgecloud.org/record2689), [Rey vd. 2019, bölümleme](https://doi.org/10.1007/s10648-018-9456-4) | Tek amaç, bölümlere ayrılmış anlatım ve kısa gereksiz girişler. Eğitim videosu örnekleminden Reels için sabit saniye veya nedensellik türetilmez. |
| [Gernsbacher 2015, altyazılar](https://gernsbacherlab.org/research/opportunity-research/papers/abstract-video-captions-benefit-everyone/) | Okunaklı Türkçe altyazı, sesle eşleme ve yalnız önemli kelimeyi vurgulama. Erişilebilirlik ve anlama temellidir. |
| [Meta, Insights API referansı](https://developers.facebook.com/docs/insights/references?locale=pt_BR) | Ölçüm erişimi hesap ve sürüme göre değişir. Erişilemeyen kaydetme, süre, takip veya tekrar sayaçları boş kalır. |

## İçerik üreticilerinden gözlemler

| Örnek | Projeye aktarılan yöntem |
|---|---|
| [Barış Özcan, TEDxBahcesehirUniversity](https://tedxbahcesehir.com/konusmaci/baris-ozcan/) ve [Evrim Ağacı'nın hikâye anlatımı söyleşisi](https://www.youtube.com/watch?v=kSGM6kIeXSw) | Bir nesne, teknoloji veya fikir üzerinden soru kurup bağlamı anlatıya yedir. Tarih için kanıtı açan özgün bir anlatım açısı seç. |
| [Johnny Harris, How I Make My Maps](https://www.youtube.com/watch?v=GsojLuJpe_0) | Harita üzerindeki hareketi coğrafi ilişkileri açıklamak için kullan. Türkçe etiket, kaynaklı rota ve sadece gerekli yakınlaşma. |
| [Lab Muffin Beauty Science, SPF örneği](https://labmuffin.com/video-spf-mean-high-spf-sunscreen-better/) ve [uygulamayı gösteren örnek](https://labmuffin.com/how-to-reapply-sunscreen-over-makeup-with-video/) | Önce izleyicinin bakım sorusunu adlandır, ardından adımı göster. Mekanizma, istisna ve pratik sonucu ayır. |
| [American Academy of Dermatology, kuru cilt bakım adımları](https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin) | Bakım adımlarını izleyicinin uygulayabileceği sırayla ver; hangi durumda dermatoloğa başvurulacağını koru. |

Bu örneklerde teknik biçim incelendi. Şablon, senaryo, ses, görüntü, yaratıcı kimlik ve erişilemeyen sayaçlar kopyalanmaz.

## Kurgu ve araç kararı

- Tarih için belgeye yavaş yakınlaşma, yön ve ölçeği açıklayan harita hareketi, kanıtlar arasında anlamlı kesme. Varsayılan 2B; bir mekân, rota veya mekanizma düz görselde anlaşılmıyorsa etiketli 3B.
- Bakım için tek alışkanlık veya mit, yakın plan uygulama, okunaklı koşul ve istisna. 3B yalnız anatomi gibi katmanlı yapıyı açıklıyorsa. Şema ve ölçek durumu görünür. Sahte sonuç, korku ve teşhis yok.
- Remotion ana kurgu; HyperFrames bağımsız HTML grafik sahnesi gerektiğinde alternatif. GSAP zaman çizelgesi ve Lottie vektör açıklaması için. Aynı sahneyi iki motorda seri üretme.
- Faster Whisper yerel Türkçe kelime zamanlaması; OpenCV görüntü kalite sinyalleri ve PySceneDetect kesmelerin gözden geçirilmesi için. Ölçümler insanın ses ve görüntü incelemesini tamamlar. Hareketli altyazı konuşmayı izler. Hızlı geçişler okuma süresini kısaltmaz.
- Lisanslı görsel için Wikimedia Commons, ikinci aday taraması için Openverse. yt-dlp sadece ayrı açık izin ve var olan pilotun izinli yolu ile. Earshot ve CC0 uisfx, sahneye anlam katan az sayıda efekt için. FFmpeg Loudnorm ölçüm, anlatımı önde tutmak için ducking. Freesound kapalı.
- Paylaşım için bağlamı olan tek bir ayrıntı, kaydetmek için kısa özet ve kaynak; tekrar izleme için anlaşılan bir görsel bağlantı, cevabı geciktirmeden. İlk kare, kapak ve başlık aynı vaadi taşır. Takip çağrısı serinin ne sağladığını bir defa söyler.

## Süre ve gelecekteki ölçüm

60–75 saniyelik mevcut onaylı biçim ve anlatıcı korunur. Daha kısa taslaklarda gereksiz tekrarlar çıkarılır, fakat kanıt veya sağlık sınırı kesilmez. Karşılaştırmada marka, Reel süresi, açılış biçimi ve ölçüm yaşı beraber kaydedilir. Eksik değer sıfır doldurulmaz. Ortalama izleme süresi tamamlanma oranı değildir. Görüntüleme/erişim tekrara dair kaba bir göstergedir ve gerçek tekrar sayısı olarak sunulmaz. Takipçi kazanımı ancak içerik düzeyi metrik gerçekten sağlandığında o Reel'e bağlanır. Editoryal eşik, gerçek veriyi değiştirmez ve otomatik paylaşımı açmaz.
