"""Read public source bytes; preserve unknown build identifiers; no model fitting."""
from pathlib import Path
import csv, json, math, hashlib, collections, re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
LIT = Path(__file__).resolve().parent
OUT = ROOT / 'data/external_v3/raw_repository'

def save_csv(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def base():
    return dict(material='316L', am_type='L-PBF', build_id='', powder_batch_id='',
                build_mapping_verified=False, strict_eligible=False,
                identity_kind='author_specimen_or_scan_identifier',
                license='CC-BY-4.0', metadata_only_condition_id=True)

raw = (LIT / 'diller2024_readme.txt').read_text()
rows=[]; block=0
for line in raw.splitlines():
    if line.startswith('Scan-number;'):
        block+=1; continue
    if block and ';' in line:
        s=line.split(';')
        if len(s)<3 or not s[1] or not s[2]: continue
        r=base(); sid=s[0]; stress=float(s[1]); n=int(s[2]); notes=s[3] if len(s)>3 else ''
        conflicts=[]
        if block==1 and stress!=450: conflicts.append('polished_methods_says_450MPa_readme_says_350MPa')
        if sid=='µ15': conflicts.append('readme_range_200MPa_article_fractography_300MPa_same_cycles')
        if block==1: conflicts.append('readme_header_Load_Level_not_Stress_range')
        r.update(row_id=f'diller2024_scan_{sid}', specimen_id=sid,
                 source_id='Diller2024_FFEMS14375', source_doi='10.1111/ffe.14375',
                 source_dataset_doi='10.5281/zenodo.21105346',
                 condition_id='diller2024_'+('polished' if block==1 else 'asbuilt'),
                 condition_author='polished' if block==1 else 'as-built',
                 stress_author_value=stress, stress_author_definition='Load-Level-in-MPa' if block==1 else 'Stress-range-in-MPa',
                 stress_range_MPa=stress if block==2 else '',
                 stress_amplitude=stress/2 if block==2 else '',
                 stress_max_MPa=stress/.9 if block==2 else '',
                 load_ratio=.1, cycles_observed=n,
                 event=0 if 'stopped without specimen failure' in notes else 1,
                 runout='stopped without specimen failure' in notes,
                 author_comment=notes, source_url='https://zenodo.org/records/21105346',
                 row_source_location='read me.txt; block '+str(block),
                 source_method_location='Diller thesis PDF pp134-135; FFEMS3394-3395',
                 force_control_status='ASTM_E466_geometry_and_stress_levels;explicit_control_mode_not_stated',
                 loading_mode='axial', temperature_C='', frequency_Hz='',
                 process_laser_power_W=250, process_scan_speed_mm_s=1500,
                 process_layer_thickness_um=40, process_hatch_spacing_um=100,
                 machine='EOS M280', mapping_status='no_build_count_or_ID_map_found',
                 stress_conflict=bool(conflicts), conflicts=';'.join(conflicts),
                 secondary_point_eligible=(block==2 and sid!='µ15'))
        rows.append(r)
assert len(rows)==44 and len({r['specimen_id']for r in rows})==44
save_csv('diller2024_all44_candidate.csv',rows)
save_csv('diller2024_asbuilt29_secondary.csv',[r for r in rows if r['secondary_point_eligible']])

# Extract the actual xlsx XML, retaining every author identifier and raw field.
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(OUT/'tomaszewski2023_data.xlsx') as z:
    strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns):
            strings.append(''.join(t.text or '' for t in si.findall('.//s:t',ns)))
    sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    xrows=[]
    for rr in sheet.findall('.//s:row',ns):
        values=[None]*12
        for c in rr.findall('s:c',ns):
            ref=c.attrib['r']; col=0
            for a in re.match('[A-Z]+',ref)[0]:col=col*26+ord(a)-64
            v=c.find('s:v',ns); val=v.text if v is not None else None
            if c.attrib.get('t')=='s' and val is not None:val=strings[int(val)]
            elif c.attrib.get('t')=='inlineStr':val=''.join(t.text or '' for t in c.findall('.//s:t',ns))
            elif val is not None:
                try:val=float(val);val=int(val) if val.is_integer() else val
                except ValueError:pass
            if col<=12:values[col-1]=val
        xrows.append((int(rr.attrib['r']),values))

tom=[]
for rownum,v in xrows:
    if v[1]!='316L':continue
    sid,mat,orientation,t,w,length,smax,smin,R,n,ro,note=v
    r=base(); high=note=='high defect density'; sa=(smax-smin)/2
    # These are conditions, never manufacture build IDs inferred from prefixes.
    cond=f'tomaszewski2023_{orientation}_A{int(t*w):02d}_L{length}_R{R}'+('_highdefect' if high else '')
    r.update(row_id='tomaszewski2023_'+sid,specimen_id=sid,
             source_id='Tomaszewski_Zenodo7650061',source_doi='',
             source_dataset_doi='10.5281/zenodo.7650061',
             related_article_dois='10.1016/j.ijfatigue.2022.107378;10.1016/j.ijfatigue.2024.108225',
             condition_id=cond,condition_author=f'{orientation};{t}x{w}mm;working_length={length};R={R};{note or ""}',
             build_direction_author=orientation,specimen_thickness_mm=t,specimen_width_mm=w,
             working_length_author_mm=length,
             stress_author_value=smax,stress_author_definition='Max. stress [MPa]',
             stress_range_MPa=smax-smin,stress_amplitude=sa,stress_max_MPa=smax,stress_min_MPa=smin,
             load_ratio=R,cycles_observed=n,event=0 if ro else 1,runout=bool(ro),
             event_evidence='Cycles to failure column; Runout field blank' if not ro else str(ro),
             author_comment=note or '',source_url='https://zenodo.org/records/7650061',
             row_source_location=f'Data.xlsx; Arkusz1!A{rownum}:L{rownum}',
             force_control_status='raw_workbook_explicit_stress_controlled',loading_mode='axial',
             frequency_Hz=10, frequency_conflict='raw_workbook10Hz_articles20Hz',temperature_C='',
             process_laser_power_W=200,process_scan_speed_mm_s=800,
             process_layer_thickness_um=30,process_hatch_spacing_um=120,
             machine='SLM 125HL (related articles; raw/article join partly unresolved)',
             mapping_status='single_build_statement_2023_article_scope28_unresolved_against_raw137',
             stress_conflict=False, conflicts='paper_dataset_scope_and_frequency_unresolved',
             secondary_point_eligible=True)
    assert abs(smin/smax-R)<1e-12 and n>0 and smax>smin
    tom.append(r)
