"""Compact Turkish evidence note and publication-style diagnostic figure."""
from __future__ import annotations
import html,json,os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from src.v3_prepare import ROOT

DEST=Path(os.environ.get('V3_OUTPUT',ROOT/'manuscript/v3'))
DEST.mkdir(parents=True,exist_ok=True)
F=Path(matplotlib.get_data_path())/'fonts/ttf'
for name,file in [('V3Body','DejaVuSans.ttf'),('V3Bold','DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(F/file)))
pdfmetrics.registerFontFamily('V3Body',normal='V3Body',bold='V3Bold')
TEAL=colors.HexColor('#176c83')
ST={name:ParagraphStyle(name,fontName='V3Body',fontSize=size,leading=leading,spaceAfter=space)
    for name,size,leading,space in [('body',9,12.3,7),('small',7.6,10.3,5),('cell',7.6,10,0)]}
ST['title']=ParagraphStyle('title',fontName='V3Bold',fontSize=18,leading=22,spaceAfter=11,textColor=TEAL)
ST['h']=ParagraphStyle('h',fontName='V3Bold',fontSize=11,leading=14,spaceBefore=8,spaceAfter=6,keepWithNext=True)
def P(s,kind='body'):return Paragraph(html.escape(str(s)).replace('\n','<br/>'),ST[kind])
def T(rows,widths):
    t=Table([[P(v,'cell') for v in r] for r in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f4')),
        ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t
def footer(c,d):
    c.saveState();c.setFont('V3Body',7);c.setFillColor(colors.HexColor('#52616a'))
    c.drawString(45,821,'AM316L | Aşama 3: veri kökeni ve gerilme seçimi | 20 Ekim 2026')
    c.drawString(45,24,'Hesaplamalı yeniden oynatma. Yeni fiziksel deney veya dış yazışma yapılmadı.')
    c.drawRightString(550,24,str(d.page));c.restoreState()

def main():
    fact=json.loads((ROOT/'results/v3/headline_facts.json').read_text());f=fact['1e7']
    folder=ROOT/'results/v3/final_cap1e7/multistress'
    s=pd.read_csv(folder/'summary.csv');c=pd.read_csv(folder/'paired_comparisons.csv')
    labels={'pooled':'Havuzlanmış Basquin','matched_intercept':'Ortak eğim / yerel kayma',
      'hierarchical':'Hiyerarşik Basquin','curved_hierarchical':'İki eğimli hiyerarşik',
      'rfl':'Rastgele yorulma limiti','local_slope':'Yerel eğim + kayma'}
    policies={'random':'Rastgele','high_stress':'Yüksek gerilme','stress_span':'Aralığı kapsama',
              'active_query_variance':'Model bilgisine göre'}
    models=list(labels)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),gridspec_kw={'width_ratios':[1.6,1]})
    x=np.arange(len(models));width=.24
    for j,(policy,color) in enumerate([('high_stress','#207b8a'),('active_query_variance','#d89335'),('stress_span','#7871aa')]):
        vals=[]
        for model in models:
            z=c[(c.panel=='external_new_specimen_only')&(c.policy==policy)&(c.model==model)&
                (c.k==3)&(c.comparison=='versus_random')&(c.metric=='log_life_gain')].iloc[0]
            vals.append(100*(10**z['mean']-1))
        axs[0].bar(x+(j-1)*width,vals,width,label=policies[policy],color=color)
    axs[0].axhline(0,color='#555',lw=.8);axs[0].set_xticks(x,[labels[z] for z in models],rotation=28,ha='right')
    axs[0].set_ylabel('Rastgele seçime göre geometrik alt ömür farkı (%)')
    axs[0].set_title('Aynı test numuneleri, k=3')
    axs[0].legend(loc='upper left',fontsize=8,frameon=False)
    base=f['hier3random']['support_cycles']['mean']
    costs=[]
    for policy in policies:
        z=s[(s.panel=='external_new_specimen_only')&(s.model=='hierarchical')&(s.k==3)&
             (s.policy==policy)&(s.metric=='support_cycles')].iloc[0]
        costs.append(z['mean']/base)
    axs[1].bar(np.arange(4),costs,color=['#999','#207b8a','#7871aa','#d89335'])
    axs[1].set_xticks(np.arange(4),list(policies.values()),rotation=28,ha='right')
    axs[1].set_ylabel('Harcanan destek çevrimi / rastgele seçim')
    axs[1].set_title('Ölçülen çevrim maliyeti')
    fig.suptitle('İki yeni yazar verisi; üretim partisi eşlemesi doğrulanmış değil',fontsize=11)
    fig.text(.01,.012,'Çok gerilmeli koşullar. Test başına C=10⁷ çevrim. Model farkları bir fayda-risk dengesi; güvenlik sertifikası değil.',fontsize=8)
    fig.tight_layout(rect=[0,.07,1,.93]);fig.savefig(DEST/'model-ve-gerilme-secimi.png',dpi=210);plt.close(fig)
    # Public, aggregate tables. Per-specimen Trombley data are not exported.
    for cap in ['1e7','1e6']:
        p=ROOT/('results/v3/final_cap'+cap)/'multistress'
        for name in ['summary.csv','paired_comparisons.csv','success_gates.csv','by_condition.csv']:
            pd.read_csv(p/name).to_csv(DEST/(cap+'-'+name),index=False)
    source_rows=[
      ['Tomaszewski / Zenodo7650061',137,137,'Gerçek numune ID; ham derlemenin tek-plaka makalesine bağlanması eksik. 40 tek-gerilmeli kayıt seçim ana analizinden ayrı.'],
      ['Diller / FFEMS14375',44,29,'Gerçek tarama-numune ID; build/parti eşlemesi yok. 14 parlatılmış ve çelişkili μ15 ana aktarım dışında.'],
      ['Dastgerdi / Addma103559',8,6,'Tek fiziksel build kaynakta açık; yazar build kodu yok. Sıcaklık belirtilmemiş; eski kaynakla tekrar olasılığı. Küçük pilot.'],
      ['Liang / tel-02951486',29,0,'Tepsi renkleri doğrulanamadı; tekrar yüklemeler var. Karantina.'],
      ['Yin / Mendeley h97k6w9vm5',18,0,'14 tamamlanmış kayıt. DED ve döner eğilme; build eşlemesi de yok. Ayrı aday.'],
      ['Trombley / önceki aşama',129,129,'Daha önce incelenmiş tek kampanya; numune→dört build eşlemesi doğrulanmış değil.']]
    pd.DataFrame(source_rows,columns=['source','raw_named_or_test_rows','phase3_replay_rows','qualification']).to_csv(DEST/'kaynak-kapisi.csv',index=False)
    study=ROOT/'data/processed/v3/common/cohort.csv';cohort=pd.read_csv(study)
    selections=pd.read_csv(ROOT/'results/v3/final_cap1e7/selections.csv')
    unique_levels=cohort.groupby('dataset_id').log_stress.nunique()
    stress=[]
    for (dataset,policy),g in selections[selections.k<=3].groupby(['dataset_id','policy']):
        d=cohort[cohort.dataset_id==dataset]
        stress.append({'dataset_id':dataset,'panel':d.panel.iloc[0],'policy':policy,
          'n_stress_levels_full_condition':int(unique_levels[dataset]),
          'selected_amplitude_min_mpa':g.stress_amplitude.min(),
          'selected_amplitude_median_mpa':g.stress_amplitude.median(),
          'selected_amplitude_max_mpa':g.stress_amplitude.max()})
    pd.DataFrame(stress).to_csv(DEST/'secilen-gerilme-ozeti.csv',index=False)

    story=[P('Az sayıda deney hangi gerilmeden seçilmeli?','title'),
      P('Açık veri kökeni denetimi ve aynı test kümesinde altı sansürlü temel modelle karşılaştırma. Bu aşama, güçlü katkı iddiası için gereken kanıtın sınırını belirliyor.','small'),
      P('Hüküm','h'),P('Gerilme seçimi hesaplamalı olarak sınandı. İki yeni büyük yazar verisi kazandık; ancak numune-parti eşlemesi doğrulanmış iki yeni bağımsız kampanya hedefine henüz ulaşılmadı. Bir küçük tek-build pilotu var. Sonuçlar yöntem üstünlüğünün modele bağlı olduğunu gösteriyor; güvenilir bir genel tasarım yöntemi kanıtlanmış değil.'),
      P('Veri kökeni: elde edilen ve kabul edilmeyen','h'),
      T([['Kaynak','Sayım','Kabul / sınırlama']]+[[r[0],f'{r[1]} ham; {r[2]} replay',r[3]] for r in source_rows],[125,79,301]),
      P('Büyük yeni aktarım: 137 Tomaszewski +29 Diller =166 numune. Gerilme seçiminin ana ikincil analizi 40 tek-gerilmeli kaydı ayırır; kalan126 numune,9 koşul ve2 yazar kampanyasıdır. Bunlar2 doğrulanmış üretim partisi anlamına gelmez. Tarihsel309 nokta/11 kaynak yalnız eğitim ve yeniden kullanılan keşifsel doğrulama içindir.','small'),
      P('Köken hataları neden önemli?','h'),P('Diller README14 parlatılmış sonuç verirken makale13 diyor; μ15 için aynı ömürle200/300MPa gerilme aralığı çatışıyor. Tomaszewski makalesi28 numunelik tek plakadan söz ediyor; ham137 kaydı o plakaya bağlayan anahtar yok. Sadece sayı/geometri eşleşen9 kayıt doğrulanmış build sayılmadı. Dastgerdi2023 ile2022 arasındaki olası tekrar nedeniyle tüm eski aile eğitimden çıkarıldı.','small')]
    story += [PageBreak(),P('Sonuç: basit seçim işe yarayabilir, üstünlük genellenmiyor','title'),
      P('Aynı sorgu numuneleri önce sabitlendi. Aday sonuçlar açılmadan rastgele, gerilme aralığını kapsayan, yüksek gerilme ve beklenen bilgiye dayalı seçim uygulandı. k=3/5/10 her koşul için destek numunesi sayısıdır; bağımsız kampanya sayısı değildir.'),
      Image(str(DEST/'model-ve-gerilme-secimi.png'),width=505,height=207),
      T([['Karşılaştırma; C=10⁷','Alt ömür etkisi','Risk / yorum'],
         ['Yüksek gerilme, k3; hiyerarşik Basquin',f"{10**f['hier3high_vs_random']['log_life_gain']['mean']:.3f}x rastgeleye göre",'Gözlenen risk %0,42; rastgele %0,45. Çevrim maliyeti yaklaşık %70 daha az.'],
         ['Aynı seçim, k3; rastgele yorulma limiti',f"{10**f['rfl3high_vs_random']['log_life_gain']['mean']:.3f}x",'Alt ömür yaklaşık %23 kısalıyor; risk de azalıyor. Fayda-risk dengesi farklı.'],
         ['Bilgiye dayalı seçim, k3; hiyerarşik',f"{10**f['hier3active_vs_random']['log_life_gain']['mean']:.3f}x",'Rastgeleye üstünlük yok.'],
         ['Bilgiye dayalı seçim, k3; yerel eğim',f"{10**f['local3active_vs_random']['log_life_gain']['mean']:.3f}x",'Yaklaşık %4 artış; gözlenen risk %2,21’den %0,65’e.'],
         ['Bilgiye dayalı seçim, k5; iki eğimli',f"{10**f['curved5active_vs_random']['log_life_gain']['mean']:.3f}x",'Yaklaşık %2,8 artış; gözlenen risk %1,49’dan %0,96’ya.']],[226,93,186]),
      P('Tüm rakamlar yeni iki specimen-only kampanyanın çok gerilmeli koşullarında, kampanya eşit ağırlıklı ve10 sabit sorgu bölmesi üzerinden. Daha büyük alt ömür tek başına üstünlük değildir. Rakamlar keşifseldir; iki kampanyayla bootstrap aralıkları güvenilir bir popülasyon güvence sınırı vermez. 10⁶ sınırında hiyerarşik yüksek-gerilme kazancı %14; RFL etkisi yaklaşık -%25: model bağımlılığı sürüyor.','small'),
      P('Az deneyin kendisi yararlı mı?','h'),P('Hiyerarşik modelde yeni çok-gerilmeli grupların gözlenen alt-sınır aşım oranı, sıfır destekle %16,16’dan üç rastgele destekle %0,45’e indi. Bu iyileşme büyük ölçüde yeni koşula uyarlamadır; akıllı gerilme seçiminin ek katkısı küçük ve modele bağlıdır. Önceden incelenen Trombley kampanyasında aynı tasarımda risk %52,44’ten %13,18’e iniyor; %10 hedefinin üzerinde. Tek kampanya için popülasyon güven aralığı verilmedi.','small')]
    story += [PageBreak(),P('Deney tasarımı, doğrulama ve kalan iş','title'),
      P('Sabit protokol ve güçlü kontroller','h'),P('Her koşul ve seed0..9 için numunelerin %40’ı (en az3) sorguya ayrıldı; kalanlar ortak aday havuzu oldu. Tüm politikalar ve modeller aynı sorgularla sınandı. Modelin sonraki seçim fonksiyonu yalnız aday/sorgu gerilmesi ile R oranını ve daha önce açılan destek sonuçlarını kabul ediyor. Açılmamış çevrim, failure veya runout alanı verilirse hata üretiyor.'),
      P('Altı model: sansürlü monoton Basquin; aynı eğitim eğimi/saçılımıyla önselsiz yerel kayma; hiyerarşik Basquin; eğitim medyanında iki eğimli hiyerarşik Basquin; normal-normal rastgele yorulma limiti; yerel eğim/kayma MAP-Laplace kontrolü. RFL gerçek sonsuz ömür olasılığı ve sağ sansürlü olabilirlik içerir; yayımlanmış Weibull modelinin birebir tekrarı değildir. Popülasyon parametre belirsizliği bütünleştirilmedi.','small'),
      P('Önceden kaydedilen ana protokol, aşama3 uyumlarından önce yazıldı; kaynak sonuçları ve eski analiz zaten görülmüştü. Bu nedenle ileriye dönük kör doğrulama değildir. Tek-gerilmeli grupları ayıran ek not, hesaplama ve toplam geçiş sayısı görüldükten sonra, politika bazlı metrikler incelenmeden kaydedildi; değişiklik yalnız gerilme kovaryatına dayanır.','small'),
      P('Denetim makbuzları','h'),
      T([['Kontrol','Kanıt'],['Hesaplama','Her sınırda430 görev,180.960 tahmin,9.880 seçilmiş destek kaydı. Aynı hesaplamalar yeni fiziksel deney değildir.'],
         ['Bağımsız aritmetik','Her sınırda3.024 özet ve4.032 eşlenik ortalama yeniden hesaplandı; en büyük fark7,45×10⁻⁹, çevrim ölçeğinde yuvarlama.'],
         ['Sorgu ve sızıntı','Tüm politika/model/k eşleşmelerinde sorgu kimliği, ayrık destek havuzu ve aile dışlama denetimleri geçti. Yeni ham dönüşümler ikinci okuyucuyla birebir.'],
         ['RFL ve sayısal çözüm','11 popülasyon uyumu yakınsadı; iki tarihsel uyumda yorulma-limiti saçılımı üst sınıra değdi.96/192 düğümle1.048 kantilde en büyük fark8,92×10⁻¹⁰ log10.'],
         ['Birim kontrolleri','13 RFL ve 6 seçim testi geçti. Fisher bilgisi bağımsız integral kontrolünde ve sansürlü risk farkları 931 durumda doğrulandı.'],
         ['Taze tam tekrar','İki çevrim bütçesi ve iki alt kümede 20 tahmin/özet/karşılaştırma tablosu yeniden üretildi; tüm değerler birebir aynı.']],[123,382]),
      P('Güçlü katkı için bir sonraki somut adım','h'),P('Öncelik daha fazla model ayarlamak değil, en az iki üretim kampanyasında gerçek numune→build→toz partisi anahtarını elde etmek. Hazır yerel istek taslakları Tomaszewski’nin137 satırını28 numunelik makaleyle eşleştirmeyi, Diller’in gerilme çatışmalarını ve build tablosunu, Trombley’nin dört build eşlemesini soruyor. Yeni plaka çıktığında politika ve model yeniden seçilmeden aynı sorgu protokolüyle sınanmalı; çevrim maliyeti yanında güvenlik ve kullanılabilir alt ömür birlikte ölçülmeli.'),
      P('Birincil kaynaklar','h'),P('Tomaszewski: Zenodo10.5281/zenodo.7650061; makaleler10.1016/j.ijfatigue.2022.107378 ve2024.108225. Diller: Zenodo10.5281/zenodo.21105346; makale10.1111/ffe.14375. Dastgerdi:10.1016/j.addma.2023.103559; eski aile10.1016/j.ijfatigue.2022.107025. Trombley:10.1038/s41598-025-97031-1; veri10.13011/m3-c93d-z035. RFL: Pascual–Meeker1999,10.1080/00401706.1999.10485925. Ayrıntılı URL, lisans, kaynak sayfası ve SHA256 listeleri tekrar üretim paketinde.','small')]
    doc=SimpleDocTemplate(str(DEST/'asama3-gerilme-secimi.pdf'),pagesize=A4,
        leftMargin=45,rightMargin=45,topMargin=47,bottomMargin=40,
        title='AM316L - Veri kökeni ve gerilme seçimi',author='Research workspace')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (DEST/'headline-facts.json').write_text(json.dumps(fact,indent=2,ensure_ascii=False)+'\n')
    print(str(DEST/'asama3-gerilme-secimi.pdf'))
if __name__=='__main__':main()
