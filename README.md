# Provenance-aware censored AM316L fatigue audit

## Current phase: 6 method comparison and continued public-data collection

Canonical source folder: `/Users/deniz2/Desktop/fatigue-ai-research`. Read `STATE.md` first. Phase5 is the latest completed model experiment: the separate rotating-bending replay and its limits are documented in `manuscript/v5/`. The verified delivery is in the current chat's `outputs/phase5`.

Phase6 is now running on the unchanged441-row corpus:12outer source families,66pair-exclusion inner training sets,146fixed configurations across existing controls, censoredGP, Student-t and joint fatigue-limit adaptation.111tests and independent numerical/runner/metric/source audits passed before the seal at20October21:05UTC (21October00:05local). SealSHA25d1641a62c49cb8f969f907ac5a4dae7838393d3553fe711b13aced4049dc3e. Actual inner population fits/scoring have started; no final model selection or outer utility result yet. The protocol is `protocols/v6/nested_design.txt`. `zsh run_v6.sh` is resumable and has exclusive pipeline/stage locks. Read current process state from live tools plus `logs/v6/pipeline_status.json`; a saved status alone is not liveness proof. All historical outcomes were already seen, so this is exploratory reuse rather than prospective confirmation.

New EPRI public-report collection provides14exact author-labelled strain-life observations (10at20C,4at300C) with report-backed RRtee-group/powder-lot55999 association; independent reading checked98numeric cells. A uniquely serialized build and virgin constant-amplitude force protocol remain unverified. Keep it separate from the stress-life441 corpus. See `literature/v6_campaigns/osti_epri2020/independent_source_audit.json` and `data/external_v6/epri/`. New adjacent bending/defect/trace assets have separate inventories and false current-fit gates; timestamps and defects are not extra fatigue-life tests. Goal remains active. No contact or publication.

## Historical phase4 open-data continuation

20 October2026. Latest addendum: `manuscript/v4/public_data_addendum_en.pdf` (4pages), Turkish explanation `manuscript/v4/acik_veri_ilerleme_raporu_tr.pdf` (3pages). Source-qualified training expands309→441 (48conditions/14DOIs/13blocks), with new numericalYankin69 held out, a115-row/two-family policy extension, and separate licensed rawLCF/SWT/interrupted-history collections. A separate67-point2026RBF table is collected (25explicitreuse/42otherconditions), not fitted. Frozen previous phases remain intact. Run `zsh run_v4.sh`; clean isolated replay matches84CSVs exactly,19tests pass and1156fixed-parameter RFL quadraturechecks pass. Source/condition qualification does not imply physical specimen/build mapping. New results do not establish general90%reliability or an originalBNN ranking. Read STATE.md and the new addendum for numerical findings and evidence limits. User-facing deliverables are in the current chat outputs/phase4. The human already requested author data; this workflow sends no correspondence.

**Historical phase: 3.1.** See `manuscript/v31/current_paper_source.json` for that English working draft or the Turkish phase3.1 report. Earlier phase1/v2 papers and outreach files are historical; outreach remains unsent.

A source-audited virgin-first-block recovery yields43 nominal-stress Merot observations with real specimen/build/powder identifiers. The common-query acquisition benchmark uses31 specimens/3 conditions/2 physical builds, but ONE author campaign. Nine local-stress records and the six-specimen Dastgerdi pilot remain separate. Six censored baselines and four stress policies share exact query/pool splits at k0/3/5. Higher proposed q10 does not establish a safe improvement: at C1e6, high-stressk3 vs random gives hierarchical1.336x/RFL1.085x q10 and7.5% observed cycle savings, while paired risk identification still permits increases of26.11pp/6.67pp. A second fully matched independent campaign remains missing.

Reproduce that historical extension with `zsh run_v31.sh`. It needs only the367-row portable input bundle; unused previous Trombley records are not required. Same-cohort fresh replay matches12 tables exactly; portable replay matches all scientific values and population fits, with a documented cache-signature-only change.19 RFL/design tests pass. No correspondence or publication occurred.

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
# Current continuation: phase5 evidence and phase6 method search

The user moved this project to `/Users/deniz2/Desktop/fatigue-ai-research` on20October2026. Runtime roots are computed from source files. No old-path symlink is needed.

Latest bounded update: `manuscript/v5/public_data_rbf_addendum_en.pdf` (3pages), `manuscript/v5/yeni_veri_ve_deney_secimi_tr.pdf` (2pages). The local phase5 delivery is in this chat's `outputs/phase5`. Run `zsh run_v5.sh` for the frozen separate rotating-bending pilot. Independent arithmetic/contrast audits and a fresh empty-cache36-table replay pass. New56exactNf observations and16approximate markers are collected with explicit gates; the441 training input is unchanged.

The research Goal is ACTIVE and incomplete. One-family model-dependent cost/life tradeoffs do not establish a new generally superior method. Phase6is developing genuinelydifferent censored baselines and family-separated tuning under the user's latest authorization. Read `STATE.md` for exact findings and the diagnostic-scope caveats. No outreach or publication has been sent.

