# STACKWISE empirical evidence model

Status: Stage-2 contract, v0.1.10

## 1. Purpose

The empirical evidence layer sits between dataset-specific analysis-ready artifacts and any cross-dataset uncertainty or decision model.

Pipeline:

`raw -> diagnostic -> harmonised/source reproduction -> validation -> analysis_ready -> empirical evidence matrix -> uncertainty model -> stack decision model`

The evidence matrix is not a technology scorecard. It is a typed set of provenance-preserving claims about quantities measured or derived under explicit conditions. Its main purpose is to prevent values with different denominators, system boundaries or statistical units from being pooled merely because they share a physical unit.

The Stage-2 contract is defined by:

- `datasets/schema/evidence_record.schema.json`;
- `datasets/evidence_metric_catalog.yml`;
- `datasets/evidence_boundary_taxonomy.yml`;
- `stackwise.evidence` validation and compatibility helpers.

The existing canonical observation schema remains the contract for dataset harmonisation and is not replaced by the evidence schema.

## 2. Formal definition

An evidence record is a verifiable claim about one quantity under one explicit scientific interpretation:

`e = <P, S, M, C, B, U, D, Q, A>`

where:

- `P` = provenance: dataset, study, DOI, licence, source artifact;
- `S` = tested stack/system configuration;
- `M` = metric identity, family, unit and value semantics;
- `C` = workload and experimental conditions;
- `B` = measurement/accounting boundary;
- `U` = empirical and independence units;
- `D` = derivation lineage, including parent evidence and shared parameters;
- `Q` = uncertainty basis;
- `A` = applicability domain and limitations.

An evidence record is therefore not equivalent to a raw sample, a row of a harmonised table, or an MCDA criterion value.

## 3. Metric identity

Physical units do not define scientific comparability.

For example, all of the following may be measured in joules but are different metrics:

- whole-device phase energy;
- whole-device capture energy;
- radio-rail full-capture energy;
- baseline-subtracted radio transaction energy;
- confirmed-minus-unconfirmed radio energy difference;
- expected whole-device energy per application report.

Each has a separate `metric_id` in the metric catalogue. A future bridge model may map between some of them, but the evidence matrix must not silently relabel one metric as another.

Canonical units are mandatory at the evidence layer. Unit conversion is allowed only when the source unit and transformation are known. Canonical-unit equality is necessary but not sufficient for direct comparison.

## 4. Structured measurement boundary

The harmonised observation field `measurement_boundary` is retained for source-level processing, but Stage 2 decomposes it into orthogonal dimensions.

### 4.1 `system_scope`

Examples:

- `radio_rail`;
- `whole_device`;
- `gateway_receiver`;
- `network_path`;
- `application_path`;
- `infrastructure`;
- `lifecycle`.

### 4.2 `temporal_scope`

Examples:

- `phase`;
- `transaction`;
- `session`;
- `trace_window`;
- `reporting_cycle`;
- `reception_event`;
- `logical_frame`;
- `day`;
- `campaign`.

### 4.3 `accounting_basis`

Examples:

- `per_phase`;
- `per_transaction`;
- `per_capture`;
- `time_average`;
- `per_reception`;
- `per_logical_frame`;
- `per_attempt`;
- `per_success`.

### 4.4 `conditioning`

This field makes denominators explicit. For example, LoED CRC status is conditional on a recorded gateway reception. It is not unconditional per transmission attempt.

### 4.5 Payload and protocol accounting

`payload_basis` distinguishes application payload, UDP/IP payload, LoRaWAN FRMPayload, PHY payload and source-specific message size.

`baseline_accounting`, `ack_rx_accounting` and `retry_accounting` state whether these components are included, excluded, conditional, not applicable or unknown.

`path_start` and `path_end` define the measured path endpoint where this is meaningful.

Technology-specific operating conditions such as phase name, data-rate mode, frequency, bandwidth, spreading factor, coding rate, bit rate and operator are carried explicitly when relevant. The metric catalogue can declare `direct_condition_fields`; if one of those conditions is unknown, the automatic compatibility check cannot return C0 direct.

## 5. Statistical unit and replication

Every record distinguishes:

- `empirical_unit`: the unit represented by the source or derived observation;
- `independence_unit`: the unit that may legitimately contribute independent replication;
- `n_source_observations`;
- `n_independent_units`;
- `dependence_structure`.

