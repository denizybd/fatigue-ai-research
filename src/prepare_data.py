"""Flatten official FatigueData-AM2022 without fitting outcomes.

Preserves source addresses and database-assumption caveats. Empty or vector-valued
metadata become missing scalar covariates; nothing is inferred from fatigue life.
"""
from pathlib import Path
import json, re, hashlib
from collections import Counter
import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]

def records(x):
    if isinstance(x, dict): return [x]
    if isinstance(x, np.ndarray): return x.ravel().tolist()
    return x if isinstance(x, list) else []

def scalar(x):
    a = np.asarray(x).ravel()
    if len(a) != 1: return np.nan
    try:
        z = float(a[0]); return z if np.isfinite(z) else np.nan
    except (ValueError, TypeError): return np.nan

def text(x):
    return x.strip() if isinstance(x, str) else ''

def normalize_doi(x):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', text(x).lower()).strip()

def main():
    raw = ROOT/'data/raw/FatigueData-AM2022.mat'
    metadata = json.loads((ROOT/'data/raw/figshare_article_22337629.json').read_text())
    f = next(f for f in metadata['files'] if f['name'].endswith('.mat'))
    assert hashlib.md5(raw.read_bytes()).hexdigest() == f['computed_md5']
    db = loadmat(raw, simplify_cells=True)['fatiguedata_am2022']
    (ROOT/'data/processed/units.json').write_text(json.dumps(db['unit'],indent=2))
    rows, dsets = [], []
    for ai, article in enumerate(records(db['articles'])):
        meta = article['metadata']; doi = normalize_doi(meta.get('doi'))
        source = doi or f"missingdoi_article_{ai:04d}"
        for di, ds in enumerate(records(article.get('scidata',{}).get('datasets',[]))):
            fat=ds['fatigue']; am=ds.get('am',{}); p=am.get('am_para',{})
            t=ds.get('testing',{}); procs=records(ds.get('processing',{}).get('proc_para',[]))
            surf=sorted({text(z.get('method')) for z in procs if z.get('type')=='SURF'})
            ht=[z for z in procs if z.get('type')=='HT']; hip=[z for z in procs if z.get('type')=='HIP']
            thermal = 'HIP' if hip else ('HT' if ht else ('NHT' if any(z.get('type')=='NHT' for z in procs) else 'unknown'))
            d = dict(article_index=ai,dataset_index=di,dataset_id=f'a{ai:04d}_d{di:03d}',
                source_id=source,doi=doi,title=text(meta.get('title')),year=scalar(meta.get('year')),
                material=text(ds.get('materials',{}).get('mat_name')),am_type=text(am.get('am_type')),
                fdata_type=text(fat.get('fdata_type')),extraction_method=text(fat.get('extract_method')),
                surface=';'.join(surf) or 'unknown',thermal=thermal,
                heat_temperature=scalar(ht[0].get('temperature',[])) if len(ht)==1 else np.nan,
                heat_time=scalar(ht[0].get('time',[])) if len(ht)==1 else np.nan,
                hip_temperature=scalar(hip[0].get('temperature',[])) if len(hip)==1 else np.nan,
                power=scalar(p.get('power',[])),scan_speed=scalar(p.get('scan_speed',[])),
                hatch_space=scalar(p.get('hatch_space',[])),layer_thickness=scalar(p.get('layer_thickness',[])),
                direction=scalar(p.get('direction',[])),preheat=scalar(p.get('preheat',[])),
                load_ratio=scalar(t.get('fat_r',[])),frequency=scalar(t.get('frequency',[])),
                test_type=text(t.get('fat_type')),temperature=scalar(t.get('fat_temp',[])),
                environment=text(t.get('fat_env')),kt=scalar(t.get('spec_kt',[])),
                load_control=text(t.get('load_ctrl')),geometry=text(t.get('spec_desc')),
                specimen_size=scalar(t.get('spec_size',[])),quality_score=scalar(ds.get('score',[])),
                scalar_metadata_provenance='database reported or default; source-measured status not recoverable globally')
            vals=np.asarray(fat.get('fat_data',[]))
            if vals.size==0: continue
            if vals.ndim==1: vals=vals.reshape(1,-1)
            d['n_observations']=len(vals); dsets.append(d)
            if d['fdata_type'].lower()!='sn': continue
            assert vals.shape[1]==3, (d['dataset_id'],vals.shape)
            for j,(n,s,r) in enumerate(vals):
                rows.append(dict(d,row_id=f"{d['dataset_id']}_p{j:03d}",point_index=j,
                    cycles_observed=float(n),stress_amplitude=float(s),runout=int(r),
                    event=1-int(r),measurement_provenance='approximately digitized' if 'shape' in d['extraction_method'] or 'color' in d['extraction_method'] else 'database extraction; see method',
                    raw_address=f'articles[{ai}].scidata.datasets[{di}].fatigue.fat_data[{j}]'))
    allrows=pd.DataFrame(rows); dsdf=pd.DataFrame(dsets)
    assert set(allrows.runout.unique()) <= {0,1}
    allrows.to_csv(ROOT/'data/processed/all_sn_observations.csv',index=False)
    dsdf.to_csv(ROOT/'data/processed/all_datasets.csv',index=False)
    # No fatigue-outcome-dependent exclusions: failures and runouts retained at all lives.
    alloy=allrows.material.str.replace(r'[^a-zA-Z0-9]','',regex=True).str.lower().isin(['316l','ss316l','aisi316l','stainlesssteel316l'])
    select=allrows[alloy & (allrows.am_type=='L-PBF')].copy()
    positive=np.isfinite(select.cycles_observed)&np.isfinite(select.stress_amplitude)&(select.cycles_observed>0)&(select.stress_amplitude>0)
    invalid=select.loc[~positive]; select=select.loc[positive].copy()
    select['log_life']=np.log10(select.cycles_observed)
    select['log_stress']=np.log10(select.stress_amplitude)
    # Retain all source IDs. Component grouping updated by duplicate/source-family audit.
    select['group_id']=select.source_id
    select.to_csv(ROOT/'data/processed/ss316l_lpbf_all.csv',index=False)
    primary=select[(select.test_type=='uniaxial') & (select.temperature.between(20,30)) & (select.kt.between(.99,1.01))].copy()
    primary.to_csv(ROOT/'data/processed/primary.csv',index=False)
    counts=lambda z:dict(rows=len(z),datasets=int(z.dataset_id.nunique()),sources=int(z.source_id.nunique()),failures=int(z.event.sum()),runouts=int(z.runout.sum()))
    report={'all_sn':counts(allrows),'ss316l_lpbf':counts(select),'primary_uniaxial_room_unnotched':counts(primary),
        'invalid_primary_candidate_rows':len(invalid),'materials':dict(Counter(allrows.material)),
        'ss316l_test_types':dict(Counter(select.test_type)),'ss316l_load_control':dict(Counter(select.load_control)),
        'ss316l_surfaces':dict(Counter(select.surface)), 'ss316l_thermal':dict(Counter(select.thermal)),
        'missing_primary':primary.isna().sum().to_dict(),
        'source_default_caveat':'Descriptor assigns uniaxial,25C,air,Kt1 when not stated. These cannot be certified source-measured from this database alone.',
        'no_equivalence':'No row identity with original Centola518 corpus claimed; source overlap only.'}
    source_map=ROOT/'literature/primary_audit/source_publications.csv'
    if source_map.exists():
        cm=pd.read_csv(source_map);cm['in_open_sn']=cm.doi.isin(set(allrows.doi));cm['in_ss316l_lpbf']=cm.doi.isin(set(select.doi));cm['in_primary']=cm.doi.isin(set(primary.doi));cm.to_csv(ROOT/'data/processed/centola_source_overlap.csv',index=False)
        report['centola_source_doi_overlap']=cm[['in_open_sn','in_ss316l_lpbf','in_primary']].sum().to_dict()
    (ROOT/'data/processed/quality_report.json').write_text(json.dumps(report,indent=2,default=int))
    print(json.dumps({k:v for k,v in report.items() if k not in ['materials','missing_primary']},indent=2))

if __name__=='__main__': main()
