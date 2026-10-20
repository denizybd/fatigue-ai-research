# Independent pre-outcome protocol review

Reviewer: parallel novelty/statistical-literature agent. Date: 2026-10-20. The root agent supplied the proposed protocol verbally; no experiment outcomes, model fits or result tables were inspected. This is a conceptual protocol review, not independent physical validation or code replication.

## Proposed design reviewed

SS316L L-PBF stress-life observations; exact failures and right-censored runouts; publication/connected-source-family outer withholding; repeated source-level fit/calibration splits; linear censored lognormal Basquin/AFT and small neural model using the same censored likelihood; raw lower-decile life, pooled endpoint calibration and source-maximum calibration; support distance, source-bootstrap location uncertainty and a frozen rank-combined gate; fixed operational thresholds versus explicitly retrospective matched-availability ranking diagnostics; one-sided violations at factors 1 and 2; censoring identification bounds; source-balanced and specimen-pooled aggregation; source resampling for uncertainty.

## Assessment

The design is well aligned with the stated scientific question and separates most previously conflated issues. It can support an empirical reliability audit. No arbitrary-source-shift guarantee or Centola reproduction should be asserted. The following details need explicit formulas and reporting safeguards before outcomes.

### Calibration formula must match its base predictor

Let y_obs=log10(min(T,C)), location mu, and model lower-decile predictor b=mu+z_0.1*sigma. If calibration scores are r=mu-y_obs, the calibrated bound is log10(L)=mu-q_0.9(r). Subtracting this q from b would count the noise adjustment twice. To conformalize b directly, use r=b-y_obs and log10(L)=b-q_0.9(r). The latter preserves heteroscedastic scale effects, while location calibration does not use sigma in the resulting bound. Label the variants accurately and freeze the selected version or ablation before observing results.

Endpoint calibration intentionally handles y_obs as a lower endpoint to the latent life. It may be conservative; it is not equivalent to a censoring-adjusted survival-conformal method. Fitting should still use proper survival likelihood terms for runouts.

### Meaning of source-max calibration

If each calibration score is the maximum over all rows of a source cohort, the target is simultaneous coverage across all members of a new exchangeable cohort. Cohort size and selection are part of the sampling mechanism. It is not a source-conditional guarantee for a fixed new manufacturing process. At nominal 90% and fewer than nine calibration cohorts, the ordinary finite-sample split-conformal cutoff is infinite; report the resulting lower bound as vacuous without clipping it into an apparently useful number.

A simultaneous all-rows event implies an unconditional simultaneous selected-subset event, so selection cannot invalidate that logical implication. However, it does not establish 90% conditional coverage for a randomly accepted part, nor does it repair nonexchangeable process shift. Ordinary pooled marginal coverage has no analogous automatic guarantee after rejection.

### Gate comparisons and empty denominators

Zero accepted observations implies undefined conditional risk, not zero risk. Report total accepted rows, accepted rows by source, and the number/fraction of sources with any accepted rows. Otherwise the macro-average may improve by omitting difficult sources entirely. The risk of an accepted specimen and the rate of danger per offered specimen are different estimands.

Matching the pooled accepted fraction may select different publications, stresses and censoring fractions. At minimum show these distributions; where feasible a prespecified per-source matched-ranking diagnostic isolates the within-source selection effect. The held-out-X ranking analysis is a retrospective comparison at equal availability, not an operational threshold that can be promised to achieve the same acceptance on future data.

Gate thresholds from calibration X are outcome-free, but that alone is not a full post-selection coverage proof. A gate tuned or chosen after calibration/test outcomes requires additional independent data or valid selective inference. Under publication shift, empirical wording is appropriate throughout.

### Censoring bounds and risk contrasts

For danger L>kT, runout T>C is definitely safe when L<=kC; otherwise the event is unknown. Let d be observed dangerous failures, u ambiguous runouts and n the relevant denominator. Report [d/n,(d+u)/n], including at source level. Censoring non-identification and sampling uncertainty are different and should not be compressed into one ordinary error bar.

A lower known-danger rate can arise by selecting more unknown runouts. For two rules A and B, the generic contrast interval is [LB_A-UB_B, UB_A-LB_B]. If it crosses zero, a true all-specimen risk improvement is not identified from these endpoints alone. A reduction in observed/identifiable violations can still be reported with that exact wording and ambiguity fraction.

### Utility and stress-mix confounding

The median lower bound among accepted specimens depends on which stresses/sources the gate admits. It is not by itself a measure of reduced conservatism. Report the safety penalty mu-log10(L), or L/10^mu, and compare calibration bounds pairwise on the same offered X. Ratios of logarithms are origin-dependent and should not be used. For gates, retain source/stress mix alongside bound magnitude and availability. A fixed required life N_required would define an interpretable decision yield, but choosing it after outcomes is exploratory.

### Effective sample size and bootstrap

Keep each source's outcomes, all methods and all seeds together in a paired source bootstrap. Seeds do not create more independent sources. Leave-publication-out models share training data; bootstrap intervals over their contributions are limited descriptive uncertainty summaries, not proof of future-process reliability. Related-source-family grouping should be reported because publication count can exaggerate independence.

### Supporting implementation checks

Check stable Gaussian survival terms, positive sigma, monotonic stress response or its violations, and correctness of the censoring masks with toy cases. Identical stress/life values are not sufficient proof of duplicate specimens; retain a distinction between exact numerical matches and verified repeated experiments. Support distance can be driven by missingness/categorical encoding and should be interpreted as recorded feature support, not direct physical defect similarity.

## Literature grounding

See `../novelty_audit.md` for verified sources. Relevant foundations are Candès/Lei/Ren (2023, DOI 10.1093/jrsssb/qkac004), Lee/Foygel Barber/Willett (DOI 10.1145/3786352), Foygel Barber et al. (2023, DOI 10.1214/23-AOS2276), and Geifman/El-Yaniv's selective-prediction work. These preclude methodological priority claims for censoring-aware conformal bounds, hierarchical calibration or rejection by themselves.