High-frequency electrical samples are not experimental replications. Gateway receptions are not independent transmitted packets. Source segments are not necessarily independent physical runs.

A missing or non-identifiable number of independent units remains null; it must not be replaced by the number of within-trace samples.

## 6. Evidence quality is multidimensional

The historical `evidence_grade` in the dataset registry is retained as a source/provenance grade. Stage 2 names this axis `source_grade`.

It must not be interpreted as inferential strength.

Three independent descriptors are used:

1. `source_grade`: A/B/C/D according to source accessibility, provenance and documentation;
2. `derivation_class`: direct empirical, source reproduced, validated derived, analytical, literature derived, assumption or expert prior;
3. `uncertainty_basis`: replicated independent units, single independent unit, hierarchical observational evidence, shared-parameter uncertainty, deterministic bound, external prior required, or none.

Thus a Grade-A dataset can legitimately have `single_independent_unit` uncertainty for a particular configuration.

## 7. Shared parameters and correlated uncertainty

Derived evidence must preserve `parent_evidence_ids` and `shared_parameter_ids`.

This is essential for Stage 3. Two derived records that use the same uncertain voltage, calibration constant, device effect or study effect are not independent merely because they occupy different rows of the matrix.

Example: the InSecTT power/energy derivations for all 20 configurations share the independently inferred source-voltage parameter. Stage 3 must propagate that shared uncertainty jointly rather than drawing 20 independent voltage errors.

## 8. Compatibility classes

Compatibility is a relation between evidence records, not a property of a technology.

### C0_DIRECT

Direct comparison is allowed only when:

- `metric_id` is identical;
- canonical unit is identical;
- all critical boundary dimensions are known and identical;
- workload conditions match, except for factors explicitly declared as the comparison variable;
- no denominator or endpoint is changed.

The `assess_compatibility()` helper is deliberately conservative and requires the caller to declare intended varying factors such as `technology`.

### C1_BRIDGEABLE

Evidence is not directly comparable, but an explicit transformation/component model can connect the estimands. The bridge must retain provenance, parent evidence and uncertain shared parameters.

Examples include radio-rail versus whole-device energy or transaction energy versus reporting-cycle energy.

C1 does not authorise pooling. It states only that a scientifically explicit bridge may be possible.

### C2_CONDITIONAL

Evidence is useful for characterization, covariate modelling or scenario calibration but is not a directly comparable decision criterion as recorded.

Examples include unmatched workloads and raw technology-specific link-quality metrics when they are used only as model inputs. A technology-specific calibrated link model may provide a C1 bridge from RSSI/SNR evidence to a `feasible_link_probability` target; the raw value itself is not the target criterion.

### C3_INCOMPATIBLE

The target estimand cannot be recovered honestly from the available evidence because a required denominator, endpoint, component or semantic link is absent.

Examples:

- LoED CRC-valid fraction -> absolute PDR/delivery probability;
- LoED logical-frame gateway count -> simultaneous RF diversity probability.

## 9. Core-four evidence plan

The first materialised evidence matrix will be long-form and will contain evidence families, not one row per technology.

| Dataset | Evidence family | Planned Stage-2 boundary | Statistical interpretation | Intended role |
|---|---|---|---|---|
| Vomhoff | phase energy | whole device / phase / per phase | source segments aggregated to logical run/phase before inferential modelling | direct or bridge input |
| Vomhoff | phase duration | whole device / phase / per phase | same logical run structure | latency/component bridge input |
| InSecTT | mean current | whole device / trace window / time average | one ~60 s trace per configuration | direct within matched workload; bridge input cross-study |
| InSecTT | integrated charge | whole device / trace window / per capture | one trace per configuration | bridge input |
| InSecTT | derived mean power | whole device / trace window / time average | validated shared 3.3 V parameter; no artificial replication | bridge input |
| InSecTT | derived capture energy | whole device / trace window / per capture | validated-derived; shared voltage uncertainty | bridge input |
| LR-FHSS | full-capture energy | radio rail / trace window / per capture | one trace per DR/ACK configuration | descriptive / bridge input |
| LR-FHSS | incremental transaction energy | radio rail / transaction / per transaction | baseline-subtracted, one independent trace/config | bridge input |
| LR-FHSS | ACK/RX overhead energy | radio rail / transaction / difference | paired configuration contrast; n=1 per side | descriptive, not population mean |
| LoED | RSSI | gateway receiver / reception event / per reception | nested observational receptions | link-model input |
| LoED | SNR | gateway receiver / reception event / per reception | nested observational receptions | link-model input |
| LoED | CRC status | gateway receiver / reception event / per reception | conditional on recorded reception | descriptive only |
| LoED | distinct gateway count | gateway receiver / logical frame / per logical frame | exact-PHY CRC-valid logical-frame semantics | descriptive/link-model input |
| LoED | gateway/SF/frequency/time variation | gateway receiver / reception event or day | nested observational structure | uncertainty calibration |