assert len(tom)==137 and len({r['specimen_id']for r in tom})==137
save_csv('tomaszewski2023_all137_secondary.csv',tom)
candidate=[]
for r in tom:
    if r['specimen_id'].startswith('SS_A02W_'):
        q=r.copy();q['build_id']='canonical_Tomaszewski107378_single_plate'
        q['mapping_status']='candidate_only_single_build_source_count_geometry_match;explicit_dataset_article_join_absent'
        candidate.append(q)
assert len(candidate)==9
save_csv('tomaszewski2023_a02w9_build_candidate.csv',candidate)
save_csv('all181_candidates.csv',rows+tom)

def readcsv(path):
    with path.open() as f:return list(csv.DictReader(f))
audit={}
for name,p in [('v2_strict309',ROOT/'data/processed/v2/strict/cohort.csv'),
               ('trombley2025',ROOT/'data/external_v2/trombley2025/fatigue_asbuilt_available129.csv')]:
    ref=readcsv(p); pairs=[]
    for r in rows+tom:
        if not r.get('stress_amplitude'):continue
        for z in ref:
            try:
                zr=float(z['load_ratio']);sa0=float(z['stress_amplitude']);n0=float(z.get('cycles_observed')or z.get('cycles'))
            except (KeyError,TypeError,ValueError):continue
            if abs(zr-r['load_ratio'])<1e-6 and abs(math.log10(n0/r['cycles_observed']))<=.02 and abs(sa0/r['stress_amplitude']-1)<=.01:
                pairs.append(dict(candidate_row_id=r['row_id'],reference_row_id=z.get('row_id')or z.get('observation_id'),
                                  reference_source=z.get('source_id'),N_candidate=r['cycles_observed'],N_reference=n0,
                                  Sa_candidate=r['stress_amplitude'],Sa_reference=sa0))
    audit[name]={'reference_rows':len(ref),'near_coordinate_pairs_Rmatched_1pctstress_0p02logN':len(pairs),
                 'near_pairs':pairs,'exact_source_DOI_matches':0,
                 'note':'Proximity screening cannot certify independence; source author/DOI and process identity also checked.'}
audit['all_metadata618']={'author_or_DOI_matches_Diller_Tomaszewski':sum(any(k in ' '.join(r.values()).lower() for k in ['diller','tomaszew','ffe.14375','2022.107378','2024.108225']) for r in readcsv(ROOT/'data/processed/all_datasets.csv'))}
articles=json.loads((ROOT/'data/raw/FatigueData-AM2022.json').read_text())['fatiguedata_am2022']['articles']
audit['all_metadata618']['author_matches']={name:[{'article_index':i,'doi':a['metadata'].get('doi'),'title':a['metadata'].get('title')} for i,a in enumerate(articles) if name in json.dumps(a['metadata'].get('author',[])).lower()] for name in ['diller','tomaszew']}
audit['all_metadata618']['author_or_DOI_matches_Diller_Tomaszewski']='See author_matches and exact DOI/source screening; all_datasets.csv omits authors.'
for cohort,p in [('all_metadata618',ROOT/'data/processed/all_datasets.csv'),('v2_strict309',ROOT/'data/processed/v2/strict/cohort.csv')]:
    for author,params in [('Diller',(250,1500,100,40)),('Tomaszewski',(200,800,120,30))]:
        hits=[]
        for r in readcsv(p):
            try:values=tuple(float(r[k])for k in ['power','scan_speed','hatch_space','layer_thickness'])
            except (ValueError,TypeError):continue
            if values==params:hits.append(r['dataset_id'])
        audit[cohort][author+'_exact_four_process_parameter_curve_matches']=sorted(set(hits))
audit['candidate_counts']={'Diller':len(rows),'Tomaszewski':len(tom),'strict_eligible':0}
audit['Tomaszewski_conditions']=dict(collections.Counter(r['condition_id']for r in tom))
(LIT/'independence_audit.json').write_text(json.dumps(audit,indent=2))
manifest=[]
for p in sorted(list(LIT.glob('*'))+list(OUT.glob('*'))):
    if not p.is_file() or p.name=='manifest.json':continue
    b=p.read_bytes();manifest.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(LIT/'manifest.json').write_text(json.dumps({'retrieved_date':'2026-10-20','files':manifest},indent=2))
print(json.dumps({'counts':audit['candidate_counts'],'conditions':audit['Tomaszewski_conditions'],
                  'reuse':{k:v for k,v in audit.items()if k in ['all_metadata618','v2_strict309','trombley2025']}},indent=2))
