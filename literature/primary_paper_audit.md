# Primary-paper audit: Centola et al., Engineering Failure Analysis 168, 109081

Audit date: 2026-10-20. DOI: [10.1016/j.engfailanal.2024.109081](https://doi.org/10.1016/j.engfailanal.2024.109081). Authors: Alessio Centola, Alberto Ciampaglia, Davide Salvatore Paolino, Andrea Tridello. Article issue year 2025; first online 19 November 2024 (PDF p1). The local supplied version has 23 PDF pages, whose printed page numbers agree with PDF page numbers.

Evidence inspected: all 23 pages extracted using pypdf, with visual inspection of rendered pp4, 5, 7, 13. Original PDF and extraction provenance are recorded in `primary_audit/provenance.json`; per-page text and selected page PNGs are retained there. Text extraction cannot resolve equation signs reliably; the censoring likelihood and Fig.8 interpretation below were visually verified.

Institutional record: [PoliTO IRIS](https://iris.polito.it/handle/11583/2994912). Public institutional PDF URL located by search: [version of record](https://iris.polito.it/retrieve/handle/11583/2994912/913485). Crossref metadata was downloaded to `primary_audit/crossref.txt`. No publisher full-text/supplement HTML was acquired through web fetch (403); the local full text is the main evidence.

## Main judgment

This is a useful, technically motivated probabilistic fatigue framework, with an explicit right-censoring treatment and a clear attempt to separate experimental scatter, finite-experiment uncertainty, and ML weight uncertainty. A study-wise generalization/calibration audit would extend its evidence, not correct an established failure of its implementation. The publication already discusses unseen manufacturing conditions, weight uncertainty outside training ranges, and uncertainty-guided selection of new experiments. Those ideas alone are not a new contribution.

The strongest bounded opportunity is to test whether lower-life recommendations remain conservative for genuinely unseen source publications, using raw failure/runout observations and a censor-aware evaluation. Neither visual fit to estimated R90C90 curves nor overlap of training/test loss curves establishes that property.

## Claim/evidence register

| Claim or issue | Exact evidence | Classification and interpretation |
|---|---|---|
| 518 observations, 51 condition datasets, 17 source articles | Sec.2.1, p4; Table1 p5 | Verified reported data composition. Observation rows are not present in the table. |
| Original550 records, 32 outliers removed | Sec.4, p9 | Verified exclusion count. Criteria, row IDs, source distribution, timing relative to data split, and sensitivity without exclusion are not reported in the inspected text. This is a reproducibility gap, not evidence the removals were wrong. |
| Source data include runouts | Sec.2.1 pp3–4 defines runout flag0=failure,1=runout | Verified; do not claim runouts are treated as failures. |
| Likelihood handles right censoring | Sec.2.2 p4 Eq.2; Sec.3.2 p7 Eq.4 | Failure contribution is log normal density in log10-life; runout contribution is log survival probability. Verified visually. This is a strong feature. |
| Statistical model | Sec.2.2 p4 Eq.1 | log10(N) conditionally normal, mean m*log10(Sa)+q, condition-level constant sigma. Fits HCF Basquin shape, with within-condition homoscedasticity as an explicit modeling assumption. |
| Load-ratio conversion | Sec.2.1 p3 | Smith–Watson–Topper equivalent fully reversed amplitude: Smax*sqrt(0.5*(1−R)). The resulting equivalent Sa, not unconverted Smax, must be used in a comparable reimplementation. |
| Size effect | Sec.2.1 p3 | Vrisk is material volume exposed to at least90% nominal stress; computed from geometry/loading configuration. Lack of this field in an open dataset limits comparability. |
| Input selection | Sec.2.1 p3; Sec.3.1 p6; Table1 p5 | Requires P,v,t,h,orientation and treatment metadata. Machine/powder variables omitted because too sparsely reported. This is an expressly acknowledged limitation, not a hidden error. |
| Treatment defaults | Sec.2.1 p4 | For no heat treatment, T=20°C and duration0 are deliberate encoding conventions. These should not be confused with measured thermal data. |
| Lifetime domain | Sec.2.1 p3 | Focus below1e7 cycles; VHCF not explicitly modeled because sparse data. Statements that framework could extend to VHCF are prospective, not validation. |
| FFNN targets and split | Sec.3.1 p6 | 18 inputs ->100/75/50 ReLU ->m,q,sigma;51 curve-level target rows; random46 training/5 testing condition datasets. Thus FFNN testing is not random observation splitting. |
| Normalization | Sec.3.1 p6 | z-score mean/SD computed on training subset explicitly. No basis to allege global standardization leakage. |
| PINN split options | Sec.3.2 p7 | Describes random observation holdout and full-condition-dataset holdout, calling latter more severe. Sec.4.1 p9 and Fig.5 identify condition15 and48 as test datasets. Exact full split memberships/seeds are absent. |
| BNN targets | Sec.2.3 p4 Eq.3; Sec.3.3 p8; Table3 p14 | BNN target is the estimated Owen R90C90 life at a stress level, not the observed raw failure time. It learns a surrogate of statistically estimated condition-level design curves. |
| BNN architecture | Sec.3.3 pp7–8, Fig.3 p8 | 19 feature inputs including stress ->100/75/50 ReLU deterministic layers; stress concatenated again before a single variational linear output. Prior standard multivariate normal; posterior full-covariance multivariate normal. Only output layer variational in shown model. |
| BNN implementation reporting | Sec.3.3 pp7–8 | TensorFlow/TFP named;1500epochs, lr.001,batch30 reported. Exact KL scale, optimizer details/version, output loss/likelihood implementation, priors in code, normalization of targets, seeds/split IDs are not recoverable from inspected prose alone. |
| BNN Monte Carlo inference | Sec.4.1 p13 | 100 forward draws per stress level. These generate uncertainty over the estimated design-curve prediction; the band is not automatically an individual-specimen prediction interval. |
| C90 selection | Sec.4.1 p13 and Fig.8 | Uses the lower10th ordered BNN curve among100 draws (roughly a pointwise lower posterior10% quantile). Does not report repeated-sampling validation of nominal90% confidence or a simultaneous-band construction. |
| R90C90 meaning | Sec.2.3 p4 Eq.3 | R90 is10th percentile life; C90 is a finite-experimental-data confidence adjustment. BNN weight uncertainty adds another layer over that estimated experimental limit. These are not interchangeable90% coverages. |
| Primary empirical comparison | Table2 p11; Figs.5–8 | Condition-specific likelihood/curve plots plus overall likelihood sum. Table2 total sums all51 datasets and therefore contains training contributions; it is not a held-out-only metric. |
| FFNN overfitting | Sec.4 pp8–9, Fig.4 | Acknowledged test-loss divergence after about50epochs; default1000epochs retained for sufficient accuracy. Honest reported weakness. |
| PINN broadening under sparse data | Sec.4.1 pp9–12, Fig.6 | Authors explicitly observe sigma increases where feature support is sparse and slope/intercept can be wrong. Clear limitation and motivation for BNN, already identified by authors. |
| Generalization claim | Sec.4 pp8–9 | Similar loss curves and selected held-out-condition fit support the shown experiments. They do not, by themselves, establish generalization to new publications, factories, machines, or calibrated risk under arbitrary shift. |
| Data/code availability | p22 | Data on request. No public code repository or standalone supplementary-data section is named in the local PDF. Narrow repository search found no repository (details below); absence in that search does not prove no code exists anywhere. |
| Active experiment selection | Conclusions p20 | Already proposes using confidence bands to choose new manufacturing conditions for experiments. Adding active learning in name alone is not novel. |

## A verified internal reporting inconsistency

Table1 p5 lists scan speed2400mm/s for condition46 (Solberg et al., ref41). Sec.4.2.1 p14 states the training scan-speed extrema are420–1200mm/s. The machine-readable Table1 transcription yields425–2400mm/s. Both table and prose were read directly; Table1 was visually checked.

This is a verified disagreement in reported ranges. It does **not** determine whether the underlying training row, the table, or the prose contains the error. Do not silently replace2400 with1200. Ask for the raw value and source geometry/process table; evaluate support distances with documented source values. This matters when a curve's dashed portion is described as outside the training domain. No demonstrated effect size or model failure follows from this discrepancy alone.

The encoded18-feature table has identical represented-feature pairs32/33 and40/41. This can reflect loading modes, surface detail, batches or other variables omitted from the representation. It is not proof of duplicate specimens. Keep such conditions together in a sensitivity grouping; ask the authors to identify their difference.

Transcriptions and computational checks: `primary_audit/table1_conditions.csv` and `primary_audit/table1_audit.json`.

## Split and derived-target leakage: what is and is not established

1. The FFNN split is by condition dataset. A criticism claiming that all models used only a random row split would be false.
2. Condition holdout does not imply publication holdout. Table1 source ref32 supplies six conditions15–20. The five-condition FFNN test split includes condition15 (p9). With only five test conditions, at least one of those six same-publication conditions must be in training. This logical deduction establishes source sharing for that displayed FFNN test case under the reported split, not an invalid split for the authors' stated condition-generalization question.
3. PINN text permits both split types, and figures label entire datasets as testing. Actual code/membership is needed to identify the exact experiments.
4. BNN labels come from condition-level fitted curves, and Table3 calls them518 labels. If those curves are estimated on all raw points before a subsequent observation split, test information enters related training labels. The paper does not supply enough operational detail to decide whether that occurred. Record this as a **target-construction leakage risk**, not a proved implementation error.
5. Full source holdout, followed by target fitting strictly inside training sources, prevents the above route. Evaluating against raw held-out failures/runouts avoids treating a curve estimated from those same test points as independently measured truth.
6. Closely related publications may share specimens. DOI grouping is necessary but not sufficient; manual source-family/specimen audits are required.

## What a reproduction can reasonably claim

Without original raw518 records, removed32 IDs, runout flags and curve-generation code, an exact numerical reproduction is unavailable. An open-data implementation can be a related-method evaluation or approximate reimplementation, with explicit differences in feature coverage, censoring, loading/risk-volume representation and training protocol.

The closest simple baseline is lognormal accelerated-life Basquin regression with observed-failure density and runout-survival contributions. A small neural model with the same survival likelihood is closer to PINN-L's statistical objective than an off-the-shelf squared-error regression treating runouts as failures. An ensemble is not the paper's BNN and must be labeled accordingly.

## Source-publication map for overlap audit

`primary_audit/source_publications.csv` records exact Table1 condition membership and DOIs. A DOI match in FatigueData-AM2022 establishes source overlap, not row identity. Publication overlap prevents declaring the open database an independent external validation of the original paper without specimen-level reconciliation.

| Ref | Condition codes | DOI |
|---|---|---|
|27|0–2|10.1108/13552541311302932|
|28|3–7|10.1016/j.addma.2019.04.011|
|29|8–9|10.1002/adem.202200751|
|30|10–13|10.1007/s40964-021-00164-8|
|31|14|10.1016/j.actamat.2020.08.033|
|32|15–20|10.1016/j.cirpj.2022.07.007|
|33|21–27|10.1016/j.ijfatigue.2020.106063|
|34|28|10.1016/j.ijfatigue.2021.106207|
|35|29–33|10.1016/j.ijfatigue.2022.106843|
|36|34–35|10.1016/j.ijfatigue.2022.106946|
|37|36–39|10.1016/j.ijfatigue.2022.107025|
|38|40–41|10.1016/j.jmst.2019.08.047|
|39|42–44|10.1016/j.jmst.2021.10.006|
|40|45|10.1016/j.mechmat.2021.103951|
|41|46|10.1111/ffe.13077|
|42|47–49|10.1016/j.procir.2016.11.138|
|43|50|10.3390/ma13153293|

## Narrow code/supplement search log

On2026-10-20 searched the exact article title with code/data/supplementary terms; searched PII S1350630724011270 with supplementary; searched Centola+SS316L+github. The institutional record and article PDF were found; no linked source code was identified in the inspected material. GitHub public repository API query `Centola fatigue` returned0 repositories (`primary_audit/github_repo_search.txt`). Crossref relation field empty; its links point to publisher text-mining endpoints, not code. This is a bounded search, not an exhaustive claim of nonexistence. Publisher/IRIS HTML direct fetch returned403 in this audit, so an uninspected publisher attachment cannot be ruled out.

## Concrete author questions

- Could you share original550 rows and final518 rows, runout definitions, source/condition/specimen IDs, exclusions and units?
- What distinguishes Table1 conditions32/33 and40/41? Is condition46 scan speed2400mm/s correct despite the1200mm/s maximum stated in Sec.4.2.1?
- Which exact conditions/points were held out for each shown model, and were random seeds reused across models?
- Were m,q,sigma/Owen labels estimated before or after the train/test division? How was k_Owen evaluated, including censored data and effective sample size?
- Could the TensorFlow/TFP environment, loss, KL scaling, optimizer, normalization, learned parameters and inference code be provided?
- Have you already evaluated leave-publication-out lower-life violations and censor-aware calibration? That determines the incremental value of a proposed audit.

These are draft research questions only; no communication was sent.
