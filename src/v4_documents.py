"""Numerically sourced v4 figures and English/Turkish evidence addenda."""
from __future__ import annotations
import argparse,html,json,math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.v3_prepare import ROOT,digest

OUT=ROOT/'manuscript/v4'
NAMES={'hierarchical':'Hierarchical Basquin','curved_hierarchical':'Two-slope hierarchical',
       'rfl':'Random fatigue limit','local_slope':'Local slope MAP',
       'pooled':'Pooled Basquin','matched_intercept':'Target intercept'}

def one(frame,**kwargs):
    for k,v in kwargs.items():frame=frame[frame[k]==v]
    assert len(frame)==1,(kwargs,len(frame))
    return float(frame.iloc[0]['mean'])

def facts():
    OUT.mkdir(parents=True,exist_ok=True)
    main=pd.read_csv(ROOT/'results/v4/controlled_cap1e7/all_regime_summary.csv')
    con=pd.read_csv(ROOT/'results/v4/controlled_cap1e7/training_contrasts.csv')
    policy=pd.read_csv(ROOT/'results/v4/headline_policy_table.csv')
    source=pd.read_csv(ROOT/'results/v4/source_holdout_cap1e7/all_regime_summary.csv')
    paired=pd.read_csv(ROOT/'results/v4/source_holdout_cap1e7/all_policy_contrasts.csv')
    f={'date':'20 October 2026','training':{'old_rows':309,'new_rows':441,'conditions':48,
        'publications':14,'source_blocks':13,'failures':380,'censors':61},
       'new_table':{'rows':69,'conditions':14,'failures':64,'censors':5,'eligible_rows':25,
         'eligible_conditions':4,'programs':1,'lab_and_build_IDs':False},
       'source_holdout':{'rows_collected':132,'eligible_rows':115,'eligible_conditions':11,'source_families':2},
       'prediction_instances':164160,'selection_instances':5200,
       'main_risks':{},'main_training_ratios':{},'source_fewshot':{},
       'policy_headlines':policy.to_dict('records')}
    for regime in ['strict309','expanded441']:
        f['main_risks'][regime]={}
        for m in NAMES:
            f['main_risks'][regime][m]={str(k):one(main,regime=regime,model=m,policy='random',k=k,metric='known_risk') for k in [0,3]}
    for m in NAMES:
        f['main_training_ratios'][m]={str(k):10**one(con,regime='expanded441',model=m,policy='random',k=k,metric='log_life_gain') for k in [0,3]}
    for m in ['hierarchical','rfl']:
        f['source_fewshot'][m]={
            'risk_k0':one(source,regime='expanded_family_excluded',model=m,policy='random',k=0,metric='known_risk'),
            'risk_k3':one(source,regime='expanded_family_excluded',model=m,policy='random',k=3,metric='known_risk'),
            'life_ratio_k3_vs_same_k0':10**one(paired,regime='expanded_family_excluded',model=m,policy='random',k=3,comparison='versus_k0',metric='log_life_gain')}
    (OUT/'phase4_evidence.json').write_text(json.dumps(f,indent=2)+'\n')
    return f,main,policy

