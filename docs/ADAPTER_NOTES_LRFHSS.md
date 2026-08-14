# LR-FHSS adapter notes

Dataset: `lorawan_lrfhss_energy_2024`  
Zenodo: `10.5281/zenodo.13838241`  
Associated article: `10.3390/s24175770`

## Source structure

Eight CSV files cover confirmed/unconfirmed LoRaWAN Class A uplinks for LR-FHSS DR8--DR11. Each file contains three metadata rows, then `Time` and current columns. Time is in seconds and current in amperes. The source metadata reports a sampling period of 20.48 us.

The Zenodo record documents a 4-byte FRM payload, +14 dBm transmit power, the Semtech LR1121 development kit and radio-interface-only measurement boundary. The associated paper documents a dedicated 3.3 V supply for the measured radio interface.

## Harmonisation policy

The adapter emits one observation per complete source trace (8 observations total). It streams the large CSVs and records:

- ACK/noACK and DR index;
- coding rate and physical bit rate;
- sample count, duration and sampling period;
- time-weighted mean, sample mean, standard deviation, min and peak current;
- integrated charge and full-trace energy using the published 3.3 V radio supply;
- fraction of negative samples (instrument noise diagnostic);
- a low-current-band diagnostic;
- a >20 mA TX-plateau diagnostic and coarse TX-burst count.

`energy_j` is deliberately defined as **energy of the complete recorded trace**. It is not silently labelled energy per message, because the capture window may contain arbitrary pre/post sleep. Any per-transaction derived metric must first validate the transmission count and transaction boundary.

## Publication reference values

The associated article reports, for an unconfirmed DR8 trace, approximately 25.7 mA during transmission and 0.5 uA in the sleep state. These values are used only for an independent scale check; they are not substituted into the raw trace.


## Stage-2 evidence policy (v0.1.13)

The Stage-2 materialiser writes separate full-capture and incremental-transaction records. Incremental transaction energy is derived only because validation found exactly one TX burst in every trace. The baseline is the trace-specific mean of the adapter low-current band (`|I| <= 100 uA`) multiplied by the source-backed 3.3 V rail and capture duration.

This baseline is an empirical within-trace proxy; it is not a replicated sleep-state experiment. Consequently every ACK/noACK x DR configuration retains `n_independent_units=1`. Matched confirmed-minus-unconfirmed DR contrasts are stored as descriptive records only and must not be interpreted as population ACK-overhead estimates.
