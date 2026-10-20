"""Conservative manual Figure 11 digitization; no fitting or inferred specimen IDs.

Coordinates refer to the original embedded 738 x 592 image, not an upscaled crop.
The visible markers were inspected at source resolution and in enlarged crops.
Ambiguous additional multiplicities are deliberately not reconstructed.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/external_v5/faue'
OUT.mkdir(parents=True, exist_ok=True)
IMAGE = ROOT / 'literature/v5_open/faue/paper_Figure11.png'
X5, X6 = 182.5, 522.5
PIXEL_ERROR = 3.0

# treatment, amplitude MPa, x/y in original embedded raster, overlap description
MARKERS = [
    ('AM-AB', 300, 139.0, 82.0, 'Distinct black rounded marker; neighbouring left diamond/line overlap not counted'),
    ('AM-LP', 300, 128.0, 82.0, 'Red diamond intersects fitted line; outline and top/bottom vertices visible'),
    ('AM-LP', 300, 154.0, 82.0, 'Two adjacent red diamonds have distinct vertices; left member'),
    ('AM-LP', 300, 161.0, 82.0, 'Two adjacent red diamonds have distinct vertices; right member'),
    ('AM-AB', 225, 249.5, 225.0, 'Left of two overlapping black circles with distinct rounded boundaries'),
    ('AM-AB', 225, 256.5, 225.0, 'Right of two overlapping black circles with distinct rounded boundaries'),
    ('AM-LP', 225, 228.0, 225.0, 'Red diamond outline visible; possible underlying black point not counted'),
    ('AM-LP', 225, 240.0, 225.0, 'Red diamond with visible top/bottom vertices'),
    ('AM-LP', 225, 274.0, 225.0, 'Distinct rightmost red diamond; sloping fit not counted'),
    ('AM-AB', 150, 377.0, 429.0, 'Isolated black circle'),
    ('AM-AB', 150, 411.0, 429.0, 'Distinct black circle with fitted-line intersection'),
    ('AM-AB', 150, 425.0, 429.0, 'Black circle has visible rounded lower boundary next to first red diamond'),
    ('AM-LP', 150, 433.0, 429.0, 'Red diamond outline visible; possible underlying black point not counted'),
    ('AM-LP', 150, 442.0, 429.0, 'Red diamond outline visible; possible underlying black point not counted'),
    ('AM-LP', 150, 451.0, 429.0, 'One resolved red diamond in dense cluster; any further multiplicity unresolved'),
    ('AM-LP', 150, 485.0, 429.0, 'Isolated rightmost red diamond'),
]

def cycles(x):
    return 10 ** (5 + (x - X5) / (X6 - X5))

rows = []
for i, (condition, stress, x, y, note) in enumerate(MARKERS, 1):
    rows.append(dict(
        extraction_id=f'faue2022_fig11_marker_{i:02d}',
        author_specimen_id='',
        physical_specimen_id='',
        extraction_id_is_physical_specimen_id=False,
        canonical_build_id='Faue2022_single_AM_build',
        canonical_build_id_type='curator_label_for_explicit_author_single_build_statement',
        author_build_id='',
        build_link_evidence='Paper PDF3 Section2: all AM samples produced in a single build; Figure11 AM marker treatment membership',
        source_doi='10.1016/j.mfglet.2022.07.083',
        source_family_id='Faue2022_Agrawal2022_same_campaign',
        source_figure='Figure11',
        source_pdf_page=6,
        source_url='https://par.nsf.gov/servlets/purl/10357954',
        material='316L stainless steel',
        process='laser powder bed fusion',
        machine='EOS M290',
        build_orientation='horizontal',
        condition=condition,
        surface_condition=('support removal and local mechanical polishing; no laser polishing' if condition == 'AM-AB' else 'support removal and local mechanical polishing; laser polishing'),
        heat_treatment='none before fatigue or laser polishing',
        stress_amplitude_MPa=stress,
        stress_definition='reported applied stress amplitude; gripping-induced additional tensile stress not quantified',
        stress_definition_evidence='Paper PDF6 discussion calls tested values stress amplitudes; thesis PDF67 printed52 explicitly gives150/225/300MPa amplitudes',
        cycles_to_failure_approx=round(cycles(x), 1),
        cycles_pixel_lower=round(cycles(x - PIXEL_ERROR), 1),
        cycles_pixel_upper=round(cycles(x + PIXEL_ERROR), 1),
        event=1,
        endpoint='reported fatigue failure; AM plotted points below runout threshold',
        source_runout_threshold_cycles=2000000,
        runout_threshold_applies_to_record=False,
        load_ratio_R='',
        frequency_Hz='',
        temperature_C='',
        feedback_control_mode='',
        waveform='',
        constant_amplitude_explicitly_verified=False,
        method_scope='reported S-N fatigue tests at fixed labelled stress levels; detailed loading protocol unreported',
        loading_axis='cylindrical axial specimen geometry and straightening/gripping described; fatigue loading mode not explicitly stated',
        x_pixel=x,
        y_pixel=y,
        x_pixel_error_assumed=PIXEL_ERROR,
        observation_origin='manual digitization of resolved plotted marker',
        approximation='pixel interval only; not a statistical confidence interval and not specimen variability',
        overlap_note=note,
        audit_panel='E2_method_uncertain_digitized_candidate',
        strict_method_eligible=False,
        physical_identity_eligible=False,
        primary_training_admitted=False,
    ))

csv_path = OUT / 'faue2022_resolved_AM_markers_E2_candidate.csv'
with csv_path.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

ambiguities = [
    dict(region_id='AMAB300_left_overlap', amplitude_MPa=300, treatment='AM-AB', x_pixel_lower=123, x_pixel_upper=134, reason='Potential black circle under left red diamond and fitted line cannot be separated securely; no observation added'),
    dict(region_id='AMAB225_left_overlap', amplitude_MPa=225, treatment='AM-AB', x_pixel_lower=224, x_pixel_upper=237, reason='Potential black circle under left red diamond cannot be separated securely; no observation added'),
    dict(region_id='AMAB150_diamond_overlap', amplitude_MPa=150, treatment='AM-AB', x_pixel_lower=430, x_pixel_upper=446, reason='Black contributions under red diamonds may include markers but exact centres and multiplicity unresolved; no observation added'),
    dict(region_id='AMLP150_dense_overlap', amplitude_MPa=150, treatment='AM-LP', x_pixel_lower=447, x_pixel_upper=457, reason='One visually resolved diamond retained at451px; any additional overlapping diamond multiplicity not reconstructed'),
    dict(region_id='reported_count_unreconciled', amplitude_MPa='', treatment='all AM', x_pixel_lower='', x_pixel_upper='', reason='Paper reports22AM specimens (11each treatment);16resolved markers extracted, without locating or reconstructing the remaining accounting gap'),
    dict(region_id='all_conventional_M', amplitude_MPa='', treatment='M-AB and M-LP', x_pixel_lower='', x_pixel_upper='', reason='Conventional machined material excluded; black crosses/red squares are not LPBF'),
    dict(region_id='fits_axes_legend_runout', amplitude_MPa='', treatment='', x_pixel_lower='', x_pixel_upper='', reason='Fit lines, axes, grid, legend and2million-cycle reference are not experimental AM records'),
    dict(region_id='thesis_Figure22', amplitude_MPa='', treatment='AM-AB and AM-LP', x_pixel_lower='', x_pixel_upper='', reason='Same campaign; six representative or summary symbols are not independent additional specimens and are not joined to paper points'),
]
with (OUT / 'faue2022_unresolved_and_excluded_regions.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(ambiguities[0]))
    w.writeheader()
    w.writerows(ambiguities)

receipt = dict(
    version='v5_Faue_conservative_resolved_markers_v1',
    source_reported_AM_n=22,
    source_reported_AM_AB_n=11,
    source_reported_AM_LP_n=11,
    extracted_markers_n=len(rows),
    extracted_by_treatment={k: sum(r['condition'] == k for r in rows) for k in ['AM-AB', 'AM-LP']},
    source_count_gap=22-len(rows),
    gap_meaning='Accounting difference only; no claim to know number or positions of all hidden overlapping markers',
    original_raster=dict(path=str(IMAGE.relative_to(ROOT)), width=738, height=592, sha256=hashlib.sha256(IMAGE.read_bytes()).hexdigest()),
    calibration=dict(x_at_1e5=X5, x_at_1e6=X6, x_scale='log10', stress_source='exact reported stress amplitude levels, not digitized y', x_error_pixels=PIXEL_ERROR, relative_pixel_error_upper=10**(PIXEL_ERROR/(X6-X5))-1, calibration_crosscheck='2million reference line near625px agrees with expected624.85px within one raster pixel'),
    author_individual_IDs_recovered=0,
    author_build_labels_recovered=0,
    explicit_single_build_statement=True,
    physically_identified_samples=False,
    experimental_protocol_complete=False,
    strict_method_admitted_n=0,
    primary_training_admitted_n=0,
    candidate_panel='E2_method_uncertain_digitized_candidate',
    independent_visual_spot_check=dict(agent='v3_methods_rfl', status='agrees on resolved-marker choices and conservative exclusion of under-diamond black regions', limitation='Visual digitization check, not independent physical fatigue validation'),
    normalized_csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
)
(OUT / 'extraction_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
assert len(rows) == 16
assert len({r['extraction_id'] for r in rows}) == 16
assert all(r['cycles_pixel_lower'] < r['cycles_to_failure_approx'] < r['cycles_pixel_upper'] for r in rows)
assert all(not r['author_specimen_id'] and not r['load_ratio_R'] for r in rows)
assert all(r['event'] == 1 and r['cycles_pixel_upper'] < 2e6 for r in rows)
print(json.dumps(receipt, indent=2))
