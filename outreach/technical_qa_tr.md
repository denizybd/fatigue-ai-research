# Teknik görüşmeye hazırlık

Bu cevaplar çalışmanın kapsamını açıklamak içindir. Kullanıcının eğitimi, uzmanlığı veya tek başına yaptığı işler hakkında varsayım içermez. Sayısal sonuçlar, aşağıda belirtilen kayıtlı deney çıktılarından alınır.

## 1. Bu çalışma hangi soruyu yanıtlıyor?

**Sade anlatım:** Bir yorulma modeli, eğitim dışında bırakılan bir yayın/köken bloğundaki gözlemlerde güvenli görünen ömür tahminleri verebiliyor mu? Daha az desteklenen veya modelin kararsız kaldığı durumları ayırmak bu sorunu azaltıyor mu?

**Teknik cevap:** Birincil görev, muhafazakâr köken bloklarını tamamen dışarıda bırakan değerlendirmede tek taraflı alt ömür sınırlarının tehlikeli iyimserlik oranını ve karar kullanılabilirliğini ölçmektir. Hedef ortalama tahmin doğruluğu tek başına değildir. Kaynak-bootstrap konum kararsızlığı ile özellik uzayındaki en yakın eğitim desteği birleştirilir; kural, yalnızca kalibrasyon verisiyle belirlenir. Birleşimin üstünlüğü önceden kayıtlı ölçütlerle sınanır; başarısız olursa üstünlük iddiası bırakılır.

## 2. Centola ve arkadaşlarının BNN modelini yeniden mi ürettik?

**Sade anlatım:** Birebir aynı modeli ve aynı deneyi çalıştırmış değiliz. Onların araştırmasından hareketle, ulaşabildiğimiz açık veri üzerinde ilgili bir soruyu inceliyoruz.

**Teknik cevap:** Özgün 518 temizlenmiş gözlem, dışlanan 32 kayıt, bölme kimlikleri ve Owen hedef oluşturma kodu elimizde değil. Açık veriyle kaynak DOI eşleşmesi, gözlem eşitliğini kanıtlamaz. Bizim modellerimiz ham kırılma/runout noktalarına uygun sansürlü lognormal olabilirlik kullanır; özgün BNN ise tahmin edilmiş R90C90 eğri ömürlerini öğrenir. Risk hacmi, tam SWT işlemi ve varyasyonel çıkış katmanı yeniden kurulmadı. Çalışma bu nedenle açık veri üzerinde ayrı bir yöntem değerlendirmesidir.

## 3. Runout neden sıradan bir kırılma noktası değildir?

**Sade anlatım:** Test durduğunda parça hâlâ sağlamsa, o andaki çevrim sayısı parçanın gerçek ömrü değildir. Yalnızca ömrünün en az o kadar olduğunu biliriz.

**Teknik cevap:** Kırılmada gerçek log-ömür gözlenir ve yoğunluk katkısı kullanılır. Runout eşiği C için gerçek ömür T>C olduğundan olabilirliğe sağkalım olasılığı P(T>C) girer. Alt ömür önerisi L≤C ise L>T olayı imkânsızdır; L>C ise henüz bilmiyoruz. Risk bu yüzden [bilinen ihlal/n, (bilinen ihlal+belirsiz runout)/n] aralığıyla verilir. Bu aralık örnekleme güven aralığı değil, sansür yüzünden sonuçtan ne kadarını tanıyabildiğimizin aralığıdır. Blok-bootstrap güven aralığı ise sınırlı blok örnekleminin değişkenliğini betimler; sansür aralığını ortadan kaldırmaz. Dışarıda-bırakma uyumları eğitim verisi paylaştığı için bootstrap aralıklarını da betimsel olarak sunuyoruz.

## 4. R90, C90, BNN belirsizliği ve conformal kalibrasyon aynı şey mi?

**Sade anlatım:** Hayır. Numunelerin doğal saçılması, az deneyden bir eğriyi tahmin etmenin belirsizliği ve makine öğrenmesi modelinin kararsızlığı farklı şeylerdir.

