# Independent critical audit

Integrity checks passed: **True**.
Checked 87 completed folds, 30402 saved predictions and 2001 source/seed/policy cells.
Strong preregistered combined-gate claim passes: **False**.

This audit recomputes split integrity, training-only encodings, all directional-risk counts, pooled/source averages and primary contrasts. It replays calibration and bootstrap gates on two named folds. It is code/analysis verification, not new external validation.

## Optimization receipts

{
  "fits": 957,
  "not_converged": 87,
  "sigma_at_bound": 0,
  "by_model": {
    "basquin": {
      "fits": 87,
      "not_converged": 0,
      "max_iterations": 13,
      "max_gradient": 4.183434953818565e-06
    },
    "linear": {
      "fits": 87,
      "not_converged": 0,
      "max_iterations": 205,
      "max_gradient": 8.773917795115114e-05
    },
    "linear_bootstrap": {
      "fits": 696,
      "not_converged": 0,
      "max_iterations": 664,
      "max_gradient": 0.00013801780605394981
    },
    "mlp": {
      "fits": 87,
      "not_converged": 87,
      "max_iterations": 1500,
      "max_gradient": 0.014680453200254073
    }
  }
}

## Primary matched-availability contrasts

| Combined minus | Known-risk difference | Descriptive 95% interval | Censoring identification interval | Seedwise differences | Passes rule |
|---|---:|---|---|---|---|
| distance | 0.001296 | [-0.006386600629406999, 0.00891340575793608] | [-0.0034847241967683276, 0.007897228505041685] | {'0': 0.0019160090800994464, '17': -0.002231464200243832, '42': 0.004204326525083157} | False |
| instability | -0.000632 | [-0.013423042197362721, 0.009090337569708442] | [-0.009070853093542554, 0.005968729302562365] | {'0': 0.003610521864275313, '17': -0.00025352487836871596, '42': -0.005253623188405796} | False |
| random | -0.003766 | [-0.01164581602715798, 0.0027274616032335075] | [-0.012825946077992863, 0.0028353967737082693] | {'0': -0.00021621188087536485, '17': -0.006483557293386294, '42': -0.004596854614799848} | False |

## Simultaneous-cohort target diagnostic

Protocol clarification v1.4 records this target before aggregate result inspection. A source cohort is known to fail simultaneous coverage if any member has an observed violation; otherwise ambiguous runouts leave its status unresolved. Three seeds do not make these independent cohorts.

| Model | Bound | Known failed cohort-seed instances | Ambiguous | Cohort-failure identification interval |
|---|---|---:|---:|---|
| basquin | cohort_max | 4/87 | 0 | [0.045977, 0.045977] |
| basquin | endpoint_pooled | 50/87 | 0 | [0.574713, 0.574713] |
| basquin | model_q10 | 50/87 | 0 | [0.574713, 0.574713] |
| linear | cohort_max | 4/87 | 0 | [0.045977, 0.045977] |
| linear | endpoint_pooled | 46/87 | 2 | [0.528736, 0.551724] |
| linear | model_q10 | 62/87 | 0 | [0.712644, 0.712644] |
| mlp | cohort_max | 5/87 | 0 | [0.057471, 0.057471] |
| mlp | endpoint_pooled | 33/87 | 2 | [0.379310, 0.402299] |
| mlp | model_q10 | 71/87 | 1 | [0.816092, 0.827586] |

## Failures

"None detected in checked scope."

## Limits and critical interpretation

- Numerical nonconvergence exists; inspect model/source-specific receipts before performance claims.
- All rows derive from the public literature database; source-block withholding is not independent newly collected external experimental validation.
- Near-coincident curves define conservative provenance blocks, not certified physical specimen identity.
- Risk intervals are empirical censoring-identification bounds; source bootstrap intervals are descriptive and do not repair distribution shift.
- Numerical replay uses the same estimator class; independently recomputed risk logic is a distinct calculation, not an independent scientific replication.
- Source-average headline rates are actually averages over 29 conservative source-family blocks, not 37 independent publications.
- All MLP fits failed the numerical convergence flag; neural-model performance remains a numerical-budget-limited diagnostic, not a validated architecture comparison.
- Results concern the frozen feature representation, homoscedastic AFTs and eight-bootstrap rank gate; they cannot establish that all BNNs/AM-ML models are unreliable or that all support-aware gates fail.
- Whole-cohort violation flags were specified by protocol clarification v1.4 before aggregate result inspection; the auditor independently recomputed those flags and their meaning.

Full machine-readable checks, sampled replay details and independent summary are in `independent_audit.json`.
