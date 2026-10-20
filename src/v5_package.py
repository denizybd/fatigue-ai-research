"""Package the bounded v5 evidence; omit original articles and author code."""
from pathlib import Path
import json
import shutil
import zipfile
from src.v3_prepare import ROOT,digest

OUTPUT=Path('/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs/phase5')


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    packet=OUTPUT/'research_packet';packet.mkdir(exist_ok=True)
    picked=set()
    def add(rel):
        p=ROOT/rel;assert p.is_file(),str(p)
        dest=packet/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dest);picked.add(str(rel))
    def tree(rel,suffixes):
        for p in sorted((ROOT/rel).rglob('*')):
            if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts:add(p.relative_to(ROOT))
    for rel in ['requirements.lock.txt','run_v5.sh','src/v2_models.py','src/v2_curved_models.py',
        'src/v3_prepare.py','src/v3_design.py','src/v3_run.py','src/v3_summarize.py','src/v3_rfl.py',
        'src/v5_rbf.py','src/v5_rbf_audit.py','src/v5_pinn_acquire.py','src/v5_pinn_import.py',
        'src/v5_documents.py','src/v5_package.py','tests/test_v3_design.py','tests/test_v3_rfl.py',
        'data/processed/v2/strict_fulltraining/cohort.csv',
        'data/processed/v4/controlled_expansion/strict309.csv',
        'data/processed/v4/controlled_expansion/expanded441.csv',
        'data/external_v4/source_expansion/source_qualified_ca_expansion.csv',
        'literature/provenance_v2/final_source_gate.csv',
        'literature/v4_open/source_expansion/v4_code_audit.json',
        'literature/v4_open/inventory/independent_v4_input_audit.json',
        'literature/v4_open/rbf2026/source_audit.json','literature/v4_open/rbf2026/independent_audit.json']:
        add(Path(rel))
    tree(Path('data/external_v4/rbf2026'),{'.csv','.json'})
    tree(Path('data/external_v5'),{'.csv','.json'})
    tree(Path('data/processed/v5/rbf'),{'.csv','.json'})
    tree(Path('protocols/v5'),{'.txt','.json'})
    for sub in ['pinn2025','faue','palmer2025','bartosak','bremen2025','ziri2022','rbf']:
        base=ROOT/'literature/v5_open'/sub
        # Curated evidence, transformation scripts and audits, not full-text snapshots.
        for name in ['source_audit.json','normalization_receipt.json','curation_receipt.json',
            'verification_receipt.json','evidence_ledger.json','independent_workbook_audit.json',
            'independent_normalization_audit.json','independent_code_review.json','design_receipt.json',
            'parent_prefit_review.json','fresh_replay_setup.json','fresh_replay_comparison.json',
            'parent_fresh_replay_verification.json','relocation_recovery_receipt.json',
            'source_curation_audit.json','official_pdf_receipt.json','overlap_screen.json',
            'diagnostic_scope_note.json','table2_source_cells.json','source_discrepancy_flags.csv',
            'download_manifest.json','pinned_commit_receipt.json','author_repository_receipt.json',
            'normalize_table2.py','curate_bremen.py','annotate_recovered_evidence.py',
            'independent_contrast_check.py','fresh_replay.py','curate_ziri.py','curate_source_tables.py']:
            if (base/name).is_file():add((base/name).relative_to(ROOT))
    for cap in ['5e6','1e7']:
        tree(Path(f'results/v5/rbf_cap{cap}'),{'.csv','.json'})
    tree(Path('manuscript/v5'),{'.pdf','.json','.csv','.png','.svg','.txt'})
    readme='''AM316L public-data collection and rotating-bending pilot - phase5

20 October2026. Local research checkpoint, not a submission or new safety guarantee.
Start with manuscript/v5/public_data_rbf_addendum_en.pdf or the Turkish report.

Reproduce the frozen RBF experiments with: zsh run_v5.sh
Python3.12.13 was used, dependencies are pinned in requirements.lock.txt.
The supplied hashes, target queries, source-family exclusion and code are checked.
No model/task pickle cache is included. A fresh empty-cache run reproduced all36
scientific CSVs and every fitted parameter/diagnostic, excluding elapsed time.
Predictions and selections repeat67source points; they are not physical test counts.

Training input is unchanged at441. PrimaryRBF25C44rows and450C23rows are separate.
All67 belong to one related source family;25ambientasbuilt points are explicitly
borrowed from108491. Exact physical specimen/build/virgin identities unverified.
5M support cost is identifiable truncated exposure. At10M use the dedicated
policy_cost_savings_bounds.csv, not inherited lower-bound support_cycle_change
as if it were exact cost. One-family confidence gates are explicitly unevaluable.
The intercept model's k0 diagnostic shift fields can be stale; its predictions
use the correct hierarchical reference. Read diagnostic_scope_note/code audit.

New source collection:44exactPINNfamilyNf,12exactstraincontrolledNf,16approximate
Faue markers, plus13source-fittedstrengthparameters. These roles are separate.
No invented specimen/batch links, future fracture covariates or source mean curves.
The PINN44 have no row-to-three-batch map or complete censor inventory and are
not reliability/acquisition fit inputs. All original source discrepancies retained.
Source URLs, hashes, licenses, qualifications and transformation code are supplied.

Article full texts, PDFs/XML/HTML/images, original author workbooks and authorcode
are excluded. PublicPINNworkbook can optionally be reacquired from publisher and
fixed authorcommit via python -m src.v5_pinn_acquire, then imported with
python -m src.v5_pinn_import. No downloaded authorcode is executed.
Graph extraction cannot be reproduced from an automatic raw-image pipeline here:
reported approximate coordinates and pixel decisions are the curated input.

The user moved the working source folder toDesktop during execution; code/input
hashes remained unchanged. Canonical runtime root is computed from sourcefile.
No correspondence or publication occurred. The goal remains active: stronger
method/tuning comparisons and a second independently mapped campaign are open.
'''
    (packet/'READ_ME_FIRST.txt').write_text(readme)
    (packet/'LICENSE_AND_ATTRIBUTION.txt').write_text('Original sources and licenses are recorded in each source_audit and curation receipt. FatigueData-AM2022 and raw source data remain attributed to their authors. Only factual numerical extractions and our research code/audits are included here. No ownership or redistribution permission in original articles or unlicensed authorcode is asserted. This is a local research packet, not a publication.\n')
    # Refuse stale unselected content in this packet; do not silently ship caches.
    for p in packet.rglob('*'):
        if p.is_file():
            rel=str(p.relative_to(packet))
            assert rel in picked or rel in {'READ_ME_FIRST.txt','LICENSE_AND_ATTRIBUTION.txt','PACKET_MANIFEST.json'},rel
    files=[dict(path=str(p.relative_to(packet)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(packet.rglob('*')) if p.is_file() and p.name!='PACKET_MANIFEST.json']
    (packet/'PACKET_MANIFEST.json').write_text(json.dumps(dict(files=files,files_count=len(files)),indent=2)+'\n')
    for name in ['public_data_rbf_addendum_en.pdf','yeni_veri_ve_deney_secimi_tr.pdf','rbf_policy_interactions.png','phase5_evidence.json','rbf_policy_evidence.csv']:
        shutil.copyfile(ROOT/'manuscript/v5'/name,OUTPUT/name)
    archive=OUTPUT/'yeni_veri_ve_doner_egme_tekrar_paketi.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(packet.rglob('*')):
            if p.is_file():z.write(p,'research_packet/'+str(p.relative_to(packet)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in files:
            import hashlib
            assert hashlib.sha256(z.read('research_packet/'+item['path'])).hexdigest()==item['sha256']
    receipt=dict(zip=archive.name,bytes=archive.stat().st_size,sha256=digest(archive),manifest_files=len(files),
        CRC_pass=True,all_archive_members_verified=True,prediction_instances=88320,selection_instances=2400,
        new_gold_campaigns=0,goal_status='active',no_contact_or_publication=True)
    (OUTPUT/'teslim_dogrulama.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
