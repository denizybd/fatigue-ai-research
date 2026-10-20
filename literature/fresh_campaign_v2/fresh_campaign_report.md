# External-campaign acquisition and provenance gate (20 October 2026)

## Result

A usable author-provided external fatigue campaign was found and acquired from publicly displayed Materials Commons specimen records. **129 as-built records are complete**, across 44/40/45 specimens at nominal diameters 1.5/2.5/5.0 mm. The article advertises 130 as-built specimens, but one public specimen page omits the fatigue stress and endpoint; no missing value was inferred. These are three related conditions in **one campaign**, not three independent laboratories/campaigns.

Article: Trombley, Birnbaum and Allison, *The influence of section diameter on the ultrasonic fatigue response of 316L stainless steel manufactured via laser powder bed fusion*, Scientific Reports 15,13385 (2025), https://doi.org/10.1038/s41598-025-97031-1 . Public full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC12008181/ . The data-availability section directly links Materials Commons dataset DOI https://doi.org/10.13011/m3-c93d-z035 , resolving to https://materialscommons.org/public/datasets/2564/overview . Dataset creator: Megan Trombley; DOI registered 3 April2025. The full article HTML/XML and repository landing/index pages are retained locally.

## Actual provenance, without equating publication date to experiment date

The article Methods report a single CL20ES powder batch, four builds on a GE Concept Laser M2 at the US Naval Research Laboratory, 370 W power/900mm/s scan/25um layers/160um spot, vertical cylindrical dogbones, 20kHz ultrasonic fully reversed axial loading with pulse/pause cooling. The public sample records have unique author specimen names, entity IDs, test dates, condition labels, maximum stress, observed cycles and explicit Failure/Runout labels. Dates range **24 June2019–12 July2021**. Prior conference presentations in 2021–2023 describe the same research; the 2024 dissertation/preprint and 2025 journal article must be treated as one source family. The experiment is newly acquired for this research, not newly performed in2025.

The article identifies fatigue failure by a 200Hz resonance-frequency change producing a visible crack, potentially before complete specimen fracture. This endpoint distinction must accompany any cross-source result. Four builds are reported but individual specimen-to-build mapping is not explicit in the displayed fields. CCV1/CCVT1/CCVT2 name prefixes must not be silently declared certified build IDs.

## Acquisition and exclusions

`acquire_trombley.py` retrieves public GET specimen pages (157 entities, four parallel requests), retains their raw HTML/hashes and extracts labeled attribute pairs. It uses no authentication, bulk archive download, upload, account creation or access-control bypass. Raw XLSX files are referenced by the pages but their UI advertises login/download; no XLSX contents were obtained or executed.

`prepare_trombley.py` produces:

- `data/external_v2/trombley2025/fatigue_asbuilt_available129.csv`: main candidate, 129 records, 103 failures and26 runouts.
- `fatigue_all_conditions.csv`:154 fatigue records including10 heat-treated,8 contour-removed,7 surface-removed specimens; small postprocessing groups remain secondary only.
- `specimen_attributes.json/csv`: extracted author labels; `manifest.json`: source URLs, access time, sizes and SHA256s.
- `exclusions.csv`: three records without fatigue stress/endpoint. Entity67563 (`CCV1-1.5a-16-au`) is an incompletely populated as-built fatigue page; entities67624/67625 are residual-stress-only specimens. No endpoint is invented.

The3 as-built condition failure/runout counts are29/15,34/6,40/5. Distinct named specimens with identical rounded coordinates/runout endpoints remain distinct; seven repeated coordinate tuples are not deduplicated automatically. All retained fatigue stress/endpoint/status fields were singleton and unambiguous across their repeated metadata display sections.

## Stress/censoring conventions

The repository labels maximum stress inMPa and R=-1, so amplitude equals maximum stress here by amplitude=(1-R)maximum/2. Observed cycles are exact displayed author values, potentially rounded, rather than plot digitizations. Runout means right censored at that specimen's **displayed endpoint**. The Methods mention1e8cycles but actual runout endpoints range1e8–2.85e8cycles; no universal administrative censoring time for failures is fabricated. This does not automatically satisfy type-I survival-conformal assumptions.

