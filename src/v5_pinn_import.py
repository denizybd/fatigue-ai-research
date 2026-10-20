"""Curate the publisher's numerical 316L supplement without guessing batch labels.

This is a source collection, not an admitted reliability/acquisition panel.
Read XLSX XML directly; the original workbook remains byte-for-byte unchanged.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'literature/v5_open/pinn2025'
OUT = ROOT / 'data/external_v5/pinn2025'
EXPECTED_SHA = '310b9ebcf313a63d1cd679958873fe8bf6fea9a7f8a2ac2efecd6dff539d3ff2'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SHEET = 'Case 2 SLM 316l'
DOI = '10.1016/j.engfracmech.2025.111136'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    book = SRC / 'original_supplement.xlsx'
    assert sha(book) == EXPECTED_SHA
    assert sha(SRC / 'author_Fatigue_data.xlsx') == EXPECTED_SHA
    with ZipFile(book) as z:
        assert z.testzip() is None
        strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        sheets = ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)
        rels = {x.attrib['Id']: x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        item = next(x for x in sheets if x.attrib['name'] == SHEET)
        rid = item.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        target = rels[rid].lstrip('/')
        target = target if target.startswith('xl/') else 'xl/' + target
        root = ET.fromstring(z.read(target))
        matrix = []
        for r in root.findall('s:sheetData/s:row', NS):
            vals = {}
            for c in r.findall('s:c', NS):
                assert c.find('s:f', NS) is None
                v = c.find('s:v', NS)
                if v is not None:
                    vals[c.attrib['r']] = strings[int(v.text)] if c.attrib.get('t') == 's' else float(v.text)
            matrix.append((int(r.attrib['r']), vals))
    header = matrix[0][1]
    assert list(header.values()) == ['Stress(MPa)', 'Î”K (MPaâˆšm)', 'Dmax', 'L/Leff', 'Nf']
    rows = []
    flags = []
    for rn, v in matrix[1:]:
        s, dk, dm, ratio, nf = [v[f'{c}{rn}'] for c in 'ABCDE']
        assert nf == int(nf) and nf > 0 and s > 0
        row = dict(
            row_id=f'pinn2025_case2_xlsx_row{rn:02d}',
            author_specimen_id='', physical_build_id='', powder_lot_id='',
            author_batch_label='', batch_membership_verified=False,
            source_doi=DOI, source_sheet=SHEET, source_range=f'A{rn}:E{rn}',
            source_family='Feng_Zhou_108486_127098_111136',
            related_original_doi='10.1016/j.ijfatigue.2024.108486',
            reported_stress_mpa=s,
            stress_interpretation='sigma_max_from_primary_Table2_Case2; workbook_header_only_Stress',
            load_ratio=0.1, stress_amplitude_mpa=0.45*s,
            stress_amplitude_provenance='derived sigma_max*(1-R)/2; primary Section2.2 R=0.1',
            log_stress=math.log10(0.45*s),
            reported_Nf_cycles=int(nf), log_life=math.log10(nf),
            event_interpretation='reported_Nf_for_fractured_samples; complete_campaign_censoring_unknown',
            deltaK_reported_mpa_sqrtm=dk, Dmax_reported=dm,
            Dmax_units='', Dmax_quantity_mapping='workbook_Dmax_not_silently_equated_to_paper_sqrtarea',
            L_Leff_reported=ratio,
            defect_measurement_timing='post_fracture_SEM; dependent_DeltaK_also_post_fracture',
            defect_fields_available_for_pretest=False,
            material='SS316L', manufacturing_process='SLM_LPBF',
            test_mode='tensile_fatigue', frequency_hz=30,
            source_reported_batches=3, manufacturing_parameters='', thermal_treatment='',
            temperature_c='', feedback_control='', surface='ground_400_to_2000_grit_and_polished',
            numeric_provenance='publisher_XLSX_individual_Nf; author_GitHub_file_identical_SHA256',
            gold_identity_qualified=False, admitted_to_frozen_training=False,
            acquisition_reliability_fit_eligible=False,
            fit_gate_reason='no_row_to_three_batch_map; complete_program_sampling_censoring_unverified',
            article_license='CC-BY-NC-ND-4.0', author_code_license='not_specified',
        )
        rows.append(row)
        if s < 210:
            flags.append(dict(row_id=row['row_id'],source_cell=f'A{rn}',value=s,
                issue='Workbook stress below Table2 reported 210..400MPa range',action='preserve180; no correction or inferred batch'))
        if ratio < .95:
            flags.append(dict(row_id=row['row_id'],source_cell=f'D{rn}',value=ratio,
                issue='Workbook L/Leff below Table2 reported0.95..1.23 range',action='preserve original; no clipping'))
        if dm < 59:
            flags.append(dict(row_id=row['row_id'],source_cell=f'C{rn}',value=dm,
                issue='Dmax below paper sqrtarea range59..282; quantity identity not specified in workbook header',
                action='preserve original Dmax label and value; unit/quantity mapping remains open'))
    assert len(rows) == 44
    assert len({x['row_id'] for x in rows}) == 44
    assert all(not x['author_batch_label'] and not x['author_specimen_id'] for x in rows)
    write_csv(OUT / 'reported_316L_44.csv', rows)
    write_csv(OUT / 'source_discrepancy_flags.csv', flags)
    raw = [dict(source_sheet=SHEET,source_excel_row=rn,**{c:v[f'{c}{rn}'] for c in 'ABCDE'}) for rn,v in matrix[1:]]
    write_csv(OUT / 'original_cell_values44.csv', raw)
    ranges={c:dict(min=min(x[c] for x in rows),max=max(x[c] for x in rows)) for c in [
        'reported_stress_mpa','reported_Nf_cycles','deltaK_reported_mpa_sqrtm','Dmax_reported','L_Leff_reported']}
    receipt = dict(
        source_doi=DOI, publisher_url='https://ars.els-cdn.com/content/image/1-s2.0-S0013794425003376-mmc1.xlsx',
        author_repository='https://github.com/spellbookrz/My_PhD_publications_data_and_code',
        publisher_and_author_workbook_sha256=EXPECTED_SHA, source_sheet=SHEET, source_range='A2:E45',
        rows=44, actual_author_specimen_ids=0, actual_row_batch_links=0,
        new_independent_campaigns_proven=0, reported_manufacturing_batches=3,
        source_family='Feng_Zhou_108486_127098_111136',
        explicit_reuse='EFM Section1/2 identifies316L data from prior work ref40=108486; ESWA snippet also reuses original316L dataset.',
        ranges=ranges, source_discrepancy_flags=len(flags),
        interpretation='All44 rows are numerical reportedNf with postfracture defect descriptors. The complete original campaign and any omitted runouts are not established.',
        row_order='Stress resets at Excel15/33 are NOT batch labels and are not used to assign groups.',
        exclusion='No fitted curves, generated observations, otheralloy rows, prospective postfracturecovariates or inferredbatchIDs.',
        normalization='Retain original5values and exactExcelcelllocators. Sa=.45*Smax derived separately; alloriginaldiscrepancies retained.',
        article_access='Official RWTH PDF indexed primary methods and publisher abstract consulted; local direct PDFGET returned248byteJS challenge, not PDF; no visualPDFcheck claimed.',
        code_access='Author code and notebook acquired read-only. Notebook is S,T LZ50example depending on absentFatigue_life.csv; not executed and not an exact316Lreproduction.',
        license='ArticleCCBYNCND4; factualnumericextractiononly in packet. Authorrepository has no explicitcode license; originalcode/workbook not redistributed.',
        fit_performed=False, frozen_v4_inputs_changed=False,
        outputs={p.name:sha(p) for p in sorted(OUT.glob('*.csv'))}, script_sha256=sha(__file__))
    (OUT / 'normalization_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    run()
