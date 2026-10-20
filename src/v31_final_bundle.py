"""Overlay current local papers/source-closure receipts on verified replay core."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,zipfile
from src.v3_prepare import ROOT,digest
BASE=Path(os.environ.get('V31_DELIVERY_ROOT','/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs/phase3-1'))
def main():
 old=BASE/'asama3-1-tekrar-uretim.zip';files={}
 with zipfile.ZipFile(old) as z:
  assert z.testzip() is None
  for n in z.namelist():
   files['audit/benchmark_original_package_manifest.json' if n=='PACKAGE_MANIFEST.json' else n]=z.read(n)
 def add(path,name=None):
  p=Path(path)
  if p.is_file():files[name or str(p.relative_to(ROOT))]=p.read_bytes()
 for folder in ['manuscript/v31','outreach/v31']:
  for p in (ROOT/folder).iterdir():
   if p.is_file():add(p)
 for name in ['README.md','STATE.md','outreach/CURRENT.txt','protocols/v3/future_independent_campaign_proposal.txt',
  'src/v31_english_figures.py','src/v31_english_documents.py','src/v31_final_bundle.py']:
  add(ROOT/name)
 for folder in ['closure_diller','closure_tomas','closure_root','closure_wu','closure_audit']:
  for p in (ROOT/'literature/v3_campaigns'/folder).glob('*'):
   # Public metadata bodies and original fulltexts are local audit inputs, not
   # needed to reproduce the frozen benchmark. Include own bounded receipts.
   if p.suffix not in ['.json','.md','.txt','.csv']:continue
   if p.name in ['solberg_title.json','solberg_author.json','solberg_thesis_record.json',
                 'Solberg2021_thesis.txt','filelink_response.txt','filelink_error.txt']:continue
   if p.stat().st_size>150000:continue
   add(p)
 for name in ['diller29-missing-source-fields.csv','tomaszewski9-missing-source-fields.csv',
              'gereken-kaynak-kaniti.txt','TESLIM_KAYDI.json','SHA256SUMS.txt']:
  add(BASE/'english-update'/name,'review/'+name)
 files['CURRENT_PACKET_README.txt']=(
 'CURRENT LOCAL REVIEW PACKET — not sent or published\n\n'
 'Read manuscript/v31/research_brief_en.pdf (1page), then current_working_paper_en.pdf (8pages). '
 'Editable sourceJSON, supplementary text, two English figures in PNG/SVG, current email draft and '
 'Turkish/English technicalQA accompany them. Human authorship/affiliation placeholders require confirmation.\n\n'
 'Scientific status: one fully lineaged additional room-temperature author campaign, not the intended '
 'plurality. The 43 nominal Merot rows yield31 acquisition specimens/3 conditions/2 builds/one powder lot/one '
 'program. Higher proposed q10 and7.5% support-cycle savings do not establish safe superiority. All first '
 'survivors stop at1e6; C1e7 is frozen primary planning, C1e6 is the prespecified source-matched sensitivity. '
 'The matched-intercept k0 label explicitly uses the hierarchical common starting prediction.\n\n'
 'Replay from this root: zsh run_v31.sh. Python3.12 and pinned requirements are used. The unchanged '
 '367-row replay inputs and50tasks need noTrombley source. Earlier local archive extraction passed all '
 '12 scientific-table exact comparisons, including identical population-fit parameters; cache hash is '
 'documented metadata. This combined packet overlays only current documentation/authoring code/source '
 'audit receipts on that verified computational core. No new model result or extra physical test is claimed.\n\n'
 'Data attribution/license is in PHASE31_README.txt; raw Merot/FatigueData derivatives/Dastgerdi table '
 'are CC BY4.0 with sources retained. The new PDF/PNG assets are our own documents/figures. Original '
 'Solberg/Merot/Trombley thesis PDFs/text/screenshots and publisher bodies are not redistributed. '
 'Original benchmark snapshot manifest is audit/benchmark_original_package_manifest.json; current '
 'FINAL_PACKAGE_MANIFEST.json hashes every current file. README/STATE were updated from that snapshot.\n\n'
 'Source dependency: reviewed Diller/Tomas/Solberg/Trombley chains do not expose the required second '
 'specimen/build crosswalk. Missing-fields templates are local and unsent. A released primary key or '
 'new source evidence is needed to advance the plural-campaign validation. Wu109943 fullmethod access '
 'remains unavailable after exact official-source recheck; novelty claims stay bounded.\n').encode()
 manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'benchmark_snapshot_zip_sha256':digest(old),
  'files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(files.items())],
  'objective_complete':False,'remaining_requirement':'second independent matched specimen/build-traceable campaign',
  'source_scope':'Bounded revalidation of available public primary chains, not a proof no public data exist anywhere.',
  'overridden_documentation':['README.md','STATE.md'],'no_changed_fitting_or_acquisition_code':True}
 # Enforce the exact computational core, not just an intention to preserve it.
 with zipfile.ZipFile(old) as z:
  for n in z.namelist():
   if n.startswith(('src/','data/','protocols/')) or n=='run_v31.sh':assert files[n]==z.read(n),n
 files['FINAL_PACKAGE_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 dst=BASE/'current-research-packet.zip'
 with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 with zipfile.ZipFile(dst) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  for r in manifest['files']:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
  assert not any('Solberg2021_thesis.pdf' in n or 'Merot2021_thesis.pdf' in n for n in z.namelist())
 receipt={'zip':dst.name,'sha256':digest(dst),'bytes':dst.stat().st_size,'entries':len(files),
   'crc_and_all_current_manifest_hashes_verified':True,'computational_core_byte_identical_to_replayed_snapshot':True,
   'models_rerun_for_document_changes':False,'paper_pages':8,'brief_pages':1,'source_gate_complete':False}
 (BASE/'current-packet-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
