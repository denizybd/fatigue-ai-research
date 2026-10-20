"""Render research deliverables from checked content and saved result tables."""
from pathlib import Path
import json,html,shutil,re
import pandas as pd
import numpy as np
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
from PIL import Image as PILImage

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'manuscript';OUT.mkdir(exist_ok=True)
FONTS=Path(matplotlib.get_data_path())/'fonts/ttf'
for name,file in [('Body','DejaVuSerif.ttf'),('BodyBold','DejaVuSerif-Bold.ttf'),('Sans','DejaVuSans.ttf'),('SansBold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FONTS/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='SansBold',italic='Sans',boldItalic='SansBold')
TEAL=colors.HexColor('#236783');LIGHT=colors.HexColor('#edf3f5');GRAY=colors.HexColor('#59666e')
STYLE={
 'title':ParagraphStyle('title',fontName='SansBold',fontSize=17,leading=21,spaceAfter=12,textColor=TEAL),
 'sub':ParagraphStyle('sub',fontName='Sans',fontSize=8.5,leading=11,spaceAfter=11,textColor=GRAY),
 'h1':ParagraphStyle('h1',fontName='SansBold',fontSize=11.5,leading=15,spaceBefore=12,spaceAfter=6,keepWithNext=True),
 'body':ParagraphStyle('body',fontName='Body',fontSize=9.6,leading=13.2,spaceAfter=7),
 'abstract':ParagraphStyle('abstract',fontName='Body',fontSize=9.2,leading=12.5,spaceAfter=7),
 'caption':ParagraphStyle('caption',fontName='Sans',fontSize=8.0,leading=10.8,spaceBefore=4,spaceAfter=10),
 'ref':ParagraphStyle('ref',fontName='Sans',fontSize=8,leading=10.6,spaceAfter=6,splitLongWords=True),
 'cell':ParagraphStyle('cell',fontName='Sans',fontSize=7.7,leading=10),
 'brief':ParagraphStyle('brief',fontName='Sans',fontSize=9.1,leading=11.3,spaceAfter=6),
 'briefhead':ParagraphStyle('briefhead',fontName='SansBold',fontSize=9.3,leading=11.5,spaceBefore=5,spaceAfter=3,keepWithNext=True)
}

def P(t,style='body'):
    t=str(t).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
    words='gözlem|deney|kırılma|runout|DOI|bağımsız|ihtiyatlı|blok|tohum|ve\\b|yeni|kaynak|onluk|çevrim|oldu|koşu|iterasyon|sentetik|ayrım|tahmin|metrik|satır|teknik|doğrulanmış|and\\b|of\\b|in\\b|rows|conditions|blocks|fits|iterations|points|seeds|models|bounds|random|extended'
    t=re.sub(r'(\d)(?=(?:'+words+'))',r'\1 ',t)
    t=re.sub(r'(?<=[A-Za-zÇçÖöŞşĞğİıÜü]),(?=\d)',', ',t)
    for a,b in [('Ekim2026','Ekim 2026'),('ordinary316L','ordinary 316L'),('BY4.0','BY 4.0'),('of17','of 17'),('and2','and 2'),('and3','and 3'),('and696','and 696'),('cap1500','cap 1500'),('cap12000','cap 12000')]:t=t.replace(a,b)
    return Paragraph(html.escape(t).replace('\n','<br/>'),STYLE[style])
def H(t):return P(t,'h1')
def footer(canvas,doc):
    canvas.saveState();w,h=A4;canvas.setStrokeColor(TEAL);canvas.setLineWidth(.6);canvas.line(48,h-32,w-48,h-32)
    canvas.setFont('Sans',7);canvas.setFillColor(GRAY);canvas.drawString(48,h-24,'AM fatigue reliability | Working research draft | 20 October 2026')
    canvas.drawString(48,25,'Computational audit; authorship and affiliation require author verification.');canvas.drawRightString(w-48,25,str(doc.page));canvas.restoreState()
def doc(path,story,top=48):
    d=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=top,bottomMargin=43,title=path.stem.replace('_',' '),author='Research workspace')
    d.build(story,onFirstPage=footer,onLaterPages=footer)
def table(data,widths=None):
    data=[[P(v,'cell') for v in row] for row in data]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#c6d0d5'))]))
    return t
def figure(name,caption,width=468):
    path=ROOT/'figures'/name
    with PILImage.open(path) as im:w,h=im.size
    return KeepTogether([Image(str(path),width=width,height=width*h/w),P(caption,'caption')])
def percent_range(l,u,d=2):return f'{l*100:.{d}f}' if abs(l-u)<1e-10 else f'{l*100:.{d}f}-{u*100:.{d}f}'

def paper():
    d=json.loads((OUT/'paper_content.json').read_text());story=[P(d['title'],'title'),P(d['subtitle']+' | Working draft; author names and affiliations not assigned.','sub'),H('Abstract'),P(d['abstract'],'abstract')]
    s=pd.read_csv(ROOT/'results/primary/summary.csv')
    for sec in d['sections']:
        story.append(H(sec['title']));story.extend(P(t) for t in sec['paragraphs'])
        if sec['title'].startswith('2.'):
            story.append(figure('01_curve_reuse_paper.png','Figure 1. Two source-DOI curves nearly coincide in physical coordinates. This is a conservative provenance-screening signal, not verified specimen identity. Three multi-DOI families are blocked together in primary tests. Data: FatigueData-AM2022 v2 [4,13]; the complete three-family graphic and point matches accompany the code.'))
        if sec['title'].startswith('4.'):
            rows=[['Model / bound','Specimen violation (%)','Cohort violation (%)','Cost (decades)']]
            for model in ['basquin','linear']:
                for bound in ['model_q10','endpoint_pooled','cohort_max']:
                    r=s[(s.model==model)&(s.bound==bound)&(s.policy=='all')].iloc[0]
                    rows.append([model+' / '+{'model_q10':'q10','endpoint_pooled':'endpoint','cohort_max':'cohort max'}[bound],percent_range(r.risk_lower,r.risk_upper),percent_range(r.cohort_violation_lower,r.cohort_violation_upper),f'{r.conservatism_decades:.3f}'])
            story.extend([Spacer(1,6),table(rows,[142,125,125,107]),P('Table 1. Equal-provenance-block summaries, averaging seeds within blocks. Ranges identify unresolved censoring, not sampling confidence. Cost is the mean within-block median of log10(model median / lower bound). Different bounds target different prediction events.','caption')])
            story.append(figure('02_risk_utility_paper.png','Figure 2. Rich-linear AFT risk and conservatism. Orange segments represent unresolved runouts; lower-panel whiskers are descriptive block-bootstrap 95% intervals. The cohort-maximum target concerns simultaneous whole-cohort coverage. The small primary cohort risk is sensitive to grouping/calibration partitions.'))
            story.append(figure('03_gate_paper.png','Figure 3. Primary matched-availability contrasts: combined minus each comparator in known violations, with descriptive paired block-bootstrap 95% intervals. The target is 80% per block; integer rounding yields 83.39% mean availability. All intervals cross zero and the frozen superiority rule fails.'))
    story.append(H('References'))
    for r in d['references']:
        story.append(P('['+r['id']+'] '+r['text'],'ref'))
        if r.get('doi'):story.append(Paragraph('<link href="'+html.escape(r['url'],quote=True)+'" color="#236783">DOI: '+html.escape(r['doi'])+'</link>',STYLE['ref']))
    doc(OUT/'paper_draft_en.pdf',story)

def supplement():
    q=json.loads((ROOT/'data/processed/quality_report.json').read_text());g=json.loads((ROOT/'data/processed/grouping_report.json').read_text())
    story=[P('Supplementary material','title'),P('Data provenance, fixed experiments, numerical diagnostics and verification receipts','sub'),H('S1. Data eligibility and provenance')]
    story.append(P('The official Figshare v2 MAT file is the processing source. The complete JSON was independently checksum-validated and 100 seeded raw coordinates were checked against the flattened MAT output. This verifies format consistency, not original specimen records. The original Centola 518-row dataset and exact code were not obtained.'))
    story.append(table([['Stage','Rows','Conditions','DOIs / blocks'],['All S-N data','15146','1610','459 DOIs'],['Ordinary316L L-PBF','1473','160','46 DOIs'],['Primary eligible stress control','1126','120','37 DOIs /29 blocks'],['Failures / runouts','987 /139','',''],['Near-point removal sensitivity','942','','29 blocks'],['Weak-edge grouping sensitivity','1126','','28 blocks']],[235,80,80,104]))
    story.append(H('Missing metadata in the preliminary eligible cohort'))
    missing=q['missing_primary'];rows=[['Scalar field','Missing rows','Interpretation']]
    for c in ['power','scan_speed','hatch_space','layer_thickness','direction','heat_temperature','heat_time','load_ratio']:
        rows.append([c,str(missing[c]),'Training-only finite median + missing flag'])
    story.extend([table(rows,[145,80,274]),P('Missing counts above apply to the1126-row current primary cohort. All primary coordinates are approximate figure digitizations. Ambient temperature, uniaxial mode, Kt=1 and other entries can be database defaults. Absence of a scalar heat temperature can also mean no heat treatment; thermal categories remain separate.','caption')])
    story.append(P('Original-source validation covers six ordinary316L points from Stern et al. and thirteen points from Voloskov et al., including four VHCF points outside the primary cohort. All19 agree in runout polarity; maximum coordinate discrepancy is approximately2.60% in cycles and0.25% in amplitude. The original raw experimental records were not obtained. Data are CC BY4.0. Source DOI overlap is16of17 Centola publications in ordinary316L L-PBF and12in the primary cohort; source overlap is not row identity.'))
    story.append(PageBreak());story.extend([H('S2. Fixed implementation and numerical behavior'),P('Each main outer fold fits19 provenance blocks, calibrates on9 and tests on1. All87 main linear fits,87 Basquin fits and696 source-bootstrap fits converge. All87 primary1500-iteration MLP fits reach the cap; they are numerical diagnostics. A separately dated post-result extension at12000iterations converges87/87, with maximum9183iterations. All retain the original objective, inputs, regularization and seeds.')])
    a=pd.read_csv(ROOT/'results/primary/summary.csv');e=pd.read_csv(ROOT/'results/mlp_extended/summary.csv');rows=[['MLP analysis / bound','Violation (%)','Cost (decades)','Increasing-life slope (%)']]
    for label,df in [('Primary cap1500',a[a.model=='mlp']),('Extended cap12000',e)]:
        for b in ['model_q10','endpoint_pooled','cohort_max']:
            r=df[(df.bound==b)&(df.policy=='all')].iloc[0];rows.append([label+' / '+b,percent_range(r.risk_lower,r.risk_upper),f'{r.conservatism_decades:.3f}',f'{r.increasing_life_with_stress_fraction*100:.2f}'])
    story.extend([table(rows,[197,118,80,104]),P('Cost and risk definitions match Table1. Positive stress-location derivative violates the expected fatigue trend with other inputs fixed; the unconstrained MLP is not a validated design law. No comparison with the original variational BNN is implied.','caption')])
    story.append(H('Output magnitudes matter'))
    u=pd.read_csv(ROOT/'results/life_bound_utility.csv');rows=[['Primary model / cohort max','Pooled median lower life (cycles)','Below one cycle (%)']]
    for m in ['basquin','linear','mlp']:
        r=u[(u.model==m)&(u.bound=='cohort_max')].iloc[0];rows.append([m,f'{10**r.pooled_log_bound_p50:.1f}',f'{r.fraction_below_one_cycle*100:.2f}'])
    story.extend([table(rows,[170,205,124]),P('Pooled magnitude diagnostics repeat each test observation over3 seeds; they are not independent specimen counts. A nonvacuous but extremely small bound can still be unusable for high-cycle design. No post-result design-life target was optimized.','caption')])
    story.append(PageBreak());story.append(H('S3. Prespecified sensitivities: rich linear AFT'))
    sens=pd.read_csv(ROOT/'results/sensitivity_comparison.csv');rows=[['Analysis / bound','Specimen risk (%)','Cohort risk (%)','Cost (decades)']]
    for _,r in sens.iterrows():rows.append([r.analysis.replace('_',' ')+' / '+{'cohort_max':'cohort','endpoint_pooled':'endpoint','model_q10':'q10'}[r.bound],percent_range(r.risk_lower,r.risk_upper),percent_range(r.cohort_violation_lower,r.cohort_violation_upper),f'{r.conservatism_decades:.2f}'])
    story.extend([table(rows,[216,100,100,83]),P('DOI-only predictions are reaggregated over the same29 primary blocks. Random-row tests withhold only20% of rows, so their test composition and sampling differ. Deduplication changes observations; weak-edge grouping changes group IDs, seeded fitting/calibration membership and block weighting. These differences are diagnostics, not isolated causal leakage effect estimates. Naive-censoring fits use incorrect training events but retain true censoring for evaluation.','caption')])
    story.append(PageBreak());story.append(H('S4. Gate contrasts and selected-source availability'))
    c=pd.read_csv(ROOT/'results/primary/paired_contrasts.csv');rows=[['Fraction / comparator','Known-risk difference (pp)','95% descriptive interval (pp)','True-risk identification (pp)']]
    for _,r in c.iterrows():rows.append([f'{r.fraction:.1f} / '+r.comparison.replace('combined minus ',''),f'{r.known_violation_difference*100:+.3f}',f'[{r.ci_low*100:+.3f}, {r.ci_high*100:+.3f}]',f'[{r.risk_difference_identification_lower*100:+.3f}, {r.risk_difference_identification_upper*100:+.3f}]'])
    story.extend([table(rows,[122,118,130,129]),P('Negative favors the combined score. At the primary0.8target every descriptive interval crosses zero; not all seedwise signs favor combination. The primary strong claim fails. The0.5random comparison has a negative empirical identification interval but a descriptive interval crossing zero; it cannot rescue the primary hypothesis.','caption')])
    s=a[(a.model=='linear')&(a.bound=='endpoint_pooled')];rows=[['Operational rule','Mean availability (%)','Blocks with any acceptance','Accepted risk (%)']]
    for _,r in s[s.policy.str.startswith('operational')].iterrows():rows.append([r.policy.replace('operational_',''),f'{r.availability*100:.2f}',f'{int(r.sources_with_any_acceptance)}/29',percent_range(r.risk_lower,r.risk_upper)])
    story.extend([table(rows,[178,100,120,101]),P('Accepted risk is undefined for empty selections. It is conditional on blocks with usable observations, whereas availability includes zeros. Different accepted block/stress/runout mixtures prevent claiming calibration from these aggregate selected rates alone.','caption')])
    story.append(PageBreak());story.append(H('S5. Complete provenance-block results'))
    cells=pd.read_csv(ROOT/'results/primary/source_seed_metrics.csv');z=cells[(cells.model=='linear')&(cells.bound=='endpoint_pooled')&(cells.policy=='all')].groupby('group_id').agg(n=('n','first'),lower=('risk_lower','mean'),upper=('risk_upper','mean')).reset_index();rows=[['Block (full mapping in source_family_map.csv)','N','Endpoint violation (%)']]
    for _,r in z.iterrows():rows.append([r.group_id,str(int(r.n)),percent_range(r.lower,r.upper)])
    story.extend([table(rows,[329,45,125]),P('Means are across3 seeds, not independent repeated experimental cohorts. The three reuse families contain4,5and2DOIs; the remaining26blocks are singleton publications. Physical independence and all possible reuse are not established.','caption')])
    story.append(PageBreak());story.extend([H('S6. Verification, provenance and reproducibility'),P('Eleven synthetic model tests check analytic likelihood gradients, Basquin recovery, censoring behavior, deterministic seeds, sample weighting and invalid inputs. Five evaluation tests cover finite-group rank resolution, strict censoring bounds, empty acceptance and training-only encoding. All16 passed before the experiment; they do not validate the physical model.'),P('A separate implementation independently recalculates87 fold memberships,30402 prediction rows and2001 source/seed/policy cells. Training encoders and operational distance thresholds are checked for every fold; full location/bootstrap/calibration replay is sampled on the first source/seed0 and first multi-DOI family/seed42. All integrity checks pass. Numerical replay shares the estimator implementation and is not an external scientific replication.'),P('The original first fold was rerun with exact agreement for54 predictions, including all3models and3bounds. A complete end-to-end replay is also executed in results/full_reproduction; its comparison receipt accompanies the final package. The supplied run_all.sh creates a fresh timestamped run directory and rejects mismatched checkpoint signatures.'),H('Protocol chronology')])
    rows=[['Version','Timing and purpose'],['v1','Pre-fit local protocol: outcomes, models, splits, calibration, gates and sensitivities'],['v1.1','Pre-fit minimum group arithmetic/checkpoint integrity/stress slope'],['v1.2','Pre-fit strict positive-claim criterion'],['v1.3','Pre-fit force-control eligibility and curve-reuse family blocks'],['v1.4','During execution, before aggregate inspection: explicit cohort target'],['v1.5','Post-result numerical failure investigation; fixed longer MLP cap']]
    story.extend([table(rows,[70,429]),P('Local Git records support chronology but are not a public timestamp authority. Outcome-dependent protocol changes are explicitly labelled. Software, exact settings, seeds, splits, logs, raw hashes and CSVs accompany the package. No email, upload, public repository or publication was performed.','caption'),H('Primary claim receipts')])
    for text in ['Population: data/processed/grouping_report.json and primary.csv.','Main numbers: results/primary/summary.csv and source_seed_metrics.csv.','H2 failure: protocols/v1_2_prefit_claim_rule.md, results/primary/paired_contrasts.csv and independent_audit.json.','Sensitivity and convergence: results/sensitivity_comparison.csv; results/mlp_extended/fit_statuses.csv.','Raw and source evidence: data/raw/manifest.json; literature/primary_paper_audit.md; literature/followon_audit.md; literature/data_source_validation.md; literature/novelty_audit.md.']:
        story.append(P(text,'ref'))
    doc(OUT/'supplementary_material.pdf',story)

def brief():
    txt=(ROOT/'outreach/one_page_brief_en.txt').read_text();parts=txt.split('\n\n');story=[]
    for i,part in enumerate(parts):
        lines=part.splitlines()
        if i==0:
            story.append(P(lines[0],'title'));story.append(P(' | '.join(lines[1:]),'sub'))
        elif len(lines)>1 and len(lines[0])<80:
            story.append(P(lines[0],'briefhead'));story.append(P(' '.join(lines[1:]),'brief'))
        else:story.append(P(part,'brief'))
    doc(OUT/'research_brief_en.pdf',story)

def turkish():
    story=[P('Yorulma yapay zekâsı: ne bulduk?','title'),P('20 Ekim2026 | Türkçe araştırma özeti ve savunulabilir iddialar','sub'),H('Sonuç: yeni bir güvenli tasarım algoritması kanıtlanmadı'),P('Ana fikrimiz, modelin eğitim verisine uzaklığını ve tahmin kararsızlığını birlikte kullanarak tehlikeli iyimser ömür tahminlerini azaltmaktı. Bu birleşik kural önceden kaydettiğimiz başarı ölçütünü karşılamadı. Sonucu iyileştirmek için veri ayrımını veya başarı ölçütünü geriye dönük değiştirmedik.'),H('Yorulma ve runout ne demek?'),P('Parçayı tekrar tekrar yüklediğinde bir süre sonra çatlak oluşabilir ve parça kırılabilir. N, kırılmaya kadar çevrim sayısıdır. Runout, deney C çevrimde durduğunda parçanın henüz kırılmamış olmasıdır: gerçek ömrünü bilmiyoruz, yalnızca C’den büyük olduğunu biliyoruz. C’yi kırılma ömrü gibi kullanmak yanlış olur.'),H('Hangi veriyi gerçekten kullandık?'),P('FatigueData-AM2022’nin açık v2 verisinden sıradan316L, lazer toz yataklı üretim, tek eksenli, oda sıcaklığında ve veri tabanında çentiksiz kabul edilen kuvvet kontrollü deneyleri seçtik.1126gözlem ve120deney koşulu var;987kırılma,139runout. Bütün noktalar yaklaşık grafik sayısallaştırmaları. Bazı deney bilgileri özgün yayında ölçülmüş değer yerine veri tabanının varsayılan etiketi olabilir.'),P('37DOI’yi otomatik olarak37bağımsız deney saymadık. Farklı yayınlarda neredeyse aynı eğrileri bulduk. Güçlü eşleşmeleri üç ailede toplayınca29ihtiyatlı kaynak bloğu kaldı. Numune kimlikleri kesinleşmediği için “aynı fiziksel numune” iddiası yapmıyoruz.'),H('Test gerçekten neyi sınadı?'),P('Her turda bir kaynak bloğunu tamamen dışarıda tuttuk.19blokla modeli eğittik,9blokla sınırları kalibre ettik, kalan blokta test ettik. Bunu0,17ve42tohumlarıyla tekrarladık. Test sonuçları eğitim, eksik değer doldurma, kalibrasyon veya karar eşiği seçimine girmedi.29blok bağımsızlık için üst sınır değil, ihtiyatlı çalışma birimimiz;3tohum87yeni deney demek değil.'),H('Seçtiğimiz doğrusal modelde temel sayılar')]
    story.append(table([['Ömür alt sınırı','Tehlikeli iyimserlik (%)','Model medyanına göre geri çekilme'],['Modelin ham q10 sınırı','28,97-30,77','0,62 log10 onluğu'],['Nokta/endpoint kalibrasyonu','14,50-15,40','1,13 log10 onluğu'],['Bütün kaynak kohortu kalibrasyonu','0,197','3,54 log10 onluğu']],[185,130,184]))
    story.append(P('Aralıklar istatistiksel güven aralığı değildir: runout yüzünden hangi olayların bilinmediğini gösterir. Sayılar29kaynak bloğuna eşit ağırlık verir; farklı bir basit modelin veya özgün BNN’nin sonucu değildir.','caption'))
    story.append(PageBreak());story.extend([H('Düşük hata tek başına neden başarı değil?'),P('Alt ömrü çok küçük seçersen, çoğu kırılma ondan sonra olur; model güvenli görünür ama parça için işe yarar tasarım ömrü vermez. Kaynak kohortu kalibrasyonu ana analizde çok az iyimser hata yaptı, fakat sınırı modelin kendi medyanından ortalama3,54onluk aşağı çekti. Sınırların havuzlanmış medyanı yaklaşık141çevrimdi; tahmin örneklerinin%4,23’ünde sınır bir çevrimin altına indi. Bu sonuç yüksek çevrimli tasarım için kullanılabilirlik sorununu gösteriyor.'),P('Daha zayıf bir kaynak eşleşmesini de birleştiren hassasiyet deneyinde bütün kohortta en az bir tehlikeli tahmin görülme oranı%4,60’tan%17,86’ya çıktı. Bu değişiklik kalibrasyona hangi kaynakların girdiğini de değiştiriyor; tüm farkı tek bir birleştirmeye bağlayamayız. Ana düşük hata oranı bir güvenlik garantisi değil.'),figure('03_gate_paper.png','Grafik. Birleşik kural eksi karşılaştırma kuralı: negatif sayı birleşik kural lehine. Çizgiler betimleyici%95blok-bootstrap aralıklarıdır. Hepsi sıfırı kesiyor. Hedef her blokta%80kabul; küçük örneklerde yuvarlama nedeniyle ortalama%83,39oldu.'),H('Sinir ağı ve doğrulama'),P('Başlangıç sinir ağı87koşunun tamamında1500iterasyon sınırına ulaştı. Bu sorunu saklamadık. Sonuç sonrasında yalnızca sayısal sınırı12000’e çıkaran ayrı kontrol yaptık;87koşunun tamamı yakınsadı. Bu, özgün Bayesçi ağı yeniden ürettiğimiz veya sinir ağlarını genel olarak karşılaştırdığımız anlamına gelmiyor.'),P('16sentetik model/değerlendirme testi geçti. Ayrı hesaplama denetimi87ayrımı,30402tahmin satırını ve2001metrik hücresini kontrol etti; yöntem seçiminde veri sızıntısı bulunmadı. Bu bir kod ve hesap denetimidir; yeni fiziksel deney veya dış bağımsız bilimsel tekrar değildir.')])
    story.append(PageBreak());story.extend([H('Tridello açısından somut değer'),P('En güçlü çıktı, görülmemiş üretim/yayın koşullarında muhafazakâr ömür önerisinin nasıl denetlenebileceğini gösteren tekrar çalıştırılabilir bir veri-kökeni ve karar değerlendirmesi. Kaynak eğrilerinin yeniden kullanılması, kalibrasyon hedefi ve tasarımda işe yararlık birlikte ölçülüyor. Birleşik kaçınma fikrinin başarısız olması da hangi basit kuralın bu veride işe yaramadığını gösteriyor.'),P('Bu, şu an güçlü ve yeni bir yöntem makalesi iddiasından çok, sağlam bir pilot/teknik not düzeyinde. Yayın, ilgi veya mentorluk garantisi yok. Özgün518satıra, numune/parti kimliklerine, dış kaynaklı yeni deneylere ve daha gelişmiş modellerle kontrollere erişim katkıyı güçlendirir.'),H('Hazırlanan iletişim ve senden beklenen adım'),P('İngilizce bir sayfalık özet, iki ana grafik, kısa e-posta taslağı ve12teknik soruya açıklamalı cevap hazır. Hiçbir e-posta gönderilmedi veya dosya dışarı yüklenmedi. Önce bu özeti ve teknik soru-cevap dosyasını okuyup çalışmayı kendi cümlelerinle anlatabilmen gerekiyor. Ardından isim/imza ve paylaşmak istediğin gerçek geçmiş bilgilerini ekleyerek taslağı değerlendirebilirsin.'),P('Tridello’dan istenecek ilk katkı dar: önerilen kaynak ailelerinin fiziksel olarak makul olup olmadığına yorum ve mümkünse518satırlık veri için kaynak-koşul eşlemesi. Bu eşleme gelmeden açık veriyi özgün makalenin bağımsız dış testi saymıyoruz.'),H('Doğrulanmış başlangıç kaynakları'),P('Centola vd.:10.1016/j.engfailanal.2024.109081; devamları10.1016/j.ijfatigue.2026.109481 ve10.1016/j.engfailanal.2026.111075. Açık veri açıklaması10.1038/s41597-023-02150-x; veri v2:10.6084/m9.figshare.22337629.v2. Ayrıntılı güncel literatür denetimi, kaynak kısıtları ve15doğrulanmış atıf İngilizce taslakta ve araştırma paketinde.'),H('Tekrar çalıştırma'),P('Araştırma klasöründe zsh run_all.sh komutu bütün hattı yeni bir sonuç dizinine kurar/çalıştırır. Kilitli paket sürümleri, ham dosya özetleri, kod, tohumlar, ayrım üyelikleri, günlükler, CSV sonuçları ve bağımsız hesap denetimi pakette bulunur. Yeni oturumun başlangıç noktası STATE.md dosyasıdır.')])
    doc(OUT/'arastirma_ozeti_tr.pdf',story)

def main():
    paper();supplement();brief();turkish();print('Rendered4PDFdeliverables')
if __name__=='__main__':main()
