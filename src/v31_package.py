"""Portable licensed first-block data + algorithms, frozen source gate and audits."""
from __future__ import annotations
import hashlib,json,os,shutil,zipfile
from pathlib import Path
from datetime import datetime,timezone
from src.v3_prepare import ROOT,digest
DEST=Path(os.environ.get('V31_OUTPUT',ROOT/'manuscript/v31'))
def main():
 DEST.mkdir(parents=True,exist_ok=True)
 stage=ROOT/'work/v31/shareable';stage.mkdir(parents=True,exist_ok=True)
 selected=set()
 def add(rel):
  p=ROOT/rel
  if p.is_file():selected.add(p)
 for p in (ROOT/'src').glob('*.py'):selected.add(p)
 for rel in ['tests/test_v3_design.py','tests/test_v3_rfl.py','run_v31.sh','requirements.lock.txt','STATE.md',
  'protocols/v3/frozen_design.txt','protocols/v3/virgin_first_exposure_extension.txt',
  'data/processed/v2/strict_fulltraining/cohort.csv',
  'data/processed/v3/firstblock/merot52.csv','data/processed/v3/firstblock/merot52.receipt.json',
  'data/processed/v3/new_candidates/dastgerdi.csv',
  'data/processed/v3/identity_replay_portable/cohort.csv','data/processed/v3/identity_replay_portable/frozen_splits.json',
  'data/external_v3/continuation_papers/data_fatigue_merot.csv',
  'data/external_v3/continuation_papers/merot_first_exposure_unique_physical70_verified.csv',
  'data/external_v3/continuation_papers/merot_first_exposure_air_nominal43.csv',
  'data/external_v3/continuation_papers/merot_first_exposure_air_localstress9_exploratory.csv',
  'data/external_v3/continuation_papers/merot_first_exposure_quarantine35.csv',
  'data/external_v3/paper_supplements/dastgerdi2023_uninterrupted_pilot6.csv',
  'literature/v3_campaigns/continuation_papers/Merot_zenodo6653187_metadata.json',
  'literature/v3_campaigns/continuation_papers/merot_source_specimen_build_crosswalk70.csv',
  'literature/v3_campaigns/continuation_papers/merot_primary_source_handoff.md',
  'literature/v3_campaigns/continuation_papers/merot_final_method_limitations.md',
  'literature/v3_campaigns/continuation_papers/merot_final_normalization_receipt.json',
  'literature/v3_campaigns/continuation_papers/merot_first_exposure_eligibility_frozen.json',
  'literature/v3_campaigns/continuation_raw/evidence_ledger.md',
  'literature/v3_campaigns/continuation_raw/source_manifest.json',
  'literature/v3_campaigns/continuation_raw/second_campaign_focused_search_receipt.json',
  'literature/v3_campaigns/continuation_trombley/thesis_lineage_audit_receipt.json',
  'literature/v3_campaigns/continuation_trombley/thesis_lineage_followup.md',
  'results/v3/identity_full_replay_comparison.json','results/v3/identity_portable_replay_comparison.json',
  'logs/v3/identity_portable_replay_final.log',
  'literature/provenance_v2/final_source_gate.csv','protocols/v2/frozen_design.txt']:
  add(rel)
 for p in (ROOT/'literature/v3_campaigns/continuation_merot_audit').glob('*'):
  if p.suffix in ['.json','.md','.csv','.py']:selected.add(p)
 for cap in ['1e7','1e6']:
  for p in (ROOT/f'results/v3/identity_cap{cap}').glob('*'):
   if p.suffix in ['.csv','.json']:selected.add(p)
 # No copyrighted thesis text/PDF/screenshots or publisher-preview bodies.
 assert not any(p.suffix in ['.pdf','.png'] for p in selected)
 readme=('Önce asama3-1-kimlik-ve-gerilme.pdf raporunu okuyun.\n\n'
 'Yeni kaynak: bir yazar kampanyasından43 nominal ilk-blok kaydı;31 numune/3 koşul gerilme seçiminde. '
 '3 gerçek üretim,2 toz partisi; seçim karşılaştırması2 üretim ve1 toz partisini kapsar. '
 'Dastgerdi6 ayrı küçük pilot; sıcaklık belirtilmemiş. İki tam yöntem uyumlu bağımsız RT kampanyası hedefi açık.\n\n'
 'Yüksek gerilme k3, hiyerarşik alt ömrü%33,6 ve RFL alt ömrü%8,5 artırır; çevrim maliyeti%7,5 azalır. '
 'Ancak sağ sansür gerçek risk artışını dışlamaz. Genel güvenilir%90 tasarım veya politika üstünlüğü kanıtlanmadı. '
 'Her panelde yalnız1 kampanya var; güven aralıkları NaN ve başarı kapıları değerlendirilemez.\n\n'
 'Tekrar: ZIPi ayrı klasöre çıkarın; Python3.12 ile zsh run_v31.sh çalıştırın. '
 'Ham CC BY4.0 CSV ve elle kaynak denetiminden geçmiş70 satırlık kimlik kapısı hash ile doğrulanır; '
 'sonra ilk-blok normalizasyonu, ortak sorgular,6 model/4 politika/10 bölme/iki sınır ve özetler yeniden hesaplanır. '
 'Tezdeki üretim eşlemesi otomatik OCR tahmini değildir; bağımsız iki okuyucunun sabit kaynak kararıdır. '
 'Tam tez PDFsi/metni/sayfa görüntüleri pakette yoktur; birincil kaynağa URL ve sayfa numarası verilir.\n\n'
 'Taşınabilir hesap367 satırdır:309 tarihsel eğitim+52 Mérot+6 Dastgerdi. Eski Trombley129 kullanılmadığı için çıkarıldı. '
 '50 görev, tüm sorgu/havuz kimlikleri ve eğitim grupları aynıdır. İki sınırdaki12 tablonun bilimsel değerleri ve '
 'uyum parametreleri tam eşleşti; prediction fit_signature önbellek metadatası, boş eski sütunlar çıkarıldığı için değişir. '
 'Aynı orijinal karma şemayla yapılan ayrı temiz tekrarda12 tablo tüm sütunlarıyla tam eşleşti. '
 'Bunlar yeni fiziksel deney ya da dış bilimsel tekrar değildir.\n\n'
 'Atıf/lisans: Mérot, Gallegos Mayorga, Morel, Pessard, Buttin ve Baffie(2022),316L L-PBF fatigue dataset, '
 '10.5281/zenodo.6653187,CC BY4.0(https://creativecommons.org/licenses/by/4.0/); '
 'değişiklikler: yalnız ilk blok, fiziksel kimlik karantinası, tezden üretim/toz eşlemesi, ayrı nominal/yerel paneller. '
 'Tez: PierreMérot(2021),tel-03688021v1,https://pastel.hal.science/tel-03688021v1; '
 'PDF85/printed61 Table2.1,PDF84 naming,PDF114–115 methods,PDF279–280 stress. '
 'Tarihsel veri FatigueData-AM2022,10.6084/m9.figshare.22337629,CC BY4.0, kaynak denetimiyle türetilmiş309 kayıt. '
 'Dastgerdi vd.,10.1016/j.addma.2023.103559,CC BY4.0 makale tablosundan6 kesintisiz numune.\n\n'
 'Yazar mesajı gönderilmedi; upload/yayın/yeni fiziksel deney yapılmadı.\n')
 (DEST/'BASLANGIC.txt').write_text(readme)
 (stage/'PHASE31_README.txt').write_text(readme)
 for rel,name in [('protocols/v3/virgin_first_exposure_extension.txt','ilk-blok-ek-protokolu.txt'),
 ('results/v3/identity_portable_replay_comparison.json','tasinabilir-tekrar-denetimi.json'),
 ('literature/v3_campaigns/continuation_merot_audit/identity_results_independent_audit.json','bagimsiz-hesap-denetimi.json')]:shutil.copy2(ROOT/rel,DEST/name)
 (stage/'PACKAGE_MANIFEST.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
  'files':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(selected)],
  'manual_source_gate':'Independently source/visual audited; final70 is a frozen manual mapping, not an automated thesis parse.',
  'omitted':'Unlicensed thesis PDF/text/screenshots, publisher preview bodies, unused Trombley raw/individual records.'},indent=2)+'\n')
 zpath=DEST/'asama3-1-tekrar-uretim.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(selected):z.write(p,str(p.relative_to(ROOT)))
  for p in stage.iterdir():z.write(p,p.name)
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  m=json.loads(z.read('PACKAGE_MANIFEST.json'))
  for row in m['files']:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
 entries=len(m['files'])+2
 delivery=[{'name':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(DEST.iterdir()) if p.is_file() and p.name not in ['TESLIM_KAYDI.json','SHA256SUMS.txt']]
 (DEST/'TESLIM_KAYDI.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
  'files':delivery,'zip_entries':entries,'zip_crc_and_all_manifest_hashes_verified':True,
  'pdf_visual_qa':'3 pages rendered and inspected; rerender inspected after final prose edits',
  'new_source_gate':'one fully lineaged additional RT author campaign; second full independent RT campaign remains unresolved'},indent=2,ensure_ascii=False)+'\n')
 (DEST/'SHA256SUMS.txt').write_text('\n'.join(r['sha256']+'  '+r['name'] for r in delivery)+'\n')
 print(json.dumps({'zip_bytes':zpath.stat().st_size,'zip_entries':entries,'deliverables':len(delivery)}))
if __name__=='__main__':main()
