"""Scientific figures generated only from immutable prediction summaries."""
from pathlib import Path
import json,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220,'figure.facecolor':'white','svg.hashsalt':'fatigue-ai-v1'})
BLUE='#236783';ORANGE='#d18b3f';GRAY='#70808b'

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None,'Creator':'AM fatigue research workflow','Description':'Derived from FatigueData-AM2022 v2, Zhang and Xu2023, CC BY4.0; code-generated analysis.'});plt.close(fig)

def main():
    s=pd.read_csv(ROOT/'results/primary/summary.csv');a=s[(s.model=='linear')&(s.policy=='all')].set_index('bound')
    bounds=['model_q10','endpoint_pooled','cohort_max'];labels=['Model 10th percentile','Pooled endpoint calibration','Source-cohort maximum']
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.6),gridspec_kw={'width_ratios':[1.2,1]})
    lo=a.loc[bounds].risk_lower.to_numpy()*100;hi=a.loc[bounds].risk_upper.to_numpy()*100;y=np.arange(3)
    axes[0].barh(y,lo,color=BLUE,label='Known dangerous')
    axes[0].barh(y,hi-lo,left=lo,color=ORANGE,label='Ambiguous runouts')
    for i,(l,u) in enumerate(zip(lo,hi)):axes[0].text(u+.5,i,f'{l:.2f}' if abs(l-u)<.005 else f'{l:.2f}-{u:.2f}',va='center',fontsize=10)
    axes[0].set_yticks(y,labels);axes[0].invert_yaxis();axes[0].set_xlim(0,38);axes[0].set_xlabel('Block-balanced specimen danger (%)')
    axes[0].legend(loc='lower right',fontsize=9,frameon=False)
    c=a.loc[bounds].conservatism_decades.to_numpy();cl=a.loc[bounds].conservatism_decades_ci_low.to_numpy();cu=a.loc[bounds].conservatism_decades_ci_high.to_numpy()
    axes[1].errorbar(c,y,xerr=[c-cl,cu-c],fmt='o',color=BLUE,capsize=4)
    axes[1].set_yticks(y,[]);axes[1].invert_yaxis();axes[1].set_xlim(0,4.5);axes[1].set_xlabel('Conservatism: log10(model median / bound)')
    for i,x in enumerate(c):axes[1].annotate(f'{x:.2f} decades',(x,i),xytext=(0,13),textcoords='offset points',ha='center',fontsize=10)
    fig.suptitle('Reliability has a utility cost on unseen provenance blocks',fontsize=14,y=1.02)
    fig.text(.03,-.07,'Rich linear censored AFT; 1126 digitized observations; 29 blocks; 3 seeds. Left: identification bounds, not confidence intervals.\nRight: mean of block-median penalties; whiskers: descriptive block-bootstrap 95% intervals. Cohort-max targets whole cohorts.\nData: Zhang and Xu, FatigueData-AM2022 v2, CC BY 4.0; DOI 10.6084/m9.figshare.22337629.v2.',fontsize=9)
    fig.tight_layout();save(fig,'02_risk_and_conservatism')

    ct=pd.read_csv(ROOT/'results/primary/paired_contrasts.csv');ct=ct[ct.fraction==.8]
    fig,ax=plt.subplots(figsize=(9.5,4.3));x=ct.known_violation_difference.to_numpy()*100;l=ct.ci_low.to_numpy()*100;u=ct.ci_high.to_numpy()*100
    ax.axvline(0,color=GRAY,lw=1);yy=np.arange(len(ct));ax.errorbar(x,yy,xerr=[x-l,u-x],fmt='o',color=BLUE,capsize=5)
    ax.set_yticks(yy,['Combined minus distance','Combined minus instability','Combined minus random']);ax.invert_yaxis();ax.set_xlabel('Difference in known-danger risk (percentage points)')
    ax.set_title('Combined rejection did not pass the prespecified success rule',pad=18,fontsize=13)
    ax.text(.01,-.26,'Target acceptance 80% within each block; actual mean 83.39% after integer rounding.\nDescriptive paired block-bootstrap 95% intervals; all cross zero. No claim of reduced true risk.',transform=ax.transAxes,fontsize=9)
    fig.tight_layout();save(fig,'03_failed_combined_gate')

    cells=pd.read_csv(ROOT/'results/primary/source_seed_metrics.csv');z=cells[(cells.model=='linear')&(cells.bound=='endpoint_pooled')&(cells.policy=='all')]
    by=z.groupby('group_id').agg(lower=('risk_lower','mean'),upper=('risk_upper','mean'),n=('n','first')).sort_values('lower')
    fig,ax=plt.subplots(figsize=(9,9.5));yy=np.arange(len(by));ax.barh(yy,by.lower*100,color=BLUE);ax.barh(yy,(by.upper-by.lower)*100,left=by.lower*100,color=ORANGE)
    names=[g.replace('curve_reuse_family_','Reuse family ').replace('10.1016/j.','') for g in by.index]
    ax.set_yticks(yy,names,fontsize=8.5);ax.set_xlabel('Pooled-endpoint-calibrated specimen danger (%)');ax.set_xlim(0,105)
    for i,n in enumerate(by.n):ax.text(101,i,f'n={int(n)}',va='center',fontsize=8)
    ax.set_title('Average reliability conceals large between-block variation',pad=14,fontsize=13)
    fig.text(.02,.005,'Mean over three seeds in each fixed block. Orange marks unresolved runouts. Small cohorts have coarse rates; no conditional guarantee.',fontsize=8.5)
    fig.tight_layout(rect=[0,.02,1,1]);save(fig,'04_block_heterogeneity')

    # Near-coincident curves are data/provenance evidence, not certified specimens.
    candidate=ROOT/'literature/data_source_validation/duplicate_curve_examples.png'
    if candidate.exists():
        shutil.copy2(candidate,OUT/'01_near_coincident_curves.png')
        svg=candidate.with_suffix('.svg')
        if svg.exists():shutil.copy2(svg,OUT/'01_near_coincident_curves.svg')

    mainfacts={'primary_count':json.loads((ROOT/'data/processed/grouping_report.json').read_text()),
        'linear_all_bounds':a.loc[bounds].reset_index().to_dict(orient='records'),
        'primary_gate_contrasts':ct.to_dict(orient='records'),
        'caption_caveat':'Provenance-block-balanced results; no certified independence, original-BNN reproduction, external experiment or arbitrary-shift guarantee.'}
    (ROOT/'results/headline_facts.json').write_text(json.dumps(mainfacts,indent=2))
    # Portrait-paper variants use a physical6.5inch canvas so labels remain
    # readable at100% PDF scale. Presentation variants above remain available.
    raw=pd.read_csv(ROOT/'data/processed/ss316l_lpbf_all.csv')
    fig,ax=plt.subplots(figsize=(6.5,4.1))
    for ds,marker,color in [('a0226_d001','o',BLUE),('a0517_d001','x',ORANGE)]:
        z=raw[raw.dataset_id==ds]
        if marker=='o':ax.scatter(z.cycles_observed,z.stress_amplitude,marker=marker,s=46,facecolors='none',edgecolors=color,label=z.source_id.iloc[0])
        else:ax.scatter(z.cycles_observed,z.stress_amplitude,marker=marker,s=46,color=color,label=z.source_id.iloc[0])
    ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Observed cycles',fontsize=10);ax.set_ylabel('Stress amplitude (MPa)',fontsize=10)
    ax.legend(fontsize=8,frameon=True);ax.set_title('Near-coincident curves under distinct publication DOIs',fontsize=11)
    fig.tight_layout();save(fig,'01_curve_reuse_paper')
    fig,axes=plt.subplots(2,1,figsize=(6.5,6.0));short=['Raw q10','Endpoint calibration','Cohort maximum']
    axes[0].barh(y,lo,color=BLUE);axes[0].barh(y,hi-lo,left=lo,color=ORANGE)
    for i,(l,u) in enumerate(zip(lo,hi)):axes[0].text(u+.4,i,f'{l:.2f}' if abs(l-u)<.005 else f'{l:.2f}-{u:.2f}',va='center',fontsize=9)
    axes[0].set_yticks(y,short,fontsize=9);axes[0].invert_yaxis();axes[0].set_xlim(0,37);axes[0].set_xlabel('Block-balanced specimen danger (%)',fontsize=10)
    axes[1].errorbar(c,y,xerr=[c-cl,cu-c],fmt='o',color=BLUE,capsize=4);axes[1].set_yticks(y,short,fontsize=9);axes[1].invert_yaxis();axes[1].set_xlim(0,4.5);axes[1].set_xlabel('Conservatism: log10(model median / bound)',fontsize=10)
    for i,v in enumerate(c):axes[1].annotate(f'{v:.2f}',(v,i),xytext=(8,6),textcoords='offset points',fontsize=9)
    fig.suptitle('Rich linear AFT: reliability and conservatism',fontsize=12);fig.tight_layout();save(fig,'02_risk_utility_paper')
    delta=ct.known_violation_difference.to_numpy()*100
    fig,ax=plt.subplots(figsize=(6.5,3.2));ax.axvline(0,color=GRAY,lw=1);ax.errorbar(delta,np.arange(3),xerr=[delta-ct.ci_low.to_numpy()*100,ct.ci_high.to_numpy()*100-delta],fmt='o',color=BLUE,capsize=4)
    ax.set_yticks(np.arange(3),['Combined - distance','Combined - instability','Combined - random'],fontsize=9);ax.invert_yaxis();ax.set_xlabel('Known-danger difference (percentage points)',fontsize=10)
    ax.set_title('Primary matched-availability test: no robust gain',fontsize=11);fig.tight_layout();save(fig,'03_gate_paper')
    print('Generated figures and headline_facts.json')

if __name__=='__main__':main()
