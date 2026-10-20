"""Render the audited current English working paper and one-page brief."""
from __future__ import annotations
import html,json,os,shutil
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
from src.v3_prepare import ROOT
OUT=Path(os.environ.get('V31_EN_OUTPUT',ROOT/'manuscript/v31'))
F=Path(matplotlib.get_data_path())/'fonts/ttf'
for n,p in [('E31','DejaVuSans.ttf'),('E31Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,str(F/p)))
pdfmetrics.registerFontFamily('E31',normal='E31',bold='E31Bold')
TEAL=colors.HexColor('#176c83')
STYLE={n:ParagraphStyle(n,fontName='E31',fontSize=size,leading=leading,spaceAfter=space) for n,size,leading,space in [('body',9.2,12.6,7),('small',7.8,10.4,5),('cell',7.3,9.7,0),('brief',8.9,12,6)]}
STYLE['title']=ParagraphStyle('title',fontName='E31Bold',fontSize=18,leading=22,spaceAfter=11,textColor=TEAL)
STYLE['h']=ParagraphStyle('h',fontName='E31Bold',fontSize=11,leading=14,spaceBefore=9,spaceAfter=6,keepWithNext=True)
STYLE['briefhead']=ParagraphStyle('briefhead',fontName='E31Bold',fontSize=9.2,leading=12,spaceBefore=5,spaceAfter=3,keepWithNext=True,textColor=TEAL)
def P(x,k='body'):return Paragraph(html.escape(str(x)).replace('\n','<br/>'),STYLE[k])
def footer(c,d):
 c.saveState();c.setFont('E31',7);c.setFillColor(colors.HexColor('#52616a'))
 c.drawString(43,822,'LPBF316L | Current source and acquisition study | 20 October 2026 | Working draft')
 c.drawString(43,23,'Exploratory replay; not a safe-design certification or independent physical replication.')
 c.drawRightString(552,23,str(d.page));c.restoreState()
def table(t,widths):
 rows=[t['columns']]+t['rows'];tb=Table([[P(x,'cell') for x in r] for r in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
 tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f4')),('LINEBELOW',(0,0),(-1,0),.6,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
 return [P(t['title'],'h'),tb,P(t['note'],'small')]
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 path=ROOT/'manuscript/v31/current_paper_source.json';x=json.loads(path.read_text())
 story=[P(x['title'],'title'),P(x['subtitle'],'small'),P(x['authorship'],'small'),P(x['status'],'small'),P('Abstract','h'),P(x['abstract']),P('Keywords: '+', '.join(x['keywords']),'small')]
 figs={f['after_section']:f for f in x.get('figures',[])}
 for sec in x['sections']:
  story.append(P(sec['heading'],'h'));story.extend(P(p) for p in sec['paragraphs'])
  if sec['heading'] in figs:
   f=figs[sec['heading']];p=OUT/Path(f['path']).name
   image=Image(str(p));h=508*image.imageHeight/image.imageWidth
   story.extend([image.__class__(str(p),width=508,height=h),P(f['id']+'. '+f['caption'],'small')])
  if sec['heading'].startswith('6.'):
   story.extend(table(next(t for t in x['tables'] if t['id']=='T2'),[46,86,101,54,221]))
 story.append(KeepTogether([P('Declarations','h'),P('\n'.join(x['declarations']),'small')]))
 story.append(P('References and access scope','h'))
 for r in x['references']:
  txt=html.escape('['+r['id']+'] '+r['citation'])
  if r.get('url'):txt+=' <link href="'+html.escape(r['url'],quote=True)+'" color="#176c83">'+html.escape(r['url'])+'</link>'
  story.append(Paragraph(txt,STYLE['small']))
  story.append(P('Evidence: '+r['evidence_scope'],'small'))
 story.extend([PageBreak(),P('Appendix A. Full model/policy comparison','title')])
 story.extend(table(next(t for t in x['tables'] if t['id']=='T1'),[92,104,64,85,69,94]))
 story.append(P('Machine-readable supplement','h'));story.append(P('The accompanying supplementary_material.txt defines source fields, likelihoods, lower-life quantiles, censoring-identified risk and paired risk changes, aggregation, protocol hashes and replay commands. Released CSVs retain every model/policy/feasible budget at both caps. The source build mapping is an audited manual fact; no automatic thesis OCR claim is made.','small'))
 paper=OUT/'current_working_paper_en.pdf'
 SimpleDocTemplate(str(paper),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=47,bottomMargin=41,title=x['title'],author='Working draft; human authorship to be confirmed').build(story,onFirstPage=footer,onLaterPages=footer)
 brief=(ROOT/'outreach/v31/research_brief_en.txt').read_text().strip().split('\n\n')
 story=[P('Few-test fatigue transfer: evidence and limits','title')]
 # Omit the plain-text title/date block already represented by the page furniture.
 for part in brief[1:]:
  lines=part.splitlines()
  if len(lines)>1:
   story.append(P(lines[0],'briefhead'));story.append(P('\n'.join(lines[1:]),'brief'))
  else:story.append(P(part,'brief'))
 briefpath=OUT/'research_brief_en.pdf'
 SimpleDocTemplate(str(briefpath),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=47,bottomMargin=41,title='Current research brief',author='Working draft; human authorship to be confirmed').build(story,onFirstPage=footer,onLaterPages=footer)
 shutil.copy2(path,OUT/path.name)
 for rel in ['manuscript/v31/supplementary_material.txt','outreach/v31/research_brief_en.txt','outreach/v31/email_draft_en.txt','outreach/v31/technical_qa_tr.txt','outreach/v31/technical_qa_en.txt']:
  p=ROOT/rel;shutil.copy2(p,OUT/p.name)
 print(json.dumps({'paper':str(paper),'brief':str(briefpath)}))
if __name__=='__main__':main()
