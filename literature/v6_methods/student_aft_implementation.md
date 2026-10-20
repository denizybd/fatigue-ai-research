The new module `src/v6_student_aft.py` implements a right-censored hierarchical Student-t accelerated-life model. No real fatigue dataset has been fitted during implementation. Its synthetic suite is `tests/test_v6_student_aft.py`.

`StudentAFTConfig(nu=4, scatter='constant', mean='linear', prior_sd=.3)` is immutable. `student_aft_grid()` returns48configurations: ν∈{4,10,Gaussian}, scatter∈{constant,loglinear}, mean∈{linear,two_knots}, and τ∈{.1,.3,1,3}. The width expansion from24to48was requested before any real-data fit. `config.receipt()` serializes Gaussian degrees of freedom as a string. Hyperparameter selection and source-balanced inner validation belong to the parent runner; the module performs no cross-validation or query-based selection.

All variables use log10 life/stress. Training-only centering/scaling gives s=(logS−mean_train(logS))/sd_train(logS), with population standard deviation (ddof0). Missing load ratios use the training median; the ratio is centered at the training mean after this imputation. For one statistical condition,

    Y_i = μ(s_i,R_i) + u + σ(s_i) T_ν,
    u ~ Normal(0,τ²).

The same fixed candidate τ is used in training-condition marginalization and in a new target prior. A linear location has one negative slope. The two-knot location has three negative segment slopes, b_j=−softplus(β_j), and two standardized training-stress quantile knots κ1,κ2 at1/3and2/3:

    μ = a+cR*(R−centerR)+b0*s+(b1−b0)*h1+(b2−b1)*h2,
    hj = max(s−κj,0)−max(−κj,0).

Raw β coordinates are unconstrained and evaluated with stable softplus/expit. Constant scatter fixes γ1=0; otherwise logσ=γ0+γ1*s. γ0 is bounded by log.05andlog2, γ1 by−.5and.5, and cR by−20and20. These are bounds on the reference scale/coefficient, not clipping of query σ. The penalty is exactly `.001*sum(b_j**2+cR**2)+.5*(gamma1/.25)**2`; intercept and γ0 are unpenalized. The mean location is monotone; heteroscedastic quantiles are not guaranteed monotone. A t scale σ differs from its standard deviation, σ√(ν/(ν−2)).

For an event indicator e, the likelihood is the log10-life density raised to e times survival at the observed endpoint raised to1−e. A runout is never recoded as a failure. Two deterministic scale starts optimize the same sum of condition log marginals and the same penalty, using analytic likelihood scores and L-BFGS-B. The successful start with the best training objective is retained. If both fail, the module raises an error rather than silently changing the model. Each observation has unit likelihood weight. This differs from older source-balanced population composite objectives; equal-family validation scores must be provided by the runner. Statistical conditions from a shared source are not certified physically independent.

`intercept_posterior` integrates the scalar u with positive adaptive Gauss-Legendre weights. Order12and24rules are compared for interval mass and posterior moments, with deterministic refinement. These comparisons give numerical error **estimates**, not a theorem bounding interior quadrature error. A separate mathematical tail bound uses the product of failure-density suprema, K, and the proper Gaussian prior:

    omitted evidence ≤ K * P(|Normal(0,τ²)| > radius).

The omitted-evidence bound relative to computed evidence must be below the fixed tolerance (default2e−8), otherwise the interval expands. Node/refinement exhaustion fails closed. Student-t posteriors can have multiple modes; no Gaussian/Laplace target approximation or single-mode collapse is used. Stable logarithmic Student survival handles far tails without probability underflow.

Target support updates only u. It does not refit slopes, knots, scatter, ν or the population prior. Only revealed support stress/ratio/endpoints/events enter the support likelihood; one target condition is required. A posterior cache includes the fitted parameters, fixed configuration, numerical settings, support covariates and revealed endpoints/events. Query outcomes are ignored by CDF/quantile/location prediction. `predict_log_score` necessarily reads query outcomes only to score an already-defined predictive law and labels that fact separately in its receipt.

Accurate posterior normalization alone can miss a much sharper future CDF kernel. Prediction therefore additionally resolves the quadrature mesh using the minimum natural scale derived from **query covariates**; this changes numerical resolution, not the model or its selected parameters. Gaussian convolution and independent direct integrals check narrow-noise/wide-prior cases. Quantiles invert the positive posterior-mixture CDF. Quantiles of component distributions are not averaged.

The runner-facing class is `CensoredStudentAFT(config=...)`, with `fit(frame)`, `predict_quantiles(query,support=None,alphas=(.1,))`, `predict_cdf(log_y,query,support=None)`, `predict_log_score(query,support=None)` and `predict_location(query,support=None)`. Prediction returns log10-life quantiles. Frames use `log_stress,load_ratio,dataset_id`; training/support/scoring additionally use `log_life,event`. `group_id` records training families and validates that each condition belongs to one family. Receipts expose convergence, all starts/bound hits, train-only transformations, quadrature estimates/tail bounds, and uncertainty limitations.

Natural Student/Normal residual variation and posterior target-intercept uncertainty are integrated. Population regression/scatter parameter uncertainty is not integrated. Finite-ν Student errors on log10life imply an infinite uncapped arithmetic mean of N; quantiles, CDF and capped expected testing cost remain finite/well-defined. No lognormal mean-life shortcut is exposed. No cross-configuration model averaging is performed implicitly.

Synthetic checks compare density/survival and analytic derivatives with SciPy distributions, heteroscedastic Gaussian marginal evidence/posteriors with exact multivariate-Normal formulas across τ=.1,.3,1,3, Student posteriors with independent direct integration for failure/runout/mixed support, a separated two-mode posterior, Gaussian/Student convolution, CDF/quantile/density consistency, natural plus posterior variance, query-outcome isolation, target-condition validation, training-gradient finite differences, monotone location/variable scatter, and one genuine48-row synthetic-only multistart fit. These checks do not establish real-campaign reliability, hyperparameter adequacy, laboratory independence or a useful-life improvement.
