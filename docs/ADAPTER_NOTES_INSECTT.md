# InSecTT adapter notes

Dataset: `insectt_wsn_power_2023`, DOI `10.5281/zenodo.7762712`.

## Source structure

The public archive contains four ZIP-compressed CSV traces: BLE, OpenThread, Ephesos, and UWB. Each trace contains a `timestamp` column plus five current columns: `current_100ms`, `current_200ms`, `current_400ms`, `current_800ms`, and `current_1600ms`.

The dataset README states that timestamps advance in 10 microsecond steps and current is measured in microamperes with a Nordic Power Profiler Kit II in source mode. Each configuration is measured for approximately 60 seconds.

The sensor acquires 2 bytes every 100 ms. Data are accumulated when communication is less frequent, giving payloads of 2, 4, 8, 16, and 32 bytes for communication periods of 100, 200, 400, 800, and 1600 ms.

## Energy boundary

The README does not state the PPK II source voltage. STACKWISE therefore does not guess a voltage and does not write `power_w`, `mean_power_w`, or `energy_j` for this dataset. The adapter provides exact current statistics and integrated charge (`charge_c`).

A related open-access publication reports mean power for the same 20 configurations in Table 1 (DOI `10.1007/978-3-031-54049-3_14`). `scripts/validate_insectt_reference.py` compares those published values to the raw-trace mean currents and estimates the implied constant source voltage as a validation diagnostic. The inferred voltage is not treated as raw metadata and is not written back into the canonical observations.

## Statistical unit

There is one approximately 60-second trace per technology/configuration, not a set of independent replicate runs. High-frequency samples within a trace are not independent experimental replicates. Therefore this dataset supports configuration-level mean/current-shape evidence but does not by itself provide between-run variance for a technology/configuration.

## Technology-specific configuration

- BLE: peripheral, LE 1M PHY, 45 ms connection interval, up to 40 skipped connection events.
- Thread: OpenThread Sleepy End Device, UDP, 1 s parent poll interval.
- EPhESOS: continuous-mode implementation using the BLE 1M PHY.
- UWB: nRF52832 plus Qorvo DW1000, periodic beacon transmission.
- The source comparison excludes acknowledgements and retransmissions.


## Stage-2 evidence policy (v0.1.12)

The harmonised 20-row table remains unchanged. Stage 2 creates a separate configuration artifact and evidence records. Mean current and charge are direct trace statistics; mean power and capture energy are derived with one shared validated voltage parameter. The parameter is not raw metadata and is not copied into canonical `voltage_v`, `mean_power_w`, or `energy_j`.

Every configuration has `n_independent_units=1`. `std_current_ua` describes within-trace current variation only and is not a between-run standard error. Hardware/firmware context is retained so UWB's nRF52832 + DW1000 implementation is not silently equated with the nRF52840 implementations used by BLE, Thread and EPhESOS.
