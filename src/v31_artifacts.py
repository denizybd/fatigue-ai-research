"""Source-audited first-exposure extension: compact Turkish evidence report."""
from __future__ import annotations
import html,json,os,shutil
from pathlib import Path
import numpy as np,pandas as pd
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
DEST=Path(os.environ.get('V31_OUTPUT',ROOT/'manuscript/v31'))
PANEL='external_identity_qualified_firstblock'
LABEL={'pooled':'Havuzlanmış Basquin','matched_intercept':'Önselsiz yerel kayma','hierarchical':'Hiyerarşik Basquin','curved_hierarchical':'İki eğimli hiyerarşik','rfl':'Rastgele yorulma limiti','local_slope':'Yerel eğim + kayma'}
POL={'random':'Rastgele','high_stress':'Yüksek gerilme','stress_span':'Aralığı kapsama','active_query_variance':'Beklenen bilgi'}
F=Path(matplotlib.get_data_path())/'fonts/ttf'
for n,p in [('V31','DejaVuSans.ttf'),('V31Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,str(F/p)))
pdfmetrics.registerFontFamily('V31',normal='V31',bold='V31Bold')
TEAL=colors.HexColor('#176c83')
S={n:ParagraphStyle(n,fontName='V31',fontSize=z,leading=l,spaceAfter=a) for n,z,l,a in [('body',9,12.2,7),('small',7.7,10.4,5),('cell',7.6,10.2,0)]}
S['title']=ParagraphStyle('title',fontName='V31Bold',fontSize=18,leading=22,spaceAfter=10,textColor=TEAL)
S['h']=ParagraphStyle('h',fontName='V31Bold',fontSize=11,leading=14,spaceBefore=7,spaceAfter=5,keepWithNext=True)
def P(x,k='body'):return Paragraph(html.escape(str(x)).replace('\n','<br/>'),S[k])
def T(rows,widths):
 t=Table([[P(c,'cell') for c in r] for r in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f4')),('LINEBELOW',(0,0),(-1,0),.6,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));return t
def footer(c,d):
 c.saveState();c.setFont('V31',7);c.setFillColor(colors.HexColor('#52616a'))
 c.drawString(45,821,'AM316L | Aşama 3.1: fiziksel kimlik ve ilk yükleme bloğu | 20 Ekim 2026')
 c.drawString(45,24,'Keşifsel hesaplama; yeni fiziksel deney ve dış yazışma yapılmadı.');c.drawRightString(550,24,str(d.page));c.restoreState()
def main():
 DEST.mkdir(parents=True,exist_ok=True)
 ss={c:pd.read_csv(ROOT/f'results/v3/identity_cap{c}/summary.csv') for c in ['1e7','1e6']}
 pp={c:pd.read_csv(ROOT/f'results/v3/identity_cap{c}/paired_comparisons.csv') for c in ss}
 def metric(c,model,policy,k,name,paired=False,comparison='versus_random'):
  d=pp[c] if paired else ss[c];q=(d.panel==PANEL)&(d.model==model)&(d.policy==policy)&(d.k==k)&(d.metric==name)
  if paired:q&=d.comparison==comparison
  return float(d.loc[q,'mean'].iloc[0])
 facts={}
 for cap in ss:
  rows=[]
  for model in LABEL:
   for policy in POL:
    for k in [0,3,5]:
     rows.append({'model':model,'policy':policy,'k':k,'q10_geometric_cycles':10**metric(cap,model,policy,k,'finite_log_lower'),
      'known_risk':metric(cap,model,policy,k,'known_risk'),'upper_risk':metric(cap,model,policy,k,'upper_risk'),
      'availability':metric(cap,model,policy,k,'availability'),'support_cycles':metric(cap,model,policy,k,'support_cycles'),
      'life_ratio_vs_random':10**metric(cap,model,policy,k,'log_life_gain',True),
      'risk_change_lo_vs_random':metric(cap,model,policy,k,'true_risk_change_lo',True),
      'risk_change_hi_vs_random':metric(cap,model,policy,k,'true_risk_change_hi',True)})
  facts[cap]=rows
 (DEST/'sayisal-bulgular.json').write_text(json.dumps(facts,indent=2,ensure_ascii=False)+'\n')
 pd.DataFrame([dict(cap=c,**r) for c,rows in facts.items() for r in rows]).to_csv(DEST/'ana-karsilastirma.csv',index=False)
 for cap in ss:
  for name in ['summary.csv','paired_comparisons.csv','by_condition.csv','success_gates.csv']:
   shutil.copy2(ROOT/f'results/v3/identity_cap{cap}'/name,DEST/(cap+'-'+name))
 d=pd.read_csv(ROOT/'data/processed/v3/firstblock/merot52.csv')
 pd.read_csv(ROOT/'data/external_v3/continuation_papers/merot_first_exposure_air_nominal43.csv').to_csv(DEST/'dogrulanmis-ilk-blok43.csv',index=False)
 shutil.copy2(ROOT/'literature/v3_campaigns/continuation_papers/merot_source_specimen_build_crosswalk70.csv',DEST/'numune-uretim-toz-eslemesi70.csv')
 conditions=sorted(d[(d.panel==PANEL)&d.dataset_id.map(d.groupby('dataset_id').size()).ge(6)].dataset_id.unique())
 names=['FS18-019 / ön korozyon','FS18-019 / referans','FS18-020 / ön korozyon']
 counts=[]
 for cap in ss:
  sel=pd.read_csv(ROOT/f'results/v3/identity_cap{cap}/selections.csv');sel=sel[(sel.dataset_id.isin(conditions))&(sel.k<=3)].copy()
  for (condition,policy,stress),g in sel.groupby(['dataset_id','policy','stress_amplitude']):
   counts.append({'cap':cap,'condition':condition,'policy':policy,'stress_amplitude_MPa':round(stress,9),'selected_count_over10_splits_k3':len(g),'fraction_of30_selections':len(g)/30})
 pd.DataFrame(counts).to_csv(DEST/'gerilme-secim-sayilari.csv',index=False)
 # Censoring identification intervals, not confidence intervals.
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
 fig,axes=plt.subplots(1,2,figsize=(10,3.1),sharex=True)
 for ax,model in zip(axes,['hierarchical','rfl']):
  for j,policy in enumerate(POL):
   lo=100*metric('1e6',model,policy,3,'known_risk');hi=100*metric('1e6',model,policy,3,'upper_risk')
   ax.plot([lo,hi],[j,j],color='#207b8a',lw=3);ax.scatter([lo,hi],[j,j],c=['#207b8a','#d89335'],s=26,zorder=3)
  ax.set_yticks(range(4),POL.values());ax.invert_yaxis();ax.axvline(10,ls='--',lw=1,color='#ab5151');ax.set_xlim(-1,46)
  ax.set_xlabel('Gerçek aşım oranının tanımlama aralığı (%)');ax.set_title(LABEL[model]);ax.grid(axis='x',alpha=.2)
 fig.suptitle('Aynı sorgular, üç destek; C = 10⁶ çevrim',fontsize=11)
 fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(DEST/'sansur-ve-risk.png',dpi=210);plt.close(fig)
 # Actual finite-pool stress choices, displayed without reading unseen outcomes.
 fig,axes=plt.subplots(1,3,figsize=(11,3.1))
 cc=pd.DataFrame(counts);cc=cc[cc.cap=='1e6']
 for ax,condition,title in zip(axes,conditions,names):
  levels=sorted(d[d.dataset_id==condition].stress_amplitude.unique())
  q=cc[cc.condition==condition]
  for j,policy in enumerate(POL):
   z=q[q.policy==policy]
   for r in z.itertuples():
    ax.scatter(r.stress_amplitude_MPa,j,s=8+r.selected_count_over10_splits_k3*8,c='#207b8a',alpha=.8)
    ax.annotate(str(r.selected_count_over10_splits_k3),(r.stress_amplitude_MPa,j),ha='center',va='center',color='white',fontsize=7)
  ax.set_yticks(range(4),POL.values() if ax is axes[0] else ['']*4);ax.invert_yaxis();ax.set_xticks(levels);ax.set_xlabel('Gerilme genliği (MPa)');ax.set_title(title,fontsize=9);ax.grid(axis='x',alpha=.15)
 fig.suptitle('İlk üç seçimin gerilmesi: dairede 10 bölmedeki seçim sayısı',fontsize=11)
 fig.tight_layout(rect=[0,0,1,.9]);fig.savefig(DEST/'hangi-gerilme.png',dpi=210);plt.close(fig)
 gate=[
 ['Mérot / Zenodo6653187',70,43,'3 gerçek üretim, 2 toz partisi; tek araştırma kampanyası. 31 nominal kayıt seçim karşılaştırmasına girer.'],
 ['Dastgerdi2023',8,6,'Gerçek numune ID ve kaynakta tek build; yazar build kodu/toz partisi/sıcaklık belirsiz. Ayrı pilot.'],
 ['Trombley2025',129,0,'Eski kampanya; ortak toz partisi kaynakta açık. Numune→4 üretim eşlemesi yok; tezde de numune→üretim anahtarı bulunmadı.'],
 ['Zhou2026 / Figshare33392110',14,0,'Yorulma satırları anonim. 8 CT kimliği bunlara bağlanamıyor; karantinada.'],
 ['Diğer yeni kaynak taraması','—',0,'Kopec veri istek üzerine; Voloskov ve Spiller ilk-blok/kimlik eşlemesi eksik; Prochaska ve diğer adaylar kapıyı geçmedi.']]
 pd.DataFrame(gate,columns=['source','source_rows','primary_or_pilot_rows','decision']).to_csv(DEST/'kaynak-kapisi.csv',index=False)
 story=[P('Numuneden üretim partisine: yeni kanıt','title'),P('Yeni kaynak kurtarma ve aynı test kümesinde gerilme seçimi. Bu ek rapor, önceki Aşama3 raporundaki “yeni tam kimlikli RT kampanya yok” tespitini günceller. Eski hesaplamalar korunur.','small'),
 P('Somut kazanım','h'),P('Mérot’un kamuya açık ham verisini tezdeki gerçek üretim kayıtlarıyla birleştirdik. İlk sabit genlikli yükleme bloğundan 70 benzersiz fiziksel numune doğrulandı. Bunların 43’ü havada 20°C ve nominal gerilme kullanıyor: 17 kırılma, 26 sağ sansür. Üç üretim aynı araştırma programının parçaları; üç bağımsız laboratuvar sayılmaz.'),
 T([['Kaynak plaka','Üretim kaydı','Toz partisi'],['02','FS18-019','TLS0993/1/1'],['03','FS18-020','TLS0993/1/1'],['04','FS19-006','TLS1051/1/1']],[105,165,235]),
 P('Neyi geçerli saydık?','h'),P('Her numunenin yalnız ilk bloğu alındı: o blokta kırıldıysa gerçek N’de olay; sağ kaldıysa gerçek durdurma N’sinde sağ sansür. Sonraki yüksek gerilme basamakları, eşdeğer ömürler ve kırılma sonrası kusur ölçümleri modele girmedi. Bu nedenle önceki aşamada dışlanan 98 dönüştürülmüş veri noktası tekrar kabul edilmiş değildir. Aynı fiziksel koordinata bağlanan tüm isimler ve eksik kimlikler karantinada.'),
 P('Dokuz küçük hacimli numunede gerilme yerel Kt düzeltmeli; ana nominal gruptan ayrı tutuldu. 18 tuz sisi deneyi de ana karşılaştırma dışında. Korozyon ve geometri deney öncesi koşullardır. F8’in farklı ön korozyon yöntemi kayıtlıdır; iki kayıtlı koşulu seçim karşılaştırmasına zaten girmiyor.','small'),
 P('Ek bağımsız kampanya arayışı','h'),T([['Kaynak','Kabul / sınır']]+[[r[0],r[3]] for r in gate],[135,370]),
 P('Tam kimlikli, yöntem uyumlu yeni oda sıcaklığı kanıtı şu anda bir yazar kampanyasıdır. Dastgerdi’nin 6 numunesi ayrı bir kaynak programından gelir; eksik sıcaklık ve olası eski aile tekrarı nedeniyle ana RT kanıtına katılmadı. İki tam bağımsız oda sıcaklığı kampanyası hedefi henüz kapanmış değil.','small')]
 rows=[['Model; k3','Yüksek / rastgele alt ömür','Risk aralığı: rastgele → yüksek']]
 for model in LABEL:
  ratio=10**metric('1e6',model,'high_stress',3,'log_life_gain',True)
  a,b=[(100*metric('1e6',model,p,3,'known_risk'),100*metric('1e6',model,p,3,'upper_risk')) for p in ['random','high_stress']]
  rows.append([LABEL[model],f'{ratio:.3f}×',f'%{a[0]:.2f}–{a[1]:.2f} → %{b[0]:.2f}–{b[1]:.2f}'])
 story += [PageBreak(),P('Daha uzun sınır, kanıtlanmış güvenlik değil','title'),
 P('Altı sansürlü model ve dört seçim politikası, önceden sabitlenmiş aynı sorgu numuneleriyle sınandı. k=3 veya 5 destek numunesi koşul başınadır. Her koşulda en az 6 kayıt gereği, ana seçim analizi 43 kaydın 31’ini, 3 koşulu ve 2 fiziksel üretimi kapsar. 21 numune ön korozyonlu; 10’u referanstır. On bölme aynı fiziksel numuneleri tekrar kullanır.'),
 T(rows,[152,107,246]),
 P('Tablo: kaynak durdurmasıyla uyumlu C=10⁶. Ömür oranı ortak sonlu tahminlerde geometrik ortalamadır. Risk aralığı sağ sansürden kaynaklanan tanımlama aralığıdır; güven aralığı değildir. Önselsiz modelin kullanılabilirliği rastgelede %73,3, yüksek gerilmede %83,3; diğer beş modelde %100. Eksik tahminler güvenli sayılmadı.','small'),
 Image(str(DEST/'sansur-ve-risk.png'),width=505,height=157),
 P('Kararın özü','h'),P('Yüksek gerilme k3, hiyerarşik alt ömrü %33,6 artırırken gözlenen destek çevrimini yalnız %7,5 azaltıyor. Aynı sorgularda gerçek risk değişimi -4,44 ile +26,11 yüzde puan arasında kalıyor. RFL’de ömür artışı %8,5; risk değişimi -1,67 ile +6,67 puan. Dolayısıyla bu artışların güvenli bir kazanç olduğunu gösteremedik.'),
 P('Beklenen bilgi politikası C=10⁶’da hiyerarşik alt ömrü %30,6, RFL’yi %8,4 artırıyor; sansürlü risk belirsizliği sürüyor. Aralığı kapsama çoğu modelde rastgeleye yakın. Sıfır destekle hiyerarşik risk %5,00–26,11; rastgele k3 ile %5,83–36,94: bu yeni kampanyada “az deney her zaman güvenliği artırır” sonucu da çıkmıyor.','small'),
 P('Önceden dondurulmuş ana C=10⁷ koşulunda yüksek-gerilme sonuçları aynıdır. Bilgi politikası hiyerarşik/RFL artışları %20,5/%12,5 olur. Kaynağın tüm hava sansürleri 10⁶’da olduğu için 10⁷ planlaması açık bir durdurma-modeli uyumsuzluğu duyarlılığıdır; görülmeyen çevrimler üretilmedi.','small')]
 story += [PageBreak(),P('Hangi gerilme seçildi, neyi kanıtladık?','title'),
 Image(str(DEST/'hangi-gerilme.png'),width=505,height=142),
 T([['Koşul','Tam aday aralığı','Yüksek gerilme k3; seçilen seviyeler'],
 ['FS18-019 / referans','225–325MPa','325MPa: 30/30 seçim. Aynı seviyede farklı numune tekrarları.'],
 ['FS18-019 / ön korozyon','150–275MPa','200/225/250/275MPa; sayılar 4/18/3/5.'],
 ['FS18-020 / ön korozyon','150–225MPa','175/225MPa; sayılar 13/17.']],[145,95,265]),
 P('Her sorgu bölmesi aday havuzunu değiştirdiği için “en yüksek” seviye bölmeye bağlıdır. Bu çalışma gözlenmiş sonlu aday havuzundan seçim yapar; sürekli gerilme optimizasyonu veya yeni bir malzeme için evrensel MPa önerisi değildir. Model bilgisi çoğu kez yüksek gerilmeye yöneldi; üstünlüğü doğrulanmadı.','small'),
 P('Güvenilirlik denetimi','h'),P('İki bağımsız okuyucu 70 numune referansını, üretim/toz tablosunu ve kaynak ilk-blok kayıtlarını doğruladı. Her çevrim sınırında 50 görev, 11.520 tahmin ve 920 destek seçimi üretildi. Bağımsız aritmetik, ortak sorgu/havuz ve aile dışlama kontrolleri geçti; en büyük ortalama farkı 9,31×10⁻¹⁰. RFL’nin iki gerçek eğitim uyumu yakınsadı; yedek modele geçiş ve parametre sınırına temas yok.'),
 P('Taşınabilir temiz tekrar, kullanılmayan eski Trombley kayıtları olmadan 367 satırla aynı 50 görevi kurdu; iki sınırdaki 12 tablodaki hesap değerleri tam eşleşti; yalnız önbellek imzası değişti. RFL normal-normal modelidir; nüfus parametre belirsizliği bütünleştirilmedi. Her panel tek yazar kampanyası olduğundan popülasyon güven aralığı hesaplanmadı. success_gates dosyasındaki sıfır geçiş, tek kampanya nedeniyle değerlendirme yapılamamasıdır; politika başarısızlığı testi değildir.','small'),
 P('Güçlü katkıya giden somut yön','h'),P('Şu an savunulabilir çıktı, izlenebilir bir ilk-blok veri kurtarma ve sansür altında gerilme seçiminin fayda-risk sınırlarını gösteren yeniden üretilebilir ölçüttür. Genel güvenilir tasarım yöntemi veya yeni algoritma üstünlüğü henüz yok. İkinci yöntem uyumlu bağımsız kampanya ve 10⁶ üstünü gerçekten izleyen sabit genlikli deneyler olmadan güvenlik iddiası büyütülmemeli. Yeni kampanyada kimlik tablosu, ortak sorgular, altı model ve dört politika sonuçlar görülmeden sabitlenmeli; yalnız daha uzun ömür değil, risk üst sınırı ve çevrim maliyeti birlikte karşılaştırılmalı.'),
 P('Güncel öncül çalışma: Wu vd., IJFatigue109943, yayınevi önizlemesinde fiziksel kontroller, grup ayrımları ve hedef verisiyle uyarlama içeriyor. Tam metin/ekleri elde edilmedi. Bu başlıklarda tek başına yenilik iddiası kurulamaz; az deneyle gerilme seçimi ve sansürlü güvenilirlik bakımından ayrıntılı fark henüz doğrulanmış değil.','small'),
 P('Birincil kaynaklar: Mérot veri DOI10.5281/zenodo.6653187 (CC BY4.0; filtreleme/eşleme yapıldı); tez tel-03688021v1, PDF84–85/114–115/279–280; makale10.1016/j.ijfatigue.2021.106552. Dastgerdi10.1016/j.addma.2023.103559. Wu10.1016/j.ijfatigue.2026.109943 (yalnız yayınevi önizlemesi). Ham veri, kaynak URLleri, karantina, protokol ve denetim makbuzları tekrar paketinde; tez PDF’si dağıtılmıyor.','small')]
 doc=SimpleDocTemplate(str(DEST/'asama3-1-kimlik-ve-gerilme.pdf'),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=47,bottomMargin=40,title='AM316L - Fiziksel kimlik ve gerilme seçimi',author='Research workspace')
 doc.build(story,onFirstPage=footer,onLaterPages=footer)
 print(str(DEST/'asama3-1-kimlik-ve-gerilme.pdf'))
if __name__=='__main__':main()
