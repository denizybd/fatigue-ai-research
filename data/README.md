# Kullandığımız veriler

[Veri kataloğu](catalogue.csv) dosya, satır sayısı, kullanım amacı ve SHA256 içerir. [Sütun sözlüğü](dictionary.csv) ana alanların birim ve anlamlarını açıklar. CSV'ler mevcut tamamlanmış hesaplardan aynen alınmıştır; bu düzenleme yeni veri veya eğitim üretmedi.

## Gerçek girdiler

- [441 gözlem](processed/v4/controlled_expansion/expanded441.csv): derlenmiş çalışma girdisi.
- [441 satırın metaverisi](processed/v7_covariates/conservative441_v1.csv): alan başına köken/bilinmeme işaretleri.
- [ORNL 60 numune](../literature/outer_region_signal_feasibility_v12/prepared_models_v1/input60.csv) ve [54 numunelik V12 alt kümesi](../literature/outer_region_signal_feasibility_v12/prepared_models_v1/input54.csv).

Katalog verisi, değerlendirmedeki sorgu sayısı ve bağımsız fiziksel üretim sayısı farklıdır. ORNL 316H tek üretimdir; 316L derlemesiyle tek doğrulama paneli sayılmaz. Koşul metaverisi aynı numunede ölçülmüş başlangıç mikroyapısı değildir. Eksik değerler sıfır sayılmaz; runout kayıtları event=0 kalır.

## Büyük ham veri

[FatigueData-AM2022 v2](https://doi.org/10.6084/m9.figshare.22337629.v2) için [orijinal manifest](raw/manifest.json) dosya bağlantısı, boyut ve hash içerir. Manifestte orijinal verinin CC BY 4.0 kaydı bulunur. Bu koşul bütün ek karma kaynaklara otomatik aktarılmadı. [ORNL veri DOI'si](https://doi.org/10.13139/ORNLNCCS/2524534) büyük XCT dosyalarının erişim kaydıdır; bu dosyalar küçük Git paketine kopyalanmadı.

Depo 25 Ekim 2026 itibarıyla publictir. Karışık kaynaklardan türetilmiş tabloların ve ORNL türevlerinin public paylaşım koşulları ayrıca doğrulanacak. Üçüncü taraf makale PDF'leri ve izin durumu belirsiz görüntüler bu rapora eklenmedi. Veri dosyası mevcut olsa bile numune kimliği, ölçüm zamanı veya lisans bilinmiyorsa katalogda bu sınır korunur.
