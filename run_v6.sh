#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
if [[ ! -f protocols/v6/freeze.json ]]; then
  print -u2 'Phase6 is not frozen; review and seal before fitting.'
  exit 1
fi
.venv/bin/python -m src.v6_pipeline
