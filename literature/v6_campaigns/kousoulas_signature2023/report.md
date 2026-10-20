# Actual public example fatigue trace, distinct from a life cohort

Mendeley DOI10.17632/9xpx3wt82r.1 provides `fatigue data.xlsx` (22,005bytes) and an R segmentation/regression script (2,197bytes) under CC BY4.0. Both actual files were downloaded by normal public GET, and their SHA256 values match the official API metadata. The worksheet has330 numeric cycle/frequency/machine-power rows, one visible sheet, no named ranges, and no sample/build/stress/lot identifier. ColumnsD:H are formatting-only. The source landing page calls this data from a fatigue test; it does not identify which physical coupon or any printed life-table entry.

The normalized CSV preserves all330 timestamps. These are **not330 fatigue tests or an additional exact S–N life observation**. The last observed cycle is not silently labelled failure. The R script was read, not executed; no regression or predictive fit was run.

The process-signature paper is DOI10.1007/s11668-023-01741-5. Its primary publisher preview is public but full text is subscription content. No paid access was attempted. A third-party search result used an ambiguous withdrawal tag; the primary Springer page identifies an original research article without a withdrawal/retraction notice, so no retraction allegation is made.

A legitimate public21-page derivative manuscript was acquired from `https://arxiv.org/pdf/2510.21018` (SHA256`ff9c8c0567e5c0ce4b7f7d1a593188e729e2ce59f6a790f9bdfe49fb0682aef1`), corresponding to DOI10.1115/1.4071939. It is primary author material, not the2025 scattering paper. Section2.1/PDF5 explicitly describes four LPBF blocks with identical parameters, whose coupons are treated as comparable. It does not supply a coupon-to-block/lot table. That four-block statement is not retroactively assigned to the14 anonymous2025 life entries.

Sections3–4.3/PDF6–10 describe resonant fully reversed bending,2Hz failure criterion and10million-cycle runout, plus cycle/frequency data and postfracture defect size. The latter is not a free pretest covariate. The paper explicitly lacks directly measured crack-size ground truth for its physics-informed proof of concept. It is an adjacent method source, not an independent experimental validation of our life-bound/acquisition objective. Dataset identifiers in its plots are not physical build IDs. Its manuscript license is not assumed from the separate Mendeley CC license.

All linked Kousoulas/Guo experiments and derivative papers stay one conservative family until physical reuse is resolved. No new primary RT axial campaign or model admission is claimed.
