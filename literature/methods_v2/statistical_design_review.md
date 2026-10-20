# Statistical design review for phase 2

Date: 2026-10-20. This review was prepared before v2 real-data model fits. It incorporates the already observed v1 outcomes, so the reused public corpus is a new exploratory benchmark, not a fresh confirmatory experiment. A genuinely new external campaign must be frozen independently.

## Executable primary question

For an entire unseen provenance family, does observing three randomly selected endpoints from one new database condition improve the lower 10% life prediction on a fixed disjoint query set, while keeping dangerous overprediction near its 10% target and retaining useful life magnitudes?

A condition here is a digitized S-N data series. It is not automatically an independently fabricated batch, and a row is not a verified unique specimen. Keep all curves or articles suspected of reusing the same campaign on the same side of the split. Remove near-duplicate rows within each target condition before creating support/query episodes, using a rule frozen by provenance analysis, to avoid showing the model a coordinate copy of a query result.

Use separate fixed-query panels: primary k=0,3 with at least8rows/condition and at least5queries; secondary k=0,3,5 with n>=10; tertiary k=0,3,5,10 with n>=15. The original primary corpus has 70conditions/24blocks at n>=8, 51/17 at n>=10 and11/7 at n>=15, before v2 provenance corrections. Do not connect aggregate points from these different panels as though they were one learning curve. Within a panel, reserve max-k supports once, keep all other rows as the common query set, and use nested prefixes of an outcome-blind seeded row-ID permutation for the smaller k. Average episode repeats within condition and condition means within provenance family. Repeated seeds are not new physical tests.

## Strong executable baselines

1. Pooled censored lognormal Basquin: y=a+b log10(S)+c R+epsilon, b<0, epsilon~N(0,sigma²). This simple model was competitive in v1; it must remain visible. Train-only median imputes missing R. Pooled model does not update from target supports.
2. Shared-slope target-intercept adaptation: keep fitted b,c,sigma fixed, estimate only the target intercept from k support endpoints using the censored likelihood. Include inverse observed curvature in approximate predictive variance. With uncensored normal data and known sigma this gives the exact flat-prior predictive variance sigma²(1+1/k). With censoring it is a Laplace approximation. All-runout support has no finite flat-prior MLE; mark unavailable rather than substituting an arbitrary shift or treating runouts as failures. Report availability and paired comparisons on the same eligible episodes separately.
3. Hierarchical censored Basquin: y_ij=m(x_ij)+u_j+epsilon_ij; u_j~N(0,tau²). Integrate u_j in the training marginal likelihood, and integrate its posterior after seeing target supports. This is empirical Bayes with population parameters estimated from training, not a full Bayesian fit. Weight condition marginal log likelihoods equally within each source, then weight provenance sources equally. This is a source-balanced composite likelihood with working condition independence; it does not establish source independence or account fully for shared-source correlation.

The implementation in src/v2_models.py constrains stress slope negative, uses proper density/survival contributions for failures/runouts and adaptive Gauss-Hermite integration around the unique scalar posterior mode. Population sigma and tau are learned without target query labels. At k=0 the predictive variance is sigma²+tau². Plugging in sigma alone is insufficient for a new condition.

## Scalar posterior and predictive lower bound

For support D={(x_i,z_i,delta_i)}, z_i=log10 min(T_i,C_i), let

p(u|D,theta) proportional to exp(-u²/(2tau²)) times product_i [phi((z_i-m_i-u)/sigma)/sigma]^delta_i [1-Phi((z_i-m_i-u)/sigma)]^(1-delta_i).

The predictive CDF at query x is integral Phi((y-m(x)-u)/sigma) p(u|D,theta) du. Invert it at alpha=.1. This integrates target intercept uncertainty and specimen scatter. All-runout posteriors are proper under the normal population prior. For all-failure supports, v=(tau^-2+k sigma^-2)^-1, h=v sum(z_i-m_i)/sigma² and the predictive law is N(m(x)+h,sigma²+v); this provides an exact implementation test. For mixed censoring, the log posterior is strictly concave; adaptive quadrature is substantially safer than a fixed prior-centered81node grid when tau/sigma is large.

The fit estimates theta=(a,b,c,sigma,tau). Its finite-training uncertainty is omitted by the main plug-in predictive distribution. A provenance-block bootstrap of TRAINING sources can propagate population uncertainty as a sensitivity: refit each bootstrap population, update each replicate using the same supports, average replicate predictive CDFs, and invert the mixture. Never average individual lower quantiles and call that the mixture quantile. Bootstrap intervals with reused outer training sets remain descriptive. A two-level source-plus-condition hierarchy is another sensitivity, but many curves per article do not provide many independent sources.

## Calibration: what is and is not justified

Endpoint split-conformal scores q10(x)-log10 min(T,C) can yield a conservative bound on true life under the appropriate exchangeability assumptions. They do not fix arbitrary source shift. Multiple correlated calibration rows do not create a row-exchangeable experiment merely because sources are weighted equally. Calibrate the same support-update procedure at each k on held-out calibration families; otherwise adaptation and calibration target different algorithms. Keep target family out of both population training and calibration.

