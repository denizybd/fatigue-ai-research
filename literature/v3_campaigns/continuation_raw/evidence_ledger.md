# Continuation raw-data search: source gate

Result on 20 October 2026: **0 newly qualified independent campaigns; 14 anonymous fatigue observations quarantined; 8 named CT/surface specimens lack a fatigue crosswalk. No fitting, prediction, acquisition-policy comparison or benchmark extension was performed by this agent.**

## Figshare 33392110

[Official repository metadata](https://api.figshare.com/v2/articles/33392110), [public dataset](https://figshare.com/articles/dataset/33392110), DOI [10.6084/m9.figshare.33392110.v1](https://doi.org/10.6084/m9.figshare.33392110.v1), CC BY 4.0, published 31 August 2026. The raw 17,575-byte workbook MD5 equals the repository supplied/computed value, `783ca9e2682bce1d5f917319b754d138`; SHA256 is in source_manifest.json. The title and description concern as-built flat/cylindrical LPBF 316L qualification tests. No paper DOI, references or related-material entries appear in the metadata.

Workbook sheets separate named surface/CT specimens (Flat F1–F4 and Cylindrical C1–C4) from anonymous experimental fatigue pairs (8 flat, 6 cylindrical). The latter have only Nf and Sr(MPa); the sheet does not provide a specimen ID, physical build, powder lot, R, Sr definition, test mode/control, temperature, frequency, failure/runout flag or stopping rule. The row locator in the normalized CSV is explicitly synthetic and is not an author specimen ID. Sr was not converted into amplitude. Nothing was inferred from ordering, geometry, filenames or CT labels. Existing Basquin/FEA output in the workbook was not imported as experimental observations.

The 14 rows fail both the strict and ≥6 pilot gate despite sufficient row count. Source-data recovery needs an author-supported table linking each fatigue row to actual specimen, build/powder batch, stress convention/R and censoring/test metadata. The CT table remains separate.

## Source-family and reuse audit

[Wu et al., Materials Letters 140105](https://doi.org/10.1016/j.matlet.2026.140105) shares authors and the four exact flat XCT defect fractions in its indexed publisher preview. Its abstract reports one LPBF build; preview Methods name EOS M290 and vertical ASTM E466 geometry. That claim is restricted to that paper. It does not establish that all anonymous rows in the different Figshare workbook came from that build. The author-repository record [DR-NTU 10356/211002](https://hdl.handle.net/10356/211002) returned 405; no accepted-manuscript PDF was obtained. Public Elsevier API supplied metadata only.

The new dataset DOI and the two Wu article DOIs have zero matches in the 618-source FatigueData-AM2022 metadata. One normalized full-author-name match, Tong Liu, belongs to the different EH36 steel paper 10.1016/j.msea.2020.139049; a name match is not physical reuse. Exact Nf overlaps against strict309, Trombley129, Tomaszewski137 and Diller44 are zero. This is a negative screen, not proof of physical independence. Stress-coordinate overlap is not computed because Sr/R are unknown. No fatigue-row→build crosswalk is verified. Do not count the related Wu sources as independent campaigns merely because they have different DOIs.

The newer Wu fatigue-ML paper 109943 is a separate prior-art warning; see prior_art_109943_scope.md for primary-preview evidence and unresolved full-text questions. There is no evidence linking the Figshare workbook to its validation series, so no such link is asserted.

## Other fresh leads and dispositions

| Lead | Primary evidence/access | Disposition |
|---|---|---|
| Wood/Kopec reused-powder fatigue, 10.1007/s11340-024-01118-1 | Full Springer HTML retrieved; 25 reuse cycles, AM250, multiple orientations, force control, zero mean, 20 Hz | Data on request; no public specimen→S,N/build crosswalk found; not admitted |
| Contaminated 316L/Ti6Al4V powder, 10.1080/17452759.2026.2626647 | Publisher page 403; indexed primary lead indicates rotating bending R−1 | Outside primary axial scope and no raw identity map retrieved; not admitted |
| OSTI 1668247 ICME 316L package | Requested purl returned 404 HTML, not PDF | No usable raw download found in this pass; not admitted |
| Qiu/Ye harmonic fatigue, PMC8836977 | Search lead: three full fatigue specimens plus interrupted-damage specimens | Below six full-life pilot specimens; interrupted tests must not become failure observations |
| Zenodo broad search pages 2–3 | Public API snapshots retained; many unrelated records | No additional verified qualifying campaign |
| Figshare exact related-title searches | API snapshots retained; exact qualification title maps back to 33392110 | No second independent campaign |

## Reproducible local files

- `data/external_v3/continuation_raw/zhou2026_supporting.xlsx`: original author workbook, preserved.
- `data/external_v3/continuation_raw/zhou2026_fatigue14_quarantined.csv`: anonymous raw values with unknown fields blank and all eligibility flags false.
- `data/external_v3/continuation_raw/zhou2026_named_CT8_no_fatigue_crosswalk.csv`: named CT/surface rows only.
- `normalize_zhou_quarantine.py`: standard-library XML extraction and overlap screen; generates the preceding CSVs and `zhou2026_source_gate.json`.
- `source_manifest.json`: access status, source URL, license and raw-file hashes.
- `manifest.json`: all continuation-owned artifact SHA256 hashes, excluding itself. A 403/404/405 artifact hash authenticates an error response, not article content.

All previous v3 data and results were left untouched. No author contact or request was sent.
