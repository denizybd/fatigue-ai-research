# Raw-repository campaign audit, 20 October 2026

**Two additional author-data acquisitions, 181 rows, zero campaigns passing the strict specimen-to-build gate at this handoff.** The useful secondary sets are Tomaszewski137 and Diller29. They are two author research programs, not two certified independent physical production batches. No predictions or fits were performed here.

## File index and identity classification

| File under data/external_v3/raw_repository | Rows | Physical identity and use |
|---|---:|---|
| `diller2024_all44_candidate.csv` | 44 | Author scan identifiers, linked to physical fatigue specimens by dataset description. Four stops without failure. Build and powder-lot identifiers absent. |
| `diller2024_asbuilt29_secondary.csv` | 29 | Author μ-scan specimen IDs, seven retained stress-range levels; μ15 excluded for a stress conflict. All are failures. Secondary only. |
| `tomaszewski2023_all137_secondary.csv` | 137 | Actual author `Specimen number` values, 12 conditions, explicit axial sinusoidal stress control. No source-certified build assignment for these137 records. Secondary only. |
| `tomaszewski2023_a02w9_build_candidate.csv` | 9 | A potential canonical single-plate subset. Matching geometry, orientation, R and count support association, but the raw repository has no explicit article link or specimen list joining the nine labels to the paper. Strict flags remain false. |
| `all181_candidates.csv` | 181 | Union for provenance inspection, not a fitting whitelist. |

`condition_id` values encode author conditions only. They must never be interpreted as physical build IDs. All `powder_batch_id` fields are blank. The nine-row build candidate is explicitly marked as a candidate; its canonical label is an analyst label for the source's single plate, not an author-issued build number.

## Diller / Siebert / Winkler, FFEMS2024

