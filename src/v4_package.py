"""Build an auditable local research packet; never publish or send it."""
from __future__ import annotations
import hashlib,json,shutil,zipfile
from pathlib import Path
import pandas as pd
from src.v3_prepare import ROOT,digest

OUTPUT=Path('/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs/phase4')

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    packet=OUTPUT/'research_packet';packet.mkdir(exist_ok=True)
    picked=set()
    def add(p):
        p=Path(p)
        if not p.is_absolute():p=ROOT/p
        assert p.is_file(),str(p)
        rel=p.relative_to(ROOT);dest=packet/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dest);picked.add(str(rel))
    def tree(rel,suffixes=None):
        for p in sorted((ROOT/rel).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and (suffixes is None or p.suffix in suffixes):add(p)
    for rel in ['requirements.lock.txt','run_v4.sh','src/v2_models.py','src/v2_curved_models.py',
        'src/v3_design.py','src/v3_prepare.py','src/v3_run.py','src/v3_summarize.py','src/v3_rfl.py',
        'src/v4_expansion.py','src/v4_policy_extension.py','src/v4_summarize.py',
        'src/v4_yankin_import.py','src/v4_jambor_import.py','src/v4_documents.py','src/v4_package.py',
        'tests/test_v3_design.py','tests/test_v3_rfl.py','protocols/v3/frozen_design.txt',
        'data/raw/manifest.json','data/raw/figshare_article_22337629.json',
        'data/processed/ss316l_lpbf_all.csv','data/processed/v2/strict_fulltraining/cohort.csv',
        'literature/provenance_v2/final_source_gate.csv']:
        add(rel)
    tree('protocols/v4')
    tree('data/processed/v4',{'.csv','.json'})
    for rel in ['data/external_v4/source_expansion','data/external_v4/yankin2025','data/external_v4/rbf2026']:
        tree(rel,{'.csv','.json'})
    for rel in ['data/external_v4/jambor2025/seven_interrupted_specimens.csv',
                'data/external_v4/jambor2025/cyclic_response_long.csv.gz',
                'data/external_v4/jambor2025/history_inventory.csv',
                'data/external_v4/jambor2025/acquisition_receipt.json',
                'data/external_v4/jambor2025/normalization_receipt.json']:
        add(rel)
    tree('data/external_v4/jambor2025/selected_original_files',{'.csv','.txt'})
    tree('data/external_v4/raw_search',{'.csv','.txt','.xlsx','.zip'})
    # All original article PDFs/XML, images, HTML/access snapshots and local fit pickles omitted.
    for rel in ['literature/v4_open/inventory','literature/v4_open/source_expansion','literature/v4_open/raw_search']:
        tree(rel,{'.csv','.json','.py','.txt'})
    for rel in ['normalization_receipt.json','source_audit.json','independent_audit.json','manifest.json',
                'overlap_screen.json','table1_transcription.json','normalize_table1.py']:
        add('literature/v4_open/rbf2026/'+rel)
    for rel in ['literature/v4_open/jambor2025/zenodo_metadata.json',
                'literature/v4_open/jambor2025/archive_inventory.json',
                'literature/v4_open/shrestha2019/source_access_and_equivalence_audit.json']:
        add(rel)
    for name in ['controlled_cap1e7','controlled_cap1e6','source_holdout_cap1e7','source_holdout_cap1e6']:
        tree('results/v4/'+name,{'.csv','.json'})
    for rel in ['results/v4/parent_replay_receipt.json','results/v4/headline_policy_table.csv']:
        add(rel)
    tree('manuscript/v4',{'.pdf','.json','.png','.svg','.txt'})
    add('literature/v4_open/raw_search/xlrd-2.0.2-py2.py3-none-any.whl')
    tree('outreach/v4',{'.txt'})
    h=pd.read_csv(ROOT/'data/processed/v2/strict_fulltraining/cohort.csv')
    e=pd.read_csv(ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv')
    h['v4_qualification']='legacy_v2_source_reviewed_CA; database scalar defaults may remain, inspect source gate'
    e['v4_qualification']='v4_source_methods_and_figure_reviewed_CA; missing physical IDs remain blank'
    full=pd.concat([h,e],ignore_index=True)
    assert len(full)==441 and full.row_id.is_unique and full.dataset_id.nunique()==48 and full.doi.nunique()==14
    d=packet/'data/processed/v4';full.to_csv(d/'training441_full_metadata.csv',index=False)
    picked.add('data/processed/v4/training441_full_metadata.csv')
    coverage=[]
    for col in ['power','scan_speed','hatch_space','layer_thickness','direction','surface','thermal',
                'heat_temperature','heat_time','load_ratio','frequency','temperature','kt','specimen_size']:
        coverage.append({'field':col,'nonmissing_rows':int(full[col].notna().sum()),'all_rows':441,
            'interpretation':'Nonmissing metadata count only; not global primary-source measurement certification.'})
    pd.DataFrame(coverage).to_csv(d/'training441_metadata_coverage.csv',index=False)
    picked.add('data/processed/v4/training441_metadata_coverage.csv')
    readme=(ROOT/'manuscript/v4/READ_ME_FIRST.txt').read_text()
    (packet/'READ_ME_FIRST.txt').write_text(readme)
    (packet/'LICENSE_AND_ATTRIBUTION.txt').write_text('Public-source licenses and attribution are recorded in data/raw/manifest.json, literature/v4_open/raw_search/source_manifest.json, data/external_v4/*/*receipt.json, and manuscript/v4/source_references.json. Each derived file preserves source DOI and transformation notes. Research scripts are supplied for reproducibility; no ownership or redistribution rights in source articles are asserted. No articlePDF/HTML/XML/fulltext/image is included.\n')
    # A complete manifest for the files actually shipped, not all private cache/audit sources.
    items=[]
    for p in sorted(packet.rglob('*')):
        if p.is_file() and p.name!='PACKET_MANIFEST.json':items.append({'path':str(p.relative_to(packet)),'bytes':p.stat().st_size,'sha256':digest(p)})
    (packet/'PACKET_MANIFEST.json').write_text(json.dumps({'files':items,'files_count':len(items),'scope':'Local numeric data,analysis,source audits,code anddocuments; exclusions inREADME.'},indent=2)+'\n')
    for name in ['public_data_addendum_en.pdf','acik_veri_ilerleme_raporu_tr.pdf','training_expansion.png','policy_cost_life.png','phase4_evidence.json']:
        shutil.copyfile(ROOT/'manuscript/v4'/name,OUTPUT/name)
    shutil.copyfile(d/'training441_full_metadata.csv',OUTPUT/'egitim_441.csv')
    archive=OUTPUT/'acik_veri_ve_tekrar_calistirma_paketi.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(packet.rglob('*')):
            if p.is_file():z.write(p,arcname='research_packet/'+str(p.relative_to(packet)))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    for item in items:
        p=packet/item['path'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256']
    receipt={'zip':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive),
        'manifest_files':len(items),'CRC_pass':True,'all_shipped_hashes_verified':True,
        'predictive_instances':164160,'physical_independence_claim':False,'goal_status':'active;broadersearchandsecondmappedcampaignremainopen'}
    (OUTPUT/'teslim_dogrulama.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