### 9.1 Vomhoff

The 1,671 harmonised observations are source-segment units. They must not automatically become `n_independent_units=1671`. The Stage-2 builder must first define and validate a logical run/phase aggregation that removes source segmentation as pseudo-replication while retaining the source-reproduction table unchanged.

### 9.2 InSecTT

There are 20 configurations but only one approximately 60 s trace for each. The millions of current samples support accurate integration of each capture but not between-run population uncertainty. The inferred approximately 3.3 V parameter is a validated derived parameter and must be linked through `shared_parameter_ids` rather than written back as raw voltage provenance.

Thread uses UDP as a transport protocol; UDP is not an application protocol. v0.1.10 corrects only this metadata field and does not change any numerical transformation.

### 9.3 LR-FHSS

Full-capture energy and incremental transaction energy remain separate metrics. ACK/noACK differences are capture-specific contrasts because there is one trace per configuration. They must not receive confidence intervals based on within-trace electrical samples.

### 9.4 LoED

LoED remains reception-side evidence. Its validated analysis-ready unit is a CRC-valid exact-PHY logical frame within one source day; wall-clock time is not part of identity. `gateway_count` is distinct-gateway observation diversity, not simultaneous reception multiplicity and not PDR.

## 10. Evidence missing before MCDA

The core-four matrix is expected to remain sparse. Missing cells are scientific results, not implementation failures.

### 10.1 Delivery reliability and coverage

No core dataset supplies a common attempted-transmission denominator across candidate technologies. Future `delivery_probability` and `feasible_link_probability` require additional standards/literature/testbed evidence or explicit technology-specific link models.

LoED cannot fill this gap by treating CRC-valid fraction as PDR.

### 10.2 End-to-end application latency

Vomhoff phase durations can support a component model but do not by themselves define application-to-application latency. Comparable end-to-end latency evidence is still missing.

### 10.3 Common device-energy decision estimand

The future target `expected_device_energy_per_application_report_j` is not directly observed across all technologies. It requires an explicit component/accounting model that connects radio-only and whole-device evidence under scenario-specific reporting/session policies.

### 10.4 Standards-based feasibility

Payload ceilings, band/regulatory constraints, operator dependency, topology, mobility support, infrastructure availability and protocol compatibility must enter as source-backed standards/vendor evidence. They are not preference scores.

### 10.5 Infrastructure and lifecycle cost

Current fleet YAML values are smoke/prototype inputs, not publishable cost evidence. Lifecycle cost needs explicit ownership, hardware, subscription, maintenance, replacement and time-horizon boundaries.

### 10.6 Upper-layer protocol/security overhead

A layer-aware stack model will eventually require evidence or analytical accounting for transport, security, application and management layers. Stage 2 first identifies these gaps; it does not add arbitrary datasets merely to populate them.

## 11. Prohibited transformations

Until an explicit bridge model exists, the following are prohibited:

- pooling all positive `energy_j` values across datasets;
- bootstrap confidence intervals over high-frequency samples as if they were independent runs;
- converting LoED CRC fractions into PDR;
- converting logical-frame gateway diversity into simultaneous RF diversity;
- treating RSSI/SNR/RSRP/SINR as one cross-RAT scalar utility without technology-specific calibration;
- assigning arbitrary uncertainty such as a fixed standard deviation to missing empirical uncertainty;
- replacing missing evidence with default MCDA scores.

## 12. Historical implementation plan after v0.1.10 — completed by v0.1.15

The following Stage-2 plan was defined after v0.1.10 and is now complete for the core-four. It is retained here as provenance of the implementation sequence:

1. implement and validate Vomhoff logical run/phase aggregation;
2. materialise InSecTT validated-derived power/energy records with shared-voltage provenance;
3. materialise LR-FHSS full-capture and transaction records as separate metrics;
4. expose LoED reception/link summaries at appropriate nested statistical units;
5. build `core_four_evidence_matrix.parquet` plus a human-readable audit table;
6. validate every row against the Stage-2 contract;
7. report evidence gaps and compatibility classes before any uncertainty model is fitted.