def figures():
    f,main,p=facts()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(8.7,3.3),sharey=True,layout='constrained')
    for ax,m in zip(axs,['hierarchical','rfl']):
        for regime,color,label in [('strict309','#56708a','309 training records'),('expanded441','#007c78','441 training records')]:
            vals=[100*f['main_risks'][regime][m][str(k)] for k in [0,3]]
            ax.plot([0,3],vals,'o-',lw=2,color=color,label=label)
            for k,v in zip([0,3],vals):ax.annotate(f'{v:.1f}%',(k,v),xytext=(5,6 if regime=='strict309' else -14),textcoords='offset points',fontsize=9,color=color)
        ax.axhline(10,color='#9b5d42',ls='--',lw=1);ax.set_xticks([0,3]);ax.set_xlabel('Selected target tests (random)')
        ax.set_title(NAMES[m],fontsize=11);ax.set_ylim(0,65)
    axs[0].set_ylabel('Observed lower-life violation (%)');axs[1].legend(loc='upper right',fontsize=8)
    fig.suptitle('New 2025 source: same queries and supports; one author program',fontsize=12)
    for ext in ['png','svg']:fig.savefig(OUT/f'training_expansion.{ext}',dpi=200,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(8.8,3.6),sharey=True,layout='constrained')
    colors={'high_stress':'#bd633d','active_query_variance':'#007c78','stress_span':'#5267a0'}
    labels={'high_stress':'Highest stress','active_query_variance':'Information planner','stress_span':'Stress span'}
    for ax,cap in zip(axs,['1e7','1e6']):
        for policy in colors:
            for m,marker in [('hierarchical','o'),('rfl','s')]:
                r=p[(p.cap==float(cap))&(p.policy==policy)&(p.model==m)].iloc[0]
                ax.scatter(r.observed_cycle_savings_percent,r.life_multiplier_vs_random,color=colors[policy],marker=marker,s=65)
        ax.axhline(1,color='#6b7278',ls='--',lw=1);ax.axvline(0,color='#ddd',lw=1)
        ax.set_xlim(-12,79);ax.set_ylim(.62,1.04);ax.set_xlabel('Observed support-cycle savings vs random (%)')
        ax.set_title('Planning cap '+('$10^7$' if cap=='1e7' else '$10^6$')+' cycles',fontsize=11)
    axs[0].set_ylabel('Geometric q10 life ratio vs random')
    from matplotlib.lines import Line2D
    handles=[Line2D([0],[0],color=c,lw=0,marker='o',label=labels[k]) for k,c in colors.items()]
    handles += [Line2D([0],[0],color='#333',lw=0,marker=m,label=l) for m,l in [('o','Hierarchical'),('s','RFL')]]
    fig.legend(handles=handles,loc='outside lower center',ncol=3,fontsize=8)
    fig.suptitle('Three selected tests: two whole-family holdouts, identical queries',fontsize=12)
    for ext in ['png','svg']:fig.savefig(OUT/f'policy_cost_life.{ext}',dpi=200,bbox_inches='tight')
    plt.close(fig)
    print('Figures and numeric document source saved')

