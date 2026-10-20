# Phase 2: provenance and few-shot lower-life bounds

Written 2026-10-20 before any phase-2 model fit. The earlier pilot's outcomes are already known. These retrospective experiments are a new, explicitly prospective-within-this-phase benchmark, not an untouched confirmation of a method invented before the pilot.

## Order and question

First audit source/curve reuse and condition meaning. Freeze the inclusion manifest and support/query IDs before fitting. Then ask whether observing 3 or 5 endpoints from a previously held-out source/condition produces materially more useful lower-life predictions without an unacceptable rise in dangerous overprediction. Ten endpoints are a limited secondary panel. A newly acquired experimental campaign, if accessible with sufficient provenance, is a separately frozen external evaluation. A newer publication date alone does not establish independence.

The unit called a condition is initially a database S-N curve, not a certified build batch. Published provenance evidence can upgrade or qualify this label. Specimen IDs absent from a publication cannot be invented.

## Data and split rules

* Preserve the v1 raw data and results. Phase 2 has its own paths and signatures.
* Main retrospective cohort excludes all three suspected cross-publication curve-reuse families. Family membership is frozen from v1 rather than optimized against phase-2 performance. The full family-blocked cohort is a sensitivity. The weak edge is merged in a sensitivity. Further changes require explicit source evidence before fits and a dated manifest.
* Every target provenance block is absent from population fitting and calibration. Other curves from the target publication cannot enter population fitting. Support contains only endpoints from the particular target curve being predicted.
* Seeds 0, 17 and 42 define outcome-blind SHA256 row-ID permutations. In each panel reserve exactly max(k) support rows; all remaining rows are fixed queries for every k in that panel. Supports are nested. No failed-only support selection.
* Panel A (primary): at least 8 rows per curve, k=0,3, at least 5 queries. Panel B: at least 10 rows, k=0,3,5. Panel C: at least 15 rows, k=0,3,5,10. Never treat comparisons across changing panels as one learning curve.
* A pre-fit near-coordinate check records potential same-curve replicates. A sensitivity removes near-coordinate clusters from target support/query sampling; it does not assert these are the same physical specimen.
* For each outer source and seed, reserve 9 other eligible provenance blocks for calibration, selected without outcomes. All other sources form the fitting partition. Calibration chooses one eligible curve and one query per block by seeded hash, defining a random-condition/random-specimen target rather than simultaneous coverage of a complete cohort. Fit every transform and population parameter on fitting sources only.
* When fewer than 9 calibration blocks exist, finite-sample 90% endpoint calibration is unavailable: its literal lower-life bound is zero. Raw model predictions remain reported. Do not replace the required rank with a convenient finite quantile.

## Models and observations

Use censored lognormal Basquin models with a non-positive log-stress slope and load ratio R. Population fitting includes failures via density and runouts via survival probability; do not fit runout endpoints as failure times.

1. Pooled monotone censored Basquin, unchanged by target support (negative control).
2. Shared population slope/scatter with only a target intercept fitted from support (unpooled adaptation control). At k=0 use the pooled prediction. All-runout support has no finite unpenalized intercept MLE and is explicitly unavailable, not silently converted to a failure fit.
3. Censored condition-random-intercept Basquin, with training-only population, within-condition scatter and between-condition variance. Infer a target intercept from the censored support likelihood and its population prior; invert the posterior predictive mixture to obtain the lower decile. At k=0 predictive variance includes new-condition variability. Retain support posterior uncertainty. This is an empirical Bayes working model, not a fully Bayesian posterior over population parameters. Equal-source composite-likelihood weights and within-source correlation limitations must be explicit.

Use adaptive numerical quadrature; check derivatives and known uncensored posterior formulas on synthetic data before real fits. Record convergence, parameter bounds, stress monotonicity and quadrature sensitivity. Population-parameter uncertainty is omitted from the main empirical Bayes bound and cannot be described as fully quantified uncertainty. A source bootstrap sensitivity will assess it if feasible.

Report raw 10th predictive percentiles and separately endpoint-calibrated bounds. Calibration residual = predicted log lower bound minus observed log endpoint, with the finite order statistic ceil(.9*(m+1)); subtract that statistic. Using the endpoint is conservative for latent failure life under the exchangeability target. This is not a claim of validity for an arbitrary unseen manufacturing process, does not remove clustered-source dependence, and is not Owen R90C90. Modern censor-aware calibration methods must be reviewed before claiming a contribution; missing potential censoring times on failures prevents direct use of Type-I algorithms but does not rule out modern right-censoring methods.

## Endpoints and prespecified claim criterion

Danger is predicted lower life greater than true failure life. With a runout endpoint C<T, L<=C establishes no danger; L>C is ambiguous. Report both identification endpoints [known dangerous/n, (known dangerous + ambiguous)/n]. These are not confidence limits. Average queries within curve, curves within source and sources equally, then average seeds within source. Physical specimens and seed-repeated prediction rows are distinct counts.

Utility is paired mean log10 lower-life gain on identical queries. A gain .09691 means 1.25x geometric lower life; report absolute lower-life distributions and fractions below 1, 100 and 10,000 cycles. Larger limits are useful only if risk is acceptable. Also report failure-only absolute log error as a diagnostic, never as the safety endpoint.

Primary positive-claim rule for hierarchical endpoint-calibrated k3 versus k0 in panel A: (i) observed source-balanced risk upper endpoint <=10%; (ii) upper endpoint of the paired descriptive 95% source-bootstrap interval for risk-upper increase <=2 percentage points; (iii) lower endpoint of the paired 95% interval for mean log-life gain >log10(1.25). Use 2,000 bootstrap samples of source-level seed-averaged contrasts. Shared fitted data prevent interpreting these as independent external confidence guarantees. Report all comparisons against pooled and unpooled controls. No broad superiority claim follows from only beating k0 or an unavailable control.

Preserve failures of this criterion. Panel B/C, raw bounds, source-specific results, known-risk versus ambiguity, and external-campaign analysis are secondary. An external single campaign does not provide multiple independent laboratories.

## Planned checks and deliverables

Audit source and point IDs in support/query/fit/calibration sets; synthetic likelihood/posterior tests; deterministic replay; numerical quadrature sensitivity; conservative near-duplicate sampling sensitivity; full-source-family and weak-edge grouping sensitivity where feasible; training-source bootstrap sensitivity; and an independent check of arithmetic and conclusions. Log every omitted or infeasible planned check rather than silently dropping it.

Deliver a provenance evidence table, frozen split manifest, executable code, complete prediction and metric tables, source-balanced paired figures, and a Turkish/English report. Assess contribution honestly; no publication, correspondence or physical test is authorized by this protocol.
