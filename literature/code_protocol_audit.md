# Independent pre-outcome code/protocol audit

Date 2026-10-20. Scope: `src/features.py`, `src/evaluation.py`, `src/run_experiment.py` against `protocols/v1_pre_outcome.md` and amendments `v1_1_prefit_integrity.md`, `v1_2_prefit_claim_rule.md`, `v1_3_prefit_provenance.md`. `src/summarize.py` was also inspected for gate comparisons and source resampling. The auditor did not fit models to real data or inspect real model outcomes. Metadata/schema counts and synthetic test output were inspected.

## Synthetic estimator verification

Command: `.venv/bin/python -m pytest tests/test_models.py -q`

Result: **11 passed in 30.06s**; captured in `logs/synthetic_models_tests.txt`. Checks include finite-difference likelihood and full-network gradients, stable normal survival tails, recovery of a simulated Basquin slope with right censoring, a runout-vs-false-failure contrast, finite/repeatable predictions, weight-scale invariance and rejected invalid/unidentified inputs. These establish numerical/statistical implementation behavior for the tested cases, not experimental generalization.

## Protocol integrity checks

| Requirement | Code inspection | Finding |
|---|---|---|
| Whole-source/family outer holdout | `run_experiment.main`: test group selected before fit/calibration permutation | Matches frozen source scheme |
| Separate calibration groups | max(9,ceil(.25*remaining)); set-disjoint assertions | Matches; direct train >=4 and total >=14 enforce v1.1 |
| Fixed seeds and 3 repetitions | default 0,17,42; seeded permutations; explicit output receipts | Matches; CLI overrides must be labeled diagnostic/amended |
| Training-only preprocessing | `Encoder.fit(tr)`; cal/test only `transform` | No test/outcome information enters fitted encoding |
| Missingness and unseen categories | finite training medians, indicators, training SD, `__unseen__` | Matches; wholly missing columns get computational 0 fill with indicator |
| No source/outcome features | feature allowlist contains stress,R,process,treatments only | Matches |
| Source-balanced likelihood | each row gets1/source_n, normalized in estimators | Each source has equal total mass |
| Source-bootstrap instability | sample whole fitting groups with replacement; multiply row weight by group count | Correct equal-source bootstrap multiplicity; no Bayesian interpretation |
| Fixed model sizes/penalties | rich/basquin linear l2=.001; MLP 12,tanh,l2=.01; iteration caps 1000/1500 | Matches frozen methods |
| Proper right censoring | estimators use density at failures and survival at runouts | Synthetic gradient/runout checks pass |
| Model-based lower10% life | location+normal_ppf(.1)*sigma | Correct sign |
| Endpoint calibration | residual=model_bound−observed log endpoint; subtract upper90% finite-sample order | Correct lower-bound construction; assumes declared endpoint target |
| Source maximum calibration | maximum residual per complete calibration group; same order rule | Matches cohort-level rather than row-level target |
| Infinite conformal quantile | evaluator returns+inf when order exceeds count; subtracting yields−inf log life | Vacuous zero-life bound, not a hidden positive prediction |
| Gate score source | distance to fitting X, instability from fitting-only bootstrap; CDF reference calibration X | No test outcomes enter score |
| Operational gate thresholds | quantiles .5/.8 of calibration scores, saved in fold receipt | Matches; actual test availability can differ |
| Matched per-source gate analysis | held-out features ranked to ceil(fraction*n), outcome-blind hash tie breaks | Appropriate retrospective diagnostic; not operational calibration |
| Random comparison |20 fixed seeded outcome-blind permutations averaged; no best realization | Matches |
| Censor-aware violation status | failures exact; runout L>C unknown; L<=C safe; severe event uses log10(2) shift | Correct partial-identification interval |
| Empty acceptance | NaN risk,0 availability | Does not falsely mark rejection as zero risk |
| Seed/source uncertainty | contrasts average seeds within source, bootstrap paired source differences | Correct resampling unit for declared descriptive comparison |
| Naive-censor sensitivity | training event overridden to1 while saved evaluation flags remain original | Correctly isolates misspecified fitting; no appropriate-survival claim |
| Checkpoint signature | data/code hashes,scheme,seeds,bootstrap count,models,naive flag; mismatches refused | Meets v1.1 safeguard |
| Stress-response check | held-out stress ±.01 log amplitude, other covariates fixed | Matches v1.1; no repair based on test outcome |

No critical train/test, sign, censoring or gate-source defect was identified in this snapshot. This is an implementation review, not proof that an eventual dataset split is physically independent or that any real result supports H1/H2.

## Reporting/operational caveats retained

- Basquin preprocessing is a numerical subset of the rich encoder for its numeric fields. The current fold receipt saves the rich encoder; explicitly saving per-model encoder receipts would be clearer, though both numeric transformations are recoverable from the rich receipt and code.
- Policy risk means exclude undefined empty-acceptance cells. Report the number of sources with acceptance and finite risk alongside averages so this denominator is transparent.
- Endpoint calibration is deliberately conservative for a censored endpoint; it is not the literature's censor-adjusted survival-conformal algorithm. Group maxima target complete-cohort coverage and depend on cohort size. Neither implies conditional safety after gate selection or under arbitrary source shift.
- Eight bootstrap fits provide a coarse instability estimate. They are fixed by the protocol and must not be increased selectively for poor test results.
- Optimizer success and sigma bounds are recorded. Nonconvergence, implausibly broad scatter or positive life-vs-stress slopes must be disclosed; numerical success is not engineering validation.
- Representation distance depends on encoding and number of categorical levels. A small distance is not a proof of adequate physical support.
- Input/source-code hashes protect checkpoint identity. Independent specimen provenance still depends on the separate source-family audit.

No edits to root-owned feature/evaluation/experiment scripts were made by this auditor. The earlier finite-only-median and infinite-conservatism fixes were already present when the final review snapshot was read.

## Amendment v1.3 grouping/eligibility review

Reviewed the final pre-fit `prepare_data.py` force-control eligibility filter and `group_sources.py` without real model fitting/outcome inspection. It yields 1126 observations/120 conditions/37 source DOIs/29 main blocks. The main path preserves all eligible observations; DOI-only, weak-edge and approximate-dedup files are separate sensitivities. Source-family labels feed the same disjoint splitting and equal-block likelihood weighting reviewed above. Deduplication is greedy and only cross-DOI inside strong families, with equal runout and R; test mode is already constant by primary eligibility. The 184 removals are explicitly mapped. Near-curve matches warrant conservative blocking but do not certify specimen identity.

Amendment v1.2 requires the combined rule to beat each comparator in every seed and have seed-averaged paired descriptive-CI upper endpoints below 0 at fraction .8. The source-seed table and contrast table expose those ingredients; no positive-claim judgment can be made from this pre-outcome audit. A favorable secondary .5 analysis cannot rescue a failed primary rule.
