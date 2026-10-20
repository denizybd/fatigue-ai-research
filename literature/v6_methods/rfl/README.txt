Authoritative v6 two-dimensional RFL control receipt index

Final source: src/v6_rfl_adapter.py
Final SHA256: f85ac7251675dd0eb84a19438f3aee9bb80b6c99ebddac7358108f8de8ac2f2e
No actual fatigue observations were fitted by this development/audit branch.

Authoritative checks:
- synthetic_receipt.json:23 tests; independent Hermite comparisons, censoring,
  analytic k0, infinity atom, scalar reduction, isolation, failure guards.
- independent_audit.json and independent_conjugate_audit.json: separate reviewer,
  exact conjugate limiting case, coarse-u reweighting and tail-bound algebra.
- benchmark_suite_final.json + final_clean_ordinary_q3/q10.json and
  final_clean_broad_q3/q10.json: sequential clean timings at final source hash.
- benchmark_synthetic.py and independent_conjugate_checks.py: replay commands.

Other *_runtime*, score_path_synthetic_benchmark.json and development cleanup
receipts are superseded/intermediate diagnostics, not final timing claims.
Some old diagnostics ran concurrently; their wall times are contention-dependent.
The cleanup receipt records only this agent's obsolete synthetic processes,
never user jobs, real fits or the old Diller source download.

Truncation/pruning bounds are conditional on the fixed positive Gamma rule.
Order/refinement differences are numerical resolution diagnostics, not formal
continuous-Gamma error theorems. Population/hyperparameter uncertainty is plug-in.
The prior describes target statistical shifts, not physical-build covariance.
No R90C90, physical validation or real-data improvement follows from these tests.