The completed Stage-2 outputs still do not authorise MCDA ranking. Stage 3 is governed by `UNCERTAINTY_MODEL.md`.

## 13. Vomhoff pre-materialisation audit checkpoint

The source-reproduction adapter intentionally preserves `run × event × diff_time` segments because the source R scripts use `diff_time` as a grouping key. Stage-2 evidence must not treat those segments as independent replicates.

Before a logical run/phase aggregation is implemented, `v0.1.10.post1` requires an audit of the real 1,671-row table. Candidate identity excludes `diff_time` but retains source Figure, source run, RAT, raw protocol key, data object and source event. Only phases explicitly used on the source Figure 3--5 phase axes are candidates for direct phase evidence; auxiliary event labels remain provenance unless separately justified.

For candidate groups with more than one source segment, the audit reports both sum and mean diagnostics but authorises neither. The scientific decision must determine whether repeated segments are additive portions of one phase, repeated occurrences of the same phase estimand, or a different source structure. This prevents pseudo-replication and prevents an equally problematic blind summation.


## 14. Vomhoff run/phase and cross-Figure independence decisions

The production `v0.1.10.post1` audit resolved the repeated-segment question for the target estimand used by STACKWISE. The 222 repeated groups are all two-segment `Data Request` groups, all metadata-consistent, and all temporally contiguous within the source sampling/timestamp resolution. For `whole_device_phase_energy_j` and corresponding phase duration at the *experimental-run* unit, these contiguous segments are additive. The independent unit remains the experimental run, not the source segment.

This does not yet make the source-Figure/run/phase table an independent evidence table. Figure 4 NB-IoT/HTTP and Figure 5 NB-IoT/HTTP reuse exact source segments for the same runs. Therefore source Figure is a derivation context, not an independence boundary. Stage-2 lineage must distinguish:

- a canonical parent experimental run/phase;
- one or more source-Figure reproduction derivations from that parent;
- any Figure-specific preprocessing/normalisation differences.

`v0.1.10.post2` quantifies that overlap over the full processed table. It does not deduplicate automatically. Final parent-run identity is fixed only after that report is reviewed.


### Vomhoff materialised example

Vomhoff demonstrates why evidence lineage and independence are explicit parts of the Stage-2 contract. The 1,671 source-reproduction rows are source `run × event × diff_time` segments. In Stage 2, contiguous `Data Request` segments are additive within run. Verified Figure-4/Figure-5 NB-IoT/HTTP reuse is collapsed at the physical/source-run level rather than treated as independent evidence.

Figure-specific transformations are not erased: Figure-5 HTTP `Idle` remains an alternate dependent view, while source-declared invalid MQTT `Idle` is not promoted to decision evidence. The run-level Parquet remains the empirical distribution source for Stage 3; the evidence-record layer reports means and independent-unit counts without artificial precision.


## 14. Implementation context and the meaning of C0 (v0.1.11.post1)

Stage-2 evidence must preserve the measured implementation, not only the nominal radio or protocol label. Optional structured fields are therefore added for `implementation_context_id`, `device_model`, `radio_module`, `firmware_version`, `measurement_instrument`, `acquisition_software`, and `implementation_notes`.

This is required before materialising InSecTT: BLE, Thread and EPhESOS are measured on the nRF52840 development platform, whereas the UWB configuration uses an nRF52832 plus Qorvo DW1000 board. Those measurements are valid system-level observations, but an observed difference cannot automatically be attributed to the nominal wireless protocol alone. Implementation differences must either be matched or explicitly declared as comparison factors.

`C0_DIRECT` is henceforth interpreted as **direct estimand comparability**: metric semantics, measurement boundary and required conditions are compatible. It is not an instruction to concatenate observations or perform naive statistical pooling. Pooling across studies, devices, dependent views or shared calibration parameters requires an explicit Stage-3 statistical model that respects `study_id`, implementation context, `independence_unit`, `dependence_structure`, `parent_evidence_ids`, and `shared_parameter_ids`.


## 16. InSecTT materialised evidence and shared calibration (v0.1.12)

InSecTT is materialised at one row per technology x reporting-period trace. The 20 traces are separate configurations, not replicated runs of one common condition. `sample_count` remains provenance for the high-resolution current trace; it never becomes `n_independent_units`.

Each configuration generates four evidence records:

