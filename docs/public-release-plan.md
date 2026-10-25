> **25 Ekim hazırlık güncellemesi:** İlk rapor, veri/sonuç dizinleri ve dosya envanteri hazırlandı. Dört kesin replay tekrarı kaldırıldı; [uygulanan kararlar](inventory/README.md) ve [doğrulama](publication-validation.json). Aşağıdaki metin ilk plandır. Public geçiş yapılmadı.

# Public açılışa hazırlık planı
25 Ekim 2026. Plan kaydıdır; public açılış, silme, arşiv taşıma veya geçmiş yeniden yazma yapılmadı.

## Doğrulanan başlangıç
Depo private. İncelenen main: 2889a7b87d728df80a337a0e9bf4aea74bc9c3e1, son push 20 Ekim. Bu güncellemeden önce 8.848 dosya / 1.571.878.877 bayt vardı. results/ 7.555 dosya / 1.339.254.397 bayt: replay ve final tahminleri önemli yer kaplıyor. Yalnız boyut, bilimsel çıktıyı silme gerekçesi değildir.
snapshot-2026-10-20-2300 sürümünde ayrıca 1.528.571.177 bayt tam yedek var. SNAPSHOT_BACKUP.md ham verileri, PDF'leri, eski .git'i, ortamı ve ara dosyaları içerdiğini söylüyor. Arşivin içeriği bu incelemede indirilip taranmadı; public için onaylanmış değildir.

## Önerilen yaklaşım
Mevcut depo özel araştırma arşivi kalsın; incelenmiş dosyalardan temiz geçmişli bir public eş depo hazırlamak öncelikli adaydır. Henüz yeni depo oluşturulmadı. Mevcut depo açılacaksa inceleme eski commitleri, etiketleri ve sürüm eklerini de kapsamalı. .gitignore geçmişe kaydedilen dosyaları kaldırmaz.

## İş sırası ve bitiş ölçütleri
1. README tek giriş noktası olsun: fiziksel soru, kanıtlanmış/olumsuz sonuç, sınırlar, yeniden üretim, kısa okuma sırası. Uzun STATE tarihçesi korunup kısa güncel durum sayfasına bağlansın.
2. Dosya envanteri çıkarılsın: kaynak/sahiplik, paylaşım koşulu, boyut, bilimsel rol, yayın kararı. Yazışma ve kişisel bilgiler, kimlik doğrulama bilgileri, paylaşımı doğrulanmamış üçüncü taraf içerik public pakete girmesin. Tüm Git geçmişi ve sürüm ekleri de incelensin; henüz bu tarama tamamlanmadı.
3. Ayrı yayın kopyasında düzen: docs/ kararlar-yöntem; src/ analiz; protocols/ önceden belirlenen kurallar; tests/ anlamlı kontroller; data/ kaynak-lisans-hash envanteri; results/ küçük seçilmiş tablolar; figures/ paylaşımı uygun şekiller; archive/ eski aşama indeksi. Ana araştırmanın dizinleri taşınarak bozulmasın.
4. Büyük sonuçlar hash ve bilimsel değer eşliğiyle sınıflandırılsın. Frozen özetler ve doğrulama makbuzları tutulsun. Yeniden üretim için gereken büyük tablolar, koşulları uygun sürümlü veri arşivinde bağlantı/hash ile saklanabilir. Doğrulanmış alternatif kopya olmadan özgün sonuç silinmesin.
5. Aynı numunede ölçüm, koşul ortalaması, kaynak simülasyonu ve varsayım ayrı etiketlensin. Veri bekleyen adaylar tek tabloda kapatılsın. Olumsuz gözenek pilotu korunsun. Yerel mekanizma, tahmin katkısı ve nedensellik iddiaları ayrı tutulsun.
6. Ağır eğitim başlatmayan küçük bir örnek, sabit girdi ve ayrım sürümü sunulsun. Temiz bir kopyadan çalışsın; dış disk ve kişisel yerel yola bağlı olmasın. Hafif CI kontrolleri eklensin.
7. Kendi kod lisansı, üçüncü taraf koşulları, atıf, yazarlık ve AI kullanım açıklaması insan tarafından kararlaştırılsın. Doğrulanmamış başarı başlığa taşınmasın.
8. Dosya listesi, küçük örnek, bağlantılar ve yayın envanteri doğrulanınca somut yayın kopyası kullanıcıya gösterilsin. Public geçiş ayrıca açık yayın talimatına bağlansın.

İlk iş: yayın envanteri ve kısa README/dizin taslağı. Yeni model taraması veya mevcut hesaplara müdahale bu planın parçası değil.
