#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
FATIGUE_RUN_ROOT="${FATIGUE_RUN_ROOT:-results/reruns/$(date +%Y%m%dT%H%M%S)}"
if [[ ! -x .venv/bin/python ]]; then
  uv venv --python 3.12.13 .venv
  uv pip install --python .venv/bin/python -r requirements.lock.txt
fi
.venv/bin/python -m src.acquire_data
.venv/bin/python -m src.prepare_data
.venv/bin/python literature/data_source_validation/duplicate_curve_audit.py
.venv/bin/python literature/data_source_validation/source_spotcheck.py
.venv/bin/python -m src.group_sources
.venv/bin/python -m pytest tests -q
.venv/bin/python -m src.run_experiment --output "$FATIGUE_RUN_ROOT/primary"
.venv/bin/python -m src.run_experiment --input data/processed/primary_doi_only.csv --output "$FATIGUE_RUN_ROOT/doi_only"
.venv/bin/python -m src.run_experiment --scheme random --output "$FATIGUE_RUN_ROOT/random_rows"
.venv/bin/python -m src.run_experiment --input data/processed/primary_deduplicated_sensitivity.csv --models linear --output "$FATIGUE_RUN_ROOT/deduplicated"
.venv/bin/python -m src.run_experiment --input data/processed/primary_weak_edge.csv --models linear --output "$FATIGUE_RUN_ROOT/weak_edge"
.venv/bin/python -m src.run_experiment --models linear --naive-events --output "$FATIGUE_RUN_ROOT/naive_censoring"
.venv/bin/python -m src.run_experiment --models mlp --mlp-maxiter 12000 --output "$FATIGUE_RUN_ROOT/mlp_extended"
for folder in primary doi_only random_rows deduplicated weak_edge naive_censoring mlp_extended; do
  .venv/bin/python -m src.summarize --folder "$FATIGUE_RUN_ROOT/$folder"
done
.venv/bin/python -m src.postprocess --root "$FATIGUE_RUN_ROOT"
.venv/bin/python -m src.independent_audit --folder "$FATIGUE_RUN_ROOT/primary"
