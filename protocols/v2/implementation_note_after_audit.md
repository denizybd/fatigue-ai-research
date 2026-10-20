# Implementation clarification after audit

20 October 2026, after the initial result inspection. No split or prediction is changed.

The small-source/external amendment describes chronological date ties as hashed specimen IDs. The frozen implementation hashes the stable repository record `row_id` instead. The independent audit verified this exact ordering and confirmed all support dates precede or equal query dates. Both keys are outcome-blind, but the wording is corrected here rather than rewriting the original pre-fit document. Each external mechanism and random seed has 99 fixed queries; their unions across seeds or mechanisms are not 99 unique independent tests.

The population uncertainty sensitivity uses 20 bootstrap replicates drawn from 11 historical training sources. It does not use 20 independently collected sources. The one external campaign cannot supply an independent campaign-level confidence interval.

Numerical quadrature was additionally evaluated at 81 rather than 41 nodes on the complete full-training internal and external tracks. The maximum log10 lower-life changes were 1.56e-7 and 2.78e-11 respectively; no danger classification changed. This is a numerical sensitivity, not validation of a physical/statistical assumption. See `results/v2/quadrature_sensitivity.json`.
