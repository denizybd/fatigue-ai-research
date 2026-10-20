#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
if [[ ! -f data/external_v2/trombley2025/fatigue_asbuilt_available129.csv ]]; then
  .venv/bin/python literature/fresh_campaign_v2/acquire_trombley.py
  .venv/bin/python literature/fresh_campaign_v2/prepare_trombley.py
fi
.venv/bin/python - <<'PY'
import hashlib
from pathlib import Path
p=Path('data/external_v2/trombley2025/fatigue_asbuilt_available129.csv')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='b6ef1ccc0fd23849a4271bac4c021ab51f8cdab536e512604fc92aa490264da1','External source changed; do not silently substitute'
PY
.venv/bin/python -m src.v3_import
.venv/bin/python -m src.v3_prepare --output data/processed/v3/replay --additions data/processed/v3/new_candidates/tomaszewski.csv data/processed/v3/new_candidates/diller.csv data/processed/v3/new_candidates/dastgerdi.csv
for budget in 1e7 1e6; do
  .venv/bin/python -m src.v3_run --dataset data/processed/v3/replay --output "results/v3/replay_cap$budget" --cap "$budget"
  .venv/bin/python -m src.v3_summarize "results/v3/replay_cap$budget"
  .venv/bin/python -m src.v3_multistress "results/v3/replay_cap$budget" --cohort data/processed/v3/replay/cohort.csv
done
.venv/bin/python -m pytest -q tests/test_v3_design.py tests/test_v3_rfl.py
