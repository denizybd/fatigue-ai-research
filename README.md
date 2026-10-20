> **Complete folder backup:** [Full snapshot release](https://github.com/denizybd/fatigue-ai-research/releases/tag/snapshot-2026-10-20-2300) includes every file, including raw data, PDFs, ignored work and the Python environment. The ordinary Git source ZIP is not the full backup. [Details and restore instructions](SNAPSHOT_BACKUP.md).

# Provenance-aware censored AM316L fatigue audit

## Current phase4 open-data continuation

20 October2026. Latest addendum: `manuscript/v4/public_data_addendum_en.pdf` (4pages), Turkish explanation `manuscript/v4/acik_veri_ilerleme_raporu_tr.pdf` (3pages). Source-qualified training expands309→441 (48conditions/14DOIs/13blocks), with new numericalYankin69 held out, a115-row/two-family policy extension, and separate licensed rawLCF/SWT/interrupted-history collections. A separate67-point2026RBF table is collected (25explicitreuse/42otherconditions), not fitted. Frozen previous phases remain intact. Run `zsh run_v4.sh`; clean isolated replay matches84CSVs exactly,19tests pass and1156fixed-parameter RFL quadraturechecks pass. Source/condition qualification does not imply physical specimen/build mapping. New results do not establish general90%reliability or an originalBNN ranking. Read STATE.md and the new addendum for numerical findings and evidence limits. User-facing deliverables are in the current chat outputs/phase4. The human already requested author data; this workflow sends no correspondence.

**Current phase: 3.1.** Start with `STATE.md` and `manuscript/v31/current_paper_source.json` (current English working draft) or the Turkish phase3.1 report delivered in the current chat. Earlier phase1/v2 papers and outreach files are historical; use `outreach/v31/` for the current unsent material.

A source-audited virgin-first-block recovery yields43 nominal-stress Merot observations with real specimen/build/powder identifiers. The common-query acquisition benchmark uses31 specimens/3 conditions/2 physical builds, but ONE author campaign. Nine local-stress records and the six-specimen Dastgerdi pilot remain separate. Six censored baselines and four stress policies share exact query/pool splits at k0/3/5. Higher proposed q10 does not establish a safe improvement: at C1e6, high-stressk3 vs random gives hierarchical1.336x/RFL1.085x q10 and7.5% observed cycle savings, while paired risk identification still permits increases of26.11pp/6.67pp. A second fully matched independent campaign remains missing.

Reproduce the current extension with `zsh run_v31.sh`. It needs only the367-row portable input bundle; unused previous Trombley records are not required. Same-cohort fresh replay matches12 tables exactly; portable replay matches all scientific values and population fits, with a documented cache-signature-only change.19 RFL/design tests pass. No correspondence or publication occurred.

Phase2 and3 retain the previous source-family, censoring and acquisition analyses. Use `zsh run_v2.sh` / `zsh run_v3.sh` to replay them. Older phase1 instructions below are retained for historical audit and do not supersede current source corrections.

## Historical phase1 record

A reproducible public-data pilot. The prespecified combined rejection hypothesis failed. This work does not establish a new safe-design algorithm.

Start with **STATE.md** or **manuscript/arastirma_ozeti_tr.pdf**.

## Deliverables

- `manuscript/paper_draft_en.pdf`, `paper_content.json` and `paper_draft_en.txt`: an English working paper with 15 verified references and editable sources.
- `manuscript/supplementary_material.pdf`: provenance, definitions, all block results, sensitivities and numerical diagnostics.
- `manuscript/research_brief_en.pdf` and `outreach/`: a one-page brief, email draft, Turkish technical Q&A and numerical claim receipts. No correspondence has been sent.
- `figures/`: scientific PNG/SVG figures generated from saved results and public data.
- `results/`: predictions, source/seed metrics, split and convergence receipts, internal independent arithmetic checks, and the full replay comparison.

## Reproduce

Tested locally on Apple M4 with 16 GiB RAM and Python 3.12.13. Versions are pinned in `requirements.lock.txt`. Network access is needed when packages or the raw MAT file are absent. No GPU or auxiliary language model is required.

```zsh
zsh run_all.sh
```

This creates a fresh timestamped directory under `results/reruns/`. It acquires the immutable v2 MAT file if absent, prepares and audits provenance, runs 16 synthetic tests and all seven experiment configurations with three seeds, summarizes results and audits the primary analysis.

To name a fresh directory and compare the replay with the delivered results:

```zsh
FATIGUE_RUN_ROOT=results/my_fresh_replay zsh run_all.sh
.venv/bin/python -m src.compare_runs --replay results/my_fresh_replay
```

Regenerate integrated tables, figures, documents and the original primary audit:

```zsh
.venv/bin/python -m src.postprocess
.venv/bin/python -m src.make_figures
.venv/bin/python -m src.build_documents
.venv/bin/python -m src.independent_audit
```

Checkpoint reuse requires exact data, code and configuration signatures. A mismatch fails explicitly. The complete delivered replay matches all predictions and summary CSVs byte for byte; see `results/full_reproduction_comparison.json`.

## Data attribution and boundaries

FatigueData-AM2022 v2 is CC BY 4.0: Zhang and Xu (2023), https://doi.org/10.6084/m9.figshare.22337629.v2 . Its descriptor is https://doi.org/10.1038/s41597-023-02150-x . Attribute these sources when reusing data and derived figures. Original article texts/PDFs retain their own licenses and are excluded from the shareable archive; URLs and evidence-bounded audit reports are included.

The original Centola 518-row data and code were not obtained. These homoscedastic AFT/MLP implementations are related-method baselines, not a reproduction of the original BNN, SWT preprocessing, risk-volume model or Owen R90C90 targets.

The 29 conservative provenance blocks are not 29 certified independent factories, laboratories or specimen campaigns. Coordinates are approximate digitizations; database defaults and undiscovered reuse remain. Censoring identification intervals exclude digitization and other errors. Bootstrap intervals are descriptive because outer fits share training data. Paper authorship, affiliation, individual contributions and disclosures require human verification.