The authors use a censored Weibull random-fatigue-limit(RFL) model for the HCF/VHCF knee. A plain log-linear Basquin model can be misspecified in this regime. A credible claim must include an appropriate knee/RFL comparator or explicitly bound its modeling scope before fitting; selecting a finite-life subset after seeing performance is prohibited.

## Overlap screen against existing historical data

Source metadata of all618 FatigueData-AM2022 articles contained no Trombley/Birnbaum/JohnAllison match; no 316L L-PBF row has the complete370W/900mm/s/25um parameter combination. DOI/title mismatch alone is insufficient. The same conservative point screen used in phase1 was also applied: matching R/runout,2%cycles/1%amplitude, greedy unique point matching per condition/curve. No historical comparison reaches≥5matchedpoints and≥85%of smaller-curve coverage. Maximum matches are3,covering≤25%of the smaller curve; isolated coincidences are recorded in `historical_coordinate_screen.csv`. This gives no positive reuse signal, but cannot prove every physical specimen independent of all historical reports. The report/CSV explicitly retain this qualification.

## Freeze and use

The campaign was acquired, mapped and quality screened before any predictions or performance-driven choices by this agent. No model was fitted. The historical/fresh source lists and final splits must be frozen by the root protocol before using external outcomes. For a new-source test, all three external diameter conditions stay out of population fitting/calibration; few-shot support/query separation is within each condition. The three conditions provide related replication within one source, not a source-level confidence interval from three independent campaigns.

## License and dissemination

**Materials Commons explicitly displays “No license specified”; DataCite rightsList is empty.** The journal article is CC BY4.0, which does not automatically relicense the separate repository records. Local analysis is possible from the publicly displayed records; raw HTML/metadata/CSV must be excluded from a public/shareable ZIP until redistribution terms are clarified. Share acquisition/transformation code, URLs, hashes and derived result summaries separately, with this limit. No correspondence was sent.

## Other fresh data screened

- Bartošák etal, DOI10.5281/zenodo.12515773 /10.1016/j.ijfatigue.2024.108608: public26.6kB archive, experimental2021–2024 data, but strain-controlled multiaxial low-cycle fatigue; outside the present stress-controlled axial HCF scope.
- Kousoulas/Guo, DOI10.1115/1.4066803: full author manuscript downloaded from https://par.nsf.gov/servlets/purl/10562826 . Original bending fatigue experiments; associated CC BY4.0 Mendeley dataset https://doi.org/10.17632/87hm5hwbpk.2 contains defect measurements/macros rather than the needed specimen fatigue table. Different loading mode; not used to fill axial-validation need.
- Aghayar etal, DOI10.1016/j.ijfatigue.2025.109365: public individual point table, but rotating bending/elevated temperature; room-temperature as-built condition explicitly reuses authors' prior study. Thus a2025publication is not automatically a fresh independent campaign.
- DOI10.17632/83wh6zdpz9.1: author thermomechanical fatigue data at550–750C, strain-controlled; excluded from current scope.
- DOI10.5281/zenodo.17086687: raw low-cycle strain histories,3.4GB; unsuitable scope and unnecessary download, not fetched.

Searches were limited to primary papers, author datasets and institutional repositories. Search terms included316L/laser powder bed/fatigue/raw data/supplementary/2023–2026, Zenodo/Mendeley/MaterialsCommons. No claims of an exhaustive data census are made.


## Extraction verification

A second implementation using Python HTMLParser DOM traversal and Decimal arithmetic (without importing acquisition/transformation functions) checked all154fatigue records including all129as-built:1,232numeric comparisons,770categorical comparisons,1,078original-attribute-JSON comparisons passed. Independently checked conditioncounts44/40/45, unique154specimen names, all129 as-built rows equal theirall-condition counterpart, and exactthree incomplete/nonfatigueentityIDs. Five labeledauthorrecord sections were separately read and their values reconciled toCSV; receipt source_read_five_records.csv. This is independent code/arithmetic extraction checking, not external scientific replication or validationofauthorrecordaccuracy.
