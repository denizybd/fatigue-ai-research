# Bartošák 108608: primary-source identity and timing pass

The [official EAN2025 follow-on paper](http://www.experimentalni-mechanika.cz/cs/konference/konference/2025.html?download=3105%3A21) was acquired as a six-page PDF. Page 2 identifies the same 20 SS316L specimens (7 axial, 8 torsional, 5 proportional); page 6 cites the exact [108608 publication](https://doi.org/10.1016/j.ijfatigue.2024.108608).

Two useful uncertainties are resolved. CT defect acquisition occurred **before fatigue testing** (page 2). Conversely, SWT stress×strain is evaluated **at Nf/2** (page 4, Eq. 9). The 20 SWT values are therefore cyclic-state inputs rather than free prescribed pretest stress amplitudes. This is a prediction-time distinction, not an allegation that the authors' conditional fatigue model is wrong. The projected-area plane also needs consistent definition in any future pretest protocol.

The Zenodo packet remains one ZIP containing a workbook and readme. Its 21 visible sheets have no hidden sheets, comments or defined-name crosswalks. Author labels 1–20 link life records to 200 defect measurements. Physical build and powder lot mappings remain unverified; no one-build assumption was made. Temperature, strain ratio and frequency remain blank. These data remain **strain-controlled multiaxial LCF**, with no force-controlled HCF classification.

The journal paper/SSRN full methods were not retrieved through normal public access. The six-page follow-on defers manufacturing details to 108608. Exact access outcomes and minimum missing crosswalk fields are in `evidence_ledger.json`.

`specimen20_evidence_annotated.csv` and `defects200_pretest_CT_evidence.csv` preserve original numbers and add these source-backed annotations. They add **zero new experiments, zero gold build-qualified records and zero fits**. Dataset license: CC BY 4.0; the separate conference PDF has no recovered explicit reuse license.
