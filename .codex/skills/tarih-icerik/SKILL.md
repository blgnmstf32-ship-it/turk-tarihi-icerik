---
name: tarih-icerik
description: Kaynaklı Türk tarihi Instagram gönderisi ve Reels taslağı oluştur; 20 rolün işini koordine et ve insan onayı olmadan paylaşma.
license: LicenseRef-No-License-Granted
---

# Türk tarihi içerik skill'i

Kullanıcı belirli bir konu verirse önce `data/topics.json` arşivini kontrol et. Konu yoksa kurumsal/akademik kaynakları tarayıp doğrulanabilir tarih, aktör, sonuç ve tarihsel bağlamla yeni kayıt öner; taslağın kaynağı açıkça tanımlansın.

`AGENTS.md` yönergelerini uygula. `config/agents.json` yirmi uzman görevini belirtir. Ücretli yapay zekâ API'leri varsayılan kapalıdır.

Kontrol/üretim komutları:

```bash
python -m unittest discover -s tests -v
python -m scripts.run --topic malazgirt-1071 --out output/malazgirt
```

Her yeni içerik için `draft_manifest.json`, `sources.json`, `caption.txt`, `voiceover.txt`, özgün post görseli ve üç sahneli MP4 çıkarmayı hedefle. Gerçekçi yapay zekâ görüntüsü yoksa varmış gibi anlatma. Kaynakların URL biçiminin doğrulanması, içerik doğrulaması değildir. İnsan onayı olmadan Instagram'a yayınlama.
