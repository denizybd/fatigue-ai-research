"""Aggregate scientific figures: no source-licensed external specimen records."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.v2_prepare import ROOT

OUT=ROOT/'figures/v2';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'svg.hashsalt':'phase2-fixed',
                     'axes.titleweight':'bold','axes.labelcolor':'#273746'})
COLORS=['#176c83','#c17e23','#7c455f','#4b7c50']

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    plt.close(fig)


def main():
    gate=pd.read_csv(ROOT/'literature/provenance_v2/final_source_gate.csv')
    eligible=gate.source_gate_status.str.startswith('eligible')
    counts=[gate.loc[eligible,'n_rows'].sum(),gate.loc[gate.source_gate_status=='exclude_variable_amplitude','n_rows'].sum()]
    counts.append(gate.n_rows.sum()-sum(counts))
    fig,ax=plt.subplots(figsize=(8.4,3.8));labels=['Methods-reviewed main cohort','Stepped-load source excluded','Reused or unresolved: quarantined']
    ax.barh(labels,counts,color=[COLORS[0],COLORS[2],'#aeb9bf']);ax.invert_yaxis()
    for i,n in enumerate(counts):ax.text(n+10,i,str(n),va='center')
    ax.set_xlim(0,800);ax.set_xlabel('Digitized observations (original pilot: 1,126)')
    ax.set_title('Source evidence changes the usable cohort',loc='left',pad=15)
    fig.text(.01,.01,'Methods reviewed does not certify every point-to-specimen identity. Raw data are unchanged.',fontsize=8,color='#59666e')
    fig.tight_layout(rect=(0,.09,1,1))
    save(fig,'01_provenance_gate')

    d=pd.read_csv(ROOT/'results/v2/fulltraining/summary.csv')
    a=d[(d.panel=='A')&(d.bound=='raw')]
    items=[('Pooled, k=0','pooled',0),('Hierarchical, k=0','hierarchical',0),('Hierarchical, k=3','hierarchical',3),('Unpooled shift, k=3','unpooled_shift',3)]
    fig,axes=plt.subplots(1,2,figsize=(9.2,4),gridspec_kw={'width_ratios':[1.2,1]})
    for i,(label,model,k) in enumerate(items):
        z=a[(a.model==model)&(a.k==k)].iloc[0]
        color=COLORS[i%4]
        axes[0].plot([z.risk_lower*100,z.risk_upper*100],[i,i],lw=6,color=color,solid_capstyle='round')
        axes[0].scatter(z.risk_upper*100,i,color=color,s=35)
        axes[1].barh(i,z.mean_log_lower,color=color)
    axes[0].set_yticks(range(4),[t[0] for t in items]);axes[0].invert_yaxis()
    axes[1].set_yticks(range(4),[]);axes[1].invert_yaxis();axes[0].axvline(10,c='gray',ls='--',lw=1)
    axes[0].set(xlabel='Danger identification interval (%)',xlim=(0,19))
    axes[1].set(xlabel='Mean log10 lower life',xlim=(0,5.8))
    fig.suptitle('Three endpoints per condition: useful average, uncertain generalization',x=.01,ha='left',fontsize=12,fontweight='bold')
    fig.text(.01,.01,'Panel A: 18 curves / 9 target sources, full historical training. Intervals describe censoring, not confidence.\nUnpooled shift availability: 98.15%; other methods: 100%. No method superiority is established.',fontsize=8)
    fig.tight_layout(rect=(0,.13,1,.95));save(fig,'02_internal_risk_utility')

    s=pd.read_csv(ROOT/'results/v2/fulltraining/source_metrics.csv')
    s=s[(s.panel=='A')&(s.bound=='raw')&(s.model=='hierarchical')]
    p=s.pivot(index='group_id',columns='k',values='risk_upper').sort_values(0,ascending=False)
    names={'10.1007/s40964-021-00164-8':'Lai','10.1016/j.ijfatigue.2022.107025':'Dastgerdi',
        '10.1016/j.jmst.2019.08.047':'Yu','10.1016/j.msea.2020.140660':'Afkhami',
        '10.1108/13552541311302932':'Spierings','10.1111/ffe.13077':'Solberg',
        '10.3390/ma12244203':'Wood','10.3390/ma13153293':'Voloskov','10.3390/ma15186278':'Kedziora'}
    fig,ax=plt.subplots(figsize=(8.4,4.8))
    for i,(source,row) in enumerate(p.iterrows()):
        c=COLORS[2] if row[3]>row[0] else COLORS[0]
        ax.plot([100*row[0],100*row[3]],[i,i],color=c,lw=2)
        ax.scatter(100*row[0],i,marker='o',facecolors='white',edgecolors=c,s=55,zorder=3)
        ax.scatter(100*row[3],i,marker='>',color=c,s=60,zorder=4)
    ax.set_yticks(range(len(p)),[names.get(v,v) for v in p.index]);ax.invert_yaxis()
    ax.axvline(10,c='gray',ls='--',lw=1);ax.set(xlim=(-2,103),xlabel='Risk upper identification endpoint (%)')
    ax.set_title('The mean hides source-specific risk increases',loc='left',pad=15)
    ax.plot([],[],marker='o',mfc='white',color='gray',ls='None',label='No target data')
    ax.plot([],[],marker='>',color='gray',ls='None',label='3 endpoints per condition');ax.legend(loc='lower right',frameon=False)
    fig.text(.01,.01,'Source-balanced descriptive estimates, seed averages. These are not individual-source safety certificates.',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,1));save(fig,'03_source_heterogeneity')

    fig,axes=plt.subplots(1,2,figsize=(9,4.4),sharey=True)
    for ax,panel,title in zip(axes,['external_random','external_chronological'],['Seeded random supports','Chronological supports']):
        for f,model,label,c,style in [('external_fulltraining','hierarchical','Straight',COLORS[0],'-'),
            ('external_curved','hierarchical_curved','Two-slope',COLORS[1],'--'),
            ('external_bootstrap','hierarchical_population_bootstrap','Population bootstrap',COLORS[2],':')]:
            z=pd.read_csv(ROOT/f'results/v2/{f}/summary.csv');z=z[(z.panel==panel)&(z.model==model)&(z.bound=='raw')].sort_values('k')
            ax.plot(z.k,100*z.risk_upper,marker='o',label=label,c=c,ls=style)
        ax.axhline(10,c='gray',ls='--',lw=1);ax.set(xticks=[0,3,5,10],xlabel='Support endpoints per diameter condition',title=title,ylim=(0,70))
    axes[0].set_ylabel('Condition-balanced dangerous-bound fraction (%)')
    axes[1].legend(fontsize=8,frameon=False)
    fig.suptitle('An acquired external campaign: adaptation helps, reliability remains conditional',x=.01,ha='left',fontsize=11,fontweight='bold')
    fig.text(.01,.01,'129 named specimens, 3 diameter conditions, ONE campaign; 99 fixed queries per mechanism/seed.\nk=3 uses 9 supports in total. Query sets differ between mechanisms: their difference is not a causal selection effect.',fontsize=8)
    fig.tight_layout(rect=(0,.13,1,.94));save(fig,'04_external_learning')


if __name__=='__main__':main()
