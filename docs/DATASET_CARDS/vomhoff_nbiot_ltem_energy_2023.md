# Dataset card: `vomhoff_nbiot_ltem_energy_2023`

## Identity

- DOI: `10.5281/zenodo.7603641`
- Technologies: NB-IoT, LTE-M
- Application protocols represented: HTTP, MQTT
- Evidence grade: A
- Status: source reproduction validated; within-Figure run/phase aggregation rule resolved; cross-Figure independence audit pending

## Licence

CC BY 4.0, verified from the live/public record during ingestion. Raw external files remain outside Git.

## Scientific role

Run-level device energy evidence for cellular IoT, including authentication/connection/data-transfer/idle/postprocessing phases and an HTTP/MQTT comparison.

## Raw structure

Three high-frequency CSV files associated with source Figures 3–5 plus R scripts. Relevant fields include current, voltage, per-sample charge, per-sample energy, source phase duration, run, event, RAT type, application protocol and optional data object.

## Measurement boundary

Device-level measurement for the experimental setup represented in the source dataset. The canonical record retains source phase and run metadata.

## Statistical unit

For source reproduction: run × event × source `diff_time` segment. For new STACKWISE statistics, segments belonging to one experimental run may need aggregation to the logical phase/run level. Source segments are not automatically independent replicates.

## Harmonisation

The adapter follows grouping/normalisation logic from `fig3.R`, `fig4.R` and `fig5.R`. Two important bugs were fixed during development: distinct repeated event segments must retain `diff_time`; missing grouping values must be canonicalised before chunked accumulation.

## Validation

Final source-derived result: 1,671 rows, zero duplicate observation IDs and clean schema validation. Source Figures 3–5 were independently reproduced to audit grouping and normalisation behaviour.

## Analysis-ready transformation

Not yet finalised. The validated 1,671-row source-reproduction table preserves `run × event × diff_time` segments. Production review found 1,449 candidate source-Figure/run/phase groups and 222 two-segment `Data Request` groups. Every repeated pair is temporally contiguous within a 6 ms audit tolerance and metadata-consistent. For the Stage-2 estimand `total phase within one experimental run`, those repeated segments are additive and remain parent lineage rather than independent replicates.

Before final materialisation, `v0.1.10.post2` audits cross-Figure source reuse. Figure 4 and Figure 5 NB-IoT/HTTP already show exact repeated source segments for runs 2--60, so source Figure cannot be treated as independent replication.

## Limitations

Cross-study generalisation must account for study/device/network conditions. The dataset does not by itself supply every workload required by the final stack-selection model.


## Stage-2 evidence status (v0.1.11)

- Independence unit: canonical physical/source run.
- Contiguous repeated `Data Request` segments: additive within run.
- Verified Figure-4/Figure-5 NB-IoT/HTTP source reuse: counted once for exact non-Idle phase evidence.
- Figure-5 HTTP Idle: alternate dependent source-filtered view.
- Figure-5 MQTT Idle: retained in source reproduction but excluded from decision evidence per source README.
- Figure-5 MQTT Standby: source-script value retained with README/script discrepancy limitation; no silent 10 s normalisation.
- Run-level empirical values are preserved for Stage-3 uncertainty modelling; source samples/segments are not treated as independent replicates.
