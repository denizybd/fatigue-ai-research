# Independent phase 2 split and arithmetic audit

20 October 2026. No frozen cohort, split, model or result file was changed by this audit.

All five requested configurations passed their cohort, original-source, protocol and gate SHA256 checks: strict, strict_fulltraining, strict_nearcluster, external and external_fulltraining. The external full-training manifest references the strict preparation manifest and identical cohort while explicitly disabling calibration; that is internally coherent.

The strict cohort has **309 observations, 32 database curves and 11 source blocks**. These are not 11 certified independent laboratories. All 29 frozen correction cells match: Wood row `a0554_d006_p004` is a failure, and nine Kedziora Renishaw rows are NHT with missing heat temperature/time. Cui contributes only the 13-row JMST representative in `cui_linked_campaign`; the related IJP paper is absent. Merot's stepped-test paper, its unresolved EFM continuation, Molaei's republished curves and other quarantined sources are absent. The near-coordinate sensitivity removes one same-event row and has 308 observations.

Every fitting/calibration/target source partition and its rows are disjoint. Support and query pools are disjoint and cover their curve. Every support count uses a nested prefix and **identical query rows**. Reserved support candidates are not returned to the query set at k=0. Each calibration source contributes one selected condition/query; that query never enters support. Calibrated and full-training tracks have identical target episodes.

Seeded SHA256 orders were independently recomputed. Chronological external episodes correctly parse US month/day/year and place support dates no later than query dates. There is a terminology deviation: ties use SHA256 of stable `row_id` (author-record address), while the amendment says specimen ID. The ordering is deterministic and outcome blind; acknowledge the exact implementation instead of reordering after outcomes.

Panel A has 9 target source blocks, B has 6 and C has 5. Their three seeds are repeated subsamples, not additional independent sources. Different panels have different eligibility/query sets and cannot form one unqualified learning curve. Near-cluster removal can change panel membership and sampling, so it does not isolate a causal effect of removing one specimen.

The external 129 complete specimens form three related diameter conditions in **one campaign**. Three random episodes plus one chronological episode are not four independent campaigns. A bootstrap over that single source cannot supply a nontrivial independent-campaign confidence interval.

Strict calibration has 6/5/4 blocks for A/B/C; external calibration has 6. For alpha=0.1, `ceil(0.9*(m+1))` exceeds m in every case. The literal endpoint-calibrated lower bound is zero life. Its zero empirical violations are vacuous and cannot establish useful reliability. Raw full-training quantiles remain secondary model-based estimates without arbitrary-source coverage guarantees.

A separate isolation test used fixed artificial parameters and poisoned query outcome columns with NaN, invalid events and infinite cycles. Pooled, unpooled-shift and hierarchical quantiles at k=0 and k=3 were unchanged on all ten queries. This checks the prediction API's outcome isolation; it does not exclude every possible form of leakage.

Independent scalar aggregation, without importing the root metric modules, reproduced **6,798 summary cells and 6,390 paired mean/bootstrap cells** across 14 completed runs and 227,310 saved prediction instances. Maximum absolute difference was 1.78e-15. These instances repeat specimens over methods, support counts and seeds; they are not independent experiments. Coverage is separated below.

| Audit group | Runs | Prediction instances | Summary cells | Paired cells |
|---|---:|---:|---:|---:|
| Original completed tracks | 9 | 104,130 | 4,642 | 4,410 |
| Post-result matched-population diagnostics | 2 | 8,358 | 374 | 360 |
| Broader-data sensitivities | 3 | 114,822 | 1,782 | 1,620 |

The broader group comprises all_family, weak_family and broader_fulltraining. All passed arithmetic checks. They include sources not cleared by the strict source gate and remain sensitivities, not primary evidence. No HTML extraction or prior source-validation work was repeated in this extension.

The additional matched-population diagnostic was independently checked without importing model or metric code. All 64 saved population parameter/transformation records match. Its 4,179 hierarchy reference rows differ from original raw predictions by less than 9e-15. Positive-support control quantiles were recomputed by a separate scalar censored MLE and observed-curvature calculation: 1,565 internal rows and 1,188 external rows, with maximum error 2.41e-12. All 408 same-support-count comparison cells and bootstrap endpoints match. Three internal all-runout episodes correctly remain unavailable; none are unavailable externally. Both methods use exactly the same finite query mask for each comparison, with availability reported separately.

This diagnostic is explicitly post-result. It matches the hierarchy's slope, load-ratio coefficient, within-condition scatter and training centering, changing only target-intercept prior borrowing. At k=0 both labels intentionally use the same hierarchical new-condition reference. It is not an unpooled estimator from zero observations. Population parameter uncertainty remains omitted. The diagnostic cannot rescue the original failed criterion.

Historical panel A, raw hierarchical full-training k=3 versus k=0: mean log10 lower-life gain is 0.28410343, with descriptive 95% interval [-0.07398438, 0.56274823]. Risk-upper-endpoint change is -0.06485135, interval [-0.30946214, 0.08293651]. The upper confidence endpoint for the upper identified true risk change is 0.09302295. A positive utility gain and the two-percentage-point safety guard are therefore not established.

Against the matched-population control at k=3, the internal hierarchy's mean log-life advantage is 0.04137, interval [-0.01660, 0.13107]. In the one external campaign it gives longer lower-life estimates but more known dangerous violations: the random-support contrast is +0.15169 log10 life and +6.20 percentage points risk; chronological support gives +0.19197 log10 life and +0.98 percentage points risk. These results do not establish that prior borrowing is uniformly superior.

Final coverage receipt: `split_audit_final_coverage.json`. Detailed receipts: `split_audit_receipt.json`, `split_audit_configurations.csv`, `split_audit_no_query_outcomes.json`, `split_audit_result_tables.json` and `split_audit_same_population.json`. Scripts with the same prefix reproduce the checks. Passing establishes internal split/arithmetic consistency, not physical validation, model novelty or independent scientific replication.
