# Protocol v1: publication-held-out censored AM fatigue reliability

Registered locally on 2026-10-20 before any real-data model fit or outcome comparison. This is a dated local preregistration, not a public or independent registry. Data/schema audits are allowed before registration. The primary hypothesis and analysis will not be changed after seeing test performance. Amendments must state timing and reason.

## Question and contribution boundary

When a source publication is unseen, do nominal lower-life predictions remain conservative? Does a fixed combination of observable feature support and source-bootstrap model instability reduce dangerous overprediction at useful decision availability, compared with its components? Group splitting, conformal prediction, Bayesian fatigue models, and rejection are prior work. The contribution candidate is the carefully sourced empirical one-sided, censor-aware reliability/utility audit. No new distribution-free guarantee, R90C90 estimator, original-data reproduction, or physical part validation is claimed.

H1: model-based lower10% life predictions can have substantially different violation rates across held-out publications; endpoint calibration and source-cohort calibration will have different reliability/conservatism tradeoffs. This is an empirical hypothesis, not a presumption of an author implementation error.

H2 (falsifiable intervention): combined support/instability rejection reduces censoring-identifiable dangerous predictions more consistently than each single score and an outcome-blind random ranking at the same per-publication accepted fraction. Primary fraction0.8; secondary0.5. If the reduction does not persist across seeds/source blocks, or censoring prevents identifying it, reject the strong claim. A null result is a valid outcome.

## Population, provenance and exclusions

Use official Figshare FatigueData-AM2022 version2, DOI10.6084/m9.figshare.22337629.v2, retaining raw bytes, hashes and license. Exact nominal316L/SS316L/AISI316L/stainlesssteel316L only; L-PBF, S-N, positive finite amplitude and observed cycles. Exclude deliberately modified alloys such as nitrogen-enhanced316L. Primary cohort: database uniaxial,20–30C,Kt0.99–1.01. These are database labels: the descriptor sometimes defaults them, so source-measured eligibility cannot be certified for every row. No outcome-length cutoff/outlier filtering; retain all reported failures/runouts. All eligible metadata and decisions saved by deterministic scripts.

Observation IDs are database addresses, not certified physical specimen IDs. No global claim that specimen overlap has been eliminated. Identify cross-source near-duplicate curves and source text clues before fitting; merge connected suspicious/reused-source families conservatively with an audit trail. A source-DOI-only sensitivity may expose grouping sensitivity but is not the primary if reuse is demonstrated. Report observations, conditions, DOIs and final independent blocks separately. Centola overlap is source DOI overlap, never row identity or an independent external replication.

Primary evaluation needs at least13 final groups and at least4 fit groups after at least9 calibration groups. If this fails, record infeasibility; do not silently reduce calibration groups to make a result. Low group count weakens inference even if fitting remains possible.

## Frozen splitting and fitting

Leave one final source/family block out at a time. For each outer fold repeat seeds0,17,42; sort remaining group identifiers, seeded permutation, reserve max(9,ceil(0.25*remaining groups)) whole groups for calibration, fit on all others. Test group has no role in imputation, scaling, model choice, calibration or operational gate thresholds. Each eligible row is test exactly once per seed. Save exact row/group membership and training encoder parameters for every fold.

All fit observations weighted so each training source/family contributes equal total likelihood. Missing scalar metadata retained as missing, with training medians and explicit missing indicators; vector-valued uncertain metadata become missing rather than an invented mean. Training mean/SD scaling; categorical surface/thermal labels include explicit unseen-category encoding. No source identifiers, observed cycles, runout status, fitted curves or database outcome-derived quantities as features. `event` is used only by the survival likelihood/evaluation.

Comparisons: (1) censored lognormal Basquin-style AFT, log amplitude+load ratio; (2) same likelihood with linear process/orientation/treatment covariates; (3)12-unit tanh location MLP with the same homoscedastic lognormal likelihood. Linear ridge l2=.001; MLP l2=.01. Fixed source-bootstrap8 fits of rich linear model measure location instability; this is not a BNN posterior. Numerical iteration caps1000 linear/1500 MLP, fixed stopping tolerances, record every convergence failure and sigma bound. No real-data hyperparameter search or best-seed selection.

These models are related censored-life implementations. Original paper's risk volume, exact SWT preprocessing, Owen curve labels and variational output layer are not reconstructed. The raw metadata cannot support those equivalences. Unconstrained nonlinear/linear covariates may violate stress monotonicity; check and report, not hide such fits.

