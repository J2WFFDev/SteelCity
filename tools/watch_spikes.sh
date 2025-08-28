#!/usr/bin/env bash
set -euo pipefail
file="${1:-wtvb_decoded.csv}"
thr="${2:-120}"
# Prints time, type, |Δ| and the three deltas when magnitude crosses threshold.
tail -n +2 -F "$file" | awk -F, -v thr="$thr" '
  { mag = $9+0; if (mag>thr)
      printf "%s  type=%s  mag=%s  d=(%s,%s,%s)\n",
             $1, $2, $9, $6, $7, $8; fflush(); }'
