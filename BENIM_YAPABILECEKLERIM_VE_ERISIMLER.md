# Kurulum yetkileri — 23.11.2026

## Yapılanlar
- 20 görev modülü, kaynaklı tarih konusu verileri, içerik taslağı, poster ve 3 sahnelik **yayına uygun olmayan** eski örnek zaten hazırlanmıştı.
- Malazgirt konusunun ilgisiz kaynak bağlantısı düzeltildi; TDV Ansiklopedisi ve TTK Kütüphanesi referanslandı.
- 5 farklı görsel + gerçek ses kaydı + SRT sağlanınca 9:16 dikey, altyazılı, sesli MP4 düzenleyen `scripts/create_reel.py` eklendi.
- 7 otomatik test geçildi. Ek olarak FFmpeg ile gerçek MP4 kodlama testi yapıldı; test ses dosyası yalnızca sentetik sestir ve yayınlanabilir konuşma değildir.
- Hiçbir ücretli video/ses/görsel API çağrısı yapılmadı. Instagram hesabına hiçbir şey gönderilmedi.

## GitHub'a geçiş için tek hesap sahibi adımı
- GitHub bağlantısı `pendikozgeguv` olarak görülüyor ancak erişilebilir proje deposu görünmüyor. GitHub bağlantısının mevcut araçları yeni depo oluşturamıyor.
- Kullanıcı `https://github.com/new` adresinden örn. `turk-tarihi-icerik` adında **Private** depo açabilir. Depo oluşunca bağlantı üzerinden dosyaları doğrudan yerleştirmek için bağlantının o depoya yazma yetkisi olup olmadığı kontrol edilir.

## Henüz eksik olanlar
- Gerçek tarihî canlandırma görselleri / hareketli sahneler ve kullanma haklarının teyidi.
- Doğal Türkçe seslendirme üretimi. Bunun için kullanıcı onaylı ücretsiz araç veya ücret sınırı belirlenmeli.
- Konuşma sürelerine oturan SRT altyazı ve QA.
- Meta Instagram profesyonel hesaba ait API izinlerinin kullanıcı tarafından verilmesi. Bu yapılmadan otomatik yayın yoktur.
- Otomatik tarih kaynak içeriği okuma; yalnızca kaynak URL'lerinin varlığı şu an kodla denetlenir.

## Gizlilik
- API anahtarı, erişim belirteci, parola dosyalara yazılmamalı. Yetki gerekiyorsa ilgili platformun güvenli yetkilendirme ekranından işlem yapılmalı.