## Bounds, calibration and selection

Model q10: b(x)=mu(x)+Phi^-1(.1)*sigma. Three bounds: b; pooled endpoint split-calibrated b-q; and source-cohort maximum split-calibrated b-q_group. In both cases residuals are r=b(X)-log10(min(T,C)) on calibration only. Pooled q uses order ceil((n+1)*.9); group scores are maximum r within each complete calibration source/family and use order ceil((m+1)*.9), +infinity if the order exceeds m. Infinite q yields zero life; flag vacuity rather than hiding it.

Endpoint calibration deliberately predicts the smaller observed endpoint and is conservative for true life under suitable exchangeability. It is not a censoring-adjusted survival conformal implementation. Source-max targets simultaneous coverage of complete cohorts, depends on cohort size, and has a finite calibration resolution. The row/cohort targets differ. No guarantee of nominal coverage on arbitrary process shift, fixed source, or conditional accepted-part risk follows.

Distance: minimum RMS Euclidean distance from query to fitting rows in the fixed encoded feature representation. Instability: SD of8 source-bootstrap linear locations. Combined score: average of calibration empirical-CDF ranks of distance and instability. Operational thresholds are calibration-feature score quantiles0.5/0.8, frozen before test; report actual availability, not promised80% availability. Core gate study uses rich-linear pooled endpoint bound.

Secondary matched-availability diagnostic: rank held-out X within each publication/family and seed, retain ceil(fraction*n) with distance, instability, combined score, or a deterministic outcome-blind random score. No test outcomes enter ranking. This is a retrospective comparison, not an operational threshold selection rule. Compare the same accepted count per source; reveal stress/censoring/source mixes. Random ranking repeats20 fixed seeds and averages source risk; never select its best realization.

## Primary estimands and uncertainty

For strict dangerous event L>T, failure rows determine status exactly. At runout C<T, L<=C proves event absent; L>C leaves it unknown. The all-observation empirical risk identification interval is [known dangerous/n,(known dangerous+unknown runouts)/n]. Use the identical construction for severe L>2*T. Bounds describe observation uncertainty, not sampling confidence intervals. Failure-only MAE/RMSE/R2 are explicitly descriptive secondary metrics on selected failures; censored likelihood scores include both outcomes.

Report pooled-row and equal-source rates, every source's risk interval/availability, and source coverage (fraction with any acceptance). Empty acceptance => risk undefined, never zero. Do not pool the3 seeds as independent observations; average each source over seeds first. Paired2000-resample source-block bootstrap keeps all methods/seeds together. CIs are descriptive because leave-one-source-out fits share training. For comparisons with different accepted censoring sets also report partial-identification contrast [LB_A-UB_B,UB_A-LB_B]. Reduced known violations alone cannot establish reduced true risk.

Utility: accepted fraction, source coverage, median mu-log10(L) (decades of conservatism), quantiles of lower-life magnitude, infinite/zero bounds, stress mix and runout fraction. A trivially tiny life bound or near-total rejection is not a successful engineering result. This is an audit, not a certified allowable stress/design-life calculation.

## Critical experiments, ablations and failure criteria

1. Full primary leave-block-out3-seed benchmark, all3 models/all3 bounds.
2. Combined gate versus distance/instability/random at matched per-source0.8/0.5 availability and operational thresholds; risk identification and bound utility together.
3. Diagnostic random-row split60/20/20 seeds0,17,42; explicitly contaminated across publications and not generalization evidence.
4. Source-family grouping sensitivity and exact duplicated-curve removal sensitivity if the pre-fit audit finds any; otherwise explicitly report no detected candidates and limitations.
5. Main source holdout repeated with censored endpoints naively treated as failures, rich linear only, as a prespecified methodological sensitivity. Never present that fit as an appropriate survival model.
6. Root independently recomputes selected prediction metrics from saved row-level output; a separate agent audits code/split/metric integrity after outcomes. Synthetic likelihood-gradient/censoring tests precede real fitting. Deterministic rerun of a held-out fold compares saved predictions.

Do not change the protocol to rescue a failed combined rule. If original518data/code unavailable, continue independent open-data evaluation and record the limitation. If calibration is too conservative, source groups too few, censoring too ambiguous, MLP unstable or duplicate provenance unresolved, report that limitation and scale the scientific claim accordingly. No publication/email/upload without the user's explicit approval.
