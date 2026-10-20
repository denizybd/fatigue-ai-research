#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
.venv/bin/python -m src.v31_source_check
.venv/bin/python -m src.v3_firstblock_import data/external_v3/continuation_papers/merot_first_exposure_unique_physical70_verified.csv
.venv/bin/python -m src.v3_prepare --without-previous --output data/processed/v3/identity_replay_portable --additions data/processed/v3/firstblock/merot52.csv data/processed/v3/new_candidates/dastgerdi.csv
for budget in 1e7 1e6; do
  .venv/bin/python -m src.v3_run --dataset data/processed/v3/identity_replay_portable --output "results/v3/identity_portable_cap$budget" --cap "$budget" --panels external_identity_qualified_firstblock external_identity_localstress_firstblock external_small_temperature_unstated
  .venv/bin/python -m src.v3_summarize "results/v3/identity_portable_cap$budget"
done
.venv/bin/python -m src.v31_compare
