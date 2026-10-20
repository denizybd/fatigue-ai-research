"""Build local user deliverables; never uploads, sends or publishes anything."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,zipfile,datetime
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
DEFAULT='/Users/deniz2/Documents/Codex/2026-10-20/bu-konuda-s-seviye-bir-al/outputs'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def selected_files():
    files=[]
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT);parts=rel.parts;name=p.name
        if any(x in ['.git','.venv','work','__pycache__','.pytest_cache'] for x in parts):continue
        if len(parts)==1:
            if name in ['README.md','STATE.md','run_all.sh','requirements.lock.txt','.gitignore']:files.append(p)
        elif parts[0] in ['src','tests','protocols','data','figures','manuscript','outreach']:
            files.append(p)
        elif parts[0]=='logs' and name!='user_research_scope.txt':files.append(p)
        elif parts[0]=='literature':
            # Keep reports, source metadata, code and derived point matches;
            # exclude copyrighted full-text extracts and source figure images.
            if p.suffix in ['.md','.csv','.json','.bib','.py']:files.append(p)
        elif parts[0]=='results':
            if name.startswith('pred_source_') or name.startswith('pred_random_'):continue
            if 'full_reproduction' in parts:
                if name in ['run_receipt.json','checkpoint_signature.json','independent_audit.json','independent_audit_report.md']:files.append(p)
            elif p.suffix in ['.csv','.json','.md','.txt']:files.append(p)
    return sorted(set(files))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default=DEFAULT);args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    copies={'manuscript/arastirma_ozeti_tr.pdf':'arastirma-ozeti-tr.pdf','manuscript/paper_draft_en.pdf':'paper-draft-en.pdf','manuscript/supplementary_material.pdf':'supplementary-material.pdf','manuscript/research_brief_en.pdf':'research-brief-en.pdf','outreach/email_draft_en.txt':'tridello-email-draft.txt','outreach/technical_qa_tr.md':'teknik-soru-cevap-tr.md','figures/01_near_coincident_curves.png':'01-source-curve-overlap.png','figures/02_risk_and_conservatism.png':'02-risk-and-utility.png','figures/03_failed_combined_gate.png':'03-combined-rule-result.png'}
    for src,dest in copies.items():shutil.copy2(ROOT/src,out/dest)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    history=subprocess.check_output(['git','log','--format=%H %aI %s'],cwd=ROOT,text=True)
    reproduction=json.loads((ROOT/'results/full_reproduction_comparison.json').read_text())
    assert reproduction['all_prediction_and_summary_checks_pass']
    counts=sum(x['predictions']['rows'] for x in reproduction['comparisons'].values());assert counts==105786
    assert len(PdfReader(out/'research-brief-en.pdf').pages)==1
    files=selected_files();manifest={'version_commit':commit,'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],
      'exclusions':'Installed environment, Git internals, copyrighted source PDFs/full-text extracts/images, duplicate per-fold prediction CSVs and duplicate full-replay prediction copies. Original final predictions, fold split/settings/status receipts, all source audits and exact replay comparison are included.',
      'data_license':'FatigueData-AM2022 v2, Zhang and Xu2023, CC BY4.0, DOI10.6084/m9.figshare.22337629.v2; descriptor10.1038/s41597-023-02150-x.',
      'raw_file_note':'Raw MAT and JSON are included unchanged with their original checksums; compressed contents are checked by ZIP CRC.'}
    package=out/'fatigue-ai-research-reproducible.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'fatigue-ai-research/'+str(p.relative_to(ROOT)))
        z.writestr('fatigue-ai-research/PACKAGE_CONTENTS.json',json.dumps(manifest,indent=2))
        z.writestr('fatigue-ai-research/GIT_HISTORY.txt',history)
    with zipfile.ZipFile(package) as z:assert z.testzip() is None
    contact=out/'tridello-contact-draft.zip'
    names=['research-brief-en.pdf','tridello-email-draft.txt','01-source-curve-overlap.png','02-risk-and-utility.png']
    with zipfile.ZipFile(contact,'w',zipfile.ZIP_DEFLATED) as z:
        for name in names:z.write(out/name,name)
        z.writestr('READ_BEFORE_SENDING.txt','DRAFT ONLY. No email has been sent. Fill your actual name/background and understand the Turkish Q&A before approving any send. This is a reproducible public-data pilot and a failed combined-gate hypothesis, not original-BNN reproduction or a certified safe-design algorithm. Data/derived plots: Zhang and Xu2023, FatigueData-AM2022v2, CC BY4.0; DOI10.6084/m9.figshare.22337629.v2. Source-family specimen identity remains unverified.\n')
    with zipfile.ZipFile(contact) as z:assert z.testzip() is None
    (out/'BASLANGIC.txt').write_text('''Önce arastirma-ozeti-tr.pdf dosyasını oku.

Çalışma, tekrarlanabilir bir açık-veri pilotu ve olumsuz birleşik-kural sonucudur. Yeni bir güvenli tasarım algoritması veya güçlü bir yeni yöntem kanıtlanmadı.

İngilizce taslak: paper-draft-en.pdf
Yöntem, veri ve tüm kontrol tabloları: supplementary-material.pdf
Tridello için tek sayfa: research-brief-en.pdf
Teknik görüşmeye hazırlık: teknik-soru-cevap-tr.md
Gönderilmemiş e-posta: tridello-email-draft.txt

fatigue-ai-research-reproducible.zip; ham veriler, kaynak/kalite raporları, kod, kilitli ortam sürümleri, protokoller, tohumlar, ayrım üyelikleri, günlükler, CSV sonuçları, grafikler ve doğrulama kayıtlarını içerir. Kurulu ortam ve kaynak makalelerin telifli tam metinleri eklenmedi. Gerekli DOI/URL ve erişim sınırları raporlarda vardır.

tridello-contact-draft.zip yalnızca bir sayfalık özet, iki grafik ve e-posta taslağını içerir. İsim imzası [Name] olarak bırakıldı. Hiçbir dosya dışarı yüklenmedi, e-posta gönderilmedi veya yayın yapılmadı.

Tekrar: paketi aç, araştırma dizininde zsh run_all.sh çalıştır. Yeni sonuç dizini oluşur; README.md komutları açıklar. STATE.md yeni oturum için durum kaydıdır.

Yerel asıl çalışma: /Users/deniz2/Documents/ChatGPT/fatigue-ai-research
Yedi deney ayarı ve üç tohumun bütün105786tahmin satırı ile özetleri yeniden çalıştırmada birebir eşleşti. Bu bir hesaplama tekrarıdır; yeni bağımsız fiziksel deney değildir.
'''.replace('bütün105786tahmin','bütün 105.786 tahmin'))
    direct=[p for p in out.iterdir() if p.is_file() and p.name not in ['TESLIM_KAYDI.json','SHA256SUMS.txt']]
    receipt={'date_local':'2026-10-20','timezone':'Europe/Istanbul','research_root':str(ROOT),'git_commit':commit,'completed_scope':'Frozen public-data study, negative H2, critical internal audit, exact full replay, English draft/supplement and Turkish/contact package. Scientific novelty, physical validation and author response are not claimed.',
       'primary_population':{'observations':1126,'conditions':120,'dois':37,'conservative_provenance_blocks':29,'failures':987,'runouts':139},
       'verification':{'synthetic_tests':16,'primary_folds':87,'independent_formula_audit':True,'full_replayed_configurations':7,'all_replayed_prediction_rows':counts,'maximum_numeric_reproduction_difference':0.0,'strong_H2_passes':False},
       'pdfs':[{'file':p.name,'pages':len(PdfReader(p).pages)} for p in direct if p.suffix=='.pdf'],
       'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(direct)],'email_sent':False,'external_uploads':False}
    (out/'TESLIM_KAYDI.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False))
    (out/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
    print(json.dumps({'output':str(out),'research_zip_MiB':round(package.stat().st_size/2**20,2),'contact_zip_MiB':round(contact.stat().st_size/2**20,2),'research_files':len(files),'git_commit':commit,'pdf_pages':receipt['pdfs'],'zip_crc_checks':'PASS'},indent=2))

if __name__=='__main__':main()