Primary article DOI [10.1111/ffe.14375](https://onlinelibrary.wiley.com/doi/10.1111/ffe.14375). Author-deposited raw [Zenodo21105346](https://zenodo.org/records/21105346), DOI10.5281/zenodo.21105346, published1July2026. Metadata explicitly grants CC BY4.0. The complete fatigue table is in the2099-byte `read me.txt`; downloading the μCT volumes is unnecessary. The external TUM DataTagger link redirected to `/login`; no authentication or access workaround was attempted.

The open [Diller dissertation](https://mediatum.ub.tum.de/doc/1739096/1739096.pdf), PDF pages134–135, reproduces article pages3394–3395. Visual checks confirmed the Methods, Table1 and specimen drawing. The machine is EOSM280; OerlikonMetco316L powder;250W,1500mm/s,100μm hatch,40μm layers. The tests use R0.1 and an Instron8800. ASTM E466 is cited for specimen geometry. The manuscript does not explicitly state the controller mode, cycling frequency, temperature or physical build count for this campaign. Repeated stress levels are consistent with constant-amplitude testing but are not an explicit control-mode statement.

The second README table is explicitly **stress range**, so Sa=Δσ/2 and σmax=Δσ/(1−R). Its30 as-built records have eight levels200,225,250,275,300,325,350,375MPa. A29-row subset excludes μ15. No runout is indicated in that table; the first table explicitly identifies four stops without failure.

Material conflicts retained rather than silently corrected:

1. README table1 contains **14** tested specimens, while Methods say13 polished specimens. The earlier handoff count43 was wrong;44 is the checked raw total.
2. Table1 uses an ambiguous `Load-Level-in-MPa` header. Its scans4,7,16 list350MPa, although Methods describe the polished tests at450MPa. All14 table1 records are excluded from the secondary stress-normalized set.
3. README μ15 has200MPa stress range and2,519,896cycles. Article §3.4, PDFp142/article3402, identifies a specimen with exactly2,519,896cycles at300MPa. μ15 is excluded. Neither source is overwritten.
4. Forty-eight manufactured specimens in Methods is not a statement of one physical build, nor a batch identifier. No filename or scan-number prefix is converted into a build ID.

The new2024 article is not a new laboratory relative to every historical FatigueData author: Diller also appears in2022 DOI10.1016/j.matchar.2022.112153. The2022 experiment is strain-controlled R−1, with36 fatigue specimens and different parameter sets/geometry, while this new campaign uses R0.1, different processing and a distinct specimen geometry. The current evidence supports a new experimental campaign rather than numerical reuse, but does not identify its build membership.

## Tomaszewski, Zenodo7650061

Author [Zenodo7650061](https://zenodo.org/records/7650061), DOI10.5281/zenodo.7650061, published21February2023, grants CC BY4.0. `Data.xlsx` is21603bytes. Its sole sheet gives actual specimen IDs,316L/AlSi10Mg material, build direction W or L, dimensions, σmax, σmin, R, cycles, runout field and defect note. Only137316L rows were normalized. No IDs are duplicated. AlSi10Mg was kept in the original workbook and not normalized into this task.

The raw workbook explicitly states uniaxial sinusoidal stress control, average10Hz, Instron8874, laboratory environment and macrocrack failure criterion. Every137316L row has a nonempty cycles-to-failure value and a blank Runout field. These are represented as events, with that interpretation recorded per row. σmin/σmax exactly equals R for all rows. For the40 R0.01 tests, σmax450, σmin4.5 and **Sa222.75MPa**. These40 rows are four geometry conditions with only one stress level each and therefore cannot compare stress-level selection policies within condition.

The related author papers are:

- [107378 open author manuscript](https://dlibra.pbs.edu.pl/Content/5098/Tomaszewski_Modelling_of_critical.pdf), DOI10.1016/j.ijfatigue.2022.107378. PDFp6 §2.1 says: “All specimens were manufactured on a single build plate”. PDFp7 §2.2 repeats the single-plate statement. Table2 onp8 specifies A02n9,A08n9,A32n10. The source also states load control and R−1. The build-direction drawing onp8 points across specimen width, consistent with raw W.
- [108225 open author manuscript](https://dlibra.pbs.edu.pl/Content/5100), DOI10.1016/j.ijfatigue.2024.108225. This provides individually named L00/L05/L20/L50 specimens and40 experimental lives atσmax450,R0.01. The estimated R−1 fatigue-strength column in its Table3 is a model output and must not be imported as experimental S–N data.

Both papers describe SLM125HL,200W,800mm/s,120μm hatch,30μm layers and no heat treatment. Both state20Hz, conflicting with the workbook's10Hz. The raw137 cannot be certified to the2023 single plate: its W/R−1 groups contain15,13,9 specimens, not10,9,9. The workbook additionally contains60 L/R−1 records and40 variable-length R0.01 records. The spreadsheet does not identify which28 records fall under the2023 paper. Assigning all137 or all37 W/R−1 rows to that plate would overstate the evidence.

The nine SS_A02W records are the narrowest candidate because the unique W/A02/R−1 condition, geometry, count9 and plotted population agree. A direct source crosswalk is still absent. No first9/first10 ID selection was made to force the other groups to fit their paper counts. The source's named2024 fatigue rows also show a potential one-record cycle discrepancy in the length5 condition (raw217394 versus paper214122); the complete author workbook is retained unchanged for follow-up.

## Independence and reuse screen

The machine-readable `independence_audit.json` records the screen. Against v2strict309, neither new article DOI nor exact four-parameter processing tuple matches. No Tomaszewski author appears in all618 FatigueData-AM2022 article metadata. Diller appears in two older sources, including the different strain-control316L experiment described above. Source DOI matching does not by itself certify physical independence.

At matched R, within1% Sa and0.02log10N, the181 candidates have23 near-coordinate pairs with strict309 (Diller2,Tomaszewski21), and zero with Trombley129. These mostly lie on common250/300/350/400MPa grids; they are recorded for sensitivity, not treated as proof of duplication. Exact processing tuples for Tomaszewski occur elsewhere in the broader FatigueData collection: maraging steel, high-temperature strain-control316L and a Finnish flexural-bending/shot-peening campaign. These are different named sources and methods. None is in strict309.

Tomaszewski versus Kedziora2022 was checked explicitly: disjoint authors/institutions; SLM125HL versus EOSM290/RenishawAM400; R−1/.01 versus.1;30 versus40μm layers. They are inconsistent with one physical campaign. Diller's two near-coordinate pairs with Kedziora also have different machine/process/surface and test-frequency reporting. Trombley uses CLM2 at370W900mm/s25μm,20kHzR−1 and different named specimens, with zero coordinate pairs. No physical specimen/build overlap was identified, but missing batch maps remain the decisive gate failure.

## Additional primary-repository screen and rejections

`search_log.json` lists queries and results. Besides the two acquisitions, the search covered NCAME/Auburn publications, Mendeley, NIST, AMBench/MDF, Zenodo and Figshare-related listings. Rejections are not claims of exhaustive absence.

| Primary candidate | Decision |
|---|---|
| Mendeley9yykp4dt26.1,2026 load–displacement316L | Quasi-static displacement control, not fatigue. |
| Mendeleyh97k6w9vm5.1,2026 Yin etal | Explicit laser-wireDED and rotating-beam fatigue. Outside current LPBF/axial scope. |
| Zenodo12515773 / Bartošák | Previously screened multiaxial strain-controlLCF. No duplicate acquisition. |
| Mendeley83wh6zdpz9.1 | Previously screened550–750°C strain-controlTMF. |
| Zenodo14763342 | EarlyLCF/microstructure,407.5MB. Not downloaded solely for current stress-life scope. |
| Zenodo10784608 | EBSD deformation-state data, not a new S–N campaign. |
| Zenodo10477561 | Authors explicitly reanalyse published fatigue tests, not original campaign data. |
| Zenodo6653187 | Merot previously acquired; stepped loading, excluded. |
| Mendeley87hm5hwbpk | Previous bending/defect dataset, not new axial fatigue records. |
| NIST maraging fatigue/DIC record927278 | Different alloy/beam experiment, secondary scope only. |
| NIST AM fatigue program | Program page found, no suitable row-level316L specimen/build campaign identified in this pass. |
| MDF/Peregrine316L builds | Rich build identity/in-situ/tensile data, no matching public fatigue outcomes identified. |
| Zenodo17610107 /17610325 | Lattice and four-point bending, outside axial coupon scope. |
| LH2CRAFT Zenodo21493116 | Cryogenic/wrought focus and embargo; no access attempt. |
| Tian2024 DOI10.1016/j.engfracmech.2024.109942 | Potential axialHCF paper; no raw specimen/build crosswalk retrieved in this pass. |

Source bytes, metadata, source URLs, licensing and SHA256 hashes are retained locally. No paid content, private login, author contact or upload was used.