def documents():
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font=Path(matplotlib.get_data_path())/'fonts/ttf'
    for n,p in [('V4','DejaVuSans.ttf'),('V4B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,str(font/p)))
    pdfmetrics.registerFontFamily('V4',normal='V4',bold='V4B')
    styles={n:ParagraphStyle(n,fontName='V4',fontSize=s,leading=l,spaceAfter=space) for n,s,l,space in [('body',9.3,13,8),('small',7.5,10.4,6),('cell',8,11,0)]}
    styles['title']=ParagraphStyle('title',fontName='V4B',fontSize=19,leading=24,spaceAfter=12,textColor=colors.HexColor('#087b79'))
    styles['h']=ParagraphStyle('h',fontName='V4B',fontSize=11,leading=15,spaceBefore=9,spaceAfter=6,keepWithNext=True)
    def clean(s):
        import re
        protected={}
        letters='A-Za-zÀ-ÿÇĞİıÖŞÜçğıöşü'
        def protect(m):
            key='§'+chr(0xE000+len(protected))+'§';protected[key]=m.group(0);return key
        s=re.sub(r'\d+(?:\.\d+)?e[+-]?\d+',protect,s)
        s=re.sub(r'(?<!['+letters+r'])(?:q10|k10|k0|k3|k5|R90C90|LPBF316L|AM316L)(?!\d)',protect,s)
        s=re.sub(r'(?<=['+letters+r'])(?=\d)',' ',s)
        s=re.sub(r'(?<=\d)(?=['+letters+r'])',' ',s)
        for key,value in protected.items():s=s.replace(key,' '+value+' ')
        s=re.sub(r';(?=\S)','; ',s)
        s=re.sub(r'(?<=['+letters+r'])(?=%)',' ',s)
        s=re.sub(r'(?<=['+letters+r'])\.(?=\d)','. ',s)
        return re.sub(r' +',' ',s).strip()
    def P(s,k='body'):return Paragraph(html.escape(clean(s)),styles[k])
    def T(rows,widths):
        t=Table([[P(str(v),'cell') for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf5f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#087b79'))]))
        return t
    def I(name,w=500):
        p=OUT/name;im=Image(str(p));return Image(str(p),width=w,height=w*im.imageHeight/im.imageWidth)
    def footer(c,d):
        c.saveState();c.setFont('V4',7);c.setFillColor(colors.HexColor('#53616a'))
        c.drawString(43,821,'Public AM316L evidence | 20 October 2026 | Exploratory research addendum')
        c.drawString(43,23,'Source-qualified data; predictive q10 is not a certified R90C90 design bound.')
        c.drawRightString(551,23,str(d.page));c.restoreState()
    f,_,p=facts()
    h=f['main_risks'];sf=f['source_fewshot']
    en=[P('What can public fatigue data actually buy?','title'),P('A controlled training-expansion and few-test stress-selection study','h'),
        P('Working addendum to the phase3.1 paper. Human authorship and affiliations remain to be supplied. The human separately requested author data; this local workflow sent no correspondence or submission.','small'),
        P('Abstract','h'),P('We expanded a source-reviewed LPBF316L fatigue training cohort from309 to441 observations, while retaining publication reuse blocks and right censoring. A new2025 numerical table supplied69 separate experimental outcomes. On its25 acquisition-eligible observations, additional training data reduced zero-shot hierarchical lower-life violations from57.5% to46.7%; after three random local tests both training regimes gave20.0%. A separate115-observation, two-family holdout replay showed that selecting high stresses cut observed support cycles by70.6%, but lowered predicted q10 life relative to random selection to0.872× for hierarchical Basquin and0.688× for a random-fatigue-limit model. These results support a reproducible open-data benchmark and a cost–utility counterexample; they do not establish a universally better acquisition policy or certified design reliability.'),
        P('Collected evidence, with non-additive counts','h'),T([
            ['Asset','Evidence and use'],['441 training observations','48conditions;14DOIs;13source-family blocks;380failures+61censors.132 newly source-qualified coordinates were already in the public database.'],
            ['69 new numerical outcomes','64failures+5runouts;14conditions; one2025 author program, held out. Publication test numbers are not laboratory/build IDs.'],
            ['20 author-ID LCF/SWT lives','Separate multiaxial/strain-controlled subset plus200defect measurements; not prescribed-stress HCF data.'],
            ['7 interrupted specimens','217,368 force/strain records in peak-valley and selected-loop views of the same7specimens; zero Nf rows manufactured.'],
            ['3 additional cyclic histories','14,499 usable cyclic-response rows;115orphan rows retained. Same Jambor family conservatively.'],
            ['2 selected AM-stainless traces','1,087,236 time samples; grade/temperature unresolved. No fabricated316L label.']], [133,367]),
        P('Counts across related repositories and different measurement types must not be summed as independent fatigue specimens. Four public raw packets were acquired fully or selectively; one large archive was inventoried by public byte ranges. A separate2026 rotating-bending table adds67 reported points, including25 reused points and42 from the other three conditions; it is not used in these frozen axial fits.','small'),
        PageBreak(),P('Controlled training expansion','title'),
        P('The comparison uses identical test queries and revealed supports. Four predeclared populations are309, 441, 347(309+Elanges38) and403(309+Zhang94). The same309-trained planner chooses supports for every predictor and population. Six unchanged censored statistical/physical baselines and four fixed acquisition policies are evaluated at ten hash seeds. Source-balanced likelihood weights change when families are added; this estimates a controlled evidence expansion, not an isolated causal effect of row count or diversity.'),
        P('The new Yankin2025 table reports stress amplitude and individual failure lives directly. Five nominal1e6 censor stops are derived from plots and the stated life range. Test temperature, explicit feedback mode, Kt, laboratory specimen IDs and build/powder identities are not supplied. Therefore this is a temperature-unstated source panel, separate from the identity-qualified room-temperature benchmark.'),
        I('training_expansion.png'),
        P('Figure1. Source/condition-balanced violation fractions, averaged over shared queries at ten repeated splits. One author program; no population confidence intervals. Dashed line: nominal10% risk target, not a guarantee.','small'),
        P('Interpretation','h'),P('At k0, more verified training evidence makes predictions more conservative and reduces observed violations, but risk remains much higher than10%. At k3 the hierarchical B/A life ratio is0.998 and violations are unchanged at20.0%; RFL life ratio is0.949 with violations unchanged at23.3%. Data quantity alone does not fix the new-source error.'),
        P('Only four conditions/25observations allow the inherited query/pool rule and k3. Three pools contain exactly three candidates, so k3 exhausts them and policy choice has no set-level effect. The remaining44observations are retained, not discarded as invalid. No k5/k10 result is invented.'),
        PageBreak(),P('Where should the few tests be placed?','title'),
        P('The separate source-family extension uses115 eligible observations/11conditions from the132 source-qualified coordinates. When Zhang is queried, training B is347; when Elanges is queried, B is403. The entire target family is absent from both training regimes. This extension was frozen after the main fits, before their numerical summaries were inspected, in response to the pool-size limitation; it is explicitly exploratory.'),
        I('policy_cost_life.png'),
        P('Figure2. Same-query k3 comparisons versus random, source-family-balanced. Circle: hierarchical; square:RFL. Costs are observed replay cycles, not wall-clock or new experimental costs. Negative savings mean more cycles.','small'),
        T([['Policy at C1e7,k3','Cycle savings','Life: hier / RFL'],['High stress','70.6%','0.872× /0.688×'],['Information planner','26.6%','0.897× /0.857×'],['Stress span','−5.6%','0.985× /0.925×']],[215,107,178]),
        P('At C1e6, high-stress savings are67.5%, with life ratios0.885/0.685. The active planner is not uniformly superior. All six baselines, k0/3/5 where feasible, risk differences, availability and two-family descriptive intervals are in the CSV supplement; displayed models are representative physical/statistical controls, not winners selected for superiority.'),
        P(f'Random k3 adaptation itself has model-dependent value: hierarchical life improves{sf["hierarchical"]["life_ratio_k3_vs_same_k0"]:.2f}× over its matched k0 while observed violations fall from{100*sf["hierarchical"]["risk_k0"]:.1f}% to{100*sf["hierarchical"]["risk_k3"]:.1f}%; RFL life improves{sf["rfl"]["life_ratio_k3_vs_same_k0"]:.2f}× but violations rise from{100*sf["rfl"]["risk_k0"]:.2f}% to{100*sf["rfl"]["risk_k3"]:.2f}%. Larger lower-life predictions alone are not evidence of a better decision.'),
        PageBreak(),P('Reproducibility and contribution boundary','title'),
        P('Provenance','h'),P('Three admitted publications supply the132-coordinate increment, blocked into two families. A whole11-point reused horizontal curve is excluded;14censor coordinates are replaced by stated1e6/2e6 stops, preserving original values. Unverified database25°C/Kt1 values are removed from certified fields. No fitted curves, tensile means or caption anchors become extra specimens. Independent source, schema and arithmetic reviews pass.'),
        P('Validation','h'),P('The four experiments produce164,160 prediction instances and5,200 selected-support instances, not that many independent tests. Independent reviews reconstruct summaries, right-censor arithmetic, family exclusions, queries and support costs. All16 unique population fits converge without fallback or selected bound hits. A fresh isolated replay reproduces84 scientific CSVs byte for byte and the fitted parameters exactly. Nineteen synthetic model/design tests pass. Across1,156 fixed-parameter RFL checks,96/192-node q10 differences are at most4.78e-10 log10cycles, without numerical exceptions or infinity-classification changes.'),
        P('What is defensible','h'),P('The contribution is a curated open proxy dataset and a controlled benchmark showing when extra source evidence or cheap high-stress tests help, fail or trade life utility for cost. It is not a new named acquisition algorithm, exact Centola replication or a demonstrated improvement over the original BNN. The441 cohort has DOI overlap8/17 with Centola; neither point identity nor original risk volume/SWT/Owen targets is established.'),
        P('Remaining scientific work','h'),P('The Mérot physical-lineage panel remains valid and separate. A second fully mapped independent room-temperature author campaign is still missing. More source-qualified data can continue to be collected and tested while that lineage question remains open. Stronger policy evidence needs multiple independent programs with candidate pools larger than the chosen test budget, complete endpoint/method fields, and successful paired safety-and-utility tests. Two-family bootstrap intervals and repeated seeds do not supply that evidence.'),
        P('Primary sources and local evidence','h')]
    refs=[('Centola et al.; original518rows on request','https://doi.org/10.1016/j.engfailanal.2024.109081'),
          ('FatigueData-AM2022; licensed source coordinates','https://doi.org/10.6084/m9.figshare.22337629'),
          ('Zhang et al.;2017 original experiments','https://doi.org/10.1016/j.msea.2017.07.071'),
          ('Zhang et al.;2019 HCF/ratcheting experiments','https://doi.org/10.1016/j.ijfatigue.2018.12.016'),
          ('Elangeswaran et al.; original CA post-treatment study','https://doi.org/10.1016/j.ijfatigue.2019.01.013'),
          ('Yankin,Perveen,Talamona; Table3','https://doi.org/10.1038/s41598-025-89003-2'),
          ('Bartosak multiaxial LCF/SWT raw data','https://zenodo.org/records/12515773'),
          ('Jambor interrupted raw histories','https://zenodo.org/records/14763342'),
          ('Jambor cyclic-softening raw data','https://zenodo.org/records/17985589'),
          ('AM/wrought-stainless raw traces','https://zenodo.org/records/17086687'),
          ('Separate2026 rotating-bending table; reuse linked','https://doi.org/10.1016/j.ijfatigue.2025.109365')]
    for title,url in refs:
        en.append(Paragraph(html.escape(clean(title))+' — <link href="'+url+'" color="#087b79">'+html.escape(url)+'</link>',styles['small']))
    tr=[P('Açık verilerle gerçekten ne başardık?','title'),P('20 Ekim2026 | Yeni veri toplama bütçesi olmadan ilerleme kaydı','small'),
        P('Yazar yanıtını beklemeden kullanılabilir veri toplamaya devam ettik. Artık savunabileceğimiz somut başarı, internetteki deneyleri kaynaklarıyla eşleştirip tekrarları ve yanlış ömür tanımlarını ayırarak çalıştırılabilir bir karşılaştırma kurmuş olmamız. Üstün ve güvenli bir yapay zekâ yöntemi bulduğumuz iddiası henüz desteklenmiyor.'),
        P('Toplanan ve doğrulanan veri','h'),T([
            ['Veri','Ne anlama geliyor?'],['441 eğitim gözlemi','Önceki309 kayda132 kaynak-denetimli nokta eklendi:48koşul,14yayın,13kaynak bloğu. Ek132 nokta yeni fiziksel deney değil; açık veri tabanında zaten vardı, şimdi yöntemlerini doğruladık.'],
            ['69 yeni tablo gözlemi','2025 tarihli ayrı bir makalede64kırılma+5runout. Grafik tahmini yerine sayısal tablo.14koşul; tek araştırma programı. Numara sütunu laboratuvar/parti kimliği yerine geçmiyor.'],
            ['20 LCF/SWT ömrü','Yazar numune kimlikleri ve200kusur ölçümü var. Gerinim kontrollü/çok eksenli deneyler; ana gerilme–ömür verisine karıştırılmadı.'],
            ['7 kesintili numune','217.368kuvvet/gerinim ölçümü toplandı. Aynı7numunenin farklı kayıtları;217.368 ayrı deney veya kırılma ömrü değil.'],
            ['Ek ham geçmişler','3çevrimsel geçmiş ve2AM-paslanmaz çelik zaman kaydı. Aynı aile/alaşım belirsizlikleri korunuyor; bağımsız316Lnumune sayısı şişirilmedi.']], [135,365]),
        P('Ayrıca2026tarihli döner-eğme tablosunda67nokta bulundu:25i eski yayından alınmış; diğer üç koşul42nokta içeriyor. Bu ayrı ölçüm alanı mevcut eksenel model deneylerine eklenmedi.','small'),
        P('Bu veri ne kadar benziyor?','h'),P('Üretim yönü, işlem durumu, gerilme, yük oranı ve ömür gibi ortak alanlar var. Fakat Centola’nın518satırını birebir almış veya yeniden üretmiş değiliz. Orijinal risk hacmi ve SWT/Owen tasarım hedeflerinin karşılığı da henüz tamamlanmış değil. Eğitim setimizin o17kaynakla DOI örtüşmesi8/17; bu satır eşitliği değildir.'),
        PageBreak(),P('Deneyler bize ne söyledi?','title'),
        P('Aynı test numunelerini ve aynı destek deneylerini kullanarak309 ve441kayıtla eğitilen altı modeli karşılaştırdık. Daha fazla veriye farklı test seçimi karıştırmadık. “İhlal”, modelin önerdiği alt ömürden önce gözlenen kırılmanın payıdır; burada koşullar ve tekrarlar üzerinden ortalama alınır.'),
        I('training_expansion.png'),
        P('Yeni69gözlemli kaynağın25gözlemi/dört koşulu karşılaştırmaya uygun. Tek kaynak olduğu için genel başarıya ilişkin güven aralığı üretmiyoruz. Diğer44gözlem veri paketinde duruyor.','small'),
        P('Somut sonuç','h'),P('Hiyerarşik modelde hiç yerel deney yokken ihlal oranı%57,5’ten%46,7’ye indi. Üç rastgele yerel deneyden sonra iki eğitim setinde de%20oldu. Hedef%10olduğu için güvenilir tasarım sınırına ulaştık diyemeyiz. Ek verinin yerel deney sonrasındaki katkısı küçük; bazı modellerde daha muhafazakâr bir sınır getiriyor.'),
        P('Gerilme seçimi','h'),P('Ayrı iki kaynak ailesinde115gözlem ve11koşul üzerinden üç/beş deneylik seçimleri sınadık. Üç yüksek gerilmeli deney, rastgele seçime göre çevrim maliyetini%68–71azalttı. Ama önerilen alt ömür, hiyerarşik modelde yaklaşık0,87–0,89katına, RFL modelinde0,69katına düştü. Bilgiye dayalı aktif seçim de her modelde üstün çıkmadı. Bu bir maliyet–ömür değiş tokuşu; daha ucuz olması tek başına daha iyi olması demek değil.'),
        PageBreak(),P('Profesöre nasıl anlatılır?','title'),
        P('Savunabileceğin cümle','h'),P('“Yeni fiziksel deney bütçem olmadan açık kaynaklardan yorulma verisi derledim. Kaynak tekrarlarını, runoutları ve deney türlerini denetledim; yeni koşullarda az sayıda deneyin hangi gerilmede yapılmasının maliyet ve ömür sınırı bakımından ne sağladığını güçlü sansürlü modellerle aynı test kümesinde karşılaştırdım.”'),
        P('Sonucun ağırlığı','h'),P('Ortada kaynakları denetlenmiş bir veri paketi, çalıştırılmış karşılaştırmalar ve gösterilebilir olumsuz sonuçlar var. “Tridello’nun modelini geçtim”, “güvenli ömrü kanıtladım” veya “518veriyi aynen kurdum” demek için kanıt yok. Genel aktif öğrenme fikri de tek başına özgün katkı sayılmıyor.'),
        I('policy_cost_life.png'),
        P('Grafikte aşağıya gitmek rastgele seçime göre daha kısa alt ömür, sağa gitmek daha az çevrim maliyeti demek. Yeni ek verilerin tamamı aynı ölçüm türünde veya aynı kanıt düzeyinde değil.','small'),
        P('Açık kalan iş','h'),P('Numune–üretim partisi eşleşmesi doğrulanmış ikinci bağımsız oda sıcaklığı kampanyası hâlâ eksik. Bu eksik, kullanılabilir kaynak verisini toplamayı durdurmuyor. Daha güçlü katkı için farklı kaynaklarda maliyet kazancının yanında güvenlik ve işe yarar ömür kazancını birlikte göstermek gerekiyor. Mevcut ölçümler bu genel üstünlüğü göstermedi. Yazar yanıtı gelirse veri kökenini ve aynı deney protokolünü yeni kanıtla genişletebiliriz.'),
        P('Denetim ve tekrar çalıştırma','h'),P('Girdi ve sonuçlar ayrı okuyucularla denetlendi. Kaynak aileleri eğitim/test arasında ayrıldı; destek seçimleri iki eğitim rejiminde aynı tutuldu. Kaynak eklendiğinde eğitim ağırlıkları da değişir; bu karşılaştırma yalnızca satır sayısının etkisini ayırmaz. Paket tüm model/politika/bütçe tablolarını, kaynakları, yeniden çalıştırma kodunu ve denetim kayıtlarını içerir. Senin önceki veri talebinden ayrı olarak, bu çalışma akışı e-posta göndermedi veya yayın yapmadı.')]
    for name,story,title in [('public_data_addendum_en.pdf',en,'Open-data fatigue evidence addendum'),('acik_veri_ilerleme_raporu_tr.pdf',tr,'Açık veri ilerleme raporu')]:
        SimpleDocTemplate(str(OUT/name),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=47,bottomMargin=42,title=title,author='Research working draft').build(story,onFirstPage=footer,onLaterPages=footer)
    (OUT/'source_references.json').write_text(json.dumps([{'title':a,'url':b} for a,b in refs],indent=2)+'\n')
    print('Two v4 documents rendered from saved numerical tables')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['figures','documents']);a=p.parse_args()
    if a.action=='figures':figures()
    else:documents()
