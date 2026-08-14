#!/usr/bin/env bash
set -euo pipefail

# Review every live landing page and DATA_LICENSES.md before running.
stackwise download insectt_wsn_power_2023 \
  --accept-license --accept-unverified-license
stackwise download vomhoff_nbiot_ltem_energy_2023 \
  --accept-license --accept-unverified-license
stackwise download loed_lorawan_edge_2020 \
  --accept-license --accept-unverified-license
stackwise download lorawan_lrfhss_energy_2024 \
  --accept-license --accept-unverified-license
