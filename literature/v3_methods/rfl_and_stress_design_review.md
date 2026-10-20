# Phase-3 physical baseline and stress-selection review

20 October 2026. This note precedes real campaign fitting by this subtask. Only synthetic outcomes were generated/read here. Phase-2 aggregate failure findings and the frozen phase-3 design were reviewed.

## Primary-source boundary

[Pascual and Meeker (1999), *Estimating Fatigue Curves With the Random Fatigue-Limit Model*](https://doi.org/10.1080/00401706.1999.10485925), sections 2 and 3.1 (printed pp. 278–279), defines a specimen-specific random fatigue limit, a conditional stress-life distribution above that limit, and the marginal density/CDF obtained by integration. Its likelihood uses failure densities and right-censor survival probabilities. Both normal and smallest-extreme-value distribution choices are explicitly allowed. The reviewed [journal-archive full text](https://www.stat.cmu.edu/technometrics/90-00/vol-41-04/v4104277.pdf) is retained with its SHA256 manifest. Its normal-normal option supports our baseline distributional choice.

[Trombley et al. (2025)](https://doi.org/10.1038/s41598-025-97031-1), section “The random fatigue limit model”, explicitly states that their RFL fitting uses a Weibull distribution and MLE following reference 68: Engler-Pinto Jr., Lasecki, Frisch Sr. and Allison (2007), *Statistical approaches applied to very high cycle fatigue*, VHCF4, pp. 369–376. Reference 77 is Pascual–Meeker (1999). Reference 67 is the different 2005 SAE paper DOI 10.4271/2005-01-0802. These references must not be conflated. The 2007 author-posted [full text](https://www.researchgate.net/publication/293110316_Statistical_approaches_applied_to_very_high_cycle_fatigue) describes RFL and censored MLE, but our implementation does not claim to reproduce its Weibull fitting or the published Trombley curves.

[Pascual (2003), *Theory for Optimal Test Plans for the Random Fatigue-Limit Model*](https://doi.org/10.1198/004017003188618760), Technometrics 45(2):130–141, already derives RFL Fisher information and plans for life quantiles, fatigue-limit quantities and D/Ds criteria. Its official publisher abstract was inspected; full-text access was blocked. [Pascual (2004)](https://doi.org/10.1109/TR.2004.829140) addresses planning with a known fatigue-limit distribution. Thus “select stress levels by information” is established prior art. The broader [Lee et al. sequential Bayesian ALT paper](https://par.nsf.gov/servlets/purl/10110948) also predates this experiment. A contribution requires new and useful evidence under source/build shift, censoring and limited tests, not a novelty claim for acquisition alone.

## Implemented model and numerical contract

`src/v3_rfl.py:NormalNormalRFL` uses base-10 logs, positive Gamma with log10(Gamma) normal, normal conditional log life, and a strictly negative stress slope. The conditional mean is

    a + b*log10((S-Gamma)/Sref) + c*(R-Rbar) + u, b<0.

`Sref` and `Rbar` are fixed from training covariates. The load-ratio term, source-balanced working likelihood, small slope penalty and target adapter are implementation extensions, not assertions that the original paper used them.

Finite-failure mass is exactly `pS = Phi((log10(S)-muGamma)/tauGamma)`; its complement is a literal atom at infinite life. A predictive alpha quantile is infinite when alpha >= pS. No finite replacement or favorable clipping is applied. Runout likelihood includes both this atom and the survival of the finite-life mixture. The derivative of the finite CDF matches the failure density.

Gamma integration transforms a truncated-normal probability to the unit interval, then uses a sine-square endpoint map and Gauss–Legendre integration. This avoids the parameter-dependent discontinuities produced by masking fixed Hermite nodes at Gamma=S. Default order is 96. Independent direct integration and order-96/192 synthetic comparisons test the calculation; a real-data order sensitivity remains required.

Three fixed training-only initializations and fixed training-based bounds are retained in each fit receipt. The selected solution is the minimum objective among numerically converged starts. Bound hits, low failure/stress counts, all starts, gradients and explicit convergence status are recorded. A boundary fit is not evidence that the fatigue-limit distribution is well identified. With no converged RFL start, the predetermined `fallback=True` behavior activates the training censored-Basquin fit, marks RFL success false and reports `fallback_active`; it must be reported separately. `fallback=False` raises instead. Population parameter uncertainty is omitted.

The optional scalar target shift has a proper normal prior whose SD is supplied from the training hierarchical Basquin fit. At k=0, its convolution with normal life scatter is exact. At positive k, partitioned global quadrature integrates its posterior using only revealed supports; no log-concavity or single-mode assumption is made. A normal-prior tail bound is checked. The adapter changes finite lives, not Gamma or its infinite-life mass. It is **not a hierarchical RFL population posterior**. Cache keys include the revealed endpoints and training prior, never query outcomes.

## Common-query acquisition design

The root protocol `protocols/v3/frozen_design.txt` fixes all query IDs before any acquisition. All policies see the same remaining candidate covariates, administrative cycle cap and tie ranks. Candidates are actual recorded specimens at recorded stresses; replay cannot invent a new stress level or fabricate its outcome. Reveal one selected endpoint at a time, truncate the support at the administrative cap, then update. Test k=3/5/10 only when feasible. Preserve the same query endpoints for all policies/models.

Useful outcome-blind controls are random, stress-span and high-stress selection; a middle-stress control is another plausible sensitivity. The frozen implementation uses the first three and sequential expected information reduction for query prediction variance. It shares this one acquisition sequence across all prediction models, so model comparisons use the same acquired tests.

For a censored normal location model, let z=(logC-mu)/sigma. One test's expected location information is

    I = [Phi(z)-z*phi(z)+phi(z)^2/Phi(-z)]/sigma^2.

For target intercept/slope covariance V, candidate design x and query moment Q=mean(x_query*x_query'), the rank-one reduction score is

    I * (x' V Q V x) / (1 + I*x' V x).

This is an approximate local design criterion. It uses the cap C and a predictive model, not the unrevealed candidate runout/end time. It does not optimize RFL shape uncertainty or prove optimality. A candidate-outcome perturbation test should leave the next selected candidate unchanged before revelation.

The same RFL, censored pooled/hierarchical Basquin and matched target-intercept controls must be evaluated under every policy. Compare reliability identification limits, availability, infinite bounds, log-life gain and observed support-cycle cost together. A higher life bound is not sufficient. Campaign, build and specimen levels must remain distinct: repeated splits and several builds from one campaign do not create new independent campaigns. With one campaign no campaign-bootstrap CI is defensible; with few campaigns wide/unstable intervals are expected.

## Verification receipt

The synthetic test module covers independent direct CDF integration, infinite mass/quantiles, inversion, stress monotonicity, censor survival, density derivative, exact no-support convolution, all-failure/all-runout/mixed posterior integration, query-outcome isolation, support-cache invalidation, quadrature sensitivity and training multistart receipts. It validates numerical behavior only. The machine-readable local receipt is `synthetic_test_receipt.json`. No physical reproduction, external safety guarantee or original Weibull replication is established.
