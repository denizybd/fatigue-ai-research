# Literature and novelty audit: publication-shift reliability of AM fatigue models

Audit date/cutoff: 2026-10-20. This is a targeted, primary-source search, not a systematic or exhaustive review. It supports selecting experiments; it does not establish a globally unique research gap. No contact was made with authors, and no local data were uploaded.

## Decision

The broad ideas **group-wise evaluation**, **conformal fatigue uncertainty**, **Bayesian/physics-guided fatigue prediction**, **cross-alloy transfer**, and **uncertainty-based rejection** are already established. Random-versus-group R-squared comparison on FatigueData-AM2022 is especially close to existing work. The defensible contribution candidate is narrower:

> A provenance-preserving, publication-held-out audit of one-sided fatigue-life decisions in AM SS316L, retaining runouts as censored outcomes and measuring whether a prespecified data-support/uncertainty rejection rule reduces identifiable dangerous overprediction at matched decision availability.

This is an empirical reliability study and possible benchmark contribution. Its value depends on the actual number of independent sources, fidelity of provenance, robustness to related-publication grouping, and the size/consistency of the result. A new algorithm or finite-sample guarantee under arbitrary process shift is not claimed.

## Closest verified prior work

### 1. Wu et al.: random, group, and cross-family evaluations already exist

