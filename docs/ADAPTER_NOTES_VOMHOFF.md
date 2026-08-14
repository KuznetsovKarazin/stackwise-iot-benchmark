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

STACKWISE creates one observation per experimental run, phase, and source `diff_time` segment rather than averaging all runs. This matches the grouping keys in the authors' R scripts and preserves repeated event labels that correspond to distinct temporal segments.

Additional provenance columns retain:

- `source_figure`;
- `source_run`;
- `source_event`;
- `source_diff_time_s`;
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


## Stage-2 logical-unit audit (v0.1.10.post1)

The 1,671 harmonised rows remain the validated source-reproduction layer. They are not rewritten. Before analysis-ready evidence is materialised, `scripts/audit_vomhoff_logical_units.py` audits candidate logical units using source Figure, run, RAT, raw application-protocol key, data object and target phase while intentionally ignoring `diff_time` as an identity field.

The audit separates the phases explicitly plotted by the source R scripts from auxiliary instrumentation/log events. Repeated target-phase segments are reported in full and are **not** automatically summed or averaged. Constancy of canonical conditions inside each candidate group is necessary but does not by itself authorise aggregation.

The audit also reports a source-documentation discrepancy for Figure 5: the README says Standby is calculated for 10 s, whereas `fig5.R` contains an explicit normalisation statement only for Idle (20 s). Source reproduction continues to follow the R script; no silent 10 s correction is introduced.


## Stage-2 independence decision (v0.1.10.post2)

Review of the real `v0.1.10.post1` export showed that all 222 multi-segment groups are two-piece `Data Request` groups. The second segment starts at the end of the first within a 6 ms tolerance in every case (5 ms source sampling plus timestamp quantisation allowance), with no metadata conflicts. For a total run-level phase estimand, these segments are additive. This changes only the future analysis-ready aggregation; the 1,671-row source-reproduction table remains unchanged.

The same review revealed exact reuse of NB-IoT/HTTP source segments between Figures 4 and 5. Therefore Figure number/file name must not define statistical independence. `scripts/audit_vomhoff_independence.py` quantifies exact cross-Figure segment signatures and run-level overlap over the full processed table. Deduplication remains a separate reviewed decision because Figure-specific preprocessing can produce distinct derived values from a shared parent run (notably Idle).


## Stage-2 materialisation policy (v0.1.11)

The production cross-Figure audit resolved the remaining independence question: 59 NB-IoT/HTTP `1K.data` runs are reused between Figures 4 and 5. Five non-Idle phases are exact source reuse; `Data Request` contains two contiguous source segments per run and is first summed within run.

`build_vomhoff_stage2_evidence.py` therefore:
1. aggregates contiguous `Data Request` segments within a source Figure/run;
2. assigns a canonical physical/source-run identity across verified Figure-4/Figure-5 reuse;
3. collapses exact non-Idle duplicate phase views to one run/phase value while retaining both Figure contexts;
4. keeps Figure-4 and Figure-5 HTTP `Idle` as dependent but semantically distinct views because Figure 5 applies an additional source filter;
5. keeps Figure-5 MQTT `Idle` in lineage but excludes it from decision evidence, consistent with the README statement that this phase is discarded when the device disconnects;
6. does not invent the README-described 10 s MQTT `Standby` normalisation absent from `fig5.R`.

The resulting analysis-ready artifact uses the physical/source run, not the source segment or source Figure, as the independence unit. No parametric confidence interval is introduced at Stage 2.
