"""Reacquire publicly supplied numerical workbooks without executing author code."""
from pathlib import Path
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'literature/v5_open/pinn2025'
EXPECTED = '310b9ebcf313a63d1cd679958873fe8bf6fea9a7f8a2ac2efecd6dff539d3ff2'
URLS = {
    'original_supplement.xlsx': 'https://ars.els-cdn.com/content/image/1-s2.0-S0013794425003376-mmc1.xlsx',
    'author_Fatigue_data.xlsx': 'https://raw.githubusercontent.com/spellbookrz/My_PhD_publications_data_and_code/8286fc1bfcefcef13cbc0bf054ed8f639ddbd22e/2025_EFM_PINN_for_fatigue_life/data/Fatigue_data.xlsx',
}


def run():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    for filename, url in URLS.items():
        p = DEST / filename
        cached = p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == EXPECTED
        if cached:
            body = p.read_bytes()
        else:
            response = requests.get(url, timeout=(15, 45))
            response.raise_for_status()
            body = response.content
            assert body.startswith(b'PK')
            assert hashlib.sha256(body).hexdigest() == EXPECTED, 'Source changed; review before curating.'
            p.write_bytes(body)
        records.append(dict(filename=filename, url=url, bytes=len(body),
            sha256=hashlib.sha256(body).hexdigest(), cached=cached))
    (DEST / 'reacquisition_receipt.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    run()