**Zicheng Wu, Yi Zhou, Ninian Sing Kok Ho, John Hock Lye Pang.** “Machine learning for fatigue life prediction of additively manufactured alloys: Quantifying predictive gain over physics baselines.” *International Journal of Fatigue* 214, 109943, issue dated January 2027. [DOI](https://doi.org/10.1016/j.ijfatigue.2026.109943), [publisher](https://www.sciencedirect.com/science/article/pii/S0142112326004640).

Evidence inspected: publisher abstract, highlights, section snippets and Crossref metadata. Full text was not obtained; direct publisher/API requests failed. Crossref DOI creation is 2026-08-22; no exact online publication date was verified. Thus retain the 2027 issue date and the access date, rather than inventing an online date. Publicly retrievable metadata must nevertheless be considered in a current novelty assessment.

The publisher describes 12,518 S-N failure points from 96 alloy designations, three splitting strategies, four ML models and three tiers of physics baselines. Its conclusions explicitly attribute inflated random-split performance to within-curve leakage, and report weaker gain within a single alloy and poor cross-family extrapolation. Source code is described as request-only. **Precludes:** presenting group splitting, leakage inflation, or single-alloy ML versus physics comparison alone as new. **Remaining candidate:** one-sided censored risk and selective decisions across independent publications; whether this is absent from its full text remains unverified.

### 2. Di Maggio et al.: entire fatigue dataset IDs were already withheld

**Luigi Gianpio Di Maggio, Chiara Gastaldi, Danilo Antonello Renzo, Cristiana Delprete, Franco Furgiuele.** “A robust methodology for dataset preparation and algorithm performance assessment in machine learning prediction of the fatigue life of additive manufactured components.” *Engineering with Computers* 41, 2937–2952 (2025), online 18 April 2025. [Full publisher text and DOI](https://doi.org/10.1007/s00366-025-02139-7).

Evidence inspected: full publisher HTML, especially Sections 2.1, 2.2 and 3.2. It prepares FatigueData-AM2022-derived metadata, predicts alternating stress from cycle count and other features, and evaluates entire S-N datasets identified by an ID not used in training. The grouped task is distinct from its ordinary five-fold assessment. An experiment-group ID need not be a publication ID or a specimen identity. **Precludes:** claiming the first withheld-curve evaluation on this public database. **Remaining candidate:** publication/related-study blocks, directional reliability and censoring. The paper's engineering reasoning and explicit whole-curve tests are strengths; it should not be reduced to an example of leakage.

### 3. Boruah: conformal fatigue intervals and local undercoverage already studied

**Irene Boruah.** “Distribution-Free Conformal Prediction for Steel Fatigue Strength: Marginal Validity Is Not Enough.” [arXiv:2608.07589](https://arxiv.org/abs/2608.07589), v1 5 August 2026, v2 14 August 2026. **Preprint**, not a verified journal acceptance.

Evidence inspected: full v1 HTML, current abstract and v2 change log. It uses the NIMS steel fatigue-strength dataset, multiple random train/calibration/test splits, and compares aggregate with predicted-strength-quartile interval coverage. The revised abstract adds Mondrian and conformal quantile methods. Its locally adaptive interval construction addresses heteroscedasticity. **Precludes:** “first conformal fatigue model,” “marginal coverage can conceal local undercoverage,” or normalized conformal scoring alone as novelty. **Difference:** conventional steel fatigue strength versus AM censored life; random rows versus unseen publications. Report results from a named version, since v1 and v2 numbers differ. The v1 PDF header naming a journal is not evidence of acceptance.

### 4. Kookalani et al.: lower-bound fatigue design and held-out steel grades

**Soheila Kookalani, Ioannis Brilakis, Hongchen Liu, Zhiqi Hu, Hamidreza Alavi, Jose Luis Chavez-Torres.** “From Explainable Predictions to Reliability-Aware Design: Interpretable Machine Learning for the Fatigue Strength of Steels.” [SSRN/DOI](https://doi.org/10.2139/ssrn.7385361), 2026 preprint; Crossref DOI creation 1 September 2026.

Evidence inspected: author-posted SSRN abstract and Crossref metadata; full manuscript not obtained. The abstract describes regime-conditional conformal intervals, leave-one-grade-out evaluation, and optimizing a lower fatigue-strength bound. **Precludes:** claiming that combining lower-bound design and grouped extrapolation is in itself new. **Remaining candidate:** AM process/source shift and the handling/identifiability of runouts. Do not borrow its advertised guarantees without checking their precise conditioning and selection assumptions.

### 5. Li: conformal prediction has already been proposed for AM fatigue

**Jun Li (presenter, Virginia Tech).** “Multi-Fidelity Machine Learning With Uncertainty Quantification for Probabilistic Fatigue Crack Growth of Additively Manufactured Alloys.” Official ASME SSDM2026, June 8–10, 2026, submission 182979. [Official abstract](https://ssdm.secure-platform.com/a/solicitations/269/sessiongallery/23090/application/182979).

Evidence inspected: complete official conference abstract. It proposes a multi-fidelity physics-informed model and conformal intervals for probabilistic fatigue crack growth/life with defect and loading uncertainty. Only the abstract was verified; no DOI, complete author list, full paper, data or code was established. **Precludes:** presenting conformal wrapping of an AM fatigue model as a first application. **Difference:** crack-growth/multi-fidelity modelling versus publication-held-out one-sided decision auditing. The abstract's word “provably” is an author claim; assumptions were unavailable for audit.

### 6. Ahn et al.: retrospective runout features are explicitly separated from deployment

**Hyoju Ahn, Jongwon Lee, Saurabh Tiwari, Nokeun Park.** “Physics-Informed Machine Learning Framework for Fatigue Life Prediction of Additively Manufactured Alloys.” *Applied Sciences* 16(13), 6493, 29 June 2026. [Publisher and DOI](https://doi.org/10.3390/app16136493).

Evidence inspected: publisher full-text passages available through search, including database, ablations and limitations; a raw HTML copy was not obtained. It uses a complete-case FatigueData-AM subset and physics-derived descriptors. It explicitly calls a runout indicator a post-test variable and recommends no-runout configurations for prospective prediction. It also explicitly lacks an independent external dataset and calibrated probabilistic intervals. **Lesson:** using runout as a prospective feature is leakage; using its status in censored likelihood/evaluation is appropriate. **Precludes:** announcing its stated runout limitation as an undiscovered flaw. Cross-validation standard deviation is not an individual-life predictive interval.

### 7. Tognan et al.: Bayesian defect-based probabilistic design predates this project

**Alessandro Tognan, Andrea Patanè, Luca Laurenti, Enrico Salvati.** “A Bayesian defect-based physics-guided neural network model for probabilistic fatigue endurance limit evaluation.” *Computer Methods in Applied Mechanics and Engineering* 418, 116521 (2024). [DOI](https://doi.org/10.1016/j.cma.2023.116521), [official institutional full text](https://research.tudelft.nl/files/162350630/1_s2.0_S004578252300645X_main.pdf).

Evidence inspected: publisher abstract/highlights/data statement and institutional PDF title/abstract. It puts El Haddad physics into a Bayesian neural model for defect-related failure probability and uses Bayesian model selection. **Precludes:** physics-guided BNN fatigue reliability as novelty. **Difference:** endurance/failure probability versus cross-publication censored life audit. Detailed validation or implementation quality was not audited here.

## Statistical foundations and constraints

### Censored survival conformal prediction

**Emmanuel Candès, Lihua Lei, Zhimei Ren.** “Conformalized survival analysis.” *JRSS B* 85(1), 24–45, published 28 January 2023. [DOI](https://doi.org/10.1093/jrsssb/qkac004), [full manuscript](https://arxiv.org/html/2103.09763).

Evidence inspected: full manuscript sections on Type I censoring, independent censoring, naïve bounds, and censoring cutoffs. It constructs covariate-dependent lower predictive survival bounds; finite-sample and approximate guarantees depend on the setting. Simply calibrating a lower bound on min(T,C) can be conservative under exchangeability, but is not equivalent to learning the lifetime distribution. More efficient censoring-adjusted methods require additional assumptions. **Constraint:** this theorem does not grant reliable coverage on arbitrary new publications or process regimes. Omitting runouts and reporting failure-only coverage changes the estimand.

### Hierarchical prediction is already a methods literature

**Yonghoon Lee, Rina Foygel Barber, Rebecca Willett.** “Distribution-free inference with hierarchical data.” Preprint first posted 10 June 2023; journal metadata published online 19 March 2026. [DOI](https://doi.org/10.1145/3786352), [arXiv](https://arxiv.org/abs/2306.06342), [authors' code](https://github.com/rebeccawillett/distribution-free-inference-with-hierarchical-data).

Evidence inspected: full arXiv v2 HTML, latest version metadata, journal Crossref metadata and official code README. It treats observations clustered in groups and derives conformal constructions under hierarchical exchangeability. A new group and a new observation within an existing group are different prediction tasks. **Constraint:** a cluster-weighted or source-max conformal construction is not a new method merely because applied to papers. Source exchangeability is itself questionable for a deliberately novel manufacturing process. Report calibration source counts separately from row counts and specify the sampling target (uniform source then uniform specimen, or pooled specimen).

### Distribution shift erodes guarantees

**Rina Foygel Barber, Emmanuel J. Candès, Aaditya Ramdas, Ryan J. Tibshirani.** “Conformal prediction beyond exchangeability.” *Annals of Statistics* 51(2), 816–845 (2023). [DOI](https://doi.org/10.1214/23-AOS2276), [full manuscript](https://arxiv.org/html/2202.13415).

Evidence inspected: full manuscript abstract, introductory setting and shift guarantees. It develops weighted quantiles/randomization and bounds coverage degradation under distribution drift. **Constraint:** weighted calibration is not a guarantee under unknown arbitrary changes in the conditional outcome distribution. Ordinary split conformal's row-exchangeability guarantee does not establish R90C90, source-conditional reliability, or selected-subset reliability. The present audit may compare methods empirically without asserting any of those guarantees.

### Rejection must be judged with availability

**Yonatan Geifman and Ran El-Yaniv.** “Selective Classification for Deep Neural Networks.” NeurIPS 2017. [Official proceedings](https://papers.nips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html), [authors' code](https://github.com/geifmany/selective_deep_learning).

**Yonatan Geifman and Ran El-Yaniv.** “SelectiveNet: A Deep Neural Network with an Integrated Reject Option.” 2019. [arXiv](https://arxiv.org/abs/1901.09192).

Evidence inspected: primary abstracts/proceedings and official code README. The risk-versus-coverage tradeoff and learned regression/classification rejection predate this project. **Constraint:** a rule that rejects everything or reports vanishing design life is not useful. Compare danger at the same accepted fraction and also compare the magnitude of accepted lower life bounds. Coverage of an interval and availability of a prediction are distinct quantities and should have distinct names in tables.

## Candidate hypotheses ranked before experiments

Scores 1–5 are project judgments, not validated measurements. Novelty means *potential specificity beyond the sources above*, not a claim of priority.

| Candidate | Specificity/novelty | Value to Tridello | Feasibility | Engineering meaning | Useful null result |
|---|---:|---:|---:|---:|---:|
| **Main:** frozen support-plus-uncertainty gate versus uncertainty-only and support-only gates, on one-sided censored publication-held-out decisions at matched availability | 3 | 5 | 4 | 5 | 5 |
| **Backup:** row/curve/source calibration levels and censored risk-identification bounds reveal when apparently reliable AM life predictions are not evaluable or not useful | 3 | 5 | 5 | 4 | 5 |
| Random row versus grouped R-squared on FatigueData-AM2022 | 1 | 3 | 5 | 3 | 2 |
| A larger BNN, transfer network, or ordinary conformal wrapper | 1 | 3 | 3 | 3 | 2 |
| Full topology optimization with predicted fatigue constraint | 1 | 4 | 2 | 4 | 3 |

**Main falsifiable formulation:** within an agreed SS316L/L-PBF population, a fixed combined score reduces source-balanced dangerous overprediction versus both component gates at prespecified availability levels, without obtaining the advantage solely through much lower accepted design lives. The protocol must define the score, training/calibration roles, danger threshold and effect-size criterion before test outcomes. A finding of no gain rejects the proposed combined gate; it does not invalidate all support-aware methods.

**Backup formulation:** published-source evaluation, censoring identification and lower-bound usefulness change the engineering interpretation of nominal uncertainty more than model architecture does. This can produce a credible negative benchmark or reporting standard even if the combined gate fails. Avoid selecting a new preferred model after inspecting test risk.

## A directly auditable runout metric

The following is elementary interval reasoning, **not a novel statistical theorem**. Let the lifetime be T, runout threshold C, and lower-life prediction L. For a factor k≥1 define danger as L>kT.

- A failure has observed T and is exactly classifiable.
- For a runout T>C, L≤kC proves absence of this dangerous event.
- A runout with L>kC is unknown; it must not be called a failure or a success.

For a fixed evaluated/accepted set of n observations, let d be exactly observed dangerous failures and u be ambiguous runouts. Then the empirical all-observation dangerous-event fraction is in **[d/n, (d+u)/n]**. With k=1 this bounds one-sided lower-bound miscoverage. These are identification bounds for the observed cohort, not confidence intervals for future parts. Apply the formula within each source before source-balanced aggregation. Sampling uncertainty and censoring non-identification are separate.

For a two-sided life interval [L,U], exact failures classify coverage; a runout C≥U proves noncoverage (T>C≥U, subject to strict endpoint conventions), while C<U generally leaves coverage unresolved. Do not reuse uncensored coverage code.

## Protocol advice arising from the audit

1. Keep source publication, fatigue-curve/group, potential specimen lineage, and raw row identity separately. Grouping by curve alone cannot establish external-publication performance. Related articles that share experiments belong in the same outer block.
2. Freeze the feature list without post-test outcome descriptors. Runout is a target/censoring status, never an input available before testing. Do not invent missing processing values or turn a missing category into a physical value.
3. Use a simple censored Basquin/AFT model as a serious baseline. An outcome-aware survival likelihood and a lower-life quantile are different from a regression fitted only on failures. Label any paper-like FFNN as an accessible reimplementation, not a Centola reproduction, unless exact data/target/splits are obtained.
4. Split independent sources for fitting, threshold selection and calibration. Ordinary row-level calibration is only a diagnostic baseline. For source-max split conformal at nominal 90%, fewer than nine calibration groups cannot produce a finite distribution-free order-statistic cutoff without additional modelling or randomization; at the smallest feasible counts it is coarse and may be extremely conservative.
5. A marginal conformal guarantee does not automatically remain valid after selecting only accepted predictions. If the gate is tuned using outcomes, it requires independent data or an appropriate selective method. Under source shift, use empirical wording even for separately calibrated gates.
6. Report both specimen-weighted and source-balanced risks, number of accepted sources, all-observation identification bounds, failure-only diagnostics, mean lower-bound magnitude, and availability. Use source-level uncertainty summaries; seeds are repetitions, not new experiments or independent publications. Leave-one-source-out fits share training data, so a source bootstrap remains a limited uncertainty summary rather than proof of independent future-source reliability.
7. Topology optimization should wait: the present question concerns the reliability of its fatigue constraint. A clearer result about where the model is unsupported is relevant to design without needing to add an optimizer whose objective can exploit the same model error.

## Search record and limitations

Searches used web search and primary URLs on 2026-10-20, then Crossref metadata retrieval and public HTML archiving. The exact query strings and source records are in `literature/novelty/search_log.json`; retrieved bytes, UTC access times, hashes and failed fetches are in `literature/novelty/fetch_manifest.json`. The audit encountered publisher/API 403 errors and one manuscript timeout. These limit full-text novelty claims. Current metadata and abstract-only findings must be revisited before submission.

Additional leads, **not relied on for established methods/results**: EFAST2026 lists a presentation titled “Censoring-Aware Machine Learning for Fatigue Life Prediction of Additively Manufactured Alloys: A Cross-Material Data-Driven Framework” (Mohi Uddin, ID214), but no full paper/DOI was verified; Liu, de Paula and Tamer's [arXiv:2501.10117](https://arxiv.org/abs/2501.10117) (initially “Censored Outcomes,” current title “Interval Outcomes”) studies conformal prediction with interval observations; Balamurugan, Ilies and Liu's [SSRN:7129248](https://doi.org/10.2139/ssrn.7129248), posted 16 July 2026, concerns CT-driven probabilistic AM fatigue. These reinforce that censoring/UQ/image learning broadly are active areas, not unoccupied territory.
