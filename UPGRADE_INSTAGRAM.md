# Daha sonraki aşama: Instagram API ile otomatik paylaşım

**Bu sürümde paylaşım bağlantısı yapılmadı, otomatik yayın kapalı.** Önce ücretsiz içeriğin kalitesini ve tarihî doğruluğunu test edeceğiz.

Yayına geçişte:
1. Instagram sayfasını **Profesyonel hesap (Creator/Business)** olarak ayarla.
2. Meta geliştirici uygulamasını açıp uygun Instagram yayın izinlerini al. Facebook Login veya Instagram Login akışları birbirinden farklıdır; uygulamanın tercih ettiği akışa göre doğru token türü kullanılmalıdır.
3. `IG_ACCOUNT_ID` ve erişim tokenlarını GitHub **Actions secrets** içine kaydet; asla kaynak koda, artifact'e veya sohbet ekranına yapıştırma.
4. Gönderi görseli ve MP4'ü Meta API'nin erişebileceği, kamuya açık HTTPS URL'de barındır. GitHub Actions artifact dosya bağlantısı Meta için doğrudan medya URL'si olarak kullanılamaz.
5. Gönderiye girecek her tarihi anlatı için **kaynak ve insan onayı** al.
6. Sonrasında Meta `/{ig-user-id}/media` → `/{ig-user-id}/media_publish` akışı uygulanabilir; Reels medyası hazır olana kadar container işleme durumu beklenir.
7. Yayın id'leri bir günlük dosyasında tutularak aynı paylaşımın tekrar gönderilmesi engellenir.

Kaynak: Meta'nın Instagram API yayımlama belgelendirmesi:
- https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing
- https://www.postman.com/meta/instagram/request/gabnx7r/publish-reel

Meta API bağlantısı yapılmadan proje yalnızca **taslak üretir**.
