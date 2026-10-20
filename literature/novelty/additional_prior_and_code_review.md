# Additional prior and pre-fit code review

Date: 2026-10-20. Reviewer: novelty/statistical-literature parallel agent. No real-data fits or outcomes were inspected. Initial protocol/code snapshot was local Git `56bd2dd`; later uncommitted corrections were read as noted below. No experiment implementation was edited by this reviewer.

## Additional prior: evidence and scope

**I.J. Wietecha-Reiman, S.M. Sabol, T.A. Palmer.** “Developing statistical tools to analyze historical stress-controlled fatigue data in additively manufactured austenitic stainless steel.” *Materials Science and Engineering: A* 902, 146580 (June 2024). [DOI](https://doi.org/10.1016/j.msea.2024.146580), [official full manuscript](https://www.osti.gov/pages/servlets/purl/2581204).

The 39-page accepted manuscript was extracted completely; pages 9, 17, 18 and 35 were rendered and visually checked. Pages 5–7 describe literature digitization/standardization and 374 retained L-PBF316L points after requiring tensile properties. Equation5/page9 explicitly blocks by publication source. Equations12–13/pages16–17 give parametric confidence/prediction intervals; page18 checks leverage/residual assumptions; AppendixB/page35 diagrams model selection/diagnostics. These are strengths for explanation and scatter analysis. No held-publication prediction, censoring likelihood, runout evaluation or rejection policy was identified in the inspected text/figures; this is a reporting observation, not proof of mishandled runouts. The page29 data statement names `github.com/wietecha-reiman/Fatigue-AM-316L`; a current fetch returned404, so data were not acquired. The manuscript uses an Elsevier user license, not an inferred CC-BY license. **Novelty boundary:** source-associated variability and interval-based statistical AM316L modelling are prior work; prospective unseen-source censored decision reliability remains a distinct question, not a demonstrated new-method claim.

Archive: `WietechaReiman2024_osti2581204.pdf`, corresponding extracted `.txt`, rendered page PNGs, `WietechaReiman2024_manifest.json` (bytes/hash/access time/page count), and `WietechaReiman2024_crossref.json`. Exact online date was not verified; Crossref DOI creation was 28 April2024 and issue date June2024. Creation is not substituted for publication.

## Review of protocol and implementation

Files read: `protocols/v1_pre_outcome.md`, `src/run_experiment.py`, `src/features.py`, `src/evaluation.py`, `src/models.py`, `src/summarize.py`. The code review is independent conceptual scrutiny, not a claim of independent data collection or numerical reproduction.

### Confirmed aligned implementation

- Censored Gaussian likelihood uses survival terms for runouts; analytic location/log-scale derivative signs are consistent with the stated model. Source-likelihood weights and bootstrap source multiplicities implement the stated equal-source weighting.
- Calibration now scores **b−y_observed** and uses **b−q**, consistently conformalizing the lower-decile predictor. It does not double-subtract location-based residual noise.
- `risk_status` uses the strict directional event and correctly marks ambiguous runouts rather than treating their endpoint as failure time. Factor2 severity uses the corresponding log10 factor.
- All imputation/encoding fits use fitting rows; support and bootstrap-instability features do not consume test outcomes. Calibration/fit/test source disjointness is asserted.
- The finite calibration order statistic returns infinity when too few scores exist. Raw lower-decile, endpoint-calibrated, and source-cohort bounds remain distinct in saved predictions.
- The summarizer preserves risk endpoints and source-level paired contrasts; median location-minus-bound is used for conservatism, with stress and censoring mixture diagnostics.

### Findings sent before fitting

| Finding | Consequence | Follow-up observed |
|---|---|---|
| Total13 groups leaves only3 fitting sources after holding1 out and reserving9 calibration sources, conflicting with the stated minimum4 | Feasibility could be overstated | Code now requires total14 and asserts fitting-source count≥4; protocol wording needs a dated clarification |
| Matched-gate stable sorting breaks ECDF-score ties by original row order, which may be sorted by stress/life | Outcome-related ordering could contaminate nominally outcome-blind ranking, especially when OOD ranks saturate | Summarizer now uses a fixed row-ID/seed hash as a secondary lexsort key |
| Checkpoints were reused solely because a filename existed | Amended data/code could silently reuse stale predictions | Code now records and checks data/code/settings signature, rejecting unsigned checkpoints |
| Protocol H2 success wording was qualitative | Post-hoc flexibility in deciding whether the combined gate succeeded | Dated amendment `protocols/v1_2_prefit_claim_rule.md`, Git8bad82e, now freezes an exact positive-claim rule |
| Numeric medians originally ignored NaN but not infinity | Nonfinite metadata could contaminate encoding despite some finite training values | Verified finite-only median correction in `src/features.py` |
| Aggregation dropped every nonfinite utility value | Vacuous zero-life bounds could be excluded from conservatism summaries | Verified explicit positive-infinity conservatism handling in the summarizer |

### Remaining interpretation limits to retain

The source-cohort bound concerns a complete exchangeable cohort, including its size/sampling mechanism. It does not certify a fixed new manufacturing process. Selecting a subset preserves an unconditional all-members-covered event, but does not imply conditional per-accepted-part coverage.

The support score operates in a chosen encoded feature space. When a training feature is constant/all-missing, replacing its scale with1 gives novel values a raw-unit-dependent influence. This is a transparent fixed heuristic, not a physical measure of process equivalence; record that limitation and do not adjust it after outcomes to rescue the gate.

A source-bootstrap draw could contain no positive-weight failure if some sources consist only of runouts. The estimator correctly rejects that unidentifiable fit, but the runner needs a recorded failure/handling policy if such a draw occurs; silently resampling until convergence would change the stated bootstrap. Main defaults should require at least two bootstrap replicates for a finite SD; the preregistered count is8.

Source-average risk after rejection should be accompanied by source availability and valid-source/seed counts. A lower known-violation fraction does not identify a true all-specimen risk reduction if censoring contrast bounds cross zero. Seeds and overlapping leave-source-out training fits do not create independent source evidence. Convergence, sigma bounds and stress-monotonicity diagnostics should be included in the final report regardless of model performance.

## Bibliographic record

The corresponding BibTeX entry was added to `references.bib`. The paper should be cited alongside the group-splitting and conformal literature when motivating the main question. It supports the relevance of publication-related variability; it does not validate our gate or its eventual results.
