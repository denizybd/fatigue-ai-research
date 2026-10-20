# Final independent claims review

Date: 20 October 2026. Reviewer: parallel novelty/statistical-audit agent. Scope: the English manuscript source (`manuscript/paper_content.json`), email and one-page brief, Turkish technical Q&A/next steps, the numerical-claims receipt, primary/sensitivity tables, neural optimization receipts, and the full-reproduction comparison. No new scientific experiments were run for this final review. PDF rendering/layout QA is the root agent's separate task; this reviewer does not claim to have visually checked the final PDFs.

## Verdict

**No unresolved substantive numerical mismatch or unsupported central claim was identified in the reviewed scope after the requested wording and receipt corrections.** The package supports a reproducible, limited public-data pilot and a failed prespecified gate hypothesis. It does not establish a new uncertainty algorithm, a reliable design rule, physical validation, a successful reproduction of Centola's BNN, or publication readiness.

## Claims checked against retained evidence

| Claim | Evidence checked | Assessment |
|---|---|---|
| Public S-N flattening: 15,146 observations / 1,610 conditions / 459 DOIs | Direct counts in `data/processed/all_sn_observations.csv`; all 459 source identifiers are DOI-like | Consistent |
| Broader ordinary-316L L-PBF subset: 1,473 observations / 160 conditions / 46 DOIs | Direct counts in `ss316l_lpbf_all.csv` | Consistent |
| Primary: 1,126 observations / 120 conditions / 37 DOIs / 29 conservative blocks; 987 failures and 139 runouts | Primary CSV, grouping report, earlier complete split audit | Consistent; blocks are precautionary provenance units, not verified independent physical campaigns |
| Missing power 548, scan speed 533, hatch spacing 684, heat temperature/time 816 each | Direct finite-data table checks | Consistent; imputed values are not presented as measurements |
| Rich-linear raw / pooled-endpoint / cohort-max risk intervals | Primary summary and independent scalar audit | 28.97–30.77%, 14.50–15.40%, and 0.197%, respectively; correctly limited to the frozen rich-linear model and block-balanced estimand |
| Heterogeneity: five zero-known-violation blocks; 21 above 10% | Direct row-based reconstruction, averaging seeds within blocks | Consistent; not generalized to all neural/AM models |
| Combined-gate H2 failed | Frozen v1.2 rule; source/seed cells; paired contrast recomputation | Correct. Per-seed signs fail required comparisons, all primary descriptive intervals include zero, and all censoring identification contrasts include zero |
| Primary cohort-max whole-cohort failure 4.60%; pooled endpoint 52.87–55.17% | Independently reconstructed cohort flags; protocol v1.4 | Correct; manuscript clearly says cohort-seed instances are not 87 independent campaigns |
| Weaker-edge grouping/split sensitivity cohort failure 17.86% | Sensitivity table | Correct; changed training/calibration membership is acknowledged, avoiding a causal claim about grouping alone |
| Primary MLP 0/87 convergence; extended-cap sensitivity 87/87, maximum 9,183 iterations | Primary fold receipts and extended `fit_statuses.csv` | Correctly separated. The extension changes only the numerical cap, is post-result, and does not replace the primary experiment or establish architecture ranking |
| Extended MLP raw / endpoint / cohort intervals | Extended summary | 40.17–44.93%, 9.30–10.06%, 0.234–0.246%; stated values match |
| Cohort-max rich-linear life magnitude: approximately 141 cycles; 4.23% below one cycle | Direct primary prediction arithmetic plus `life_bound_utility.csv` | Exactly 143/3,378 repeated prediction instances below one cycle (4.2333%); median 141.394 cycles. The text correctly distinguishes repeated seed predictions from unique specimens |
| Numerical claims receipt | Recomputed hashes of all seven named inputs after refresh | All seven match the current named inputs |

The primary source-block audit previously checked all 87 folds, 30,402 prediction rows and 2,001 source/seed/policy cells, with no integrity mismatch. It reconstructed training-only encodings, source-family disjointness, distances, thresholds/acceptance flags, risk and utility metrics, and primary contrasts. Two selected folds replayed calibration and bootstrap gate calculations. This is computational and critical verification, not independent experimental replication.

## Full computational reproduction

The root's complete rerun covers primary, DOI-only, random-row, approximate-deduplication, weak-edge, naïve-censoring and extended-MLP configurations, with all three seeds. This reviewer independently compared the bytes/hashes of every original/replayed `predictions.csv` and `summary.csv`: **all 14 file pairs match**, consistently with `full_reproduction_comparison.json` and its zero numeric-difference report.

That establishes deterministic reproduction in the pinned local environment. It does not establish portability across arbitrary numerical-library/platform versions, new physical data, independent model implementation, or future-source reliability.

## Fair treatment of prior work and source status

- The manuscript recognizes that the transfer continuation already withholds experimental datasets. It does not depict that study as random-row-only validation.
- It recognizes the topology continuation's case-specific risk-volume checks and discussion of physical validation. It does not accuse the authors of ignoring component-scale limitations.
- Wietecha-Reiman's publication blocking, Di Maggio's complete-curve evaluation, and Wu's splitting/baseline comparison are acknowledged as limiting novelty.
- Wu is labelled with its 2027 issue date and metadata/abstract availability at the search cutoff; its unacquired full text is disclosed. Exact online publication date is not invented.
- Boruah is labelled an arXiv preprint; no journal acceptance is asserted. The inspected manuscript version versus revised metadata distinction is retained.
- Conformal survival, hierarchical inference and distribution-shift assumptions are distinguished from R90C90 and from a safe decision rule.
- The revised wording says Centola's raw data/code **were not obtained for this study**, with data reported available on request. It avoids claiming global unavailability or author withholding.

The search remains targeted rather than exhaustive. Some closest related preprints/conference abstracts are in the literature audit rather than the short manuscript bibliography. A submission-stage refresh/full-text review remains appropriate; present wording makes no first-method claim that depends on their absence.

## Corrections raised and resolved

1. Removed global-unavailability wording about Centola's data/code.
2. Replaced Turkish Q&A language implying leave-laboratory-out or verified source-family independence with publication/provenance-block language.
3. Replaced an ambiguous phrase suggesting independent external open data with a separate open-data method evaluation.
4. Refreshed the extended-MLP status-file hash after its postprocessing export stabilized; all receipt hashes now match.
5. Requested an explicit distinction between censoring-identification uncertainty and digitization error. The root reports integrating that limitation in Section 6. Digitization error can change strict boundary classifications and is not included in the reported runout identification intervals.

The final small wording edits require the root's final PDF rerender/visual check; this is a presentation check, not a remaining scientific experiment in this review.

## Limits that should remain visible

The 29 blocks do not establish 29 independent manufacturing campaigns. Approximately digitized endpoints and default metadata are not raw specimen records. Equal-block and pooled-row risks differ. Identification bounds cover censoring ambiguity, not all errors. Bootstrap intervals are descriptive because fits share training data. The feature-distance heuristic and eight-bootstrap instability score are fixed choices, not physical support proofs. The homoscedastic models do not represent every strong hierarchical, physics-informed or Bayesian baseline. Complete-cohort calibration depends on cohort size, membership and exchangeability, and the weak-edge sensitivity exposes fragility. Numerical convergence is distinct from physical correctness.

The communication package appropriately asks for a limited technical comment/source-to-condition map. It does not invent the user's credentials, imply a favorable author response, or present the pilot as a safe engineering tool. No external contact, upload or publication was performed by this reviewer.
