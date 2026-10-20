"""Download public PDF via standard HTTP byte ranges; validate offsets, length and parser."""
import requests,concurrent.futures,hashlib,json,datetime,re
from pathlib import Path
from pypdf import PdfReader
out=Path(__file__).parent
url='https://lutpub.lut.fi/bitstream/handle/10024/164752/Shahriar%20Afkhami_A4.pdf?isAllowed=y&sequence=1'
size=22960346;chunk=1024*1024
parts=[(a,min(a+chunk-1,size-1)) for a in range(0,size,chunk)]
def get(ab):
 a,b=ab
 for attempt in range(3):
  try:
   r=requests.get(url,headers={'Range':f'bytes={a}-{b}'},timeout=(5,20))
   assert r.status_code==206 and r.headers.get('Content-Range')==f'bytes {a}-{b}/{size}' and len(r.content)==b-a+1
   return a,r.content
  except Exception:
   if attempt==2:raise
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:p=dict(ex.map(get,parts))
b=b''.join(p[a] for a,_ in parts);assert len(b)==size and b[:4]==b'%PDF';f=out/'afkhami2021_complete.pdf';f.write_bytes(b);r=PdfReader(f)
f.with_suffix('.txt').write_text('\n'.join(f'\n--- PDF PAGE {i+1} ---\n'+(x.extract_text()or'') for i,x in enumerate(r.pages)))
d=dict(url=url,path=str(f),bytes=len(b),pages=len(r.pages),sha256=hashlib.sha256(b).hexdigest(),method='HTTP206validatedranges',accessed=datetime.datetime.now(datetime.timezone.utc).isoformat());(out/'download_manifest_ranged.json').write_text(json.dumps(d,indent=2));print(d)