**Teknik cevap:** R90, koşullu ömür dağılımının alt yüzde 10'luk niceliğine karşılık gelir. C90, bu malzeme niceliğini sınırlı deneyle tahmin etmenin güven düzeyini ifade eder. Özgün çalışmada BNN ağırlık dağılımı, tahmin edilmiş Owen R90C90 hedefinin ML belirsizliğini ayrıca modeller. Bizim q10 sınırımız lognormal modelden gelir; sonradan yapılan split kalibrasyon, gözlenen uç noktaya veya bütün kaynak kohortuna yöneliktir. Bu bir Owen R90C90 tahmini değildir; yeni üretim koşullarında koşullu yüzde 90 güvenlik garantisi vermez.

## 5. Neden rastgele satır bölmesi yerine kaynak ailesini dışarıda bırakıyoruz?

**Sade anlatım:** Aynı deney kampanyasının bazı noktalarını öğretip diğerlerini sınamak, yeni bir laboratuvarı tahmin etmekten daha kolay olabilir. Aynı deneyin başka makalede yeniden çizilmiş olması da bu ayrımı bozabilir.

**Teknik cevap:** Benzer üretim, yüzey, cihaz, numune ve veri çıkarma etkileri aynı kaynakta kümelenir. Yakın eğriler farklı DOI'larda tekrar görünebildiği için ana ayrım muhafazakâr kaynak aileleriyle yapılır. Her dış döngüde bir aile testte, en az dokuz başka blok kalibrasyonda ve kalanlar eğitimdedir. Rastgele satır bölmesi yalnızca karşılaştırmalı teşhistir. Kaynak bölmesi de tüm gerçek parti bağımsızlığını kanıtlamaz; kalan örtüşmeler mümkündür.

## 6. Kaynak ailelerinin gerçekten aynı numuneler olduğu kanıtlandı mı?

**Sade anlatım:** Hayır. Çok benzer eğrileri aynı güvenlik bloğunda tutuyoruz; bundan fiziksel numunelerin kesinlikle aynı olduğu sonucu çıkmaz.

**Teknik cevap:** Önceden belirlenen güçlü kenar ölçütü, küçük eğrinin en az yüzde 85'ini kapsayan en az beş ayrı yakın nokta, aynı yük oranı/test modu ve 1,02 ömür/1,01 gerilme çarpanı toleranslarıdır. Üç çok-DOI'lı aile, tekil yayın bloklarıyla birlikte 37 DOI'ı 29 muhafazakâr köken bloğuna indirir. Ana analizde gözlem silinmez. DOI-only, daha zayıf kenarı birleştirme ve yaklaşık gözlem ayıklama ayrı duyarlılıklardır. Kaynak metni ve yazarın deney kimlikleri bu varsayımı daha güçlü biçimde doğrulayabilir veya çürütebilir.

## 7. “Veri desteği” ve “belirsizlik” burada nasıl ölçülüyor?

**Sade anlatım:** Yeni durumun eğitim örneklerine ne kadar benzediğini ve eğitimdeki kaynakları değiştirince modelin ne kadar oynadığını ölçüyoruz.

**Teknik cevap:** Destek skoru, yalnızca eğitimle kodlanıp ölçeklenen uzayda en yakın eğitim satırına RMS Öklid uzaklığıdır. Kararsızlık, sekiz köken-bloğu-bootstrap doğrusal modelin log-ömür konum tahminlerinin standart sapmasıdır. İki skor, kalibrasyon verisinin ampirik dağılım sıraları üzerinden ortalanır. Bu skor ne BNN posteriorudur ne ölçüm hatası dağılımı ne de fiziksel veri desteğinin ispatıdır. Özellik kodlaması, eksiklikler ve kaynak sayısı sonucu etkiler.

## 8. Tahminden kaçınarak herhangi bir yöntemi başarılı göstermek kolay değil mi?

**Sade anlatım:** Evet. Bütün zor örnekleri reddederek veya kullanışsız derecede kısa ömür önererek güvenli görünmek mümkündür. Bu yüzden güvenlikle birlikte ne kadar karar verebildiğimize de bakıyoruz.