Gui et al. (2024), *Conformalized survival analysis with adaptive cut-offs*, Biometrika111:459-477, DOI10.1093/biomet/asad076, explicitly assumes censoring time C is observed for all units, including failures (section1.2), plus conditionally independent censoring. Its covariate-dependent cutoffs and weighting can be more efficient than endpoint calibration. The current database does not record potential C for failures, so directly applying that algorithm is unjustified. A reported uniform stopping rule in a new source could supply C, but it must be verified rather than inferred from the largest endpoint. https://academic.oup.com/biomet/article/111/2/459/7458444

Sesia and Svetnik (2025), *Doubly Robust Conformalized Survival Analysis with Right-Censored Data*, ICML/PMLR267:53989-54029, offers DR-COSARC for ordinary right censoring. It estimates a censoring model, imputes latent C conditional on C>observed failure time, and uses weighted conformal survival prediction. Its asymptotic double robustness is not a source-shift guarantee. It still requires iid calibration/test draws and conditionally independent censoring (section2.1), nuisance estimation/positivity conditions, and a correct adaptation of its theorem to clustered meta-episodes. It is a relevant future comparator; missing C alone does not make all modern survival conformal methods infeasible. Official R code was read, not executed here. https://proceedings.mlr.press/v267/sesia25a.html ; https://github.com/msesia/conformal_survival

A small k target-only distribution-free calibration is intrinsically limited: with three calibration endpoints, the finite-sample90% split-conformal rank ceil(.9*(3+1)) is4, exceeding3, and produces an infinite correction/zero lower-life bound. Informative bounds after three tests necessarily borrow assumptions or historical populations. Do not market the empirical-Bayes result as a distribution-free90% guarantee.

## Outcomes and falsification

Primary risk is the all-query identification interval [known violations/n,(known violations+ambiguous runouts)/n] for L>T; it is not a confidence interval. Report per-condition and equal-family risk, raw bounds, calibrated bounds if used, and severe L>2T. Utility should use identical queries: paired log10(L_k/L_0), lower-life quantiles, fraction below1cycle, and a reference life requirement chosen before outcomes if engineering context supports one. Reducing median-minus-bound alone can hide an inaccurate median. Shrinking uncertainty is not automatically useful if bounds were already too optimistic.

A defensible positive result would improve paired useful life while retaining risk within a prespecified tolerance, show family-level uncertainty and outlier failures, beat pooled and unpooled-shift baselines, survive provenance/dedup/parameter-uncertainty sensitivity, and transfer to an independently documented campaign. Failure to meet the risk target means the adapted bounds are not demonstrated reliable, even if MAE improves. An aggregate target does not establish per-condition reliability. No result on one campaign certifies a general laboratory-to-laboratory method.

## Existing fatigue and external-campaign context

Liu, Lu and Hoogenboom (2017), *Hierarchical Bayesian fatigue data analysis*, IJF100:418-428, DOI10.1016/j.ijfatigue.2017.03.043, already studies small fatigue samples, hierarchical priors and predictive P-S-N curves including both parameter and observation scatter. Hierarchical borrowing for few fatigue tests is prior art. The executable v2 model is a benchmark implementation, not a new hierarchical method. https://repository.tudelft.nl/record/uuid%3A0ba81de0-e1b6-4461-911f-af2db3a645e8

Trombley, Birnbaum and Allison (2025), DOI10.1038/s41598-025-97031-1, reports130as-built specimens at three diameters, four builds,20kHz andR=-1. Failure is a200Hz resonance shift indicating a crack, not complete fracture; runout is10^8cycles. Supports are retrospectively sampled from a mix of intermediate/high-stress and staircase testing, so they cannot be interpreted as a validated sequential experimental-design policy. The authors use Weibull random fatigue-limit fitting, making curvature/fatigue-limit sensitivity relevant. Basquin-only comparison should acknowledge this limitation. https://www.nature.com/articles/s41598-025-97031-1

The Pascual-Meeker random fatigue-limit model (1999), DOI10.1080/00401706.1999.10485925, uses specimen-specific random gamma: logN=a+b log(S-gamma)+epsilon whenS>gamma, otherwiseN=infinity. A single deterministic shifted-stress threshold is not a reproduction of that model. An executable finite curvature sensitivity is a continuous monotone two-slope Basquin curve with a knot fixed from TRAINING stresses; it cannot be called the original Weibull-RFL model. https://www.stat.cmu.edu/technometrics/90-00/vol-41-04/v4104277.pdf

## Verification receipt

Ten synthetic tests pass at initial code handoff: conjugate posterior and exact marginal likelihood; independent scipy.quad check for mixed censoring; proper all-runout posterior;41vs81adaptive quadrature stability for a narrow likelihood far from its prior center; analytic marginal likelihood gradient; predictive posterior variance and monotonicity; explicit all-runout MLE unavailability; pooled slope/scatter recovery; hierarchical variance recovery; train-only R imputation. No real-data outcomes were fitted by this agent. These computational checks are not physical validation or independent scientific replication.
