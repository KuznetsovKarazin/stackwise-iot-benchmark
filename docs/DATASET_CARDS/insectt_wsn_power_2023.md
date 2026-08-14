# Dataset card: `insectt_wsn_power_2023`

## Identity

- DOI: `10.5281/zenodo.7762712`
- Technologies: BLE, Thread/OpenThread, UWB, EPhESOS
- Evidence grade: A
- Status: validated; Stage-2 analysis-ready materialised in v0.1.12

## Licence

CC BY 4.0, verified from the dataset README.

## Scientific role

High-resolution current evidence for short-range/mesh technologies as a function of communication interval and aggregated payload.

## Raw structure

Four approximately 60 s traces. Each trace contains timestamp plus current columns for 100, 200, 400, 800 and 1600 ms communication periods. Measurement rate is 100 kS/s; timestamps advance by 10 microseconds and current is in microamperes.

The sensor produces 2 bytes every 100 ms; accumulated communication payloads are therefore 2, 4, 8, 16 and 32 bytes at the five periods.

## Measurement boundary

Power Profiler Kit II source-mode current measurement of the source experimental platform. Source voltage is not explicitly stated in the dataset README.

## Statistical unit

One approximately 60 s trace per technology × communication-period configuration. Millions of within-trace samples estimate that trace precisely but are not independent experimental replicates.

## Harmonisation

The adapter streams nested ZIP members, maps timestamp scale and current units, computes current statistics and integrates charge. Canonical energy remains missing because source voltage is absent from raw metadata.

## Independent validation

Published Table 1 mean powers for the same 20 configurations were used as an independent scale check. Implied source voltage:

- median: 3.3000554 V;
- min/max: 3.2990682 / 3.3112278 V;
- CV: 0.0785%;
- power RMSE using median voltage: 0.1974 microW;
- power MAPE: 0.0348%.

This strongly supports the timestamp and current-unit interpretation.

## Analysis-ready transformation

The validated inferred voltage may be used to derive mean power and energy with `analysis_voltage_provenance` explicitly marked as inferred from the associated publication Table 1. It is not written back into raw-derived canonical voltage metadata.

## Limitations

No independent replicate traces per configuration are provided. Between-run, between-device and environmental variance must therefore be represented through broader study/design uncertainty rather than sample-level standard errors.


## Stage-2 materialisation

Version 0.1.12 emits 20 configuration-level observations and 80 typed evidence records. The independent unit is one approximately 60 s trace per technology x reporting-period configuration (`n_independent_units=1`). The inferred source voltage is stored once as `insectt_ppk2_source_voltage_v`; all derived power/energy records reference it. No sample-level confidence interval is produced.

Implementation context is explicit: BLE/Thread/EPhESOS use nRF52840-based platforms, while UWB uses nRF52832 + Qorvo DW1000. Cross-technology results therefore describe measured system configurations rather than isolated protocol-only effects.