**Teknik cevap:** Operasyonel eşikler kalibrasyonda dondurulur ve gerçek test kabul oranı açıklanır. İkincil eşit-kabul karşılaştırmasında her köken bloğunda aynı sayıda örnek kabul edilir; birleşik skor, tekil skorlar ve 20 sabit rastgele sıralama ile karşılaştırılır. Ana kabul hedefi 0,8, ikincil hedef 0,5'tir. Kaynak kapsamı, sansür karışımı, gerilme dağılımı, alt ömür büyüklüğü ve muhafazakârlık da raporlanır. Boş kabulün riski sıfır değil, tanımsızdır.

## 9. Birleşik kuralın üstün olduğunu söyleme ölçütümüz ne?

**Sade anlatım:** Birkaç iyi örnek veya tek bir iyi tohum yetmez. Önceden seçtiğimiz ana karşılaştırmaların hepsinde tutarlı bir yarar görmemiz gerekir.

**Teknik cevap:** Protokol v1.2'ye göre, 0,8 kabulde birleşik kuralın bilinen-ihlal farkı uzaklık, kararsızlık ve rastgele sıralamanın her birine göre üç tohumun her birinde negatif olmalıdır. Tohumlar köken bloğu içinde ortalandıktan sonra, eşleştirilmiş köken-bloğu-bootstrap betimsel yüzde 95 aralığının üst ucu da sıfırın altında olmalıdır. Bunlardan biri geçmezse güçlü hipotez başarısız veya sonuçsuz sayılır. Gerçek riski azalttığımızı söylemek için sansürün kısmi-tanımlama farkının üst ucunun da negatif olması gerekir.

## 10. Kalibrasyon gerçekte neyi garanti ediyor?

**Sade anlatım:** Kalibrasyon geçmişteki ayrı veride tahminleri düzeltir. Yeni bir üretim sürecinde otomatik olarak aynı güvenliği sağlayacağını söyleyemeyiz.

**Teknik cevap:** Pooled uç-nokta düzeltmesi b(x)−log10(min(T,C)) artıklarından üst nicelik çıkarır; gerçek ömürden küçük olan gözlenen uç noktayı hedeflemesi muhafazakârlık yaratabilir. Kaynak-maksimum düzeltmesi ise köken bloğu içindeki en büyük artığı kullanır ve bütün kohort düzeyinde farklı bir hedefe yönelir. İlgili değiştirilebilirlik varsayımları keyfî kaynak/üretim kaymasında garanti değildir. Özellikle koşullu kabul edilen altgrupta güvenlik veya tek kaynakta kapsama bu yöntemlerden doğrudan çıkmaz.

## 11. Sayısal yakınsama ile fiziksel olarak doğru davranış aynı mı?

**Sade anlatım:** Hayır. Bir çözücünün durma ölçütüne ulaşması, modelin fiziksel olarak doğru ya da yeni koşullarda güvenilir olduğunu göstermez. İlk deneydeki sayısal sorunu ayrıca inceleyip hangi sonucun asıl deney, hangisinin sonradan yapılan sayısal inceleme olduğunu açıklıyoruz.

**Teknik cevap:** Dondurulmuş 1.500 iterasyon sınırında 87 MLP uyumunun hiçbiri yakınsamadı. Bu, ilk MLP çıktılarından mimari üstünlük sıralaması çıkarmayı engeller. Sonuç-sonrası v1.5 sayısal duyarlılığı aynı amaç, girdiler, ağırlıklar, tohumlar ve durma toleranslarıyla sabit 12.000 sınırını kullandı; 87/87 uyum yakınsadı, en yüksek iterasyon 9.183 oldu. Bu çözümleyicinin işlev-azalması ölçütüdür; fiziksel doğrulama değildir. Ayrı MLP incelemesinde köken-blok dengeli numune-risk tanımlama aralıkları q10 için yüzde 40,17–44,93; pooled için yüzde 9,30–10,06; cohort için yüzde 0,234–0,246 oldu. Bunlar ana sonuçları değiştirmez ve mimari sıralaması kurmaz. Ayrıca doğrusal/MLP konumları zorunlu monoton değildir; gerilmeyi ±0,01 log birim değiştiren kayıtlı kontrol fiziksel bakımdan şüpheli pozitif eğimleri raporlar.

## 12. Tridello'dan en somut olarak ne isteyeceğiz?

