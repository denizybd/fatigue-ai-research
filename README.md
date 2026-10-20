# Provenance-aware censored AM316L fatigue audit

**Current phase: 2.** Start with `STATE.md`, `manuscript/v2/arastirma_ozeti_tr.pdf` or `manuscript/v2/research_note_en.pdf`. Source review found a stepped-load eligibility problem and label corrections in the old open-data pilot. Its earlier scientific interpretation and contact package require the phase-2 addendum.

Phase 2 tests 0/3/5/10 endpoints per new condition using strong censored monotone fatigue baselines, fixed queries, source holdouts, an acquired 129-specimen campaign, curvature/parameter sensitivities and a matched-population control. The intended reliable-and-useful criterion failed. No general hierarchical-method superiority is established. Reproduce it with `zsh run_v2.sh`; original phase-1 instructions remain below for historical audit.

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
