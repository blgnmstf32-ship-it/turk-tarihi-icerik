# Instagram Reels kalite standartları

**Eski sürümün hatası:** Üç düz metin sahnesi birleştirilip sessiz MP4 olarak sunuldu. Bu yayın kalitesini karşılamıyor.

## Zorunlu geçiş koşulları

1. Açılış 2 saniyede olayın merakını gösteren canlı sahne.
2. En az 5 birbirinden farklı tarihî canlandırma, arşiv fotoğrafı (varsa lisanslı), hareketli harita veya gerçek çekim. Yazı kartı tek başına sahne sayılmaz.
3. Anlaşılır, doğal Türkçe konuşma kaydı, bütüne hakim; `voiceover.wav` / `voiceover.mp3`. Piper'in çevrimdışı sesi sentetiktir; yalnız tempo/durak iyileştirmesi doğal insan kaydı sayılmaz. Hâlâ yapay duyuluyorsa yayın kalite kapısını geçmez.
4. Gerçek ses parçası sürelerine göre hizalanmış altyazı `.srt` (kelime düzeyinde forced alignment değildir).
5. Yasal müzik/SFX (tercihen özgün); konuşma hiçbir sahnede boğulmaz.
6. Tarihî kıyafet ve dönem kontrolü; 1071'de Osmanlı üniforması, hilalli modern bayrak veya modern silah yok.
7. En az iki güvenilir kaynak üzerinden tarih kontrolü; doğrulanmamış rakam veya sahte alıntı yok.
8. Render: dikey 9:16 en az 720x1280, 20–60 saniye, H.264 video + AAC audio.
9. Maliyet tavanı: Kullanıcının açık onayı olmadan ücretli üretim yok.
10. Yayın: Tarihçi/insan gözden geçirmesi + Instagram sahibinin onayı olmadan yayına alınamaz.

`scripts/release_check.py`, yalnızca teknik asgari kaliteyi doğrular; içerik etkileyiciliği için insan incelemesi zorunludur.
