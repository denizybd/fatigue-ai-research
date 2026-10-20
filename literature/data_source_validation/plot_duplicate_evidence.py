"""Source-screening figure; no model predictions are used."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
data=pd.read_csv(ROOT/'data/processed/ss316l_lpbf_all.csv')
examples=[('a0226_d001','a0517_d001','Liang publications: 12/12 points'),
          ('a0068_d000','a0146_d000','Elangeswaran publications: 11/11 points'),
          ('a0142_d002','a0469_d000','Zhang publications: 11/11 points')]
fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
for ax,(a,b,title) in zip(axes,examples):
    for ds,color,marker,fill in [(a,'#0072B2','o','none'),(b,'#D55E00','x',None)]:
        r=data[data.dataset_id==ds]
        if marker=='o':
            ax.scatter(r.cycles_observed,r.stress_amplitude,s=64,marker=marker,
                edgecolors=color,facecolors='none',label=f'{ds}\n{r.doi.iloc[0]}')
        else:
            ax.scatter(r.cycles_observed,r.stress_amplitude,s=44,marker=marker,
                c=color,label=f'{ds}\n{r.doi.iloc[0]}')
    ax.set_xscale('log');ax.set_yscale('log');ax.set_title(title,fontsize=10)
    ax.set_xlabel('Observed cycles');ax.set_ylabel('Stress amplitude (MPa)')
    ax.grid(alpha=.2);ax.legend(fontsize=6,loc='best')
fig.suptitle('Near-coincident curves across publication DOIs\nScreening evidence; specimen identity is not proven',fontsize=12)
fig.savefig(HERE/'duplicate_curve_examples.png',dpi=190)
fig.savefig(HERE/'duplicate_curve_examples.pdf')
