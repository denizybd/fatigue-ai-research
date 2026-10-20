"""Apply pre-outcome conservative curve-reuse blocks; retain raw observations.

Near identity is a provenance flag, not certified shared physical specimens.
Primary block membership and sensitivity deduplication are frozen before fits.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=[
 ['10.1007/978-3-030-05861-6_36','10.1016/j.addma.2021.102570','10.1016/j.ijfatigue.2019.01.013','10.1016/j.matdes.2020.108962'],
 ['10.1016/j.ijfatigue.2018.12.016','10.1016/j.ijfatigue.2019.105194','10.1016/j.matdes.2018.02.054','10.1016/j.msea.2017.07.071','10.1051/matecconf/201816522006'],
 ['10.1016/j.ijfatigue.2022.106843','10.1111/ffe.13684']]

def main():
    p=pd.read_csv(ROOT/'data/processed/primary.csv');p['group_id']=p.source_id
    mapping={d:f'curve_reuse_family_{i+1:02d}' for i,f in enumerate(FAMILIES) for d in f}
    p['group_id']=p.source_id.map(mapping).fillna(p.source_id)
    p.to_csv(ROOT/'data/processed/primary.csv',index=False)
    doi=p.copy();doi['group_id']=doi.source_id;doi.to_csv(ROOT/'data/processed/primary_doi_only.csv',index=False)
    # Prespecified weak-edge conservative sensitivity, not a confirmed reuse claim.
    weak=p.copy();weak.loc[weak.source_id.isin(['10.1016/j.ijplas.2021.103172','10.1016/j.jmst.2021.10.006']),'group_id']='weak_reuse_sensitivity_01'
    weak.to_csv(ROOT/'data/processed/primary_weak_edge.csv',index=False)
    # Sensitivity only: greedily retain lowest database-address row in each
    # near-coincident cross-DOI cluster, with same runout, load ratio, and mode.
    # The main analysis does not delete any such approximate observations.
    retained=[];removed=[]
    for idx,row in p.sort_values('row_id').iterrows():
        match=None
        if row.group_id.startswith('curve_reuse_family'):
            candidates=p.loc[retained]
            candidates=candidates[(candidates.group_id==row.group_id)&(candidates.source_id!=row.source_id)&(candidates.runout==row.runout)&(candidates.load_ratio==row.load_ratio)]
            close=candidates[(np.abs(np.log(candidates.cycles_observed/row.cycles_observed))<=np.log(1.02))&(np.abs(np.log(candidates.stress_amplitude/row.stress_amplitude))<=np.log(1.01))]
            if len(close):match=close.iloc[0].row_id
        if match is None:retained.append(idx)
        else:removed.append({'removed_row':row.row_id,'retained_near_match':match,'reason':'prespecified approximate cross-DOI duplicate sensitivity; not proven specimen identity'})
    p.loc[retained].to_csv(ROOT/'data/processed/primary_deduplicated_sensitivity.csv',index=False)
    pd.DataFrame(removed).to_csv(ROOT/'data/processed/deduplication_sensitivity_map.csv',index=False)
    p.groupby(['group_id','source_id']).agg(n=('row_id','size'),runouts=('runout','sum')).reset_index().to_csv(ROOT/'data/processed/source_family_map.csv',index=False)
    report={'rows':len(p),'conditions':p.dataset_id.nunique(),'source_dois':p.source_id.nunique(),'conservative_blocks':p.group_id.nunique(),'runouts':int(p.runout.sum()),'families':FAMILIES,'dedup_sensitivity_rows':len(retained),'removed_near_coincident_rows':len(removed),'weak_edge_blocks':weak.group_id.nunique(),'qualification':'Near-identical digitized curves define conservative leakage blocks; physical specimen identity not established.'}
    (ROOT/'data/processed/grouping_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
