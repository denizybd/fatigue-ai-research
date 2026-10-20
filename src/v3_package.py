"""Package code, licensed author data, derived aggregates and audit receipts."""
from __future__ import annotations
import hashlib,json,os,shutil,zipfile
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
from src.v3_prepare import ROOT,digest
DEST=Path(os.environ.get('V3_OUTPUT',ROOT/'manuscript/v3'))

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    direct={
      ROOT/'protocols/v3/frozen_design.txt':'sabit-deney-protokolu.txt',
      ROOT/'protocols/v3/covariate_scope_addendum.txt':'tek-gerilme-grubu-ek-notu.txt',
      ROOT/'literature/v3_campaigns/raw_repository/author_mapping_request_drafts.txt':'yazarlar-icin-veri-sorulari.txt',
      ROOT/'results/v3/full_replay_comparison.json':'tam-tekrar-denetimi.json'}
    for p,name in direct.items():shutil.copy2(p,DEST/name)
    (DEST/'BASLANGIC.txt').write_text(
      'Önce asama3-gerilme-secimi.pdf raporunu okuyun.\n\n'
      'Aynı sorgu numuneleriyle dört gerilme seçimi ve altı sansürlü model sınandı. '
      'İki yeni büyük yazar veri seti kazandık; numune→build→toz partisi eşlemesi doğrulanmış '
      'iki yeni bağımsız kampanya henüz elde edilemedi. Bu açık bağımlılık kapanmış sayılmıyor. '
      'Bir küçük tek-build pilotu var; sıcaklık ve olası eski-veri tekrarı sınırlamaları korunuyor.\n\n'
      'Sonuçlar keşifseldir. Yüksek gerilme k3 seçiminde hiyerarşik Basquin alt sınırı yaklaşık%20 '
      'artar ve gözlenen destek çevrim maliyeti yaklaşık%70 azalır; RFL aynı seçimde daha kısa '
      'alt sınır ve daha düşük risk verir. Genel politika üstünlüğü veya güvenilir%90 tasarım '
      'garantisi gösterilmedi. Maliyet çevrim sayısıdır; duvar saati veya para değildir.\n\n'
      '1e7/1e6 CSVler çok-gerilmeli koşulların kampanya eşit ağırlıklı sonuçlarıdır. '
      'success_gates içindeki geçişler yalnız keşifsel sayısal ekranlamadır; iki kampanyayla '
      'bootstrap aralığı güçlü popülasyon güvencesi sağlamaz. Hamveri kimlik kapısı ayrıca geçmelidir.\n\n'
      'Tekrar üretim: ZIPi ayrı klasöre çıkarın; zsh run_v3.sh çalıştırın. Python3.12 ve kilitli '
      'bağımlılıklar önerilir. Ana veriler ve ilk protokol değişmez; script yeni replay klasörüne yazar. '
      'Trombley ham/normalize numune kayıtları lisans belirtilmediğinden pakette yoktur; açık '
      'yazar sayfalarından yerelde alınır ve özgünSHA256 aranır. Kaynak değişmişse script durur. '
      'Her iki bütçenin20 tablosu mevcut yerel veriyle taze çalıştırmada birebir tekrarlandı.\n\n'
      'Yazar soruları yalnız taslaktır, gönderilmedi. Dış yazışma/yayın/yeni fiziksel deney yapılmadı.\n',encoding='utf-8')
    stage=ROOT/'work/v3/shareable';stage.mkdir(parents=True,exist_ok=True)
    selected=set()
    def add(p):
        p=Path(p)
        if p.is_file():selected.add(p)
    for folder in ['src','tests','protocols/v3']:
        for p in (ROOT/folder).glob('*'):
            if p.suffix in ['.py','.txt','.md','.json']:add(p)
    for name in ['run_v3.sh','requirements.lock.txt','STATE.md','README.md']:
        add(ROOT/name)
    for name in ['data/processed/v2/strict_fulltraining/cohort.csv',
                 'data/processed/ss316l_lpbf_all.csv','data/raw/FatigueData-AM2022.json',
                 'data/raw/manifest.json','data/raw/figshare_article_22337629.json',
                 'data/DATA_DICTIONARY.md','data/SOURCE_AND_MEASUREMENT_ASSUMPTIONS.md',
                 'data/processed/v3/common/frozen_splits.json']:
        add(ROOT/name)
    for p in (ROOT/'data/processed/v3/new_candidates').glob('*.csv'):add(p)
    for p in (ROOT/'data/external_v3/paper_supplements').glob('*.csv'):add(p)
    for p in (ROOT/'data/external_v3/raw_repository').glob('*.csv'):add(p)
    add(ROOT/'data/external_v3/raw_repository/tomaszewski2023_data.xlsx')
    # The small original named DED-fatigue source is separate; large corrosion
    # curves and the231-row mixed literature table are not needed for this study.
    for name in ['yin_named18_outside_scope.csv','yin_complete14_outside_scope.csv','Ar_vs_N2_JMP_Final.jmp']:
        add(ROOT/'data/external_v3/raw_repository/yin2026_secondary'/name)
    raw_notes=['report.md','manifest.json','source_manifest.json','search_log.json',
       'independence_audit.json','normalization_receipt.json','independent_source_gate_review.json',
       'author_mapping_request_drafts.txt','normalize_raw_candidates.py','diller2024_readme.txt',
       'zenodo21105346_metadata.json','zenodo7650061_metadata.json','yin2026_secondary_report.md',
       'yin2026_extraction_receipt.json','yin2026_public_files.json']
    for name in raw_notes:add(ROOT/'literature/v3_campaigns/raw_repository'/name)
    for p in (ROOT/'literature/v3_campaigns/paper_supplements').glob('*'):
        if p.suffix in ['.json','.csv','.py'] or p.name=='paper_search_evidence.txt':add(p)
    for p in (ROOT/'literature/v3_methods').glob('*'):
        if p.suffix in ['.json','.md','.py']:add(p)
    for name in ['acquire_trombley.py','prepare_trombley.py','fresh_campaign_report.md',
                  'materialscommons_datacite.json','trombley_quality_and_provenance.json']:
        add(ROOT/'literature/fresh_campaign_v2'/name)
    add(ROOT/'results/v3/headline_facts.json');add(ROOT/'results/v3/full_replay_comparison.json')
    for name in ['final_cap1e7','final_cap1e6']:
        folder=ROOT/'results/v3'/name
        for sub in ['', 'multistress']:
            for p in (folder/sub).glob('*'):
                if p.suffix not in ['.json','.csv']:continue
                if p.name in ['predictions.csv','selections.csv']:
                    d=pd.read_csv(p)
                    if 'panel' in d:d=d[d.panel!='external_previous_unmapped_build']
                    else:d=d[~d.dataset_id.str.startswith('trombley')]
                    q=stage/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True)
                    d.to_csv(q,index=False)
                else:add(p)
    for name in ['final_cap1e7.log','final_cap1e6.log','full_replay.log','summary_cap1e7.log','summary_cap1e6.log']:
        add(ROOT/'logs/v3'/name)
    (stage/'PHASE3_README.txt').write_text((DEST/'BASLANGIC.txt').read_text()+
      '\nData attribution: FatigueData-AM2022,10.6084/m9.figshare.22337629, CC BY4.0; '
      'Tomaszewski,10.5281/zenodo.7650061, CC BY4.0; Diller etal.,10.5281/zenodo.21105346, CC BY4.0; '
      'Dastgerdi etal.,10.1016/j.addma.2023.103559, article/table CC BY4.0; '
      'Yin etal.,10.17632/h97k6w9vm5.1,CC BY4.0, outside scope. '
      'Trombley repository no license specified: raw metadata and individual endpoints/predictions omitted. '
      'Unchanged source-paper PDFs are not redistributed; URLs/page evidence/hash manifests remain.\n'
      'Filtered predictions and selections in this archive exclude Trombley; derived aggregates include it. '
      'Fresh run_v3.sh creates all predictions locally after source acquisition.\n')
    files=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(selected)]
    generated=[p for p in stage.rglob('*') if p.is_file()]
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'files':files,
        'generated_filtered_files':[{'path':str(p.relative_to(stage)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(generated)],
        'raw_external_omitted':'Trombley raw/normalized entity metadata, full mixed cohort, original mixed predictions and individual selected outcomes',
        'strict_additional_identity_qualified_rt_campaigns':0,
        'objective_remaining':'At least two source-certified specimen/build/batch mappings remain unavailable.'}
    (stage/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    zpath=DEST/'asama3-tekrar-uretim.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(selected):z.write(p,str(p.relative_to(ROOT)))
        for p in sorted(stage.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(stage)))
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        names=z.namelist();assert len(names)==len(set(names))
        assert not any('data/external_v2/' in n for n in names)
    deliverables=[]
    for p in sorted(DEST.iterdir()):
        if p.is_file() and p.name not in ['SHA256SUMS.txt','TESLIM_KAYDI.json']:
            deliverables.append({'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)})
    (DEST/'TESLIM_KAYDI.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
       'files':deliverables,'zip_crc_verified':True,'zip_entries':len(names),
       'pdf_visual_qa':'All3pages rendered and inspected; finalpage rechecked after replay-row addition',
       'full_replay':'20tables exact; see tam-tekrar-denetimi.json',
       'strict_identity_gate':'NOT ACHIEVED for additional new RT campaigns'},indent=2,ensure_ascii=False)+'\n')
    (DEST/'SHA256SUMS.txt').write_text('\n'.join(f"{x['sha256']}  {x['name']}" for x in deliverables)+'\n')
    print(json.dumps({'zip_bytes':zpath.stat().st_size,'zip_entries':len(names),
                      'deliverable_count':len(deliverables)},indent=2))
if __name__=='__main__':main()
