# Processed-data dictionary

Prepared 2026-10-20 from `src/prepare_data.py`, the official MAT units/schema, and the source-validation report. This documents preparation and metadata, not model outcomes. Raw source: Zhang and Xu, [FatigueData-AM2022 v2](https://doi.org/10.6084/m9.figshare.22337629.v2), CC BY 4.0; descriptor [10.1038/s41597-023-02150-x](https://doi.org/10.1038/s41597-023-02150-x). Raw SHA256, access time and URL are in `data/raw/manifest.json`. Units copied verbatim from the MAT object are in `data/processed/units.json`.

## Files and observational unit

- `all_datasets.csv`: one row per database dataset, including non-S–N fatigue types. It contains metadata and dataset sizes, not individual fatigue observations.
- `all_sn_observations.csv`: one row per S–N database point across alloys/processes.
- `ss316l_lpbf_all.csv`: exact ordinary 316L-name whitelist, L-PBF, finite positive observed cycles and stress amplitude. No life/outlier filtering.
- `primary.csv`: additionally database-labeled force-controlled uniaxial,20–30°C and Kt0.99–1.01, with conservative source-family blocks. The frozen protocol specifies these inclusion rules. Defaults in the database prevent certifying every eligibility variable as source-measured.
- `centola_source_overlap.csv`: original-paper reference/condition map linked by DOI, with inclusion flags for each prepared cohort. These are publication matches, not specimen matches.
- `primary_doi_only.csv`: same 1126 observations with DOI-only groups; potentially contaminated sensitivity.
- `primary_weak_edge.csv`: same rows with an additional weaker candidate edge merged; 28 blocks.
- `primary_deduplicated_sensitivity.csv`: 942 rows after greedy 184 near-coincident cross-DOI removals inside strong families; not the primary cohort.
- `deduplication_sensitivity_map.csv`: every approximate removal mapped to its retained near-match; it does not certify physical specimen identity.
- `source_family_map.csv` and `grouping_report.json`: source-to-block mapping and frozen grouping criteria/qualifications.
- `quality_report.json`: deterministic counts, missingness and scope caveats.

An observation is a database-extracted plotted point. Multiple observations may represent the same published campaign, and physical-specimen uniqueness is not certified. IDs identify database locations. Do not call them original specimen IDs.

At initial preparation: all S–N 15146 points/1610 datasets/459 source IDs; ordinary 316L L-PBF 1473/160/46; initial preliminary primary 1130/121/37. The pre-fit v1.3 eligibility correction removes four strain-control-labeled rows, leaving 1126 observations/120 conditions/37 source DOIs and 987 failures/139 runouts. Conservative near-curve families give 29 primary blocks. All 1126 primary rows have extraction method `color and shape`, so the coordinates are approximate digitizations rather than newly measured or author-provided raw specimen data. These counts describe the v1.3 pre-fit cohort. DOI count and block count are different units of independence.

## Field definitions

Blank scalar CSV entries represent missing/unusable scalar values. `scalar()` accepts exactly one finite numeric value; empty, multivalue/range, nonnumeric or nonfinite input becomes missing. A raw one-element entry may itself be a source mean, not an individual measurement. No midpoint of a range is invented.

| Field | Type / unit | Meaning and origin | Modeling use |
|---|---|---|---|
| `article_index` | integer, zero-based | Position in raw `articles` array | provenance only |
| `dataset_index` | integer, zero-based | Position in this article's `scidata.datasets` | provenance only |
| `dataset_id` | string | Stable preparation address `a####_d###` | grouping/audit only |
| `source_id` | string | Lowercase DOI with DOI-URL prefix stripped; fallback article-address ID when absent | split/weights only |
| `doi` | string | Normalized source-publication DOI; may be empty in wider database | linkage only |
| `title` | string | Database publication title | provenance only |
| `year` | numeric year | Singleton publication-year metadata | provenance only |
| `material` | string | Raw database material name; modified316L alloy kept distinguishable | inclusion only |
| `am_type` | string | Raw database AM process class, e.g. `L-PBF` | inclusion only |
| `fdata_type` | string | Database fatigue-data type; observation tables restricted to S–N | inclusion only |
| `extraction_method` | string | Database's declared figure/table extraction procedure | provenance only |
| `surface` | string | Sorted distinct `SURF` method strings joined with semicolons; `unknown` if absent | rich categorical input |
| `thermal` | string | `HIP` if any HIP step, otherwise `HT` if any HT, otherwise explicit `NHT`, otherwise `unknown` | rich categorical input |
| `heat_temperature` | float, °C | Singleton temperature of the sole HT step; missing if zero/multiple steps or range | rich numeric input |
| `heat_time` | float, h | Singleton duration of the sole HT step; same ambiguity rules | rich numeric input |
| `hip_temperature` | float, °C | Singleton temperature of sole HIP step | saved, not model input |
| `power` | float, W | Singleton laser-power process metadata | rich numeric input |
| `scan_speed` | float, mm/s | Singleton scan-speed metadata | rich numeric input |
| `hatch_space` | float, µm | Singleton hatch-spacing metadata | rich numeric input |
| `layer_thickness` | float, µm | Singleton layer-thickness metadata | rich numeric input |
| `direction` | float, degree | Angle between AM build platform and loading direction per descriptor;0 horizontal,90 perpendicular | rich numeric input |
| `preheat` | float, °C | Singleton preheat metadata, potentially database-default25°C | saved, not model input |
| `load_ratio` | float, dimensionless | R=minimum/maximum stress in database testing metadata | both input sets |
| `frequency` | float, Hz | Singleton fatigue-test frequency; ranges become missing | saved, not model input |
| `test_type` | string | Database fatigue-test mode; default may be uniaxial | inclusion/audit only |
| `temperature` | float, °C | Singleton fatigue-test temperature; default may be25°C | inclusion/audit only |
| `environment` | string | Database fatigue-test environment; default may be air | audit only |
| `kt` | float, dimensionless | Elastic stress-concentration factor; default may be1 | inclusion/audit only |
| `load_control` | string | Database force/strain/displacement label; may derive from data-type convention | audit only |
| `geometry` | string | Raw specimen description/cross-section description | provenance only |
| `specimen_size` | float, mm | Singleton critical-section size; multicomponent dimensions become missing | saved, not model input |
| `quality_score` | float, dimensionless | Database completeness rating, based on nonempty entries; not an experimental error bound | audit only |
| `scalar_metadata_provenance` | string | Fixed caution that database-reported/default status is unresolved per field | audit only |
| `n_observations` | integer | Number of raw points in the dataset, repeated on its observation rows | audit only |
| `row_id` | string | Stable database address `a####_d###_p###` | joins/receipts only |
| `point_index` | integer, zero-based | Row position in raw fatigue-data array | provenance only |
| `cycles_observed` | float, cycles | First S–N column: failure life T when failed, right-censor endpoint C when runout | outcome only |
| `stress_amplitude` | float, MPa | Second S–N column, stress amplitude; database may convert published maximum stress | input via log transform |
| `runout` | integer0/1 | Third S–N column:0 failure,1 test ended without failure | likelihood/evaluation only |
| `event` | integer0/1 | Derived `1-runout`:1 failure,0 right censored | likelihood/evaluation only |
| `measurement_provenance` | string | Approximate digitization when extraction method contains shape/color; otherwise unresolved database extraction | audit only |
| `raw_address` | string | Explicit article/dataset/point path back to MAT hierarchy | provenance only |
| `log_life` | float, log10(cycles) | log10 of observed endpoint, including runouts | outcome only |
| `log_stress` | float, log10(MPa) | log10 stress amplitude, using MPa numerically | both input sets |
| `group_id` | string | Canonical DOI or `curve_reuse_family_##` conservative family ID per frozen grouping | splits/weights only |

## Training transformations

`src/features.py` fits imputation/scaling/categories only on each fitting partition. Basquin-style input set is log stress plus load ratio. Rich inputs add direction,power,scan speed,hatch,layer,HT temperature/time and surface/thermal categories. Every numeric feature gets a missing-value indicator. Finite training median fills missing values; a wholly missing training column receives 0 as an explicit computational fill, accompanied by missing indicators. Means/SDs are then computed on training-imputed values. Constant-scale columns use SD 1. Surface/treatment strings are categorical whole labels rather than a manually inferred common treatment ontology; unseen test labels receive `__unseen__`.

`event`, observed life, source ID and metadata quality scores are not encoder inputs. Bootstrap grouping and likelihood weighting use `group_id` only. No risk-volume feature, SWT-equivalent-stress correction, specimen-local defect measure, fitted S–N curve label or Owen multiplier is computed by this pipeline.

## Measurement/default distinction and censoring

Stress amplitude is not maximum stress, nor the equivalent fully reversed amplitude used by Centola. The descriptor converts reported maximum stress with amplitude=(1−R)*maximum/2; that is an amplitude definition conversion, not a mean-stress correction. Our models include raw R as a covariate and do not claim equivalence to the original paper's SWT preprocessing.

The descriptor defaults unspecified tests to uniaxial,25°C air,Kt1, and makes conventions for as-built/NHT/preheat and load control. Public rows do not always record whether a value was directly reported or defaulted. Thus inclusion means **database-labeled** room-temperature unnotched uniaxial, not universal verification from original test reports.

At a runout, true failure life exceeds `cycles_observed`. A lower-life prediction below that endpoint is demonstrably conservative for that specimen; a larger prediction has unknown violation status. Neither ordinary failure-only coverage nor treating endpoint C as exact failure T is appropriate. `event` polarity is explicitly reversed from the raw runout flag.

The preliminary 1130-row cohort had 1126 force and 4 strain labels. Amendment v1.3 excluded the four strain-labeled records before any real model fit, yielding the force-controlled primary cohort. Scalar process fields have substantial missingness:548 power,533 scan speed,684 hatch,140 layer,23 direction,8 load ratio,816 HT temperature/time. These are row counts, not independent missingness events.

## Scope limitations

- Original Centola518 rows and32 excluded rows are not obtained;12 of its17 source DOIs occur in this primary cohort,16 in the wider ordinary 316L L-PBF cohort. No row identity is established.
- Database geometry/size cannot be silently converted to Centola's90%-stress risk volume. Loading gradients, full geometry, and stress-field calculations would be needed.
- Thermal coding compresses multistep schedules. HIP time/pressure are not rich-model inputs; HT numeric fields do not represent all possible heat treatments.
- Surface categories preserve database wording. Similar words may mean different roughness histories, and rare labels can proxy a publication.
- Feedstock chemistry, machine calibration, roughness, residual stress, defects, testing standard and physical batch identity are not fully represented. Conditional association does not establish a causal parameter recommendation.
- Digitization uncertainty is not propagated as an explicit measurement-error distribution. Original-source checks are targeted, not exhaustive.

## Frozen source-family and approximate-duplicate sensitivities

Amendment v1.3 conservatively joins three connected source families before fitting, using at least five distinct near-coincident points covering at least 85% of the smaller curve, with matching R and test mode and multiplicative life/stress tolerances1.02/1.01. This reduces 37 DOI groups to 29 blocks. It flags plausible curve reuse and is not proof of repeated physical specimens. All 1126 observations remain in the main analysis.

DOI-only splitting deliberately restores 37 groups as a potentially contaminated sensitivity. A weaker3/4-point edge joins 10.1016/j.ijplas.2021.103172 with 10.1016/j.jmst.2021.10.006, giving 28 blocks in a sensitivity. Approximate cross-DOI deduplication within strong families retains the lowest database-address representative greedily, with the same runout and R and fixed near-coordinate tolerances;184 rows are removed only in this 942-row sensitivity. Distinct replicates may be merged, so it cannot replace the primary. Every removal is recorded. See `src/group_sources.py`, `grouping_report.json`, and the mapping CSVs for exact reproducible membership.
