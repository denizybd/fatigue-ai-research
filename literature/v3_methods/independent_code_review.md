# Independent phase-3 code review

Reviewed `src/v3_design.py`, `src/v3_prepare.py`, `src/v3_run.py`, and `src/v3_summarize.py` against `protocols/v3/frozen_design.txt` (SHA256 46808419f7b6bdb1639c66da1d0cb266a58b3ef3b83624666db30f7208c1df1c). No root-owned files were edited by this review.

## Correctness findings

The query split is fixed before acquisition and is common across every policy/model/cap. Acquisition receives only `row_id`, `log_stress`, and `load_ratio` from candidate/query frames; the selection function rejects outcome-bearing frames. Endpoints enter support only after selection. Support censoring at the administrative cap is correct. Nested policy prefixes do not inspect unselected outcomes. `stress_span` selects highest stress first, then lowest (farthest from highest), then maximin log-stress separation. The local MAP recovery solver fits the same objective, without query-performance selection.

Expected information was independently integrated from squared normal failure scores plus the runout atom at seven standardized censor levels (-12,-5,-2,0,2,5,12). Maximum absolute error from the implementation was 5.33e-15. Paired true-risk change bounds were checked against 931 possible extended-real threshold/true-life combinations, including infinity; all cases were contained. The absolute known/upper risk calculation and treatment of unavailable bounds are conservative identification limits.

Condition-to-campaign-to-seed aggregation does not count repeated splits as independent campaigns. Finite-life utility is computed only on matched finite prediction pairs, with ordinary/finite availability and infinity rates retained separately. A model's infinite q10 predictions must therefore remain visible beside its finite-pair utility. No predictive coverage or full population posterior follows from the point estimates.

## Actionable cache findings sent to root

The first task-shard signature omitted the frozen input/split hashes, so reusing an output directory after changing normalized endpoints could have reused stale predictions. The first fitted-model signature also omitted `v3_run.py`/fit configuration, so a changed weighting implementation could have reused stale fits. Root reported both signature issues fixed before final delivery. Final file/receipt audit verifies current hashes rather than accepting old validation shards.

## Evidence scope

The 610-row frozen cohort has 309 historical rows, 129 previously examined Trombley rows, 137 additional Tomaszewski rows, 29 Diller rows, and six uninterrupted Dastgerdi pilot specimens. Tomaszewski/Diller have author specimen identities but unresolved specimen-to-build mapping. Dastgerdi has explicit single-build evidence with an analyst canonical label, but test temperature is unstated and the related 2022/2023 source family must be excluded from training. These gates are separate in the dataset; no new strict room-temperature campaign with both specimen/build identity was verified by this code review. Several builds, conditions or seeds cannot be called independent campaigns.

The prior `old_external`, `historical` and `preliminary` result folders were runtime validation runs and were superseded. `audit_results.py` independently checks final query/pool identity, training-source exclusions, observed support-cycle arithmetic, all aggregate mean metrics and paired contrast means, without refitting models or calling acquisition. Its final machine-readable receipt is retained separately after the final run completes.

Combined synthetic command: `.venv/bin/python -m pytest -q tests/test_v3_design.py tests/test_v3_rfl.py`; result: 19 passed in 1.19s. This is numerical/code evidence only.

## Final independent receipts

`independent_final_cap1e7_audit.json` passes 180,960 prediction rows, 9,880 selected-test rows, 430 frozen tasks, 3,024 absolute summary means and 4,032 paired-contrast means. Maximum mean difference is 7.45e-9, from cycle-scale floating-point arithmetic. Query/pool identity, training-source exclusions and observed support-cycle recalculation all pass. Every current v3 source hash matches the final receipt. All 11 RFL fit sets converged with no fallback; two historical leave-source fits have a fatigue-limit scatter bound hit and are flagged. The full 309-row training fit is interior. An interior optimizer solution does not prove identifiability.

`real_quadrature_sensitivity.json` compares 96 versus 192 fatigue-limit quadrature nodes without population refitting. The predetermined ID-based subset is the lexicographically first dataset and seed 0 from each of 14 campaigns, every policy and all feasible budgets. It covers all 11 fit sets and 1,048 q10 predictions. Infinity status is identical; maximum finite log10-quantile difference is 8.9183e-10. This checks numerical integration at fixed parameters and does not integrate population parameter uncertainty.
