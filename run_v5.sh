#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
# Keep the supplied frozen split manifest; every input/code hash is checked.
for cap in 5e6 1e7; do
  .venv/bin/python -u -m src.v5_rbf run --output "results/v5/rbf_cap$cap" --cap "$cap"
  .venv/bin/python -m src.v5_rbf summarize --output "results/v5/rbf_cap$cap"
  .venv/bin/python -m src.v5_rbf_audit "results/v5/rbf_cap$cap"
done
