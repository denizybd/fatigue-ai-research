# Post-result matched-population control

2026-10-20. Explicitly written AFTER the original v2 strict, full-training and external outcomes were inspected, and BEFORE this diagnostic was executed. This is an exploratory ablation and cannot rescue or replace the original prespecified primary criterion.

The initial unpooled-shift control borrowed the pooled Basquin slope and total residual scatter. The hierarchical method instead estimated a different slope and decomposed within-condition scatter from between-condition variability. Therefore its contrast with that control does not isolate the effect of target-intercept shrinkage or a target prior.

Use the exact frozen strict full-training and external full-training episodes. Reconstruct each previously fitted hierarchical population from its saved parameters and the matching TRAINING data transformation; do not refit, tune or select populations. Retain the same target support IDs, support sizes, seeds and common query sets. The original predictions remain immutable.

The new matched-population unpooled control uses exactly the hierarchy's population slope, load-ratio coefficient and within-condition sigma, estimating only a target-condition intercept by its censored support likelihood. It omits the target population prior. Include the same inverse observed-curvature predictive intercept variance as the original unpooled control. With all failures this is the exact known-sigma flat-prior normal predictive variance; with censoring it is a Laplace approximation. If all supports are runouts, the intercept is unidentifiable and the method is unavailable rather than silently repaired.

At k=0 both labels use exactly the original hierarchy's new-condition predictive variance sigma^2+tau^2 and original lower decile. This is an explicit shared zero-shot reference, not an unpooled estimator with zero observations. For k>0 compare the hierarchical and matched unpooled predictions on the same available query pairs, reporting the missing-episode fraction and all-runout cause.

Report raw model-based lower deciles only, availability, known/ambiguous violation intervals, absolute lower-life levels and paired differences. Compare methods at the same k as well as each to k0. Include paired partial-identification risk-change endpoints and descriptive source-bootstrap intervals; one external campaign has no between-campaign interval. This diagnostic conditions on estimated population parameters and does not propagate their uncertainty. It does not create a coverage theorem, R90C90 estimate, or novel method.
