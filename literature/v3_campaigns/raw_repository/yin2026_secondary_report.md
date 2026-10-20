# Yin2026 follow-up: outside primary scope, physical build mapping still absent

[Mendeley h97k6w9vm5.1](https://data.mendeley.com/datasets/h97k6w9vm5/1), published15October2026, provides author data under CC BY4.0. This is **laser-wireDED316L with rotating-beam fatigue**, therefore outside the LPBF/axial question. No data from this acquisition were pooled or fitted.

The public UI's anonymous files API supplied two files. Both were acquired and their SHA256 values exactly match the repository checksums:

- `Ar_vs_N2_JMP_Final.jmp`,229052bytes, `0c3608512a34f0cb4013b8e7f377bb1a832a5cd5b8287c58353894acaef82eaf`.
- `DED CycPol Curves_Summary_Submit.xlsx`,22084992bytes, `6d760fbf17cd688eb1bb242501f16ba4747558d477817dea2b1576130804bdbc`.

The JMP file has231rows and47columns. It mixes original campaigns and previously published LPBF/wrought/ASME data. Its Source column explicitly names Shrestha2021, Leuders2014, Blinn2021, Mower2016 and others. Those rows must not be interpreted as new independent data or imported wholesale.

The named APL_FY24 and APL_FY23 source groups give18actual specimen labels: FY24_A_1–6, FY24_N_1–6, A_01–03,N_01–03. Gas is separately reported per row as Argon or Nitrogen; it is not inferred from A/N prefixes. Machine=Meltio, orientation=Horizontal, method=RBF,R=−1,frequency100Hz are explicit. Four FY24 records lack both stress and cycles. Fourteen records have complete fatigue outcomes:11failures and3runouts. The three runouts stopped at5,000,000cycles.

Two clean CSVs retain these18named rows and14complete rows, respectively. The MPa/ksi conversion agrees within5.7e−14MPa. R−1 permits the nominal bending maximum stress to be represented as its amplitude, with the interpretation recorded. The author's many scaled-RBF and converted-R columns are not newly observed tests and were not normalized as experimental outcomes.

The data support specimen→gas and specimen→author source-year labels. **They do not support specimen→physical build/wall/lot identity.** No Build ID, Wall ID or Lot field occurs among the47columns. Source-year and gas conditions are not promoted to build IDs. The corrosion workbook's13sheet names identify Ar/N2/wrought tests and electrochemical curves; they add no fatigue specimen-to-build crosswalk in this inspection. No related experimental article or build-layout evidence is linked in the repository landing metadata.

The JMP reader is the MIT-licensed open source `martyblaber/jmpio-python` at commit5e9d49f. It required a local NumPy2 offset-scalar cast fix; the pristine source ZIP and patch explanation are retained. The table's embedded JMP scripts were read as metadata and never executed. Numerical/identity crosschecks, parser version, row counts and missingness are in `yin2026_extraction_receipt.json`. This is a useful next mapping request, not a new qualified independent campaign.
