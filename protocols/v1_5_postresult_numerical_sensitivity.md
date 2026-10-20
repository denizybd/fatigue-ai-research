# Numerical sensitivity v1.5: after initial results, not confirmatory

2026-10-20 after primary results and independent audit revealed all87 MLP fits reaching the frozen1500-iteration limit. This is a numerical investigation of a recorded failure, not a new primary test or test-error-selected hyperparameter search. Original results remain unchanged and cannot support a validated neural-architecture comparison.

The first prespecified fold's training data alone were refit at a12000-iteration cap with identical seed, inputs, weights, objective, regularization and stopping tolerances. It converged by the original function-reduction criterion at4464iterations (gradient max0.00010034). No test prediction was used to select this diagnostic cap.

Repeat every original source-block fold/seed for MLP only at this fixed12000cap, preserving every result and failure. Report separately as an exploratory numerical sensitivity. No best-of-cap model selection, no modification to the primary linear/gate conclusions. More optimizer iterations are not independent experimental validation.
