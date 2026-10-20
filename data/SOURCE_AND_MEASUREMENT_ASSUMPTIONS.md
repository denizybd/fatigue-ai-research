# Source and measurement assumptions

Date 2026-10-20; prepared independently of real model outcomes. This report interprets deterministic data preparation and documented source semantics. It does not select thresholds or change the frozen cohort.

## What is available

The official FatigueData-AM2022 v2 MAT file is a checksum-verified public-data starting point. Its rows combine source metadata and extracted fatigue graphs. All 1126 v1.3 primary S–N coordinates are marked `color and shape` by the database and are therefore approximate digitizations. They are genuine reports of experimental campaigns, but the numbers used here are not certified instrument-level raw measurements. Source database and descriptor should both be credited: [data v2](https://doi.org/10.6084/m9.figshare.22337629.v2), [Zhang and Xu2023](https://doi.org/10.1038/s41597-023-02150-x).

The root research workflow separately retains raw bytes, access/license/hash records, a deterministic parser and targeted source-graph spotchecks. The spotchecks support specified records/columns; they do not validate every field of every database observation.

## Three different types of value

1. **Extracted experimental outcome:** plotted stress amplitude and failure/runout cycles. Approximate numerical coordinates; graph scale, marker classification and overlaid literature curves can create extraction errors.
2. **Reported or default metadata:** process settings, orientation, treatments and testing conditions. Raw singleton numbers may be particular values or means; values such as25°C, Kt 1 and uniaxial may be database defaults. There is no globally recoverable per-field measured/default flag.
3. **Analysis-derived quantity:** IDs, scalar-missing decisions, log transforms, encoder fills/scales/categories, source weights and source-family membership. These are computational choices, not new measurements.

No missing manufacturing parameter is reconstructed from fatigue life. Empty/range/multivalue scalars become missing. Training medians and missing indicators are used downstream without pretending that the filled values were measured for that specimen. The processed-data dictionary names which fields enter models and which are retained only for audit.

## Source independence and identity

`row_id` and `dataset_id` are raw hierarchy addresses. They do not certify unique physical specimens. A DOI identifies a publication; a single publication can contain multiple conditions and also reproduce earlier studies' plotted data. Distinct DOIs can report the same specimens. Shared authorship alone is insufficient evidence of specimen reuse.

The independent source-validation report identifies a concrete reuse mechanism in Voloskov Figure3: it overlays older published points. Checking that only that paper's own blue symbols were extracted is required before treating its DOI as independent. Any confirmed repeated curve should be joined with its originating source in a documented family, with exact evidence retained. Near-equal rounded pairs alone are a candidate flag, not proof of duplication. Likewise, identical represented process features in original Centola conditions32/33 and 40/41 do not prove repeated specimens.

The original Centola corpus contains17 source publications. Our map links16 to the wider ordinary 316L L-PBF cohort and12 to the initial primary cohort. This is source overlap, preventing a blanket claim of independent external replication. Direct numerical reproduction remains unavailable without original raw/cleaned records and target-generation code.

## Physical comparison limits

- Raw database stress amplitude and R are retained. This differs from Centola's SWT-equivalent fully reversed amplitude; an amplitude conversion is not a mean-stress correction.
- The primary cohort's room-temperature/unnotched/uniaxial status partly rests on descriptor defaults. It describes database labels and must be worded accordingly.
- The preliminary primary had four strain-control labels among 1130 points. Pre-fit amendmentv1.3 corrected eligibility to force control, leaving 1126 rows; this was a metadata-only correction before model outcomes.
- Cross-section size alone is not90%-stress risk volume. The latter needs geometry/loading/stress-gradient information unavailable in a single scalar; no equivalent risk volume is invented.
- Ordinary316L and nitrogen-enhanced316L remain distinct. Publication group can be shared, but modified-alloy responses are not silently pooled into the exact ordinary-alloy cohort.
- No life/outlier cutoff is applied. Runouts retain censoring semantics and contribute survival likelihood.
- Point-coordinate rounding and source/extraction uncertainty are not equivalent to ML parameter uncertainty. Source bootstrap location instability is a model-sensitivity score, not instrument uncertainty or a Bayesian posterior.

## What the resulting study can support

The proposed study can audit related censored-life models on a publication/family-held-out open-data cohort and show how reliability/conservatism depends on those boundaries. It cannot establish exact reproduction of Centola's BNN, calibration of an R90C90 material design curve, machine-to-machine causal effects, or validated safety of a manufactured component. These boundaries hold regardless of whether the observed result is positive or negative.

## Pre-fit family decisions in amendmentv1.3

The automated curve screen found strong candidates; three connected families are conservatively joined into 29 blocks across 37 DOI sources, while all1126 eligible rows remain. The criterion is at least five distinct near-coincident points, at least 85% coverage of the smaller curve, matching R/mode, life within multiplicative1.02 and stress within 1.01. This is evidence for a leakage-risk block, not an exact specimen-reuse certificate. Family membership and source counts are retained in `source_family_map.csv`/`grouping_report.json`.

Publication-only splitting is explicitly a potentially contaminated sensitivity. A weaker edge gives 28 sensitivity blocks. Greedy approximate cross-DOI deduplication removes 184 candidate rows inside strong families only in a 942-row sensitivity, keeping a removal-to-representative map. It can merge distinct experimental replicates and therefore is not promoted to the main data set. No claim is made that all reuse has been found or that the remaining 29 blocks are proven independent physical campaigns.
