"""Evidence-sourced open-data intake and RBF pilot addenda."""
from pathlib import Path
import html
import json
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.v3_prepare import ROOT,digest

OUT=ROOT/'manuscript/v5'
MODELS=['pooled','hierarchical','curved_hierarchical','rfl','matched_intercept','local_slope']
LABELS=['Pooled','Hierarchical','Two-slope','RFL','Intercept','Local slope']
POLICIES=['high_stress','active_query_variance','stress_span']
PLABELS=['Highest stress','Information planner','Stress span']
PANELS=['rbf_primary25C','rbf_sensitivity450C']


def facts():
    OUT.mkdir(parents=True,exist_ok=True)
    heads=[];few=[];training=[]
    for cap in ['5e6','1e7']:
        folder=ROOT/f'results/v5/rbf_cap{cap}'
        audit=json.loads((folder/'parent_independent_audit.json').read_text());assert audit['status']=='PASS'
        s=pd.read_csv(folder/'all_regime_summary.csv')
        c=pd.read_csv(folder/'all_policy_contrasts.csv')
        tc=pd.read_csv(folder/'training_contrasts.csv')
        costs=pd.read_csv(folder/'policy_cost_savings_bounds.csv')
        def val(d,metric,**kw):
            for key,v in kw.items():d=d[d[key].eq(v)]
            d=d[d.metric.eq(metric)];assert len(d)==1,(metric,kw,len(d))
            return float(d.iloc[0]['mean'])
        for panel in PANELS:
            for regime in ['strict309','expanded441']:
                for k in [3,5]:
                    for model in MODELS:
                        for policy in ['random']+POLICIES:
                            key=dict(panel=panel,regime=regime,model=model,policy=policy,k=k)
                            co=costs.copy()
                            for x,v in key.items():co=co[co[x].eq(v)]
                            assert len(co)==1;co=co.iloc[0]
                            r=key|dict(cap=float(cap),
                                risk=val(s,'known_risk',**key),risk_upper=val(s,'upper_risk',**key),
                                random_risk=val(s,'known_risk',**(key|dict(policy='random'))),
                                finite_availability=val(s,'finite_availability',**key),
                                life_ratio_vs_random=10**val(c,'log_life_gain',comparison='versus_random',**key),
                                paired_risk_lo=val(c,'true_risk_change_lo',comparison='versus_random',**key),
                                paired_risk_hi=val(c,'true_risk_change_hi',comparison='versus_random',**key),
                                savings_lo=co.savings_percent_lower,savings_hi=co.savings_percent_upper)
                            heads.append(r)
                        key=dict(panel=panel,regime=regime,model=model,policy='random',k=k)
                        few.append(key|dict(cap=float(cap),life_ratio_vs_k0=10**val(c,'log_life_gain',comparison='versus_k0',**key),
                            risk_k0=val(s,'known_risk',**(key|dict(k=0))),risk=val(s,'known_risk',**key)))
                        training.append(key|dict(cap=float(cap),life_ratio_BA=10**val(tc,'log_life_gain',**key),
                            paired_risk_lo=val(tc,'true_risk_change_lo',**key),paired_risk_hi=val(tc,'true_risk_change_hi',**key)))
    frame=pd.DataFrame(heads);frame.to_csv(OUT/'rbf_policy_evidence.csv',index=False)
    pd.DataFrame(few).to_csv(OUT/'rbf_random_fewshot_evidence.csv',index=False)
    pd.DataFrame(training).to_csv(OUT/'rbf_training_evidence.csv',index=False)
    fresh=json.loads((ROOT/'literature/v5_open/rbf/fresh_replay_comparison.json').read_text())
    assert fresh['status']=='PASS' and fresh['scientific_csv_count']==36
    for cap in ['5e6','1e7']:
        assert json.loads((ROOT/f'results/v5/rbf_cap{cap}/independent_contrast_audit.json').read_text())['status'].startswith('PASS')
    f=dict(date='20 October 2026',training_rows=441,training_changed=False,
        newly_curated_exact_Nf=dict(pinn2025=44,palmer2025=12),new_exact_Nf_total=56,
        approximate_marker_candidates=dict(faue2022=16),
        aggregate_fatigue_strength_rows_bremen=13,new_gold_identity_campaigns=0,
        bartosak_reannotated_specimens=20,bartosak_reannotated_defects=200,
        RBF=dict(source_rows=67,failures=63,censors=4,prior_reused_RTcurve=25,
            other_condition_points=42,ambient_rows=44,high_temperature_rows=23,source_families=1,
            predictions_total=88320,selected_support_instances=2400),
        protocol_sha256=digest(ROOT/'protocols/v5/rbf_design.txt'),
        pair_audit_files=[str(p.relative_to(ROOT)) for p in (ROOT/'results/v5').glob('rbf_cap*/independent_contrast_audit.json')],
        clean_replay_scientific_csvs=36,clean_replay_maximum_numeric_difference=0,
        clean_replay_all_fit_parameters_equal=True,
        no_new_physical_tests=True,no_original_Centola_reproduction=True,
        no_publication_or_contact=True,goal_status='active; second mapped independent campaign and strong contribution unresolved')
    (OUT/'phase5_evidence.json').write_text(json.dumps(f,indent=2)+'\n')
    return frame,f


