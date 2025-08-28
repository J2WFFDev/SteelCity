#!/usr/bin/env bash
# usage: ./watch_events.sh decoded.csv [thr] [gap_seconds] [hz]
# thr: magnitude threshold; gap_seconds: sub-threshold time that ends an event
# hz: sample rate used to compute durations and the gap in samples
set -euo pipefail
file="${1:-wtvb_decoded.csv}"
thr="${2:-120}"
gap_s="${3:-0.20}"
hz="${4:-25}"

awk_cmd="${AWK:-awk}"

tail -n +2 -F "$file" | "$awk_cmd" -F, -v thr="$thr" -v gap_s="$gap_s" -v hz="$hz" '
  BEGIN { gapsamp = int(gap_s*hz + 0.5) }
  function finish() {
    if (n>0) {
      dur = n / hz
      mean = sum / n
      rms = sqrt(sum2 / n)
      printf("%s .. %s  dur=%.2fs  n=%d  max=%.1f at %s  d=(%s,%s,%s)  mean=%.1f  rms=%.1f  area≈%.1f\n",
             t0, t_last, dur, n, maxmag, t_max, dx, dy, dz, mean, rms, mean*dur)
      fflush()
    }
    n=0; quiet=0; sum=0; sum2=0; maxmag=0
  }
  { mag = $9+0 }
  {
    if (mag > thr) {
      if (n==0) t0=$1
      n++; quiet=0; t_last=$1
      sum += mag; sum2 += mag*mag
      if (mag>maxmag) { maxmag=mag; t_max=$1; dx=$6; dy=$7; dz=$8 }
    } else if (n>0) {
      quiet++
      if (quiet>=gapsamp) finish()
    }
  }
  END { finish() }'
