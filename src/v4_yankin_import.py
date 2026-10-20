"""Extract individual Table 3 values from the official 2025 primary article XML.

The table's No column is a publication identifier, not a laboratory or build ID.
Runout endpoints are nominal plot-derived values; failures are tabulated integers.
"""
from __future__ import annotations
import hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOI = '10.1038/s41598-025-89003-2'

def run():
    source = ROOT/'literature/v4_open/yankin2025'
    out = ROOT/'data/external_v4/yankin2025'
    out.mkdir(parents=True, exist_ok=True)
    raw = source/'primary_fulltext.xml'
    root = ET.fromstring(raw.read_bytes())
    table = root.find('.//table-wrap[@id="Tab3"]')
    assert table is not None
    rows = []
    for tr in table.findall('.//tbody/tr'):
        cells = [''.join(td.itertext()).strip() for td in tr]
        for offset, treatment in [(0, 'AB'), (4, 'HT')]:
            if len(cells) <= offset or not cells[offset]:
                continue
            no, stress, life, angle = cells[offset:offset+4]
            event = int(life.lower() != 'run out')
            n = int(life.replace(',', '')) if event else 1_000_000
            rid = f'yankin2025_table3_{int(no):02d}'
            rows.append(dict(
                row_id=rid, specimen_id='', publication_test_number=int(no),
                dataset_id=f'yankin2025_{treatment}_{int(angle):02d}',
                group_id='yankin2025_program', campaign_id='yankin2025_program',
                doi=DOI, source_id='yankin2025', year=2025,
                material='SS316L', am_type='LPBF',
                stress_amplitude=float(stress), cycles_observed=n, event=event,
                runout=1-event, log_stress=float(np.log10(float(stress))),
                log_life=float(np.log10(n)), load_ratio=-1., direction=int(angle),
                surface='as_printed', thermal=treatment,
                heat_temperature=1000 if treatment == 'HT' else np.nan,
                heat_time=.5 if treatment == 'HT' else np.nan,
                power=200, scan_speed=750, hatch_space=100, layer_thickness=50,
                process_units='power W; scan_speed mm/s; hatch_space and layer_thickness micrometre',
                preheat=170, frequency=np.nan, frequency_min_hz=1, frequency_max_hz=20,
                temperature=np.nan, environment='', load_control='', kt=np.nan,
                test_type='axial_push_pull_stress_specified',
                panel='new_source_temperature_unstated',
                identity_gate='publication_test_number_no_lab_or_build_id',
                measurement_provenance='primary_Table3_numerical_observation',
                cycles_provenance='Table3_integer' if event else 'nominal_1e6_from_Fig4_Fig8_and_text',
                source_location='PDF9_Table3; PDF3_methods; PDF7_8_fatigue_description',
                fit_exclude_groups='yankin2025_program', build_id='', powder_lot_id='',
                source_license='CC-BY-NC-ND-4.0; article not redistributed',
            ))
    d = pd.DataFrame(rows).sort_values('publication_test_number')
    assert d.publication_test_number.tolist() == list(range(1,70))
    assert d.row_id.is_unique and len(d) == 69 and int(d.event.sum()) == 64
    assert set(d.loc[d.event == 0, 'publication_test_number']) == {6,50,54,58,69}
    assert d.dataset_id.nunique() == 14
    d.to_csv(out/'table3_69.csv', index=False)
    counts = d.groupby(['dataset_id','thermal','direction']).agg(
        n=('row_id','size'),failures=('event','sum'),stress_levels=('stress_amplitude','nunique'))
    counts.to_csv(out/'condition_counts.csv')
    receipt = dict(doi=DOI, source_url='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11805919/fullTextXML',
        xml_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        pdf_sha256=hashlib.sha256((source/'primary_paper.pdf').read_bytes()).hexdigest(),
        normalized_sha256=hashlib.sha256((out/'table3_69.csv').read_bytes()).hexdigest(),
        n=69, failures=64, runouts=5, conditions=14,
        identity='No1..69 are publication test numbers, not author laboratory specimen codes.',
        missing='Test ambient, explicit feedback control mode, Kt, specimen/build and powder lot IDs are not supplied in the retained primary article.',
        event_definition='Tabulated fatigue failure; five explicit run outs remain right-censored.',
        endpoint='1e6 nominal plot-derived stop, not an integer reported in Table3. Figs4/8 and PDF7 text checked.',
        exclusions='No one-cycle UTS values, fitted S-N curve coordinates, predictions, tensile means or fracture-derived covariates imported.',
        split='Hold whole author program out; single new source, not14 independent campaigns.',
        overlap='2025 primary results absent from 2022 source window; whole source held out. This alone is not a specimen lineage proof.',
        redistribution='Local factual extraction and acquisition script; do not bundle adapted article graphics or original XML/PDF into deliverable.')
    (out/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(counts.to_string())
    print(json.dumps(receipt,indent=2))

if __name__ == '__main__':
    run()
