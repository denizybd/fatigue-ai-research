"""Local phase-2 delivery. Explicitly excludes unlicensed external raw records."""
from __future__ import annotations
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from datetime import datetime,timezone
from src.v2_prepare import ROOT

DEST=Path('/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs/phase2')
RUNS=['strict','fulltraining','curved_fulltraining','nearcluster_fulltraining','no_afkhami',
      'external','external_fulltraining','external_curved','external_bootstrap',
      'same_population_internal','same_population_external','all_family','weak_family','broader_fulltraining']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def selected():
    files=[]
    for name in ['STATE.md','README.md','run_v2.sh','requirements.lock.txt']:
        files.append(ROOT/name)
    for folder in ['src','tests','protocols/v2','figures/v2','manuscript/v2']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files.append(p)
    for p in (ROOT/'outreach').glob('v2_*'):files.append(p)
    for name in ['primary.csv','primary_weak_edge.csv','source_family_map.csv','grouping_report.json',
                 'v2_provenance_condition_ledger.csv','v2_provenance_metadata_corrections.csv']:
        files.append(ROOT/'data/processed'/name)
    for p in (ROOT/'data/processed/v2').rglob('*'):
        if not p.is_file():continue
        if p.parent.name.startswith('external') and p.name=='cohort.csv':continue
        files.append(p)
    for name in ['FatigueData-AM2022.mat','manifest.json','figshare_article_22337629.json']:
        p=ROOT/'data/raw'/name
        if p.exists():files.append(p)
    files.extend([ROOT/'data/DATA_DICTIONARY.md',ROOT/'data/SOURCE_AND_MEASUREMENT_ASSUMPTIONS.md'])
    for folder in ['literature/provenance_v2','literature/methods_v2','literature/fresh_campaign_v2']:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            if p.suffix in ['.md','.py','.json']:files.append(p)
            elif p.suffix=='.csv' and not any(v in p.name for v in [
                'source_read_five_records','independent_fresh_validation_rows','historical_coordinate_screen']):
                if 'fresh_campaign_v2' in p.parts and p.name not in [
                    'historical_source_gate.csv','split_audit_configurations.csv']:
                    continue
                # Per-specimen external checks remain local; source-level gate
                # and aggregate audit tables are derived evidence.
                header=p.read_text(errors='replace').splitlines()[0]
                if not any(v in header for v in ['cycles_observed','stress_max_MPa','specimen_name','repository_entity_id']):files.append(p)
    for folder in RUNS:
        for p in (ROOT/'results/v2'/folder).rglob('*'):
            if not p.is_file() or p.suffix not in ['.csv','.json','.md']:continue
            if 'tasks' in p.relative_to(ROOT/'results/v2'/folder).parts:continue
            if 'external' in folder and p.name=='predictions.csv':continue
            files.append(p)
    for p in (ROOT/'results/v2').glob('*.json'):files.append(p)
    for p in (ROOT/'logs/v2').glob('*.log'):files.append(p)
    return sorted(set(files))

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    copies={'manuscript/v2/arastirma_ozeti_tr.pdf':'arastirma-ozeti-tr.pdf',
            'manuscript/v2/research_note_en.pdf':'research-note-en.pdf',
            'manuscript/v2/research_brief_en.pdf':'research-brief-en.pdf',
            'outreach/v2_email_draft_en.txt':'tridello-email-draft.txt',
            'outreach/v2_technical_qa_tr.txt':'teknik-soru-cevap-tr.txt',
            'literature/provenance_v2/final_source_gate.csv':'kaynak-kapisi.csv',
            'data/processed/v2_provenance_metadata_corrections.csv':'kaynak-duzeltmeleri.csv',
            'figures/v2/03_source_heterogeneity.png':'kaynaklara-gore-risk.png',
            'figures/v2/04_external_learning.png':'dis-kampanya-sonuclari.png'}
    for src,dst in copies.items():shutil.copy2(ROOT/src,DEST/dst)
    (DEST/'BASLANGIC.txt').write_text('Önce arastirma-ozeti-tr.pdf dosyasını okuyun. İngilizce teknik rapor altı, kısa özet bir sayfadır.\n\n'
        'Bu aşama önceki pilotun veri uygunluğu ve bilimsel yorumunu düzeltir. Eski iletişim paketi yeni düzeltmeler eklenmeden kullanılmamalıdır. '
        'Yeni güçlü ve güvenilir algoritma gösterilmedi; az gözlemli uyarlama ortalamada yararlı olsa da kaynak bazında risk artabiliyor.\n\n'
        'Paket yerel kod, protokol, kaynak kapısı, tarihsel veri ve sonuçları içerir. Dış kampanyanın lisansı belirtilmeyen ham/normalize numune kayıtları ve tek-numune tahminleri eklenmedi; '
        'yazarların açık sayfalarından yerel alma kodu ve özet sonuçlar sağlandı. Çalıştırma: zsh run_v2.sh. Python 3.12.13 ve kilitli bağımlılıklar kullanılır; '
        'eksik dış kayıtlar yeniden alınır ve özgün SHA256 ile eşleşmesi aranır. Kaynak değişmişse sessizce yeni sonuç üretilmez.\n\n'
        'E-posta yalnız taslak. Gönderim, yükleme, yayın veya yeni fiziksel deney yapılmadı.\n')
    with zipfile.ZipFile(DEST/'tridello-contact-draft.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in ['research-brief-en.pdf','tridello-email-draft.txt','kaynaklara-gore-risk.png','dis-kampanya-sonuclari.png','BASLANGIC.txt']:
            z.write(DEST/name,name)
    files=selected()
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
      'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],
      'exclusions':'External Materials Commons raw HTML, normalized per-specimen records, external per-specimen predictions; copyrighted full texts/images; environments/Git internals; redundant replay/per-task copies. Full original historical predictions and combined fit/split receipts are retained.',
      'scope':'Source-method reviewed benchmark and failed reliable-usefulness claim; no independent physical replication.',
      'original_data_attribution':'Zhang & Xu2023 FatigueData-AM2022 v2 DOI10.6084/m9.figshare.22337629.v2 CC BY4.0; descriptor10.1038/s41597-023-02150-x.',
      'external_source':'Trombley etal2025 DOI10.1038/s41598-025-97031-1; repository10.13011/m3-c93d-z035 has no specified data license.'}
    archive=DEST/'fatigue-phase2-reproducible.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,Path('fatigue-ai-research')/p.relative_to(ROOT))
        z.writestr('fatigue-ai-research/DELIVERY_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert not any('/data/external_v2/' in n for n in names)
        assert not any('/external/cohort.csv' in n or '/external_fulltraining/cohort.csv' in n for n in names)
        assert not any('/external' in n and n.endswith('/predictions.csv') for n in names)
    (DEST/'TESLIM_KAYDI.json').write_text(json.dumps({k:v for k,v in manifest.items() if k!='files'}|
        {'archive_files':len(files)+1,'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
         'deliverables':[{ 'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(DEST.iterdir())
             if p.is_file() and p.name not in ['SHA256SUMS.txt','TESLIM_KAYDI.json']]},indent=2)+'\n')
    (DEST/'SHA256SUMS.txt').write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(DEST.iterdir())
        if p.is_file() and p.name!='SHA256SUMS.txt')+'\n')
    print(json.dumps({'output':str(DEST),'archive_files':len(files)+1,'archive_MiB':archive.stat().st_size/1024**2},indent=2))

if __name__=='__main__':main()
