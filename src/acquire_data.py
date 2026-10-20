"""Fetch immutable official MAT v2, validating publisher checksum and size."""
from pathlib import Path
import hashlib,json,datetime,urllib.request,os
ROOT=Path(__file__).resolve().parents[1]
URL='https://api.figshare.com/v2/articles/22337629'
EXPECTED_MD5='1f66b2a5e48146c2d5a27739ad24ff30'
def main():
    folder=ROOT/'data/raw';folder.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(URL,timeout=60) as f:metadata=json.load(f)
    if metadata['version']!=2:
        with urllib.request.urlopen(URL+'/versions/2',timeout=60) as f:metadata=json.load(f)
    assert metadata['version']==2
    file=next(f for f in metadata['files'] if f['id']==41023478)
    assert file['computed_md5']==EXPECTED_MD5
    path=folder/file['name']
    if not path.exists():
        temporary=folder/(file['name']+'.download')
        with urllib.request.urlopen(file['download_url'],timeout=60) as response,temporary.open('wb') as out:
            while chunk:=response.read(1024*1024):out.write(chunk)
        assert hashlib.md5(temporary.read_bytes()).hexdigest()==EXPECTED_MD5
        os.replace(temporary,path)
    data=path.read_bytes();assert len(data)==file['size'] and hashlib.md5(data).hexdigest()==EXPECTED_MD5
    (folder/'figshare_article_22337629.json').write_text(json.dumps(metadata,indent=2))
    entry={'source_url':file['download_url'],'metadata_url':URL,'doi':metadata['doi'],'license':metadata['license'],'file':str(path.relative_to(ROOT)),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'md5':EXPECTED_MD5,'accessed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'notes':'Original MAT bytes, no modification; pinning v2/file41023478.'}
    old=json.loads((folder/'manifest.json').read_text()) if (folder/'manifest.json').exists() else []
    kept=[z for z in old if z['file']!=entry['file']]
    (folder/'manifest.json').write_text(json.dumps([entry]+kept,indent=2));print(json.dumps(entry,indent=2))
if __name__=='__main__':main()
