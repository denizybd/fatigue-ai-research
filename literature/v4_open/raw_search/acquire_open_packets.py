"""Reacquire the three public packets with standard GET/Range requests only.

Existing immutable raw payloads are verified and reused. No author code is run.
The 3.36 GB archive is not bulk-downloaded; two exact public members are selected.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile
import hashlib
import json
import struct
import zlib

LIT = Path(__file__).resolve().parent
ROOT = LIT.parents[2]
DATA = ROOT / 'data/external_v4/raw_search'


def get(url, start=None, end=None):
    headers = {} if start is None else {'Range': f'bytes={start}-{end}'}
    with urlopen(Request(url, headers=headers), timeout=90) as r:
        if start is not None and r.status != 206:
            raise RuntimeError('Public server did not honor byte range; no bulk fallback.')
        return r.read()


def metadata(record, name):
    path = LIT / name
    if not path.exists():
        path.write_bytes(get(f'https://zenodo.org/api/records/{record}'))
    obj = json.loads(path.read_text())
    assert int(obj['id']) == record
    return obj


def verify_md5(path, expected):
    assert hashlib.md5(path.read_bytes()).hexdigest() == expected.split(':')[1], path


def archive(record, metadata_name, prefix, extract_subdir=None):
    obj = metadata(record, metadata_name)
    assert obj['metadata']['license']['id'] == 'cc-by-4.0'
    f = next(x for x in obj['files'] if x['key'] == 'Dataset.zip')
    path = DATA / (prefix + 'Dataset.zip')
    if not path.exists():
        path.write_bytes(get(f['links']['self']))
    verify_md5(path, f['checksum'])
    with ZipFile(path) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            rel = Path(member.filename)
            assert not rel.is_absolute() and '..' not in rel.parts
            dest = DATA / (prefix + rel.name) if extract_subdir is None else DATA / extract_subdir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            payload = z.read(member)
            assert zlib.crc32(payload) == member.CRC
            if dest.exists():
                assert dest.read_bytes() == payload
            else:
                dest.write_bytes(payload)
    return {'record': record, 'repository_md5_verified': True, 'archive': str(path.relative_to(ROOT))}


def partial_lcf():
    obj = metadata(17086687, 'lcftest2025_zenodo_metadata.json')
    f = next(x for x in obj['files'] if x['key'].endswith('.zip'))
    url, size = f['links']['self'], f['size']
    ipath = LIT / 'lcftest2025_remote_zip_inventory.json'
    if ipath.exists():
        inventory = json.loads(ipath.read_text())
    else:
        tail = get(url, size-65536, size-1)
        pos = tail.rfind(b'PK\x05\x06')
        endrec = struct.unpack('<4s4H2IH', tail[pos:pos+22])
        length, offset = endrec[5], endrec[6]
        central = get(url, offset, offset+length-1)
        (LIT / 'lcftest2025_zip_central_directory.bin').write_bytes(central)
        entries, pos = [], 0
        while pos < len(central):
            h = struct.unpack('<4s6H3I5H2I', central[pos:pos+46])
            assert h[0] == b'PK\x01\x02'
            name = central[pos+46:pos+46+h[10]].decode('utf8')
            entries.append({'name': name, 'compressed_size': h[8], 'size': h[9],
                'compression': h[4], 'local_header_offset': h[16], 'crc32': h[7]})
            pos += 46+h[10]+h[11]+h[12]
        inventory = {'zip_url': url, 'zip_size': size, 'repository_checksum': f['checksum'],
                     'central_directory_offset': offset, 'central_directory_size': length,
                     'entries': entries}
        ipath.write_text(json.dumps(inventory, indent=2) + '\n')
    assert inventory['zip_size'] == size
    dest = DATA / 'lcftest2025_selected_members'
    dest.mkdir(parents=True, exist_ok=True)
    verified = []
    for name in ['AM_H_1am_2.csv', 'AM_V_1am.csv']:
        entry = next(x for x in inventory['entries'] if x['name'] == name)
        assert entry['compression'] == 8
        raw = dest / name
        if not raw.exists():
            offset = entry['local_header_offset']
            h = struct.unpack('<4s5H3I2H', get(url, offset, offset+29))
            assert h[0] == b'PK\x03\x04'
            start = offset+30+h[9]+h[10]
            payload = get(url, start, start+entry['compressed_size']-1)
            assert len(payload) == entry['compressed_size']
            (dest / (name+'.deflate')).write_bytes(payload)
            raw.write_bytes(zlib.decompress(payload, -15))
        payload = raw.read_bytes()
        assert len(payload) == entry['size'] and zlib.crc32(payload) == entry['crc32']
        verified.append({'file': name, 'crc32_verified': True,
                         'sha256': hashlib.sha256(payload).hexdigest()})
    pdf = next(x for x in obj['files'] if x['key'].endswith('.pdf'))
    p = DATA / ('lcftest2025_'+pdf['key'])
    if not p.exists():
        p.write_bytes(get(pdf['links']['self']))
    verify_md5(p, pdf['checksum'])
    return {'record': 17086687, 'selected_members': verified,
            'full_archive_downloaded_or_MD5_verified': False}


if __name__ == '__main__':
    DATA.mkdir(parents=True, exist_ok=True)
    depfile = LIT / 'xlrd_dependency_receipt.json'
    wheel = LIT / 'xlrd-2.0.2-py2.py3-none-any.whl'
    if not wheel.exists():
        if depfile.exists():
            dep = json.loads(depfile.read_text())
        else:
            package = json.loads(get('https://pypi.org/pypi/xlrd/2.0.2/json'))
            item = next(x for x in package['urls'] if x['filename'] == wheel.name)
            dep = {'package': 'xlrd', 'version': '2.0.2', 'url': item['url'],
                   'sha256': item['digests']['sha256']}
            depfile.write_text(json.dumps(dep, indent=2)+'\n')
        payload = get(dep['url'])
        assert hashlib.sha256(payload).hexdigest() == dep['sha256']
        wheel.write_bytes(payload)
    result = [archive(12515773, 'bartosak2024_zenodo_metadata.json', 'bartosak2024_'),
              archive(17985589, 'jambor2026_zenodo_metadata.json', 'jambor2026_', 'jambor2026_extracted'),
              partial_lcf()]
    (LIT / 'reacquisition_verification_receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'raw_packets_verified': 3, 'no_model_fitting': True}, indent=2))
