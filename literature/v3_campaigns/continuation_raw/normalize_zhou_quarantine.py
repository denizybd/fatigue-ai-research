"""Preserve public author numbers without inventing specimen IDs or stress units."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import csv,json,hashlib,unicodedata

LIT=Path(__file__).resolve().parent
ROOT=LIT.parents[2]
OUT=ROOT/'data/external_v3/continuation_raw'
F=OUT/'zhou2026_supporting.xlsx'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(F)as z:
    shared=[]
    if 'xl/sharedStrings.xml'in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS):
            shared.append(''.join(t.text or ''for t in si.findall('.//s:t',NS)))
    sheets={}
    names=[e.attrib['name']for e in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',NS)]
    for i,name in enumerate(names,1):
        sheet={}
        for cell in ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml')).findall('.//s:c',NS):
            value=cell.find('s:v',NS)
            if value is None:
                text=''.join(t.text or ''for t in cell.findall('.//s:t',NS));value=text or None
            else:
                value=value.text
                if cell.attrib.get('t')=='s':value=shared[int(value)]
                elif value is not None:
                    try:value=float(value);value=int(value)if value.is_integer()else value
                    except ValueError:pass
            sheet[cell.attrib['r']]=value
        sheets[name]=sheet

def write(name,rows):
    with (OUT/name).open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

s=sheets['Experimental fatigue data and B'];fatigue=[]
for geometry,c1,c2 in [('flat','A','B'),('cylindrical','E','F')]:
    for row in range(2,10):
        n,stress=s.get(c1+str(row)),s.get(c2+str(row))
        if n is None and stress is None:continue
        assert isinstance(n,(int,float))and n>0 and isinstance(stress,(int,float))and stress>0
        fatigue.append(dict(row_locator=f'zhou2026_fatigue_{geometry}_sheetrow{row}',
                            locator_is_specimen_id=False,author_specimen_id='',build_id='',powder_batch_id='',
                            author_geometry=geometry,cycles_author_Nf=n,stress_author_Sr_MPa=stress,
                            stress_definition='Sr(MPa);range_vs_amplitude_vs_maximum_unverified',
                            stress_amplitude_MPa='',load_ratio='',event='',runout='',
                            temperature_C='',frequency_Hz='',control_mode='',loading_mode='',
                            material='316L',am_type='LPBF',surface_author='as-built',
                            strict_eligible=False,pilot_eligible=False,fit_eligible=False,
                            status='quarantine_missing_identity_and_methods',
                            source_dataset_doi='10.6084/m9.figshare.33392110.v1',
                            source_url='https://figshare.com/articles/dataset/33392110',
                            cell_address=f"'Experimental fatigue data and B'!{c1}{row}:{c2}{row}",
                            source_license='CC-BY-4.0'))
assert len(fatigue)==14
write('zhou2026_fatigue14_quarantined.csv',fatigue)

rough=sheets['Surface roughness'];defect=sheets['XCT-resolved defect volume frac'];ct=[]
for row in range(2,10):
    a,b=rough.get('A'+str(row)),defect.get('A'+str(row));assert a==b
    ct.append(dict(author_specimen_label=a,source_dataset_doi='10.6084/m9.figshare.33392110.v1',
                   surface_Sa_um=rough['B'+str(row)],defect_volume_fraction_pct=defect['B'+str(row)],
                   build_id='',fatigue_row_locator='',fatigue_identity_crosswalk_verified=False,
                   candidate_source_family='Wu2026_matlet140105_flat4_exact_defect_fractions'if a.startswith('Flat')else'',
                   no_canonical_build_assigned=True,source_license='CC-BY-4.0'))
write('zhou2026_named_CT8_no_fatigue_crosswalk.csv',ct)

articles=json.loads((ROOT/'data/raw/FatigueData-AM2022.json').read_text())['fatiguedata_am2022']['articles']
def norm(s):return ' '.join(sorted(unicodedata.normalize('NFKD',s).lower().replace(',',' ').split()))
targets=['Zhou, Yi','Wu, Zicheng','Liu, Tong','Zhang, Zihan','Ho, Ninian Sing Kok','Pang, John Hock Lye']
hits=[]
for i,a in enumerate(articles):
    m=a['metadata'];matching=[author for author in m.get('author',[])if norm(author)in {norm(t)for t in targets}]
    if matching:hits.append(dict(article_index=i,doi=m.get('doi'),title=m.get('title'),matched_names=matching))
overlap={}
target_dois={'10.6084/m9.figshare.33392110.v1','10.1016/j.matlet.2026.140105','10.1016/j.ijfatigue.2026.109943'}
refs=[('v2_strict309',ROOT/'data/processed/v2/strict/cohort.csv'),('Trombley129',ROOT/'data/external_v2/trombley2025/fatigue_asbuilt_available129.csv'),('Tomaszewski137',ROOT/'data/external_v3/raw_repository/tomaszewski2023_all137_secondary.csv'),('Diller44',ROOT/'data/external_v3/raw_repository/diller2024_all44_candidate.csv')]
for name,path in refs:
    with path.open()as f:ref=list(csv.DictReader(f))
    vals={float(r['cycles_observed'])for r in ref}
    doi_hits=[]
    for r in ref:
        for key,value in r.items():
            if ('doi'in key.lower()or key=='source_id')and value:
                for doi in target_dois:
                    if doi.lower()in value.lower():doi_hits.append({'field':key,'doi':doi})
    overlap[name]={'rows':len(ref),'exact_Nf_matches':sum(float(r['cycles_author_Nf'])in vals for r in fatigue),
                   'source_identifier_matches':doi_hits,
                   'coordinate_stress_overlap_not_assessed':'Sr and R unverified; conversion would fabricate metadata'}
audit=dict(dataset_rows=14,named_CT_rows=8,strict_eligible_rows=0,qualified_campaigns=0,
           raw_data_md5=hashlib.md5(F.read_bytes()).hexdigest(),
           author_name_matches_in_618_metadata=hits,
           overlap_screen=overlap,
           source_family_reuse={'Wu140105':'Strong candidate family relation: shared authors; four exact flat XCT defect fractions in public preview and workbook. No fatigue-row linkage proven.',
                                'Wu109943':'Shared authors; no evidence yet connecting this dataset to validation series. Do not count as independent external evidence from this lab twice.'},
           single_build_claim_scope='Wu140105 abstract confirms a single build in that paper; does not identify the14 anonymous fatigue rows in this different dataset.',
           no_fits_or_predictions_performed=True)
audit['source_doi_matches_in_618_metadata']=[{'article_index':i,'doi':a['metadata'].get('doi')}for i,a in enumerate(articles)if str(a['metadata'].get('doi','')).lower()in target_dois]
(LIT/'zhou2026_source_gate.json').write_text(json.dumps(audit,indent=2))
print(json.dumps({k:v for k,v in audit.items()if k not in ['source_family_reuse','single_build_claim_scope']},indent=2))
