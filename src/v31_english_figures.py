"""English scientific figures; original finite-pool replay, no new fitting."""
from pathlib import Path
import os
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.v3_prepare import ROOT
OUT=Path(os.environ.get('V31_EN_OUTPUT',ROOT/'manuscript/v31'))
LABEL={'pooled':'Pooled Basquin','matched_intercept':'Unpooled shift','hierarchical':'Hierarchical Basquin','curved_hierarchical':'Two-slope hierarchical','rfl':'Random fatigue limit','local_slope':'Local slope + shift'}
POL={'random':'Random','high_stress':'High stress','stress_span':'Stress span','active_query_variance':'Expected information'}
PANEL='external_identity_qualified_firstblock'
def make_figures():
 OUT.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
 p=pd.read_csv(ROOT/'results/v3/identity_cap1e6/paired_comparisons.csv');s=pd.read_csv(ROOT/'results/v3/identity_cap1e6/summary.csv')
 p=p[(p.panel==PANEL)&(p.k==3)&(p.comparison=='versus_random')];s=s[(s.panel==PANEL)&(s.k==3)]
 def val(d,m,po,metric):return float(d[(d.model==m)&(d.policy==po)&(d.metric==metric)]['mean'].iloc[0])
 fig,(ax,bx)=plt.subplots(1,2,figsize=(11,4.3),gridspec_kw={'width_ratios':[1.3,1]})
 x=np.arange(len(LABEL));w=.24
 for j,(policy,color) in enumerate([('high_stress','#207b8a'),('stress_span','#7871aa'),('active_query_variance','#d89335')]):
  ax.bar(x+(j-1)*w,[100*(10**val(p,m,policy,'log_life_gain')-1) for m in LABEL],w,label=POL[policy],color=color)
 ax.axhline(0,color='#555',lw=.7);ax.set_xticks(x,list(LABEL.values()),rotation=27,ha='right');ax.set_ylabel('Geometric q10 gain vs random (%)');ax.legend(frameon=False,fontsize=8);ax.set_title('Same queries; three support tests per condition')
 for j,model in enumerate(['hierarchical','rfl']):
  for off,policy,color in [(-.12,'random','#777'),(.12,'high_stress','#207b8a')]:
   lo=100*val(s,model,policy,'known_risk');hi=100*val(s,model,policy,'upper_risk')
   bx.plot([lo,hi],[j+off,j+off],color=color,lw=3,label=POL[policy] if j==0 else None);bx.scatter([lo,hi],[j+off]*2,c=color,s=20)
 bx.set_yticks([0,1],['Hierarchical','RFL']);bx.invert_yaxis();bx.axvline(10,color='#ac5151',ls='--',lw=1);bx.set_xlim(-1,44);bx.set_xlabel('Violation identification interval (%)');bx.set_title('Censoring limits the safety conclusion');bx.legend(frameon=False,fontsize=8)
 fig.suptitle('Source-qualified Merot first exposures: 31 specimens, one author campaign; C = 10⁶',fontsize=11)
 fig.text(.01,.008,'Intervals reflect right-censoring, not sampling confidence. No population CI from one campaign. Unpooled-shift availability is 73–83%.',fontsize=8)
 fig.tight_layout(rect=[0,.08,1,.94])
 for ext in ['png','svg']:fig.savefig(OUT/f'policy_tradeoff_en.{ext}',dpi=300)
 plt.close(fig)
 d=pd.read_csv(ROOT/'data/processed/v3/firstblock/merot52.csv');ds=sorted(d[d.panel==PANEL].groupby('dataset_id').filter(lambda g:len(g)>=6).dataset_id.unique());sel=pd.read_csv(ROOT/'results/v3/identity_cap1e6/selections.csv');sel=sel[sel.k<=3]
 fig,axes=plt.subplots(1,3,figsize=(11,3.5));names=['FS18-019 / pre-corroded','FS18-019 / reference','FS18-020 / pre-corroded']
 for i,(a,group,name) in enumerate(zip(axes,ds,names)):
  z=sel[sel.dataset_id==group].copy();z['stress']=z.stress_amplitude.round(7)
  for j,policy in enumerate(POL):
   g=z[z.policy==policy].groupby('stress').size()
   for stress,n in g.items():a.scatter(stress,j,s=14+9*n,color='#207b8a');a.annotate(str(n),(stress,j),ha='center',va='center',color='white',fontsize=7)
  a.set_yticks(range(4),list(POL.values()) if i==0 else ['']*4);a.invert_yaxis();a.set_xticks(sorted(d[d.dataset_id==group].stress_amplitude.unique()));a.set_xlabel('Stress amplitude (MPa)');a.set_title(name,fontsize=9);a.grid(axis='x',alpha=.15)
 fig.suptitle('Stress choices from the same frozen candidate pools (k=3)',fontsize=11)
 fig.text(.01,.01,'Numbers count selections over 10 repeated splits (30 per policy/condition); they are not independent specimen counts or continuous-stress optima.',fontsize=8)
 fig.tight_layout(rect=[0,.07,1,.91])
 for ext in ['png','svg']:fig.savefig(OUT/f'stress_choices_en.{ext}',dpi=300)
 plt.close(fig)
if __name__=='__main__':make_figures()
