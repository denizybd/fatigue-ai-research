PHASE 4: PUBLIC AM316L EVIDENCE PACKET
20 October 2026

Start with manuscript/v4/public_data_addendum_en.pdf or acik_veri_ilerleme_raporu_tr.pdf.

This is a local research deliverable. The human separately requested author data; this workflow sent no correspondence and made no submission. Earlier phase 3.1 physical-lineage results remain available separately. Finding a second independently mapped room-temperature campaign remains part of the active goal.

COLLECTED EVIDENCE

441 source-qualified training observations: 48 conditions, 14 publications, 13 source blocks, 380 failures and 61 censors. The 132-row increment was already in the public database; its original experimental methods and observations are now source-reviewed. These are not 132 newly performed tests.

69 new numerical Table 3 outcomes from Yankin 2025: 64 failures and five runouts in 14 conditions. Publication test numbers are not laboratory or build IDs. The acquisition comparison uses 25 observations in four eligible conditions, at k=0 or 3; the other 44 remain collected.

Separate RBF 2026 Table 1: 67 reported points, with 63 failures and four runouts. Twenty-five points reuse the room-temperature as-built curve from reference 108491. The other three conditions provide 42 points. Primary indexed table text was obtained and independently checked; a downloaded PDF visual check is not claimed. These data are absent from the frozen axial models.

Bartosak: 20 author-ID multiaxial LCF/SWT life records plus 200 defect measurements. Separate strain-controlled domain.

Jambor 2025: seven interrupted specimens and 217,368 response samples. No failure life, event flag or fixed stress ratio was invented. Peak-valley and whole-cycle histories are views of the same seven specimens.

Jambor 2026: three cyclic histories with 14,499 valid rows and 115 orphan rows retained separately. Same precautionary source family as Jambor 2025; physical overlap remains unresolved.

Huo/Roy: two selected AM-stainless histories with 1,087,236 time samples. Alloy grade and temperature remain unverified; no 316L assignment was invented.

Do not sum these different measurement types or related repositories as independent physical fatigue specimens.

DATA ENTRY POINTS

- data/processed/v4/training441_full_metadata.csv retains all available source, process and condition metadata. Legacy 309-row scalar fields can include database defaults: nonmissing does not mean primary-source-certified.
- data/processed/v4/controlled_expansion/ holds the canonical stress, R, N, event and grouping columns actually used by the six present models. This is not the original Centola 19-feature input.
- data/external_v4/source_expansion/ contains the 132-row increment, 416 row decisions, 278 corrections and four caption anchors. Anchors are not extra observations.
- data/external_v4/yankin2025/ contains all 69 table records and provenance. Five nominal 1e6 censor stops are plot-derived, not numeric stopping times supplied by Table 3.
- data/external_v4/rbf2026/ contains all 67 points and the 42-point subset. Exact individual runout stops are unknown; 5e6 is a conservative lower bound. A 6.07e6 failure beyond the minimum threshold is retained without alleging a source error.
- data/external_v4/jambor2025/ and raw_search/ retain original and normalized response/SWT data, source IDs and units.

REPLAY

Extract the packet and run: zsh run_v4.sh

The script creates a local .venv if absent, installs pinned dependencies, prepares input hashes and splits, and runs both designs at both planning caps. Existing cached fits must match input/code hashes. An empty work/v4/model_cache directory forces fresh population fits. No external Trombley records are needed.

Computational replay starts from the curated numerical CSVs. It does not automatically reconstruct observations from article figures. Source scripts, URLs, original values and audit ledgers document the acquisition and manual method gates.

The completed empty-cache replay in a separate root reproduced 84 scientific CSVs byte for byte and all fitted parameters. Nineteen synthetic model/design tests pass. Across 1,156 fixed-parameter RFL evaluations, the maximum 96/192-node q10 difference is 4.78e-10 log10 cycles. Independent reviewers reconstruct query/support equality, complete family exclusions, censoring bounds, costs and headline arithmetic.

Results retain all six models, four policies, feasible k=0/3/5, ten seeds and both caps. The 164,160 prediction instances and 5,200 support-selection instances are repeated replays, not independent experiments. The single Yankin program has no population CI; two-family bootstrap intervals are descriptive. The 309-trained acquisition planner is fixed across regimes. Adding source families changes the working-likelihood weights as well as row count.

ATTRIBUTION AND ACCESS

FatigueData-AM2022 is CC BY 4.0, DOI 10.6084/m9.figshare.22337629; retain its authors and metadata in data/raw/. All four acquired Zenodo packets indicate CC BY 4.0; creator attribution, DOIs, source README files and transformations are retained.

The numerical primary-table extractions retain exact source provenance. The Yankin article uses CC BY-NC-ND 4.0; its original PDF, XML and graphics are not bundled. The RBF article's exact license terms were not fully render-verified; its publisher full text is not bundled. No original article PDF, HTML, XML, image or full-text transcript is shipped.

The original 407 MB Jambor microscopy archive remains in the local research repository; selected mechanical CSVs and producer checksum receipts are included here. The 3.36 GB Huo archive was not fully downloaded or MD5-verified; selected public HTTP-range members have CRC and SHA checks.

CONTRIBUTION BOUNDARY

This is an open proxy and controlled method evaluation, not an exact reproduction of Centola's 518 rows, original BNN, SWT/risk-volume inputs or Owen R90C90 target. The 441-row cohort overlaps eight of the 17 original source DOIs; row identity is unestablished. General 90% design reliability and a universally superior active policy are not established. Unknown feature timing does not become permission to use postfailure measurements as prospective covariates.
