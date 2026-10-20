"""Public primary metadata/source fetches; no login or outcome fitting."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,requests
D=Path(__file__).resolve().parent
sources=[
 ('voloskov2023_wiley.html','https://advanced.onlinelibrary.wiley.com/doi/10.1002/adem.202200831'),
 ('voloskov2023_openalex.json','https://api.openalex.org/works/https://doi.org/10.1002/adem.202200831'),
 ('spiller2025_openalex.json','https://api.openalex.org/works/https://doi.org/10.1016/j.msea.2025.148439'),
 ('wu2026_crossref.json','https://api.crossref.org/works/10.1016/j.ijfatigue.2026.109943'),
 ('prochaska2024_oa.xml','https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC11443111')]
def get(item):
 name,url=item
 try:
  r=requests.get(url,timeout=25);p=D/name;p.write_bytes(r.content)
  return {'file':name,'url':url,'status':r.status_code,'bytes':len(r.content),
     'sha256':hashlib.sha256(r.content).hexdigest(),'content_type':r.headers.get('content-type')}
 except Exception as e:return {'file':name,'url':url,'error':str(e)}
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(get,sources))
 (D/'fetch_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out,indent=2))
 for name in ['voloskov2023_openalex.json','spiller2025_openalex.json']:
  j=json.loads((D/name).read_text())
  print(name,json.dumps({'title':j.get('title'),'locations':[
   {'source':(x.get('source') or {}).get('display_name'),'landing':x.get('landing_page_url'),
    'pdf':x.get('pdf_url'),'license':x.get('license')} for x in j.get('locations',[])]}))
 j=json.loads((D/'wu2026_crossref.json').read_text()).get('message',{})
 print('WU',json.dumps({k:j.get(k) for k in ['title','published','published-online','link','URL','relation']}))