def figures():
    d,_=facts();d=d[(d.regime=='expanded441')&(d.cap==5e6)&(d.k==3)]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(10.8,5.6),layout='constrained')
    colors=['#b85d3c','#087e83','#6175ac'];x=np.arange(6);width=.24
    for j,panel in enumerate(PANELS):
        for i,(policy,label,color) in enumerate(zip(POLICIES,PLABELS,colors)):
            a=d[(d.panel==panel)&(d.policy==policy)].set_index('model').loc[MODELS]
            axs[0,j].bar(x+(i-1)*width,a.life_ratio_vs_random,width,color=color,label=label)
            axs[1,j].bar(x+(i-1)*width,100*a.paired_risk_hi,width,color=color)
        axs[0,j].axhline(1,color='#6b7177',lw=.9,ls='--')
        axs[1,j].axhline(0,color='#6b7177',lw=.9)
        for ax in axs[:,j]:ax.set_xticks(x,LABELS,rotation=25,ha='right');ax.grid(axis='y',alpha=.15)
        axs[0,j].set_title('25 C: primary' if j==0 else '450 C: separate sensitivity')
    axs[0,0].set_ylabel('q10 life ratio to random selection')
    axs[1,0].set_ylabel('Paired risk change to random (pp)')
    axs[0,0].set_ylim(0,1.9);axs[0,1].set_ylim(0,1.9)
    axs[1,0].set_ylim(-7,11);axs[1,1].set_ylim(-7,11)
    axs[0,0].legend(fontsize=8,loc='upper left')
    fig.suptitle('Three selected tests, 441-row training, 5 million-cycle support cap\nSame queries/supports; one source family; empirical replay only',fontsize=11)
    for ext in ['png','svg']:fig.savefig(OUT/f'rbf_policy_interactions.{ext}',dpi=210,bbox_inches='tight')
    plt.close(fig)


