"""Finalize read-only evidence audit after the current English delivery is frozen."""
from pathlib import Path
import json,hashlib,datetime
from pypdf import PdfReader
ROOT=Path('/Users/deniz2/Documents/ChatGPT/fatigue-ai-research')
OUT=Path('/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs/phase3-1/english-update')
A=ROOT/'literature/v3_campaigns/closure_audit/current_requirement_evidence.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
j=json.loads(A.read_text());m=json.loads((OUT/'TESLIM_KAYDI.json').read_text());v=json.loads((OUT/'visual_qa_receipt.json').read_text())
checks=[]
for row in m['files']:
 p=OUT/row['name'];checks.append({'name':row['name'],'bytes_match':p.stat().st_size==row['bytes'],'sha256_match':sha(p)==row['sha256']})
assert all(r['bytes_match'] and r['sha256_match'] for r in checks)
assert sha(OUT/'current_paper_source.json')==sha(ROOT/'manuscript/v31/current_paper_source.json')==v['source_json_sha256']
assert sha(OUT/'current_working_paper_en.pdf')==v['paper_sha256']
assert sha(OUT/'research_brief_en.pdf')==v['brief_sha256']
assert len(PdfReader(OUT/'current_working_paper_en.pdf').pages)==8
assert len(PdfReader(OUT/'research_brief_en.pdf').pages)==1
assert v['all_initial_pages_rendered_and_visually_inspected']
assert sorted(v['latest_modified_paper_pages_reinspected']+v['other_current_pages_pixel_identical_to_inspected_versions'])==list(range(1,9))
claim=json.loads((ROOT/'literature/v3_campaigns/closure_audit/english_claim_review.json').read_text())
assert claim['input_sha256']['manuscript/v31/current_paper_source.json']==v['source_json_sha256']
assert claim['table_audit']['all_match_printed_precision']
assert claim['k0_code_check']['disclosure_present_in_final_source']
wu=json.loads((ROOT/'literature/v3_campaigns/closure_wu/official_access_outcome.json').read_text())
assert wu['result']=='NO_OFFICIAL_FULLTEXT_OR_SUPPLEMENT_OBTAINED'
assert wu['new_identity_qualified_fatigue_records']==0
assert 'Current phase: 3.1' in (ROOT/'README.md').read_text()
assert 'second' in (ROOT/'STATE.md').read_text().lower()
for r in j['requirements']:
 if r['id']=='R13':
  r['evidence'].append('literature/v3_campaigns/closure_wu/official_access_outcome.json')
  r['status']='BOUNDED_EXTERNAL_ACCESS_LIMIT_AFTER_TARGETED_CLOSURE'
  r['interpretation']='RFL, information-based planning and transfer are established. Exact official Wu metadata/ORCID/NTU/publisher checks recovered no full text or supplement. Novelty remains limited to what the publisher preview supports; no unsupported absence claim is made. No further concrete readily accessible primary lead is currently documented.'
 if r['id']=='R14':
  r['status']='PASS_CURRENT_DELIVERED_DRAFTS_AND_QA'
  r['evidence']+=['outputs/phase3-1/english-update/TESLIM_KAYDI.json','outputs/phase3-1/english-update/visual_qa_receipt.json','literature/v3_campaigns/closure_audit/english_claim_review.json']
  r['interpretation']='Current 8-page English scientific paper, 1-page brief, supplementary methods/data dictionary, email draft and Turkish/English Q&A are delivered. All 17 manifest file hashes/bytes match. Final PDF/source hashes agree with the complete visual inspection chain. An independent reader verifies all 32 table rows, source limits, k0 reference disclosure and corrected creator attributions. No correspondence was sent.'
 if r['id']=='R15':
  r['status']='PASS_CURRENT_STATE_ENTRYPOINT_AND_NO_CORRESPONDENCE'
  r['interpretation']='README leads with phase3.1/current outreach and marks older material historical; STATE retains the missing-second-campaign condition. All current drafts remain unsent. No external upload, publication or physical test was performed.'
j['audited_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
j['english_delivery_final']={'manifest':str(OUT/'TESLIM_KAYDI.json'),'manifest_sha256':sha(OUT/'TESLIM_KAYDI.json'),'checks':checks,'all17files_hashes_and_sizes_match':len(checks)==17 and all(r['bytes_match'] and r['sha256_match'] for r in checks),'paper_pages':8,'brief_pages':1,'source_json_sha256':v['source_json_sha256'],'visual_qa_receipt_hash':sha(OUT/'visual_qa_receipt.json'),'final_PDF_hashes_match_visual_receipt':True,'all8paper_pages_covered_by_inspection_or_pixel_identity':True,'brief_inspected_layout_retained':v['final_brief_content_and_layout_unchanged_from_inspected_one_page'],'independent_claim_review_pass':claim['verdict']}
j['current_document_state']={'source_texts':'complete','rendering':'complete','delivery_manifest':'verified17/17','paper_pages':8,'brief_pages':1,'current_source_sha256':v['source_json_sha256'],'QAs':'Current Turkish and English versions, local unsent drafts.'}
j['remaining_computational_scientific_work_without_new_identities']['remaining_routine_work']=[]
j['remaining_computational_scientific_work_without_new_identities']['pending_scientific_checks_under_frozen_protocol']=[]
j['new_source_closure_summary']['wu_official_fulltext_or_supplement_obtained']=False
j['new_source_closure_summary']['wu_new_qualified_records']=0
j['blocking_condition']['all_current_concrete_source_closure_routes_complete_negative']=['Diller public deposit/dissertation/student-catalog build crosswalk','Tomaszewski exact raw-ID/article single-build inclusion key','Solberg official 173-page thesis: 316L section lacks identity key; maraging table excluded','Trombley official 196-page thesis/public process edges: common powder only, no four-build individual join','Wu109943 exact official fulltext/supplement access route']
j['blocking_condition']['status_recommendation']='Recommend blocked, not complete: the same missing-second-campaign source-lineage dependency recurs across the three parent-identified goal turns; all required computations, current drafts, audits and concrete currently available source leads are finished. Final parent bundling of these audit files may proceed without any new scientific run. Progress on the unmet primary requirement needs newly available primary identity/method evidence or explicitly authorized source clarification. Parent must set and report the actual goal status.'
j['blocking_condition']['meaningful_progress_during_recurrence']='Mérot recovery and the current English package were real progress. They are now delivered but do not fulfill the plural-campaign requirement. The impasse recommendation is made after that independent work is finished, not merely because the source search is difficult.'
j['blocking_condition']['external_evidence_only_not_compute_capacity']=True
j['overall_objective_complete']=False
j['final_verdict']='AVAILABLE_CURRENT_WORK_DELIVERED; BROADER_OBJECTIVE_INCOMPLETE; RECURRING_EXTERNAL_SOURCE_DEPENDENCY_SUPPORTS_BLOCKED'
A.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'english_manifest_checks':len(checks),'all_hashes_match':True,'all_source_visual_hashes_match':True,'drafts_delivered':True,'objective_complete':False,'status_recommendation':'blocked — parent controls actual status','audit_sha256':sha(A)},indent=2))