**Sade anlatım:** Önce kısa bir yöntem yorumu ve veri kökenine ilişkin sınırlı bir kontrol isteyeceğiz. İşbirliği veya olumlu yanıtı elde edilmiş sonuç gibi sunmayacağız.

**Teknik cevap:** Bir sayfalık özet ve iki grafik üzerinden, kaynak ailelerinin fiziksel olarak anlamlı olup olmadığı, yeni bir kaynakta alt-ömür güvenilirliğinin tasarım gündemine ne kattığı ve özgün 518 noktalı veri setinin kaynak/koşul eşlemesinin paylaşılabilirliği sorulabilir. Tam veri aktarımından önce kaynak haritası bile örtüşme ve ayrım tanımını iyileştirebilir. Topoloji/TL bağlantısı modelin sınırlarını yeni tasarım veya yeni alaşıma taşımakla ilgilidir; bu çalışma topoloji çözümü, fiziksel parça doğrulaması veya onların BNN'sinin başarısızlık kanıtı değildir.

Yöntem belgeleri: `protocols/v1_pre_outcome.md` ve v1.1–v1.3 değişiklikleri; `data/DATA_DICTIONARY.md`; `literature/primary_paper_audit.md`. Bu dosya iletişim hazırlığıdır; hiçbir mesaj gönderilmedi.

## Kayıtlı zengin doğrusal AFT sonucunun kısa anlatımı

`results/primary/summary.csv` sonuçlarına göre zengin doğrusal modelin model-tabanlı q10 alt ömür sınırı için köken bloklarına eşit ağırlıklı ampirik ihlal tanımlama aralığı yüzde 28,97–30,77; pooled uç-nokta kalibrasyonunda yüzde 14,50–15,40'tır. Kaynak-maksimum kalibrasyonunda gözlenen oran yüzde 0,197 olurken, köken bloğu bazındaki medyan model-medyanı/alt-sınır farklarının ortalaması 3,54 log10-ömür basamağına çıkar. Bu maliyet, gözlenen ömür medyanına değil modelin tahmin ettiği medyan ömre göre ölçülür. Daha az gözlenen ihlal tek başına kullanışlı tasarım ömrü anlamına gelmez.

Birleşik kuralın güçlü üstünlük hipotezi **geçmedi**. `paired_contrasts.csv` içinde 0,8 ana kabul hedefinde uzaklık kuralına göre bilinen-ihlal farkı +0,13 yüzde puandır; betimsel yüzde 95 eşleştirilmiş köken-bloğu-bootstrap aralığı −0,64 ile +0,89 puan arasındadır. Kararsızlık ve rastgele karşılaştırmaların aralıkları da sıfırı içerir. `source_seed_metrics.csv` üzerinden yapılan kontrolde uzaklığa göre fark 0 ve 42 tohumlarında, kararsızlığa göre fark 0 tohumunda pozitif olduğundan, her-tohum-negatif şartı da sağlanmaz. Bu sonuçları özgün BNN'nin hatası veya gelecek üretim koşulları için garanti gibi anlatmıyoruz.

## Gruplama/bölme duyarlılığının sınırı

`results/sensitivity_comparison.csv`, dondurulmuş zengin doğrusal AFT için pooled numune-risk aralıklarını ana analizde yüzde 14,50–15,40, zayıf-kenar duyarlılığında yüzde 16,03–16,88, yaklaşık ayıklamada yüzde 15,00–15,72 verir. Kaynak-maksimum kalibrasyonunun asıl hedefi olan tam kohortta en az bir ihlal oranı ana analizde yüzde 4,60 iken zayıf-kenar incelemesinde yüzde 17,86'dır. Gruplama değişince eğitim/kalibrasyon üyelikleri de değişir; bu fark yalnızca gruplamanın izole nedensel etkisi değildir. Güvenli bir algoritma ilan etmek için dayanak oluşturmaz. Bu yüzdeler tüm modellere veya özgün BNN'ye genellenmez.

Sonradan yapılan sayısal MLP incelemesi `results/mlp_extended/summary.csv`, yakınsama kayıtları `fit_statuses.csv` ve protokol v1.5'te ayrıdır. V1.4, tam-kohort ve ortalama-numune hedeflerinin açıkça ayrılmasını kaydeder.
