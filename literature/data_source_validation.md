# Data source and semantics validation

Audit date: 2026-10-20. Scope: raw schema semantics; defaults versus observations; two original-publication checks. This is a targeted spotcheck, not full validation of every database record.

## 1. Runout polarity and units: verified

The official [FatigueData-AM2022 descriptor](https://doi.org/10.1038/s41597-023-02150-x), Data Records section, defines the first fatigue-data column as cycles N (or ΔK), the second as stress/strain amplitude (or crack-growth rate), and the third S–N/ε–N column as **1 for runout, 0 for failure**. Full JATS XML was independently retrieved from [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10151339/fullTextXML) and saved as `FatigueData_descriptor_2023.xml`. The default-unit system in the raw JSON agrees: cycles and MPa.

The descriptor's Eqs5–6 convert maximum stress to amplitude using `sigma_a = (1 - R) * sigma_max / 2`. This is a definition conversion, distinct from a mean-stress correction to equivalent fully reversed loading. A runout at c therefore means Nfailure > c and must enter an appropriate survival term, not a failure-density term.

## 2. Database defaults are not necessarily source measurements

The descriptor explicitly specifies the following conventions. Their presence in an individual row alone does not prove direct reporting by the experimenter.

| Entry | Descriptor convention | Recommended provenance label until checked |
|---|---|---|
| Missing numeric/text values | Empty arrays/lists/strings/cells | missing |
| Surface/heat/preheat if not applied | As-built / NHT / 25°C | database-coded not-applied/default; inspect source |
| Test type/environment/Kt if unspecified | Uniaxial / 25°C air / Kt=1 | database-default possible |
| Feedstock | Powder for L-PBF/E-PBF/P-DED; wire for W-DED | database-default possible |
| Load control | Force for S–N; strain for ε–N; load for da/dN; displacement for VHCF | database-default possible |
| One numeric value | Specific value or mean | reported-specific-or-mean unresolved |
| Two numeric values | Lower and upper bound | range; do not silently average |

The public schema does not supply a per-field marker that always distinguishes assumed defaults from explicit measurements. Flag ambiguous provenance rather than inventing certainty. Even a source's statement of room temperature does not independently establish an exact measured 25°C.

## 3. Stern et al.: completed graph spotcheck

Source: [Improving the Defect Tolerance of PBF-LB/M Processed 316L Steel by Increasing the Nitrogen Content](https://doi.org/10.1002/adem.202200751), original published PDF downloaded from [TU Dortmund repository](https://eldorado.tu-dortmund.de/bitstreams/85e849cf-99ec-4498-ac69-b65c8a91d353/download). CC BY; 13 pages. File: `Stern_2023_2200751.pdf`; p10 rendered and Figure10 extracted unaltered.

The first complete article object of the still-downloading JSON was decoded with the standard JSON decoder and saved separately; it is **not a claim that the entire JSON download was complete or checksum verified**. Original filenames and source are retained in the manifest.

Figure10's six black 316L markers correspond to sigma_max = 520,480,440,400,360,320 MPa. Original R=0.1 requires amplitudes 234,216,198,180,162,144 MPa. The database agrees within 0.10% in stress and within 0.40% in cycles against an independent manual reading of the extracted graph pixels. Exact comparison rows and axis calibration are in `Stern_Fig10_spotcheck.csv`. Marker pixels were selected visually; these cycle estimates are approximate. All six specimens are plotted as failures and the database flag is zero.

The red markers represent the chemically modified **316L + Nitrogen**, not a second ordinary-316L dataset. The database names the two materials separately. Exclude the modified material from an exact ordinary-316L cohort; if used in an exploratory alloy study, retain this distinction and the common publication group.

Original §2.3 pp3–4 verifies machining/polishing, no downstream heat treatment, a 3-mm fatigue gauge, 250W/800mm·s−1/100µm hatch/50µm layer. §2.9 verifies constant-amplitude R=0.1, 10Hz. Do not confuse the multiple-amplitude step tests with the constant-amplitude Figure10 data.

The database author list begins with Becker, while the published first author is Stern. It is unsuitable for constructing first-author labels; group by canonical DOI.

## 4. Voloskov et al.: source verification and expected values

Source: [Very High Cycle Fatigue Behavior of Additively Manufactured 316L Stainless Steel](https://doi.org/10.3390/ma13153293). CC BY; 11 pages. Full JATS XML was downloaded from [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7435938/fullTextXML), and the published PDF from a [Semantic Scholar mirror](https://pdfs.semanticscholar.org/e579/e3c7dea46f2377a603e9d2961fb9a032830b.pdf). DOI/title/11-page body and license agree. Source files and rendered pages4–5 are retained.

Figure3 p5 distinguishes the current study's blue filled HCF markers (R=0.1, 30Hz) and blue open VHCF markers (R=−1, approximately20kHz). The figure also overlays literature points from Spierings2013, Leuders2014, and Xiong2019. Those other symbols are **not new Voloskov specimens**.

Independent visual expected values were recorded before obtaining the final database subset in `Voloskov_Fig3_manual_expected.csv`: nine HCF observations, including two runouts around 1e7 cycles at sigma_max275 and250MPa, and four VHCF failure markers around (4e7,270), (1.4e8,260), (4e8,250), (1.1e9,255), in cycles/MPa maximum stress. HCF amplitudes require factor0.45; VHCF amplitudes equal maximum stresses.

**Completed MAT-derived comparison:** all13 study points match the13 database observations, with zero runout disagreements and no unmatched database rows. Largest differences from manual graph readings are2.60% in cycles and0.25% in stress. `Voloskov_Fig3_spotcheck.csv` records the matched row IDs and differences; `source_spotcheck.py` regenerates this comparison from `all_sn_observations.csv`. The source's borrowed comparison series were therefore not found as extra records under this DOI. This targeted result does not establish absence of repeated records elsewhere.

§2.1/Table1 verifies vertical specimens, 113W power, 600mm/s traverse speed, hatch0.08mm=80µm, layer0.020mm=20µm, machining, and no heat treatment. §2.2 gives a VHCF surface-temperature range15–45°C, so replacing it with exact25°C discards reported information. Figure3's blue-arrow runouts can independently test the flag polarity.

Source precision limit: the Figure5 caption describes a 450MPa specimen at2.23e5 cycles, whereas the Figure3 blue marker at450MPa is around2.86e5. This apparent plot/prose disagreement is not resolved by digitization. It does not establish a database error; the spotcheck tests agreement with Figure3, not the author's unshared specimen records.

§3.1 p4 cautions about traditional stress-based R=0.1 to R=−1 transformations for AM316L. Therefore, equivalent fully reversed stress corrections deserve a raw-R sensitivity analysis. This is separate from the unambiguous amplitude conversion above.

## 5. Duplicate/source-family evidence

Verified reuse clue: Voloskov Figure3 deliberately reproduces other publications' comparison points. Verification of blue-only extraction is required before declaring publication independence. This is a clue, not proof that FatigueData duplicated those points.

Potential Shrestha2019/2021 overlap was investigated through the [official Auburn NCAME publication list](https://eng.auburn.edu/ncame/publications). Both articles are listed; a displayed 2021 DOI link is mismatched with its title. No campaign/record equivalence has been established. **Do not merge source groups on shared authors alone.** Further investigation requires actual full text or near-identical curve evidence.

Conservative current rule: preserve canonical publication DOIs and dataset indices, flag candidate reuse, and join publications only when repeated specimens or reused source curves are documented or near-identical curve correspondence is demonstrated. The [17-publication Centola map](primary_audit/source_publications.csv) is a linkage starting point, not proof of row correspondence with the open database.

### Completed pre-fit curve-reuse screen

The read-only `duplicate_curve_audit.py` compared160 ordinary-316L L-PBF datasets from46DOIs. Same load ratio, mode, and runout status were required; matched coordinates were within2% in cycles and1% in amplitude. Unique greedy matching prevents one point from representing several observations. A screen of at least3 matches and50% of the smaller dataset yielded30 candidate curve pairs and no exactly identical numerical coordinate pairs. Approximate matches are expected when the same original graph is independently digitized.

For conservative pre-fit grouping, use the stronger subset with at least5 unique near matches and85% smaller-curve coverage. This yields the following connected publication components. These are **near-identical-curve families**, not proof of specimen identity, and no rows are removed by this audit.

| Family | Canonical source DOIs | Quantitative evidence |
|---|---|---|
| Elangeswaran/post-treatment | 10.1007/978-3-030-05861-6_36; 10.1016/j.addma.2021.102570; 10.1016/j.ijfatigue.2019.01.013; 10.1016/j.matdes.2020.108962 | Multiple11/11 and10/10 matches; shared smaller curves5/5 to7/7 link the fourth source. |
| Zhang/process/fatigue | 10.1016/j.ijfatigue.2018.12.016; 10.1016/j.ijfatigue.2019.105194; 10.1016/j.matdes.2018.02.054; 10.1016/j.msea.2017.07.071; 10.1051/matecconf/201816522006 | 11/11,12/13,10/11,9/9,8/8 and6/7 matches form the connected component. |
| Liang/surface/cyclic | 10.1016/j.ijfatigue.2022.106843; 10.1111/ffe.13684 | Independent conditions12/12 and11/11 matched. |

An unconfirmed weaker pair, 10.1016/j.ijplas.2021.103172 versus10.1016/j.jmst.2021.10.006, has3/4 matches. It does not meet the strong-family rule. Retain it as a sensitivity candidate; do not call it confirmed reuse. DOI-only and stronger-family grouping should both be reportable, with the family-aware version used to avoid known near-identical curves crossing training/test boundaries.

`duplicate_curve_candidates.csv` includes exact dataset/row links. `duplicate_curve_examples.png` overlays three strong examples directly from the open data. This screen does not test author intent, and it does not show that Centola's private518-row corpus contains the same duplicates.

### Load-control eligibility issue

The primary candidate table contains4 rows from `a0517_d002` (10.1111/ffe.13684) marked as S–N but `load_control=strain`. The paper's methods explicitly include both strain-controlled LCF and stress-controlled HCF experiments. For a prospectively stress-controlled primary benchmark, exclude the strain-control rows before fitting and retain them in the broader raw table. Do not treat a stress amplitude extracted from a strain-controlled cycle as the same prospective covariate as an imposed stress amplitude.

### Advertised alternative repository

The OSTI manuscript for DOI10.1016/j.msea.2024.146580 advertises `https://github.com/wietecha-reiman/Fatigue-AM-316L`. On2026-10-20 that URL, GitHub's repository API, and its contents API returned404. No flat file was acquired; a published link is insufficient evidence of current public access. This dataset was not combined with the present benchmark or treated as independent validation.

## Deliverables and remaining check

- `data_source_validation/manifest.json`: source URLs, access timestamps, licenses, SHA256, and verification status.
- Original PDFs/XML; page renders and embedded figure extracts.
- Stern six-point comparison CSV and source-article JSON snapshot.
- Voloskov thirteen-point independent expected-value CSV and completed matched-row comparison.
- Cross-publication near-duplicate screening script, candidate table, and strong-family overlay figure.
- No source measurements were inferred for unreported fields; no experimental rows were deleted or changed by this audit.
