"""Consolidate source-based decisions before outcomes; preserve raw corpus."""
from pathlib import Path
import json
import pandas as pd
from src.v2_prepare import ROOT,digest


def main():
    r=ROOT/'literature/provenance_v2'
    g=pd.read_csv(r/'source_gate.csv').set_index('source_id',drop=False)
    z=pd.read_csv(ROOT/'literature/methods_v2/source_checks/seven_source_evidence.csv')
    for row in z.to_dict('records'):
        doi=row['doi']
        g.loc[doi,['evidence_level','url','locator','note']]=[
            row['evidence_level'],row['source_url'],'See seven_source_evidence.csv exact section/page',
            row['evidence']+' LIMIT: '+row['limits']]
        g.loc[doi,'source_gate_status']=('eligible_methods_verified' if doi in [
            '10.1016/j.ijfatigue.2022.107025','10.1016/j.jmst.2021.10.006']
            else 'quarantine_source_or_endpoint_unverified')
        if doi in ['10.1016/j.jmst.2021.10.006','10.1016/j.ijplas.2021.103172']:
            g.loc[doi,'family_id']='cui_linked_campaign'
        if doi=='10.1016/j.ijplas.2021.103172':
            g.loc[doi,'source_gate_status']='quarantine_reuse_prefer_JMST_representative'
        if doi=='10.1016/j.mtla.2022.101591':
            g.loc[doi,'source_gate_status']='quarantine_stress_definition_conflict'
    f=pd.read_csv(ROOT/'literature/fresh_campaign_v2/historical_source_gate.csv')
    for row in f.to_dict('records'):
        doi=row['doi']
        g.loc[doi,['evidence_level','url','locator','note']]=[
            row['status'],row['source_url'],row['locator'],row['evidence']+' LIMIT: '+row['decision']]
        g.loc[doi,'source_gate_status']=('eligible_methods_verified' if row['status']=='METHODS_VERIFIED_PRIMARY_PDF'
                                        else row['status'].lower())
    g.to_csv(r/'final_source_gate.csv',index=False)
    data=pd.read_csv(ROOT/'data/processed/primary.csv')
    changes=[]
    for c in pd.read_csv(ROOT/'data/processed/v2_provenance_metadata_corrections.csv').to_dict('records'):
        selected=(data.row_id==c['row_id']) if pd.notna(c['row_id']) else (data.dataset_id==c['dataset_id'])
        for rowid in data.loc[selected,'row_id']:
            changes.append({'row_id':rowid,'field':c['field'],
                            'corrected_value':c['source_supported_value'],
                            'source_url':c['source_url'],'locator':c['locator']})
            if c['field']=='runout':
                changes.append({'row_id':rowid,'field':'event',
                                'corrected_value':1-int(c['source_supported_value']),
                                'source_url':c['source_url'],'locator':'Derived 1-runout from source correction'})
    pd.DataFrame(changes).to_csv(r/'frozen_point_corrections.csv',index=False)
    (r/'frozen_gate_receipt.json').write_text(json.dumps({'final_source_gate_sha256':digest(r/'final_source_gate.csv'),
        'point_corrections_sha256':digest(r/'frozen_point_corrections.csv'),
        'n_eligible_sources':int(g.source_gate_status.str.startswith('eligible').sum()),
        'n_corrected_cells':len(changes),
        'qualification':'Source methods verified; approximate points are not comprehensively matched to original physical specimen IDs.'},indent=2)+'\n')
    print('Consolidated source gate and',len(changes),'corrected cells')


if __name__=='__main__':main()
