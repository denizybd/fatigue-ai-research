Tamamlanan ana v6 paneli, üç gözlemin yararlı olduğunu gösteriyor; gerilme seviyelerini seçen özel bir politikanın rastgele seçimi birlikte daha uzun sınır, daha az risk ve daha düşük maliyetle geçtiğini göstermiyor.

1 milyon ve10 milyon çevrim durdurma sınırlarının her birinde, yedi ayarlanmış model × dört politika =28 karşılaştırmanın tamamında, k3'ün k0'a göre uygun olasılıksal log-skor kazancının betimsel %95 aralığı sıfırın üzerinde. Bu, üç açığa çıkarılan deneyin modelin dağılım tahminini iyileştirdiğine dair geniş bir tarihsel panel bulgusu. Aynı12 kaynak kullanıldığı için28 hücre veya iki durdurma sınırı bağımsız fiziksel tekrarlar sayılmaz.

Önceden belirlenen özel gerilme-seçimi başarı şartı daha güçlü: rastgele seçime göre en az%5 uzun ömür sınırı, risk artışı üst sınırı en fazla2 yüzde puan, sonlu eşleşme en az%95 ve çevrim maliyet oranı üst sınırı en fazla0.9. Her durdurma sınırında476 tek-model/bütçe/altküme kapısının0'ı,28 model-sınıfı birleşiminin0'ı bu şartı geçti. Beş sınıftan en az üçünün geçmesi ve hiçbir sınıfta ömür kazancı tersine dönmemesi şartı da sağlanmadı. Bu, tahmin skoruna dayanan kalite kapısı değildir; iki kavram ayrı tutulmalı.

| k3 politikası, rastgele seçime göre | 1M kaynak-ağırlıklı maliyet oranı üst sınırının ortalaması / betimsel üst95 | 10M aynı ölçüm | Ömür ve risk sonucu |
|---|---:|---:|---|
| Yüksek gerilme |0.565 /0.691 |0.495 /0.634 | Daha ucuz; local-slope ve RFL sınıflarında ömür sınırı tersine dönüyor.10M'de Student sınıfı da tersine dönüyor. |
| Gerilme aralığını yayma |1.205 /1.364 |3.309 /4.493 |10M'de bazı modellerde küçük pozitif alt ömür kazançları var; maliyet ve risk şartları birlikte geçmiyor. RFL sınıfında tersine dönüş var. |
| Aktif sorgu varyansı |1.172 /1.427 |2.304 /3.106 | Yedi ayarlanmış modelde k3 tam panel ömür-kazancı alt95 sıfırın üzerinde değil; maliyet üstünlüğü yok. |

Bu maliyetler kaynaklara eşit ağırlıklı eşleşmiş çevrim oranlarıdır; takvim süresi, para maliyeti veya tüm kayıtların toplam maliyet oranı değildir.10M'deki sansürlü maliyetler, aynı numune iki politikada varsa ortak belirsizliğin bağlanmasıyla hesaplandı; iki bağımsız marjinal aralık çıkarılmadı.

Daha uzun bir tahmin tek başına güvenli ve işe yarar bir sınır anlamına gelmiyor. Örneğin1M'de Student k3 sınırları k0'a göre belirgin uzuyor, fakat politikalara göre ampirik risk üst95 yaklaşık0.140–0.219;0.1 şartını karşılamıyor. GP'de olasılıksal skor iyileşmesi var, ancak k3-k0 ömür kazancı alt aralığı sıfırı aşmıyor. Model bağımlılığının önemli nedeni, dağılım kalitesinin ve alt-kuyruk güvenli tasarım kararının aynı hedef olmaması.

Panelin kapsamı37 koşul,12 muhafazakâr kaynak ailesi,370 tohumlu görev; k0/k3 için model-politika başına1510 sorgu satırı. Bunlar370 yeni fiziksel deney veya doğrulanmış bağımsız üretim partisi değildir. k5 yalnızca11, k10 yalnızca4 kaynakta mümkün; gerilme seçimi gerçekten farklılaşabilen k10 altkümesi1 kaynak içeriyor ve iki-kaynaklı betimsel aralık kurulamaz. Bu altkümeler tam12-kaynak paneli gibi sunulamaz.

Ana v6 ömür/risk hesabı ham q10 sınırlarını değerlendirir; 1M/10M etiketleri deney durdurma bütçeleridir. Sonradan ayrı mühürle hesaplanan sonlu ufuk pinball/karar analizi bu denetime dahil edilmedi. Bu denetim R90C90, doğrulanmış bağımsız üretim partileri veya küresel optimizasyon garantisi sağlamaz.

Bütünlük ve bağımsız kontrol: skor okumadan önce21 mühürlü girdi, iki çalıştırmanın tahmin/deney-seçimi CSV hashleri, analiz/ölçüt kod hashleri ve tam370 görev doğrulandı. Orijinal analiz makbuzları türetilen özet/kapı dosyalarını hashle bağlamıyor; bu sınır açıkça kaydedildi. Bu denetim tüm bu dosyaların hashlerini sabitledi, her ufukta476 kapıyı ve28 sınıf birleşimini yeniden kurdu; doğrulanmış ham tahminlerden224 k3 özetini bağımsız hiyerarşik toplamayla,272 maliyet özetini8-köşe hesabıyla kontrol etti. Kontrol sonunda bütün girdi hashleri aynı kaldı. Eski sonuçlar, mühürler ve çalışan işler değiştirilmedi; yeni model eğitimi veya ana analiz tekrarı çalıştırılmadı.
