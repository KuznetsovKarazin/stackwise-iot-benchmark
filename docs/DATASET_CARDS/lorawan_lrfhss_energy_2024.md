# Dataset card: `lorawan_lrfhss_energy_2024`

## Identity

- DOI: `10.5281/zenodo.13838241`
- Associated publication DOI: `10.3390/s24175770`
- Technology: LoRaWAN LR-FHSS
- Configurations: ACK/noACK × DR8–DR11
- Evidence grade: A
- Status: validated; Stage-2 analysis-ready materialised in v0.1.13 with replication limitation

## Scientific role

Radio-interface transaction-energy evidence for LR-FHSS and diagnostic comparison of confirmed versus unconfirmed operation across DR8–DR11.

## Raw structure

Eight approximately 60 s current traces sampled every 20.48 microseconds. Source metadata specify a 4-byte FRM payload and +14 dBm transmit power. The associated publication documents a dedicated 3.3 V supply for the measured LR1121 radio interface.

## Measurement boundary

Radio interface only, not total end-device energy.

## Statistical unit

One source trace per ACK/noACK × DR configuration. Production validation detected exactly one TX burst in each trace. There are no independent repeated traces per configuration.

## Harmonisation

The adapter streams each trace, computes time-weighted current statistics, charge and full-capture energy using the source-backed 3.3 V rail. Canonical `energy_j` means energy of the complete capture, including baseline sleep.

## Validation

Structural checks passed for all eight configurations with zero warnings/schema errors.

Reference diagnostics:

- unconfirmed DR8 TX plateau: approximately 25.468 mA;
- publication TX-state reference: approximately 25.7 mA;
- error: approximately -0.90%;
- unconfirmed DR8 low-current band: approximately 0.424 microampere;
- publication sleep reference: 0.5 microampere.

The mean thresholded plateau across all confirmed and unconfirmed traces is not interpreted as a universal TX current because confirmed traces include receive/ACK states.

## Analysis-ready transformation

After confirming one TX burst per capture, STACKWISE derives incremental transaction energy by subtracting sleep-baseline energy from the complete capture. Confirmed-minus-unconfirmed energy is computed pairwise by DR.

These differences are labelled **capture-specific ACK/RX overhead**. They are not population-level expected ACK overhead because each configuration has only one source trace and ACK placement/state behaviour can vary.

## Limitations

The released Stage-2 dataset contains one trace per condition; the measurement is radio-only and confirmed-state behaviour is capture-specific. Population repeatability is not identified from the released traces and must not be inferred from within-trace measurement precision.


## Materialised Stage-2 artifact (v0.1.13)

The materialiser emits 8 full-capture records, 8 baseline-subtracted incremental-transaction records and 4 matched-DR confirmed-minus-unconfirmed contrast records. The implementation context records the LR1121 development kit/radio and Keysight N6705A DC Power Analyzer as measurement hardware and Keysight 14585A Control and Analysis Software as acquisition/control software; the Zenodo record's original `Power Analyzer: Keysight 14585A` wording is retained as a provenance discrepancy. All configuration-level evidence retains one independent trace; the four ACK/RX contrasts are descriptive single contrasts and do not define population uncertainty.


## Stage-3H instrumentation and repeatability review (v0.1.24)

Primary-source reconciliation distinguishes the measurement instrument from the PC software. The associated Sensors paper identifies the **Keysight N6705A DC Power Analyzer** as the measurement hardware. The Zenodo dataset description labels `Power Analyzer: Keysight 14585A`, while Keysight documentation identifies **14585A as Control and Analysis Software** used with N6705-family power analyzers. STACKWISE therefore stores N6705A in `measurement_instrument`, 14585A in `acquisition_software`, and preserves the Zenodo wording in provenance notes. No numerical trace value changes.

The paper also states that current/duration were measured for several individual transmission processes and that differences were negligible. It does not report the repeat count or numerical run-to-run SD/CV/CI, and the open Stage-2 dataset still contains one trace per ACK/noACK x DR configuration. The statement is retained as **qualitative low-variability evidence only**; it is not converted to a numerical prior.
