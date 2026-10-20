# Follow-on audit: topology and multi-alloy transfer

Audit date: 2026-10-20. Scope: targeted methods, validation, uncertainty, data-access, and limitation audit. This is **not a computational reproduction**.

## Access and verification status

Crossref/OpenAlex metadata were retrieved locally and preserved under `literature/followons/`. Public IRIS repository landing pages and their advertised PDF bitstreams returned Cloudflare HTTP 403 to HTTP clients. The in-app browser also failed to expose usable article content. Publisher FULL API requests returned HTTP 401; a metadata XML response is preserved. No access control was bypassed. **Neither follow-on PDF was downloaded successfully; consequently no PDF checksum or local page rendering is claimed.**

Both papers' author-upload full text was subsequently readable through the web index on ResearchGate, identifying Alessio Centola as uploader. Page/section labels below come from those indexed full texts. Equations, plots, and appendix tables need later visual verification against downloaded PDFs. The transfer appendix's table body was not text-recoverable through the index. Supplements were advertised but were not obtained.

## Topology paper: observations

[DOI 10.1016/j.ijfatigue.2026.109481](https://doi.org/10.1016/j.ijfatigue.2026.109481); [official record](https://iris.polito.it/handle/11583/3009771); [author-upload full text](https://www.researchgate.net/publication/399560885_Data_driven_topology_optimization_of_AM_parts_accounting_for_process-affected_fatigue_performance_Application_to_automotive_and_aerospace_components).

| Evidence location | Observation |
|---|---|
| §2.1 pp2–3 | Fatigue BNN: deterministic 100/75/50 hidden layers, variational output, R50/R90C90 targets; 90/10 training/test split and ten-fold validation. Publication grouping is unspecified. |
| §2.2 p3; Table2 | Defects BNN uses critical-defect/Gumbel information; 222 defect observations. |
| Fig5; Appendix A | SS316L fatigue database: 518 observations, 51 datasets, 17 source articles. Appendix records condition-level inputs, not complete specimen-level life records. |
| §3.1.1 pp6–7 | SS316L risk-volume range: approximately 27–1005 mm³. |
| §2.3 p4; §5 pp11–13 | Maximum training risk volume supplies a conservative design input. Final component risk volume must be checked case by case. |
| §5; Fig15 p14 | Final V90: SS316L 88.77/52.46 mm³; titanium 33.65/25.83 mm³. Training maxima used: 1005/10560 mm³. |
| §5 pp11–13 | Dedicated experimental validation remains necessary for critical applications. |
| Appendix C; data availability p17 | Supplements advertised; underlying data available upon reasonable request. |

Both process-to-life and process-to-defect routes inform computational topology design. This is relevant continuation, rather than independent new-specimen fatigue validation. The authors explicitly address geometry/risk-volume limitations; calling these neglected would misrepresent the paper.

## Transfer paper: observations

[DOI 10.1016/j.engfailanal.2026.111075](https://doi.org/10.1016/j.engfailanal.2026.111075); [official record](https://iris.polito.it/handle/11583/3013143); [author-upload full text](https://www.researchgate.net/publication/406058166_Data_scarcity_in_fatigue_design_of_AM_parts_A_transfer_learning_framework_to_model_the_process_-_structure_-_property_relationship).

| Evidence location | Observation |
|---|---|
| §2.1 p3 | Database: 2498 observations/222 datasets/71 publications. Titanium: 1106/88/32; aluminum: 874/83/22; SS316L: 518/51/17. |
| §2.2 pp3–4, Eqs1–2 | Basquin/lognormal fatigue model; runouts enter through survival likelihood. Owen shift constructs R90C90 targets. |
| §3.1 p5 | BNN has deterministic hidden layers and variational outputs. Internal split: 90/10. |
| §3.3 pp6–7, Fig4 | Reduced training databases sample **whole experimental datasets**, approximately 50/100/150/200 points; ten nested dataset combinations. |
| §3.3 p7 | External evaluation datasets are excluded from training. Metric: curve R² normalized by experimental R50-line R². |
| §3.3 p7 | Normalization uses training target-alloy data and, for TL, pretraining-alloy data. |
| §5.2; Fig15 pp14–17 | Parameter-response comparison uses the full-database BNN as reference; this is model-to-model agreement. |
| Appendix A pp18–25 | Condition-level table omits stress, life, runout labels. |
| Appendix C/data availability p28 | Supplements advertised; data on request. |

The paper already performs group-excluded validation at **dataset level**. A claim that its evidence rests exclusively on random rows is false. Publication-level independence and empirical lower-bound calibration are not established by the inspected evaluation.

## Research interpretation and classifications

The following are our inferences or proposed research questions, rather than findings reported by the authors.

1. **No confirmed implementation error.** We have not obtained executable author code or exact split lists. Unspecified grouping is a reporting boundary, not proof of leakage. The censored likelihood in the transfer paper is evidence against claiming that runouts were treated as failures.
2. **Reported limitations.** The topology paper acknowledges geometry differences, conservative choices, case-specific volume checks, and the need for physical tests. An audit should test those choices empirically without implying that the authors ignored them.
3. **Reproducibility limitation.** Condition-level appendices do not supply specimen-level stress/life/censoring labels. Public availability of appendices is insufficient for exact reproduction. Request raw and cleaned labels, source IDs, runout thresholds, group splits, preprocessing, curve-fitting/Owen code, trained weights or code, and supplements.
4. **Untested dependence hypothesis.** Different processing datasets can come from one publication or shared experimental campaign. Holding out a dataset might still leave related data in training. The size and direction of this effect require publication/source linkage and actual experiments. It cannot be inferred from validation terminology alone.
5. **Untested calibration hypothesis.** Predicting a distribution over an R90C90 target is different from validating a lower survival bound for a specimen drawn from a new publication. Bayesian weight variation, population fatigue scatter, finite-sample confidence, and domain shift must be separated. A coverage result must explicitly define its target and handle censoring.
6. **Narrow candidate contribution.** Compare dataset-held-out and publication-held-out evaluation; estimate dangerous life overprediction and lower-bound violations; then test whether support-aware abstention improves that risk at matched acceptance. Evaluate against uncertainty-only and support-only gates, with thresholds fixed on training publications. A negative result would show limits of the proposed gate.
7. **Connection to Tridello's agenda.** A trustworthy criterion for requesting an extra fatigue experiment or declining a process-to-life prediction could complement transfer and topology tools. This is a prospective contribution; originality and engineering utility remain unproven.

## Prerequisites for any paper-specific criticism

- Obtain exact source-publication/campaign linkage and verify repeated specimens.
- Determine whether exclusion of an external dataset also excludes other datasets from its publication.
- Inspect executable target fitting and normalization order; do not assume order from prose.
- Verify equations/appendix content visually and inspect supplements.
- Evaluate full curves and censored observations; do not equate R² or posterior width with calibrated design reliability.
- Keep an open-data benchmark explicitly separate from reproduction of these private specimen databases.