def documents():
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font=Path(matplotlib.get_data_path())/'fonts/ttf'
    for n,p in [('V5','DejaVuSans.ttf'),('V5B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,str(font/p)))
    pdfmetrics.registerFontFamily('V5',normal='V5',bold='V5B')
    styles={n:ParagraphStyle(n,fontName='V5',fontSize=size,leading=lead,spaceAfter=after) for n,size,lead,after in [('body',9.2,13.2,8),('small',7.6,10.5,6),('cell',8.1,11.2,0)]}
    styles['title']=ParagraphStyle('title',fontName='V5B',fontSize=19,leading=24,spaceAfter=12,textColor=colors.HexColor('#176a7b'))
    styles['h']=ParagraphStyle('h',fontName='V5B',fontSize=11,leading=15,spaceBefore=8,spaceAfter=6,keepWithNext=True)
    def P(s,kind='body'):return Paragraph(html.escape(s),styles[kind])
    def T(rows,widths):
        table=Table([[P(str(v),'cell') for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf4f7')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#176a7b'))]))
        return table
    def I():
        p=OUT/'rbf_policy_interactions.png';im=Image(str(p));return Image(str(p),width=500,height=500*im.imageHeight/im.imageWidth)
    def footer(c,d):
        c.saveState();c.setFont('V5',7);c.setFillColor(colors.HexColor('#52616a'))
        c.drawString(43,821,'Open AM316L evidence | 20 October 2026 | Working addendum')
        c.drawString(43,23,'Exploratory source replay. Predictive q10 is not an R90C90 certificate.')
        c.drawRightString(551,23,str(d.page));c.restoreState()
    d,f=facts()
    def r(panel,model,policy='high_stress'):
        a=d[(d.cap==5e6)&(d.k==3)&(d.regime=='expanded441')&(d.panel==panel)&(d.model==model)&(d.policy==policy)]
        assert len(a)==1;return a.iloc[0]
    rt=r(PANELS[0],'hierarchical');ht=r(PANELS[1],'hierarchical')
    rr=r(PANELS[0],'rfl');hr=r(PANELS[1],'rfl')
    table=[['Model','25 C life ratio','25 C risk: random / high','450 C life ratio']]
    for model,label in zip(MODELS,LABELS):
        a=r(PANELS[0],model);b=r(PANELS[1],model)
        table.append([label,f'{a.life_ratio_vs_random:.3f}',f'{100*a.random_risk:.2f}% / {100*a.risk:.2f}%',f'{b.life_ratio_vs_random:.3f}'])
    en=[P('Public data, useful test selection, and the remaining evidence gap','title'),
        P('A source-intake update and an exploratory rotating-bending transfer pilot','h'),
        P('Abstract','h'),P(f'New publisher and thesis sources yielded 56 exact reported 316L fatigue lives, 16 separately resolved approximate plot markers, and 13 fitted fatigue-strength parameter rows. These measurement types are retained separately. None supplies a second fully mapped specimen-to-build campaign. An additional rotating-bending replay uses 67 previously collected source outcomes, including a reused 25-point reference curve. Across the same held-out queries, three high-stress tests reduced truncated support cycles by {rt.savings_lo:.1f}% at 25 C. The hierarchical q10 life ratio to random selection was {rt.life_ratio_vs_random:.3f}, with observed violation increasing from {100*rt.random_risk:.2f}% to {100*rt.risk:.2f}%. The random-fatigue-limit ratio was {rr.life_ratio_vs_random:.3f}. At 450 C the hierarchical ratio was {ht.life_ratio_vs_random:.3f}. The evidence shows model- and condition-dependent cost, life and risk tradeoffs; it establishes neither a universally superior policy nor population reliability.'),
        P('New public evidence and its permitted use','h'),
        T([['Source','Collected facts and qualification'],
            ['Zhou / Feng PINN family','44 exact Nf rows from the publisher XLSX, byte-identical to author GitHub data. Three batches are reported but row membership is absent. SEM defect descriptors are measured after fracture. Original stress/range discrepancies retained. Catalog only; zero acquisition/reliability fit rows.'],
            ['Wietecha-Reiman et al. 2025','12 exact Table 2 lives at three build angles, strain control, 0.25 Hz, HIP condition. Cycles retained without doubling to reversals. No laboratory specimen/build/lot identities; separate strain-controlled panel.'],
            ['Faue 2022','16 resolved AM markers from a 22-test, one-build report. Approximate lifetimes have pixel intervals; overlap multiplicity, R, control, frequency and temperature remain unresolved. Candidate only.'],
            ['Jun Zhang 2025 thesis','13 source-fitted strength parameter rows and non-additive counts. These are not 13 Nf observations. R=-1 load-controlled HCF includes explicit reloads after runout; pointwise first exposure needs separation.'],
            ['Bartosak / Halamka follow-on','Existing 20 identified specimens and 200 defect rows reannotated: CT is pretest, while supplied SWT uses the Nf/2 cycle. No new physical specimens added.']], [125,375]),
        P('The 441-row source-reviewed axial training input is unchanged. Exact numerical data are not automatically complete-program reliability data. Source family 108486 / 127098 / 111136 is grouped as related work, not three independent campaigns. Article full texts, author code without an explicit license, and original workbooks are omitted from the redistributed factual packet.','small'),
        PageBreak(),P('A common-query test of stress selection','title'),
        P('The separately frozen protocol precedes v5 predictions but follows source transcription: this is exploratory replay. All 67 reported S-N outcomes belong to one conservative 108491 / 109365 family. Ambient conditions supply 44 points and 450 C conditions 23. The 25 C as-built curve reuses 25 prior points; the other 42 points are not proven unique physical specimens. Publication point locators remain distinct from specimen identities.'),
        P('Six unchanged censored baselines compare fixed 309- and 441-row populations. Four policies share identical query/pool splits, with ten seeds per condition. One 309-trained hierarchical Fisher planner chooses the same sequential supports for all predictors and populations. Candidate/query outcomes are absent from selector inputs. k3 is primary, k5 supporting and feasible k10 ambient results appendix. No target family enters population training.'),
        P('The primary 5 million-cycle cap makes min(T,cap) support exposure identifiable. Source runouts survive at least 5 million cycles. The 6.07 million-cycle failure remains a source failure and becomes censored only when revealed under the shorter cap. The 10 million-cycle sensitivity retains the known 5 million-cycle censor evidence and reports cost intervals, not invented exact stops. Rotation frequency is unknown, so cycle cost is not translated into hours or money.'),
        I(),P('Figure 1. Life ratios and paired risk changes to random at k3. 441-row training, primary support cap. Repeated splits are not independent experiments; confidence intervals for new programs are unavailable. The active planner is shared and is not optimized separately for RFL.','small'),
        PageBreak(),P('Results and what would count as a contribution','title'),
        T(table,[113,96,190,101]),
        P(f'High-stress versus random, k3: support-cycle savings are {rt.savings_lo:.1f}% at 25 C and {ht.savings_lo:.1f}% at 450 C, common to every predictor because supports are shared. RFL life ratios are {rr.life_ratio_vs_random:.3f} and {hr.life_ratio_vs_random:.3f}. The highest-stress strategy can increase useful life for one predictor while reducing it for another. At 450 C it usually buys cost and risk reductions at shorter predicted life. k5, k10, all policies, both populations and both caps remain in the numerical evidence.'),
        P('Quality control','h'),P('Independent parent arithmetic checks reconstruct source endpoints, all selected support exposures, common query/support sets, 6,048 absolute summary cells and cost-savings intervals across both caps. Maximum absolute mean difference is 2.23e-16. All eight distinct population model fits report convergence. Matched-intercept k0 predictions correctly use the hierarchical reference; stale last-fit shift fields in its k0 diagnostic objects are excluded from numerical convergence interpretation. The frozen predictive code and reported science are unchanged. Fresh replay and independent paired-contrast receipts accompany the packet.'),
        P('Claim boundary','h'),P('This is an auditable public-data benchmark and a counterexample to treating cheap high-stress tests or a single information planner as universally better. It is not yet an established new acquisition method, a second mapped independent campaign, exact reproduction of Centola\'s 518 records, or superiority to that paper\'s BNN. Empirical q10 violations from one source family cannot certify R90C90. The original strict criterion remains unresolved: reproducible useful-life improvement against strong baselines at acceptable risk on genuinely independent campaigns.'),
        P('Next scientific decision','h'),P('The immediate testable direction is to learn when adaptation should prioritize intercept correction versus fatigue-limit uncertainty, and evaluate a risk/cycle/utility decision rule against the same simple high-stress and local-fit controls. Such a method would require a new outcome-blind protocol and fresh source families; the present results cannot be reused as unlabelled confirmation. If the advantage does not survive independent families, retain the benchmark and reject the method claim.'),
        P('Primary sources','h')]
    refs=[('New numerical PINN source','10.1016/j.engfracmech.2025.111136'),('Strain-controlled Table 2','10.1007/s10853-025-11259-w'),('Faue source','10.1016/j.mfglet.2022.07.083'),('Bremen thesis','10.26092/elib/4986'),('RBF table','10.1016/j.ijfatigue.2025.109365'),('Reused RBF reference','10.1016/j.ijfatigue.2024.108491'),('Original probabilistic ML study','10.1016/j.engfailanal.2024.109081')]
    for label,doi in refs:en.append(Paragraph(html.escape(label)+' - <link href="https://doi.org/'+doi+'" color="#176a7b">'+html.escape(doi)+'</link>',styles['small']))
    tr=[P('İlerleme var; güçlü yöntem katkısı henüz kanıtlanmadı','title'),
        P('20 Ekim 2026 | Açık kaynaklardan veri toplama ve yeni karşılaştırma','small'),
        P('Deney bütçesi olmadan gerçek yayın verilerini toplayıp aynı hedef numunelerde adil bir karşılaştırma kurduk. Şu anda güçlü temel modelleri bağımsız üretim kampanyalarında güvenilir biçimde geçen özgün bir yöntemimiz yok. Bu rapor, elde edilen somut veriyi ve yeni karşılaştırmanın neyi gösterdiğini ayırıyor.'),
        P('Bu turda ne elde ettik?','h'),
        T([['Kaynak','Somut kazanım'],['44 sayısal ömür','2025 PINN makalesinin yayıncı Excel eki bulundu. Yazar deposundaki kopya birebir aynı. Üç üretim grubunun hangi satırlara ait olduğu yok. Kırılma sonrası kusur özellikleri deney öncesi tahmine sokulmadı.'],['12 sayısal ömür','2025 açık makalesinin bireysel tablosu PDF ile doğrulandı. Gerinim kontrollü, HIP uygulanmış 316L; ana gerilme kontrollü eğitim verisinden ayrı.'],['16 yaklaşık nokta','22 AM deney bildiren Faue çalışmasının grafiğinde ayrı seçilebilen işaretler. Üst üste binen noktaların sayısı uydurulmadı.'],['13 istatistik parametresi','173 sayfalık açık tezden kaynakta hesaplanmış yorulma dayanımı parametreleri. Bunlar 13 yeni deney ömrü değil.'],['20 numunenin kullanım açıklaması','Mevcut açık LCF verisinde CT kusurlarının deneyden önce ölçüldüğü doğrulandı. SWT ise ömrün yarısındaki çevrime bağlı; doğrudan önceden bilinen yük girdisi değil.']], [123,377]),
        P('Yeni toplanan kesin ömür satırı 56; yaklaşık grafik adayı 16. Bu sayılar ayrı tutuluyor. İkinci bir bağımsız numune-üretim partisi eşlemesi henüz bulunamadı. Eğitimdeki 441 kayıt değişmedi. Orijinal 518 kaydın aynısını topladığımız veya orijinal BNN\'yi yeniden ürettiğimiz iddia edilmiyor.'),
        P('Döner-eğme karşılaştırması','h'),P('Önceki turda toplanan 67 tablo noktasıyla ayrı bir deney türüne geçişi sınadık. Bunların 25\'i önceki makaleden alınmış eğri; tümünü tek kaynak ailesi tuttuk. Oda sıcaklığındaki 44 nokta ile 450°C\'deki 23 nokta ayrı değerlendirildi. Altı sansürlü temel model, dört seçim yöntemi, aynı hedefler ve aynı seçilmiş destek deneyleri kullanıldı. Ana bütçe üç deney; beş ve uygun koşullardaki on deney sonuçları da saklandı.'),
        PageBreak(),P('Yeni sayısal bulgu: kazanç koşula ve modele bağlı','title'),
        P(f'Oda sıcaklığında üç yüksek gerilme deneyi, rastgele seçime göre çevrim maliyetini %{rt.savings_lo:.1f} düşürdü. Hiyerarşik modelin q10 ömür sınırı {rt.life_ratio_vs_random:.2f} katına çıktı; gözlenen ihlal %{100*rt.random_risk:.2f}\'den %{100*rt.risk:.2f}\'ye yükseldi. RFL modelinde ise aynı seçilmiş deneylerle ömür oranı {rr.life_ratio_vs_random:.2f} oldu. Aynı seçim farklı modellere farklı yarar sağlıyor.'),
        P(f'450°C duyarlılığında yüksek gerilme seçimi %{ht.savings_lo:.1f} çevrim tasarrufu sağladı, fakat hiyerarşik modelin ömür sınırı rastgele seçimin {ht.life_ratio_vs_random:.2f} katına indi. Tek kampanya ailesinden, tekrar bölünmüş az sayıdaki numuneden çıkan bu sonuçlar genel güvenlik garantisi değildir.'),
        I(),
        P('Grafik: üç seçilmiş deney, 441 kayıtla eğitim, 5 milyon çevrimlik bütçe. Üstte ömür oranı, altta rastgele seçime göre ihlal değişimi var. İngilizce model adları teknik eşleştirme için korundu.','small'),
        P('Bundan nasıl güçlü katkı çıkar?','h'),P('Somut aday, yeni koşulda hangi belirsizliği düzeltmemiz gerektiğini ayırt eden bir deney seçimi: eğrinin yer değiştirmesini mi, eğimini mi, yorulma sınırını mı öğrenmeliyiz? Böyle bir yöntem, basit yüksek gerilme seçimini ve küçük yerel fiziksel uyumu aynı güvenlik ve maliyet koşullarında geçebilirse değerli olur. Mevcut sonuçları yöntem seçip sonra başarı kanıtı olarak kullanamayız; yeni protokol ve bağımsız kaynak gerekir.'),
        P('Doğrulama ve açık sınır','h'),P('İki çevrim bütçesinde toplam 88.320 tahmin ve 2.400 seçilmiş destek örneği oluştu; bunlar yeni fiziksel deney sayıları değil. Kaynak/gerilme/sansür ve maliyet hesabı bağımsız denetlendi. Eşleşmiş karşılaştırma ve temiz yeniden çalıştırma kayıtları pakette. Sıfır deneyli yerel kesişim modelinin tanı günlüklerindeki eski kaydırma alanları bilimsel sonuç olarak kullanılmadı. Hedef hâlâ açık: ek bağımsız kampanya ve temel modeller karşısında güvenilir, işe yarar yöntem avantajı.')]
    for name,story in [('public_data_rbf_addendum_en.pdf',en),('yeni_veri_ve_deney_secimi_tr.pdf',tr)]:
        SimpleDocTemplate(str(OUT/name),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=44,bottomMargin=40,title='Public AM316L evidence and stress selection',author='').build(story,onFirstPage=footer,onLaterPages=footer)
    print('Saved English/Turkish v5 documents')


if __name__=='__main__':
    figures();documents()
