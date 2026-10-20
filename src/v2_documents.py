"""Evidence-bounded phase-2 reports generated from saved tables."""
from __future__ import annotations
import html,json
from pathlib import Path
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
from src.v2_prepare import ROOT

OUT=ROOT/'manuscript/v2';OUT.mkdir(parents=True,exist_ok=True)
F=Path(matplotlib.get_data_path())/'fonts/ttf'
for name,file in [('VBody','DejaVuSans.ttf'),('VBold','DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(F/file)))
pdfmetrics.registerFontFamily('VBody',normal='VBody',bold='VBold')
TEAL=colors.HexColor('#176c83');GRAY=colors.HexColor('#56656d')
ST={
 'title':ParagraphStyle('title',fontName='VBold',fontSize=18,leading=22,spaceAfter=12,textColor=TEAL),
 'h':ParagraphStyle('h',fontName='VBold',fontSize=11.4,leading=15,spaceBefore=10,spaceAfter=6,keepWithNext=True),
 'body':ParagraphStyle('body',fontName='VBody',fontSize=9.2,leading=13,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='VBody',fontSize=7.7,leading=10.5,spaceAfter=6),
 'cell':ParagraphStyle('cell',fontName='VBody',fontSize=8,leading=10.5),
 'brief':ParagraphStyle('brief',fontName='VBody',fontSize=9.1,leading=12,spaceAfter=7)}

def P(s,kind='body'):
    return Paragraph(html.escape(str(s)).replace('\n','<br/>'),ST[kind])
def H(s):return P(s,'h')
def T(rows,widths):
    t=Table([[P(v,'cell') for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f4')),
        ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t
def fig(name,width=480):
    from PIL import Image as I
    p=ROOT/'figures/v2'/name
    with I.open(p) as x:w,h=x.size
    return Image(str(p),width=width,height=width*h/w)
def footer(c,d):
    c.saveState();c.setStrokeColor(TEAL);c.line(45,812,550,812)
    c.setFont('VBody',7);c.setFillColor(GRAY)
    c.drawString(45,821,'AM316L fatigue | Phase 2 working research note | 20 October 2026')
    c.drawString(45,24,'Computational study. Historical experiments are credited to their original authors.')
    c.drawRightString(550,24,str(d.page));c.restoreState()
def build(name,story):
    doc=SimpleDocTemplate(str(OUT/name),pagesize=A4,leftMargin=45,rightMargin=45,
        topMargin=47,bottomMargin=40,title=name.replace('_',' '),author='Research workspace')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
def summary(folder):return pd.read_csv(ROOT/f'results/v2/{folder}/summary.csv')
def choose(d,panel,model,k,bound='raw'):
    return d[(d.panel==panel)&(d.model==model)&(d.k==k)&(d.bound==bound)].iloc[0]
def pct(z):return f'{100*z.risk_lower:.2f}-{100*z.risk_upper:.2f}%'

def main():
    internal=summary('fulltraining');ext=summary('external_fulltraining')
    h0=choose(internal,'A','hierarchical',0);h3=choose(internal,'A','hierarchical',3)
    gain=10**(h3.mean_log_lower-h0.mean_log_lower)
    contrasts=pd.read_csv(ROOT/'results/v2/fulltraining/paired_contrasts.csv')
    q=contrasts[(contrasts.panel=='A')&(contrasts.model=='hierarchical')&(contrasts.bound=='raw')&(contrasts.k==3)]
    g=q[q.metric=='log_gain'].iloc[0];r=q[q.metric=='true_risk_change_hi'].iloc[0]
    facts={'internal_raw_A':{'risk_k0':pct(h0),'risk_k3':pct(h3),'geometric_gain':gain,
        'gain_descriptive95':[10**g.lo95,10**g.hi95],'true_risk_increase_hi95':r.hi95},
        'historical_methods_reviewed':{'rows':309,'curves':32,'source_blocks':11},
        'external':{'specimens':129,'conditions':3,'campaigns':1,'support_k3_total':9,'fixed_queries_per_mechanism':99},
        'primary_success':False,'interpretation':'Useful source-audit and counterexample benchmark, not a new dependable-design method.'}
    (OUT/'headline_facts.json').write_text(json.dumps(facts,indent=2)+'\n')

    en=[]
    en += [P('Provenance first: how far do three fatigue endpoints carry a new condition?','title'),
      P('A source-audited, censored AM316L benchmark with an acquired external campaign. The prespecified useful-calibration criterion was not met.','small'),
      H('Finding'),P(f'In a retrospective full-training model-based track, three endpoints per new condition increased the geometric lower-life limit by {gain:.2f}x while the source-balanced danger identification interval fell from {pct(h0)} to {pct(h3)}. The descriptive source-bootstrap gain interval is {10**g.lo95:.2f}-{10**g.hi95:.2f}x and includes no improvement. Some sources became less safe. This is a promising aggregate trend, not a demonstrated reliable-design algorithm.'),
      H('Why provenance had to precede fitting'),
      P('The original public-data pilot contained 1,126 approximately digitized points. Original-methods review identified 98 records from Merot et al. as stepped-load/damage-equivalent observations rather than ordinary independent constant-amplitude lifetimes. They were excluded. Further publication-level reuse, unresolved figure-to-experiment mappings and a maximum-stress/amplitude conflict required quarantine. The main cohort contains 309 points, 32 database curves and 11 source blocks with reviewed experimental methods. These are not 11 certified independent laboratories, nor are database row IDs physical specimen IDs.'),
      fig('01_provenance_gate.png',465),
      P('Additional source-supported corrections: one Wood endpoint labelled runout was a fracture; one Kedziora Renishaw group inherited an unsupported heat treatment. Corrections are applied only to derived phase-2 data. Raw files and v1 outputs remain immutable. These findings concern our open-data benchmark and do not prove an error in Centola et al.’s unavailable 518-row dataset. [1-4]','small')]
    en += [PageBreak(),H('Frozen question and models'),
      P('For an unseen provenance source, do 3, 5 or 10 endpoints from one new condition improve useful lower-life limits? All other curves from that source remain outside population fitting and calibration. Conditions mean source S-N series, not verified build batches. All model features and population parameters are learned from historical fitting sources.'),
      T([['Panel','Endpoints per condition','Eligible curves / sources','Fixed-query minimum'],
         ['A: primary','0, 3','18 / 9','5'],['B: secondary','0, 3, 5','14 / 6','5'],['C: limited secondary','0, 3, 5, 10','6 / 5','5']], [85,145,145,130]),
      P('Seeds 0, 17 and 42 define outcome-blind record-ID permutations. Reserve the maximum support pool once per panel and use all remaining records as the same queries for every k. The panels have different populations; they are not a single learning curve. Runouts contribute a survival likelihood, not an exact failure density.'),
      P('Baselines: (i) pooled monotone censored lognormal Basquin; (ii) a target-only intercept update with historical slope/scatter; (iii) a condition-random-intercept Basquin model, updating a proper target intercept posterior with censored support. The predictive lower decile integrates specimen scatter and target intercept uncertainty. Population parameters are empirical Bayes estimates; the main bounds omit their estimation uncertainty. A training-source bootstrap mixture with 20 replicates from 11 historical sources assesses this externally. A continuous two-slope monotone curve with a training-only median stress knot is a prespecified curvature sensitivity.'),
      H('Calibration and claim discipline'),
      P('The original primary criterion required a useful 90% endpoint-calibrated bound, risk at most 10%, a paired risk-increase limit and a greater-than-1.25x life gain supported by descriptive source-bootstrap intervals. Source review leaves only 4-6 calibration blocks when at least four fitting blocks are retained. The required finite-sample rank exceeds the calibration count, so the literal bound is zero. It is safe but useless and fails the utility criterion. This finite-rank result applies to this frozen calibration protocol, not to every parametric or survival method.'),
      P('A separately recorded full-training raw track fits all other verified sources and reports model-based 10th percentiles. It does not replace the failed calibrated primary test. Hierarchical borrowing and modern survival conformal prediction are established prior work. Missing potential censoring times on failures rule out direct Type-I calibration, but modern right-censoring methods exist; none guarantees arbitrary manufacturing-source shift. [5-8]'),
      H('Risk and utility'),P('Danger is L>T. For a runout C<T, L<=C establishes safety for that event; L>C remains ambiguous. Report [known violations/n, (known+ambiguous)/n]. These are censoring identification endpoints, not confidence intervals. Average within curve, then source, then seeds. Utility is paired log10(Lk/L0) on identical queries; larger unsafe limits are not useful. Source bootstrap intervals are descriptive because outer models reuse training sources.')]
    en += [PageBreak(),H('Internal results: average gain is not source reliability'),
      fig('02_internal_risk_utility.png',485),
      P(f'The full-training raw A-panel gain is {gain:.2f}x ({10**g.lo95:.2f}-{10**g.hi95:.2f}x descriptive 95% interval). The upper bootstrap endpoint for the upper identified true-risk increase is +{100*r.hi95:.2f} percentage points, above the 2-point noninferiority margin. Hence even the secondary raw result does not meet the intended robust positive-claim standard.'),
      fig('03_source_heterogeneity.png',450),
      P('Solberg’s source risk upper endpoint falls from 100% to 3.03%, driving most of the mean improvement. Lai increases from 23.33% to 42.60%; Spierings from 0% to 6.94%; Kedziora from 0% to 11.11%. These are small-source descriptive estimates, not certificates. Deleting the unfavorable sources or treating seed repeats as new experiments would be invalid.','small')]
    rows=[['Mechanism / k','Danger fraction','Geometric lower life']]
    for panel,label in [('external_random','Random'),('external_chronological','Chronological')]:
        for k in [0,3,5,10]:
            z=choose(ext,panel,'hierarchical',k)
            rows.append([f'{label} / {k}',pct(z),f'{10**z.mean_log_lower:,.0f} cycles'])
    en += [PageBreak(),H('Acquired external campaign: the limits become shorter and less dangerous'),
      P('Trombley, Birnbaum and Allison’s public Materials Commons pages provide 129 complete named as-built specimens: 44/40/45 at 1.5/2.5/5.0 mm diameter. The article states 130; one incomplete page is excluded without imputation. All 154 available fatigue records and the 129-record subset were independently checked against the public HTML. No strong historical-coordinate reuse signal was found. This is one campaign with three related conditions. Four builds are reported, but specimen-to-build mapping is not certified. [9-10]'),
      P('Tests were performed in 2019-2021, at 20 kHz and R=-1. The failure endpoint is a resonance-drop/visible-crack criterion, potentially before full fracture. Thus this is a cross-campaign, cross-endpoint stress test, not clean validation of an identical fracture-time distribution. Preserve actual runout endpoints; do not invent a universal potential censoring time for failures.'),
      T(rows,[155,145,205]),
      P('k is per diameter condition: k=3 uses nine support endpoints in total. Each mechanism and seed keeps 99 common queries over its k values. Random and chronological mechanisms have different query sets, so their difference cannot identify a causal benefit of a selection policy. One campaign provides no independent campaign-level confidence interval.'),
      P('Random k3 reduces danger from 53.66% to 13.19%, still above 10%, by lowering the life limit about 4.68x rather than extending it. The 20-population-bootstrap mixture has 16.42% random-k3 danger; the two-slope model has 13.20%. Chronological k3 gives 1.96% on its own query population. We retain every result rather than select the most favorable mechanism.'),
      P('The original article uses a Weibull random-fatigue-limit model. Our finite curvature control is not its reproduction, and superiority over that relevant physical comparator is untested. This limitation must remain in any communication. [9,11]','small')]
    en += [PageBreak(),H('Controls, sensitivities and verification'),
      fig('04_external_learning.png',480),
      P('An explicitly post-result diagnostic holds the hierarchical population slope/scatter fixed and replaces prior borrowing with an unpooled censored target intercept. At k0 its reference equals the same hierarchical predictive distribution; all-runout supports remain unavailable. This control avoids attributing a changed population scatter to a benefit from shrinkage. It was not used to rescue the original primary claim.'),
      P('On matched internal k3 queries, hierarchical versus this simple control gives about 1.10x life, with a descriptive interval including no gain. Externally on random supports, the control has 6.99% danger versus 13.19% for the hierarchy, at approximately 1/1.42 of its life limit. There is a tradeoff, not demonstrated prior-specific superiority. Availability and common-query masks are retained.'),
      P('Near-coordinate clustering removes one historical point; the A-panel risk endpoints remain unchanged. Excluding Afkhami, whose stress-axis visual verification remains unresolved, gives k3 risk 9.00-9.70%. Full-family/weak-edge and broader database-labelled analyses are sensitivity results, not replacements for reviewed-source evidence. They retain unresolved original-experiment and stress-definition issues.'),
      P('All 31 synthetic model/evaluation tests pass. Two independently written arithmetic checks reproduce core source-balanced summaries and paired censoring contrasts. Direct scalar numerical integration checks mixed-censor posteriors. Critical strict, full-training and external predictions were replayed byte for byte. These establish computational consistency, not independent physical replication. Fit statuses, split IDs, hashes and exact commands are saved.'),
      H('Boundaries'),P('The cohort remains digitized with incomplete physical specimen/batch IDs. Several method-reviewed sources lack exhaustive point matching. Original author endpoints and sampling protocols differ; staircase-selected stresses and retrospective random supports are not an optimized sequential test policy. Counts of endpoints are not measured machine hours or monetary savings. We did not run new physical experiments, obtain Centola’s original data/code, reproduce the BNN/Owen calculations, or establish general source-conditional coverage.')]
    en += [PageBreak(),H('Contribution assessment and the next discriminating experiment'),
      P('The defensible contribution is a provenance-corrected benchmark, concrete source/label corrections and a documented counterexample to interpreting average few-shot improvement as reliable performance in every new condition. The hierarchical method itself is established. This package supports a focused technical discussion with Tridello, not a claim of a new validated fatigue-design algorithm.'),
      P('The next question should be: with a fixed test budget, which stress levels reveal a harmful new-condition shift and produce the largest useful lower-life limit at acceptable source-specific risk? First secure physical specimen/build IDs, consistent failure definitions and actual censoring plans. Then benchmark the published random-fatigue-limit model and the matched simple intercept control. Freeze one common query set across random, stress-spanning and chronological support policies; choose any policy only using development campaigns. Test on additional independent campaigns and report source-specific failures, not only an average. A new campaign and a frozen protocol are required for a strong confirmatory claim.'),
      H('References and evidence'),
      P('[1] Zhang & Xu. FatigueData-AM2022 v2. Data DOI 10.6084/m9.figshare.22337629.v2; descriptor DOI 10.1038/s41597-023-02150-x. CC BY 4.0.','small'),
      P('[2] Merot et al. Observations on process/corrosion defects. DOI 10.1016/j.ijfatigue.2021.106552. Original methods section 2.4/Table 3; source-method evidence in provenance_report.md.','small'),
      P('[3] Wood et al. Materials 12,4203 (2019). DOI 10.3390/ma12244203. Sections 2.1/2.9/3.4.1, Figures 9/14. https://pmc.ncbi.nlm.nih.gov/articles/PMC6947212/','small'),
      P('[4] Kedziora et al. Materials 15,6278 (2022). DOI 10.3390/ma15186278. Sections 2/3.3. https://pmc.ncbi.nlm.nih.gov/articles/PMC9505810/','small'),
      P('[5] Liu, Lu & Hoogenboom (2017). Hierarchical Bayesian fatigue data analysis. DOI 10.1016/j.ijfatigue.2017.03.043.','small'),
      P('[6] Candes, Lei & Ren (2023). Conformalized survival analysis. DOI 10.1093/jrsssb/qkac004.','small'),
      P('[7] Gui et al. (2024). Conformalized survival analysis with adaptive cut-offs. DOI 10.1093/biomet/asad076.','small'),
      P('[8] Sesia & Svetnik (2025). Doubly Robust Conformalized Survival Analysis with Right-Censored Data. https://proceedings.mlr.press/v267/sesia25a.html','small'),
      P('[9] Trombley, Birnbaum & Allison (2025). Section diameter and ultrasonic fatigue. DOI 10.1038/s41598-025-97031-1. https://pmc.ncbi.nlm.nih.gov/articles/PMC12008181/','small'),
      P('[10] Materials Commons campaign DOI 10.13011/m3-c93d-z035. https://materialscommons.org/public/datasets/2564/overview . Dataset license unspecified; raw/normalized repository records excluded from the shareable archive.','small'),
      P('[11] Pascual & Meeker (1999). Estimating fatigue curves with the random fatigue-limit model. DOI 10.1080/00401706.1999.10485925.','small'),
      P('[12] Centola et al. DOI 10.1016/j.engfailanal.2024.109081. Tridello-group transfer continuation: DOI 10.1016/j.engfailanal.2026.111075. Original 518 records/code were not obtained; these public-data source corrections do not prove errors in that work.','small')]
    build('research_note_en.pdf',en)

    tr=[P('Az deneyle daha güvenilir yorulma sınırı: ne öğrendik?','title'),
        P('20 Ekim 2026 | İkinci araştırma aşaması | Sonuç: değerli veri denetimi ve bir sınır koşulu; henüz yeni, güvenilir tasarım yöntemi yok.','small'),
        H('Açık cevap'),P('Üç deney bazı yeni koşullarda çok işe yarıyor; bunu her koşula genelleyemiyoruz. Tarihsel veride ortalama alt sınır uzadı ve ortalama tehlikeli tahmin azaldı. Ancak belirsizlik geniş, birkaç kaynakta risk arttı ve dış kampanyada rastgele üç gözlemle hedefin üzerinde risk kaldı. Basit bir yerel düzeltme yöntemi de güçlü sonuç verdi. Hiyerarşik modelin üstünlüğünü kanıtlamadık.'),
        H('Önce veriyi düzelttik'),P('Önceki 1.126 noktalı pilotta bir kaynakta 98 kaydın bağımsız sabit gerilme deneyleri olmadığı ortaya çıktı. Aynı numuneye artan gerilme basamakları uygulanmış. Bu kaynağı yeni analizden çıkardık. Yeniden yayımlanmış eğriler, tam eşleştirilemeyen kayıtlar ve bir maksimum gerilme/genlik çelişkisi de ana kümeden ayrıldı.'),
        P('Ana küme: 309 yaklaşık grafik noktası, 32 eğri, yöntemi incelenmiş 11 kaynak bloğu. Bu, 11 bağımsız fabrika veya her noktanın özgün numune kimliği doğrulandı demek değil. Bir runout kaydının aslında kırılmış numune olduğunu ve bir koşula yanlış ısıl işlem atandığını kaynak metinlerinden düzelttik. Ham veri korunuyor.'),
        fig('01_provenance_gate.png',465),
        P('Bu düzeltmeler bizim açık veri benchmarkımıza aittir. Centola/Tridello’nun özgün 518 kaydı elimizde yok; onların verisinde aynı hataların olduğunu göstermedik. Önceki pilotun sayısal tekrarı doğru olsa da bilimsel yorumu kusurlu veri varsayımlarına bağlıydı. Eski iletişim paketinin yerine bu aşamanın düzeltmeli özeti kullanılmalı.','small'),
        PageBreak(),H('Üç gözlemle ne değişti?'),
        P(f'Aynı test noktaları korunarak, her yeni eğriden 3 gözlem kullanıldı. Bütün diğer doğrulanmış tarihsel kaynaklarla eğitilen modelde kaynak dengeli risk aralığı {pct(h0)} iken {pct(h3)} oldu. Alt ömür sınırlarının geometrik ortalaması {gain:.2f} katına çıktı.'),
        P(f'Fakat bu kazanç için betimleyici %95 kaynak bootstrap aralığı {10**g.lo95:.2f}-{10**g.hi95:.2f} kat. Yani kazanç olmadığını dışlayamıyoruz. Gerçek risk değişiminin üst sınırındaki belirsizlik de +{100*r.hi95:.2f} puan artışa izin veriyor. Başarı için önceden koyduğumuz güçlü ölçütler geçilmedi.'),
        fig('03_source_heterogeneity.png',445),
        P('Ortalama iyileşmenin çoğu Solberg kaynağındaki büyük düzeltmeden geliyor. Lai kaynağında risk üst ucu %23,33’ten %42,60’a yükseliyor. Diğer bazı kaynaklar da kötüleşiyor. Bu yüzden ortalama %8,93, yeni bir parçanın veya her koşulun %90 güvenli olduğunun kanıtı değildir.'),
        H('Neden kalibrasyon sıfır ömür verdi?'),P('Kaynakları dikkatle ayırınca 9 bağımsız kalibrasyon bloğu kalmıyor. Dondurduğumuz dağılımdan bağımsız %90 yöntemin matematiksel sonucu sıfır alt sınır oluyor. Sıfır ömür güvenli ama tasarımda işe yaramaz. Bu, bütün belirsizlik yöntemleri imkânsız demek değil; az veriyle bilgi veren bir sınır için ek fiziksel/istatistiksel varsayım gerektiğini gösteriyor.'),
        PageBreak(),H('Yeni alınan gerçek kampanyada ne oldu?'),
        P('Yazarların açık numune sayfalarından 129 kullanılabilir kayıt elde ettik. Üç çap koşulunda 44/40/45 numune var; hepsi tek ilişkili kampanyadan geliyor. Makaledeki 130. numunenin gerekli alanları açık sayfada yoktu; uydurmadık. Kayıtlar grafikten çıkarılmış değil, yazarın numune bazında bildirdiği değerler. Ayrı bir ayrıştırıcıyla kaynak sayfaları tekrar kontrol edildi.'),
        P('Burada “3 gözlem”, her çap koşulu için 3, toplam 9 destek gözlemi demek. Her seçim mekanizması ve tohum içinde diğer 99 test noktası bütün k değerlerinde aynı tutuldu. Rastgele seçimde modelin tehlikeli sınır oranı %53,66’dan %13,19’a düştü. Bu kez alt sınır uzamadı: aşırı yüksek tahmin yaklaşık 4,68 kat aşağı çekildi. Hedef hâlâ aşılmış durumda.'),
        fig('04_external_learning.png',480),
        P('Kronolojik seçimde %1,96 görüldü; ancak farklı test noktaları ve farklı destek seçimi kullanıldığı için bunu rastgele seçime karşı kanıtlanmış üstünlük sayamayız. Bu tek kampanya için bağımsız kampanyalar arası güven aralığı yok. Ayrıca deneyin sonlanma ölçütü tam kopmadan önce görünen çatlakla ilişkili rezonans değişimi; tarihsel kırılma ömürleriyle tamamen aynı hedef değil.'),
        P('Kaynak-parametresi belirsizliğini ekleyen duyarlılıkta rastgele üç gözlemin riski %16,42; eğrisel temel modelde yaklaşık %13,20 çıktı. Sonuç yalnız düz bir Basquin çizgisinin seçilmesinden kaynaklanmıyor, fakat makalenin Weibull rastgele yorulma sınırı modeli henüz yeniden kurulmadı.'),
        PageBreak(),H('En güçlü basit kontrol ne söyledi?'),
        P('Sonuçları gördükten sonra, açıkça keşifsel olarak bir kontrol daha ekledik: hiyerarşik modelin aynı eğimini ve saçılımını tutup yalnız yeni koşulun yerel ömür kaymasını hesapladık. Böylece önsel bilginin etkisini, farklı saçılım kullanmanın etkisinden ayırdık. Dış rastgele panelde bu basit kontrol %6,99 risk verdi; hiyerarşik modelin %13,19’una karşı daha düşük ama daha kısa ömür sınırları sundu. Hiyerarşinin gerekli veya üstün olduğunu söyleyemeyiz.'),
        H('Neyi teslim ediyoruz?'),P('Kaynak kanıtları, düzeltme kaydı, sonuç görülmeden dondurulan protokoller, 0/3/5/10 gözlemli deneyler, güçlü basit ve hiyerarşik sansürlü modeller, eğrilik ve veri-kökeni duyarlılıkları, ayrı kampanya testi, bağımsız aritmetik denetimi ve birebir sayısal tekrar. Yeni fiziksel deney yapılmadı. Deney sayısını azaltmanın parasal veya cihaz-saati maliyetini ölçmedik.'),
        H('Güçlü katkı için sıradaki tek soru'),
        P('Yeni bir üretim partisinde ilk birkaç deneyi hangi gerilmelerde yaparsak, yanlış model varsayımını erken fark edip güvenilir ve işe yarar bir alt sınıra ulaşırız? Bunu sınamak için aynı test kümesi üzerinde rastgele seçim, gerilme aralığını kapsayan seçim ve gerçek kronoloji karşılaştırılmalı. Yöntem seçimi geliştirme kampanyalarında yapılmalı; son testte farklı, önceden ayrılmış kampanyalar kullanılmalı.'),
        P('Önce gerçek numune/üretim partisi eşlemesi, ortak kırılma tanımı ve sansür planı gerekli. Sonra yayımlanmış rastgele yorulma sınırı modeli ve aynı popülasyonlu basit yerel kontrolle karşılaştırma yapılmalı. Başarı ortalamada değil, kaynak bazında risk ve işe yarar ömür sınırıyla aranmalı. Bu, mevcut veriyi daha fazla ayarlayıp olumlu sonuç çıkarmaktan daha güçlü bir araştırma sınaması olacak.'),
        H('Tridello’ya sunulabilecek dürüst mesaj'),P('“Açık veride deney kökenini incelerken somut uygunluk/etiket sorunları bulduk. Az gözlemle uyarlama ortalamada iyileşse de bazı yeni koşullarda güvenilirliği bozuluyor. Elimizde tekrarlanabilir bir benchmark ve yeni kampanya denemesi var. Numune/parti eşlemesi ve uygun deney seçimi tasarımı konusunda sınırlı teknik görüşünüzü almak isteriz.” Bu bir teknik işbirliği daveti için somut; güçlü yeni algoritma iddiası için erken. Hiçbir e-posta gönderilmedi.'),
        P('Ayrıntılı kaynaklar ve denetlenebilir sayılar İngilizce teknik raporda ve tekrar üretim paketinde. Sansür aralıkları güven aralığı değildir. Bootstrap aralıkları, ortak eğitim verisi ve az kaynak nedeniyle betimleyicidir.','small')]
    build('arastirma_ozeti_tr.pdf',tr)

    brief=[P('Few-shot fatigue limits after a provenance audit','title'),
      P('AM316L | Working technical brief | Computational benchmark, not a validated safe-design method','small'),
      H('Question'),P('Can a few endpoints from a new AM316L condition make lower-life limits both safer and useful? We tested censored monotone Basquin baselines, target-intercept updating and hierarchical borrowing, using fixed support/query splits and held-out source blocks.','brief'),
      H('Concrete evidence'),P('Original-methods review reduced a 1,126-point public pilot to 309 points/32 curves/11 method-reviewed source blocks for the main cohort. It identified stepped-load observations, republished curves and source-supported runout/treatment corrections. Physical specimen/batch independence remains incompletely documented. These are corrections to this open-data benchmark, not proof of errors in Centola et al.’s original 518 records.','brief'),
      H('Results'),P('In the secondary full-training raw track, three endpoints per condition increased geometric lower life 1.92x and reduced mean danger identification endpoints from 13.35-15.41% to 8.31-8.93%. The descriptive 95% source-bootstrap life-gain interval is 0.84-3.65x; risk worsens for several sources. The prespecified 90% calibration becomes a zero-life bound with the available source count, so its usefulness criterion fails.','brief'),
      P('An acquired author-provided campaign contains 129 complete specimens in three diameter groups, representing one related campaign. Three random endpoints per group (nine total) reduce danger from 53.66% to 13.19% by lowering overly optimistic limits. A matched simple target-intercept control gives 6.99% at shorter life. No hierarchical superiority or general 90% source-conditional guarantee is established. The campaign uses a crack-related ultrasonic endpoint, not necessarily full fracture.','brief'),
      H('A narrow next step'),P('A useful continuation would test stress-level selection at fixed query sets and matched experimental budgets against a random-fatigue-limit baseline and simple local updating. This needs specimen/build lineage, consistent failure definitions, actual censoring plans and additional held-out campaigns. A source-to-condition mapping or brief methodological feedback would resolve a concrete bottleneck.','brief'),
      P('Code, split receipts, aggregate figures and independent arithmetic checks are available locally. No new physical experiment or correspondence was performed. Original data DOI: 10.6084/m9.figshare.22337629.v2 (CC BY 4.0). External article: 10.1038/s41598-025-97031-1; repository data license unspecified, so raw external records are excluded from the shareable archive.','small')]
    build('research_brief_en.pdf',brief)

if __name__=='__main__':main()
