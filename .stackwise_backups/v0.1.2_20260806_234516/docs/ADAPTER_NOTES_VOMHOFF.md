# Vomhoff NB-IoT/LTE-M adapter

Dataset: `vomhoff_nbiot_ltem_energy_2023`  
DOI: `10.5281/zenodo.7603641`

## Source structure

The three CSV files contain 5 ms device-level samples. The relevant source fields are:

- `current`: current in amperes;
- `voltage`: voltage in volts;
- `current_As`: charge contribution of the sample in ampere-seconds;
- `consumption_Ws`: energy contribution of the sample in watt-seconds, numerically joules;
- `diff_time`: source phase duration;
- `run`, `event`, `rat_type`, `application_protocol`, and optionally `data`: experimental grouping variables.

## Harmonisation unit

STACKWISE creates one observation per experimental run and phase rather than averaging all runs. This preserves replication for confidence intervals and mixed-effects models.

Additional provenance columns retain:

- `source_figure`;
- `source_run`;
- `source_event`;
- `raw_duration_s`;
- `raw_energy_j`;
- `normalisation_factor`;
- `normalisation_rule`;
- `charge_as`.

## Source-defined normalisation

The implementation follows the authors' supplied R scripts.

1. Figure 3: `Idle Connected` energy and duration are divided by two.
2. Figure 4: `Idle` energy is rescaled to a 20 s interval.
3. Figure 5: HTTP/MQTT idle rows are first filtered using the source rule
   `current <= 0.063 A OR elapsed time < 5000 ms`; the retained interval is then rescaled to 20 s.

Both raw and normalised quantities are retained. No voltage, unit, or phase boundary is inferred beyond what is explicit in the source files and scripts.
