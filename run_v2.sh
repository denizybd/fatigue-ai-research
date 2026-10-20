#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
FATIGUE_V2_RUN_ROOT="${FATIGUE_V2_RUN_ROOT:-results/v2/reruns/$(date +%Y%m%dT%H%M%S)}"
if [[ ! -x .venv/bin/python ]]; then
  uv venv --python 3.12.13 .venv
  uv pip install --python .venv/bin/python -r requirements.lock.txt
fi
.venv/bin/python -m pytest tests -q
# The reviewed historical cohort and frozen split files are delivered. Reusing
# the frozen files preserves their pre-fit chronology and exact signatures.
for pair in strict:strict strict_fulltraining:fulltraining strict_nearcluster_fulltraining:nearcluster_fulltraining no_afkhami:no_afkhami all:all_family weak:weak_family broader_fulltraining:broader_fulltraining; do
  dataset="${pair%%:*}"
  result="${pair##*:}"
  .venv/bin/python -m src.v2_run --dataset "data/processed/v2/$dataset" --output "$FATIGUE_V2_RUN_ROOT/$result"
  .venv/bin/python -m src.v2_summarize "$FATIGUE_V2_RUN_ROOT/$result"
done
.venv/bin/python -m src.v2_run --dataset data/processed/v2/strict_fulltraining --output "$FATIGUE_V2_RUN_ROOT/curved_fulltraining" --curved
.venv/bin/python -m src.v2_summarize "$FATIGUE_V2_RUN_ROOT/curved_fulltraining"
# External records have no stated redistribution license and are deliberately
# absent from the shareable archive. Fetch the authors' public pages locally.
if [[ ! -f data/external_v2/trombley2025/fatigue_asbuilt_available129.csv ]]; then
  .venv/bin/python literature/fresh_campaign_v2/acquire_trombley.py
  .venv/bin/python literature/fresh_campaign_v2/prepare_trombley.py
fi
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib,pandas as pd
p=Path('data/external_v2/trombley2025/fatigue_asbuilt_available129.csv')
expected='b6ef1ccc0fd23849a4271bac4c021ab51f8cdab536e512604fc92aa490264da1'
if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
    raise SystemExit('External source/normalization changed: review provenance; do not silently resume frozen results')
x=pd.read_csv(p);x['dataset_id']=x.condition_id;x['group_id']='trombley2025_one_campaign';x['doi']='10.1038/s41598-025-97031-1'
h=pd.read_csv('data/processed/v2/strict/cohort.csv')
for folder in ['external','external_fulltraining']:
    target=Path('data/processed/v2')/folder/'cohort.csv'
    pd.concat([h,x],ignore_index=True).to_csv(target,index=False)
PY
for pair in external:external external_fulltraining:external_fulltraining; do
  dataset="${pair%%:*}"
  result="${pair##*:}"
  .venv/bin/python -m src.v2_run --dataset "data/processed/v2/$dataset" --output "$FATIGUE_V2_RUN_ROOT/$result"
  .venv/bin/python -m src.v2_summarize "$FATIGUE_V2_RUN_ROOT/$result"
done
.venv/bin/python -m src.v2_run --dataset data/processed/v2/external_fulltraining --output "$FATIGUE_V2_RUN_ROOT/external_curved" --curved
.venv/bin/python -m src.v2_summarize "$FATIGUE_V2_RUN_ROOT/external_curved"
.venv/bin/python -m src.v2_population_bootstrap --output "$FATIGUE_V2_RUN_ROOT/external_bootstrap"
.venv/bin/python -m src.v2_summarize "$FATIGUE_V2_RUN_ROOT/external_bootstrap"
.venv/bin/python -m src.v2_same_population_control --original "$FATIGUE_V2_RUN_ROOT/fulltraining" --dataset data/processed/v2/strict_fulltraining --output "$FATIGUE_V2_RUN_ROOT/same_population_internal"
.venv/bin/python -m src.v2_same_population_control --original "$FATIGUE_V2_RUN_ROOT/external_fulltraining" --dataset data/processed/v2/external_fulltraining --output "$FATIGUE_V2_RUN_ROOT/same_population_external"
echo "Fresh phase-2 replay saved to $FATIGUE_V2_RUN_ROOT"