1. `trace_mean_current_a` — direct empirical, whole-device, complete trace, time-average;
2. `trace_charge_c` — direct empirical, whole-device, complete trace, per-capture integration;
3. `derived_mean_power_w` — validated-derived from mean current and one shared voltage parameter;
4. `derived_capture_energy_j` — validated-derived from integrated charge and the same shared voltage parameter.

The shared parameter is stored separately because its future uncertainty is correlated across all derived records. The 20 configuration-specific implied voltages are validation checks against rounded published mean-power values, not 20 independent calibration measurements. No confidence interval is inferred from their spread.

Implementation context is part of applicability: UWB uses nRF52832 + DW1000, while BLE, Thread and EPhESOS use nRF52840-based implementations. Thus direct evidence remains scientifically useful as measured system configurations, but protocol-only attribution is not identified by this dataset.


## 17. LR-FHSS materialised evidence (v0.1.13)

LR-FHSS contributes radio-interface-only evidence from eight approximately 60 s source captures (confirmed/unconfirmed x DR8--DR11). The implementation context is LR1121DVK1TBKS / LR1121 in a complete LR-FHSS network, measured with Keysight N6705A DC Power Analyzer hardware and Keysight 14585A Control and Analysis Software. The Zenodo record's original `Power Analyzer: Keysight 14585A` wording is retained as a provenance discrepancy. The source dataset specifies 4-byte FRM payload and +14 dBm transmit power; the associated publication provides the 3.3 V radio supply used by the harmonised integration.

Three metric families are materialised:

1. `radio_full_capture_energy_j`: measured/integrated energy over the entire capture, baseline included.
2. `radio_incremental_transaction_energy_j`: full-capture energy minus trace-specific low-current baseline energy, after validating exactly one TX burst. This is a transaction-level bridge input, not whole-device energy per application report.
3. `radio_ack_rx_overhead_energy_j`: confirmed minus unconfirmed incremental transaction energy at matched DR. This is a single capture-specific contrast and is descriptive only.

The low-current baseline uses the trace-specific mean for samples with `|I| <= 100 uA`. Its numerical contribution is below 0.1% of the full-capture energy in all eight validated traces, but its uncertainty is not converted into an artificial CI. All eight configuration records have one independent unit. Electrical samples contribute integration precision only, not experimental replication.


## 18. LoED materialised evidence policy (v0.1.14)

LoED contributes hierarchical reception-side evidence, not transmission-attempt reliability. The materialised evidence layer contains:

- `gateway_rssi_dbm`: mean recorded-reception RSSI within exact SF/frequency/bandwidth strata;
- `gateway_snr_db`: mean cleaned canonical SNR within the same strata;
- `gateway_crc_valid_fraction_of_receptions`: CRC-valid proportion with recorded receptions as denominator;
- `logical_frame_distinct_gateway_count`: mean distinct-gateway observation count for CRC-valid exact-PHY logical frames;
- `logical_frame_multi_gateway_fraction`: proportion of such logical frames observed by more than one distinct gateway.

All LoED records use hierarchical observational uncertainty with `n_independent_units = null`. Companion summary tables preserve descriptive dispersion and gateway structure. RSSI/SNR are bridge inputs for a later technology-specific feasible-link model; CRC and logical-frame diversity are not bridges to PDR.


## 19. Unified core-four matrix contract (v0.1.15)

Stage-2 source records are now assembled without changing their metric identities or boundaries. The canonical matrix contains 398 records across 14 empirical metric IDs plus one shared InSecTT calibration parameter. The matrix assembler validates schema/catalogue conformity, global evidence-ID uniqueness, parent lineage and shared-parameter lineage. Optional implementation fields absent from the earlier Vomhoff materialisation are added as null columns in tabular exports; no information is invented.

The assembly produces a boundary profile rather than forcing a common denominator. Twenty distinct dataset/metric boundary signatures remain, including whole-device phase, whole-device trace-window, radio-rail transaction/capture and gateway-reception/logical-frame evidence. This heterogeneity is intentional.

The decision-target gap matrix audits five target-only estimands. Bridgeable evidence remains C1 until an explicit model is implemented; conditional LoED link evidence remains C2 for delivery modelling; prohibited CRC/diversity proxies remain excluded; absent evidence is labelled E0_MISSING and is never assigned a default score. Successful assembly completes the core-four inventory portion of Stage 2 and authorises work on Stage 3 uncertainty specification, not publication MCDA.
