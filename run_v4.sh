#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
 python3 -m venv .venv
 .venv/bin/python -m pip install -r requirements.lock.txt
fi
.venv/bin/python -m src.v4_expansion prepare
.venv/bin/python -m src.v4_policy_extension prepare
for cap in 1e7 1e6; do
 .venv/bin/python -u -m src.v4_expansion run --output "results/v4/controlled_cap$cap" --cap "$cap"
 .venv/bin/python -m src.v4_summarize "results/v4/controlled_cap$cap"
 .venv/bin/python -u -m src.v4_policy_extension run --output "results/v4/source_holdout_cap$cap" --cap "$cap"
 .venv/bin/python -m src.v4_summarize "results/v4/source_holdout_cap$cap"
done
