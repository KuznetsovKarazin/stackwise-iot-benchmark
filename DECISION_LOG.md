# STACKWISE decision log

This file records methodological decisions that affect scientific interpretation. Decisions are intentionally separated from implementation details so they can be cited or challenged later.

## D001 — Feasibility before preference

**Decision:** Apply hard technical feasibility constraints before MCDA ranking.

**Reason:** An infeasible technology must not become preferred merely because soft criteria compensate for a violated requirement.

## D002 — Preserve measurement boundaries

**Decision:** Never pool energy, latency or link-quality values across incompatible measurement boundaries without an explicit transformation/model.

**Reason:** Radio-only, full-device, modem, gateway and end-to-end measurements describe different quantities.

## D003 — Do not invent missing voltage

**Decision:** If a trace contains current but source voltage is absent, report charge/current and leave energy missing unless voltage is introduced as an explicit external or validated derived parameter.

**Applied to:** InSecTT.

## D004 — Separate source reproduction from new analysis

**Decision:** Preserve a source-reproduction layer that follows the original authors' processing, and create a distinct analysis-ready layer for STACKWISE-specific statistical units and transformations.

**Reason:** Reproducing a published figure and constructing an independent statistical analysis are different tasks.

**Applied to:** Vomhoff Figures 3–5.

## D005 — Experimental runs, not within-trace samples, define replication

**Decision:** High-frequency samples from one physical capture are not treated as independent experimental replicates.

**Reason:** Otherwise standard errors become artificially small through pseudoreplication.

**Applied to:** InSecTT and LR-FHSS.

## D006 — Inferred InSecTT voltage remains derived provenance

**Decision:** The approximately 3.3 V source voltage independently reconstructed from the publication power table is not written back as if it were raw dataset metadata.

**Reason:** The inference is extremely well validated but still comes from cross-source reconstruction.

## D007 — LR-FHSS canonical energy is full-capture energy

**Decision:** `energy_j` for LR-FHSS denotes the entire recorded approximately 60 s radio trace.

**Reason:** Capture duration includes baseline sleep and must not be silently relabelled as per-message energy.

## D008 — LR-FHSS incremental transaction energy is a derived metric

**Decision:** Derive transaction incremental energy by subtracting a documented sleep baseline after confirming exactly one TX burst per capture.

**Reason:** This produces a more portable transaction metric while preserving the original full-capture energy.

## D009 — ACK overhead is capture-specific until replicated

**Decision:** Confirmed-minus-unconfirmed LR-FHSS energy differences are reported as capture-specific ACK/RX overhead, not expected ACK overhead for the technology.

**Reason:** There is only one source trace per DR/confirmation configuration; Rx1/Rx2 behaviour can materially change individual captures.

## D010 — LoED reception logs do not imply absolute PDR

**Decision:** LoED will provide reception-side RSSI/SNR/SF/CRC/gateway-diversity evidence but not absolute packet-delivery probability by default.

**Reason:** Received-packet logs do not supply a complete denominator of all transmitted packets.

## D011 — LoED sample for development, full archive for production

**Decision:** Build and test the LoED adapter on the official six-day sample, then rerun the frozen adapter on the complete public archive for paper results.

**Reason:** This reduces development cost without silently turning a convenience sample into the final evidence base.

## D012 — Evidence uncertainty includes study/design uncertainty

**Decision:** Dense sampling inside one experiment does not justify narrow technology-level uncertainty. Study, device, environment and measurement-boundary uncertainty must be represented separately.

**Reason:** Measurement precision and external validity are different quantities.

## D013 — LoED physical payload is fingerprinted, not copied

**Decision:** Retain a SHA-256 fingerprint of the public LoED `physical_payload` field for packet identity while excluding the raw payload string from the harmonised table.

**Reason:** The fingerprint is sufficient for reproducible cross-gateway identity checks and reduces unnecessary propagation of packet contents into derived research artefacts.

## D014 — LoED gateway diversity requires temporal packet clustering — SUPERSEDED

**Historical decision (superseded by the later full-corpus logical-frame audit):** Reconstruct a transmission candidate only when gateway rows share the exact physical-payload fingerprint within one source day and occur within a configurable short temporal gap.

**Reason:** The same encrypted physical frame can be received by multiple gateways, but an identical frame retransmitted later must not be silently merged with the earlier transmission.

**Historical default:** 1.0 s. This rule is no longer used after the full-corpus audit demonstrated that fixed wall-clock gaps are not defensible for physical-transmission identity.

## D015 — CRC-valid fraction is reception-conditional, not PDR

**Decision:** Gateway/day summaries may report the fraction of recorded receptions with a valid CRC, but this metric is explicitly labelled conditional on received rows.

**Reason:** LoED does not enumerate all transmission attempts, so neither missing rows nor CRC-valid fractions provide an absolute packet-delivery denominator.


## D-010 — Full LoED processing must be bounded-memory and day-partition aware

**Decision.** The full LoED corpus is processed directly from the source ZIP into Parquet in chunks. Validation and packet-reception clustering operate one source day at a time rather than loading the entire corpus into a single pandas DataFrame.

**Reason.** The six-day sample already contains 326,870 gateway receptions. The full campaign is substantially larger, and whole-table materialisation would make reproducibility dependent on workstation RAM rather than on the scientific method. Packet identity is already constrained within source day by design, so day-partition processing preserves the clustering semantics.

**Consequence.** `stackwise harmonize loed_lorawan_edge_2020 --strict` automatically uses the streaming path, prefers the complete ZIP when both sample and full archives are present, and writes compressed Parquet incrementally. Validation and analysis-ready cluster outputs are likewise generated incrementally.

## D-LOED-STREAM-002 — Single-pass validation of monolithic full LoED Parquet

**Decision.** Full-corpus LoED validation and analysis-ready construction must scan the harmonised Parquet once sequentially and reconstruct one source day at a time. Repeated filtered scans by `source_file` are prohibited for the paper-scale corpus.

**Reason.** The v0.1.8 approach was memory-bounded but repeatedly rescanned the same Parquet file, producing multi-hour validation runtimes. The harmoniser already writes source days contiguously, so a one-pass day buffer preserves the intended statistical unit while reducing I/O complexity from approximately days × corpus scans to one corpus scan.


## D015 — LoED clusters represent CRC-valid logical frames, not physical emissions

**Decision:** Analysis-ready LoED clustering groups all CRC-valid receptions of the exact PHY-payload fingerprint within one source day. CRC-invalid receptions are excluded from packet identity reconstruction.

**Reason:** A full-corpus audit of 865 clusters with observation spans above 1 s showed both repeated confirmed/unconfirmed uplink observations and systematic multi-gateway timestamp offsets around one second. Therefore a fixed wall-clock threshold cannot reliably distinguish one physical RF emission from retransmissions across unsynchronized gateway clocks.

**Consequence:** `gateway_count` is interpreted as distinct-gateway observation diversity for a logical LoRaWAN frame. Timestamp span may include clock offsets and retransmissions. It is not simultaneous RF multiplicity and is not PDR.


## D-LOED-07 — Validation must not rebuild deterministic derived artifacts by default

**Decision.** Once the LoED analysis-ready logical-frame Parquet has been built under a fixed clustering semantic, routine validation reuses that artifact. Gateway-level structural checks and logical-frame checks are treated as separate validation layers. A full logical-frame rebuild is reserved for explicit semantic audits after changing clustering rules.

**Rationale.** Reconstructing millions of deterministic groups during every validation duplicated work already performed by the analysis-ready stage and caused multi-hour runtimes without adding evidence when neither the harmonised input nor clustering semantics had changed. Cache reuse is guarded by a local Parquet signature and reported explicitly in the validation summary.


## D-LOED-08 — Validation caches are scoped to their exact input artifact

**Decision.** Implicit reuse of the repository-level LoED logical-frame Parquet is permitted only for the canonical repository LoED observations Parquet. Temporary fixtures, alternative experiments, and external Parquet inputs must reconstruct logical-frame summaries from their own data unless a matching cache is passed explicitly.

**Rationale.** A cache is a derived scientific artifact, not a global constant. Reusing a valid cache for a different input can produce internally plausible but scientifically incorrect validation summaries. Input-scoped cache isolation is therefore a correctness property, not merely a testing convenience.

## D-EVID-01 — Stage-2 evidence records are distinct from harmonised observations

**Decision.** The canonical observation schema remains the dataset-harmonisation contract. Cross-dataset empirical evidence is represented by a separate typed evidence record.

**Reason.** A source row, an analysis-ready statistical unit and a cross-study scientific claim are different objects. Reusing one schema for all three would hide derivation lineage and encourage invalid pooling.

**Consequence.** Stage-2 records must validate against `datasets/schema/evidence_record.schema.json` before entering uncertainty or decision modelling.

## D-EVID-02 — Measurement boundary is a structured signature

**Decision.** Stage 2 decomposes measurement boundary into system scope, temporal scope, accounting basis, conditioning/denominator, payload basis, baseline/ACK/retry accounting and path endpoints.

**Reason.** A single label such as `full_device_cycle` or `end_device_radio_cycle` is insufficient to establish comparability across studies.

**Consequence.** Equal physical units do not imply direct comparability. Unknown critical boundary fields prohibit C0 direct classification.

## D-EVID-03 — Source grade and inferential strength are separate axes

**Decision.** Registry `evidence_grade` is interpreted as source/provenance quality and is mapped to Stage-2 `source_grade`. Derivation class and uncertainty basis are recorded separately.

**Reason.** A Grade-A source can still contain one independent trace per configuration and therefore cannot support a population confidence interval from within-trace samples.

**Consequence.** No single A-D label is used as a substitute for replication, independence or uncertainty information.

## D-EVID-04 — Compatibility is conservative and relational

**Decision.** Evidence-pair compatibility uses four classes: C0 direct, C1 bridgeable, C2 conditional and C3 incompatible.

**Reason.** Compatibility depends on metric semantics, boundary, denominator, workload and intended comparison factor; it is not a property of a technology alone.

**Consequence.** C1 requires an explicit bridge model and does not authorise pooling. C3 evidence cannot populate the target decision criterion.

## D-EVID-05 — Shared derivation parameters must be explicit

**Decision.** Derived evidence records retain `parent_evidence_ids` and `shared_parameter_ids`.

**Reason.** Parameters such as the inferred InSecTT supply voltage create correlated uncertainty across multiple records.

**Consequence.** Stage 3 must propagate shared uncertainty jointly rather than treating each evidence row as independent.

## D-EVID-06 — Thread UDP metadata belongs to the transport layer

**Decision.** The InSecTT Thread adapter records UDP in `transport_protocol`, not `application_protocol`.

**Reason.** UDP is a transport-layer protocol. The previous field placement was a semantic metadata error.

**Consequence.** No numerical observation, unit interpretation or validated energy/current result changes.


## D-EVID-002 — Audit Vomhoff repeated target-phase segments before aggregation

**Decision.** Do not materialise Vomhoff Stage-2 run/phase evidence by blindly summing or averaging the validated `run × event × diff_time` rows. First audit repeated segments within a candidate logical key composed of source Figure, source run, RAT, raw application-protocol key, source data object and source target event.

**Reason.** The 1,671 source-reproduction rows follow the authors' R grouping semantics, but repeated `diff_time` rows inside one run are not automatically independent replicates. Conversely, summing them is only valid if they are additive subsegments of one logical phase. The real processed table must decide this rather than a synthetic assumption.

**Scope.** Only phases explicitly plotted by source Figure 3--5 scripts are candidate phase evidence at this checkpoint. Auxiliary instrumentation/log events remain in the validated source-reproduction layer but are not promoted automatically.

**Additional audit.** Figure 5 source README states a 10 s Standby calculation, while `fig5.R` explicitly normalises only Idle to 20 s. STACKWISE continues to reproduce the R script and reports realised Standby durations separately; no undocumented correction is introduced.

**Consequence.** `v0.1.10.post1` is an audit-only patch. It produces diagnostics and a run manifest but no analysis-ready Vomhoff evidence artifact and no MCDA input.


## D-VOM-01 — Contiguous repeated `Data Request` segments are additive for the run-level phase estimand

**Decision.** For the Stage-2 estimand *total source phase energy/duration within one experimental run*, repeated Vomhoff `Data Request` source segments that belong to the same source Figure/run/RAT/protocol/data-object/event group are additive. Energy, duration and other extensive quantities are summed; the source segment identifiers and `segment_count` remain in lineage. The segments are not treated as independent replicates.

**Evidence.** The production `v0.1.10.post1` audit found 222 multi-segment target groups, all with exactly two segments and all labelled `Data Request`; 119 occur in Figure 4 and 103 in Figure 5. No candidate group has inconsistent technology/protocol/payload/boundary metadata. Direct review of the exported 444 segment rows showed that the start of the second segment follows the first-segment start plus its duration within the source sampling/timestamp resolution in every group. Using a 6 ms audit tolerance (5 ms source sampling plus 1 ms timestamp quantisation allowance), all 222 pairs pass; the maximum absolute residual is approximately 5.22 ms.

**Reason.** The temporal adjacency and identical within-group conditions support interpretation as contiguous source subdivisions of one run-level phase. Treating the two rows as independent observations would create pseudo-replication. Taking their arithmetic mean would estimate a segment rather than the required total run-level phase.

**Scope.** This rule is specific to the run-level *total phase* estimand. It does not claim that a source segment can never be analysed separately for a different estimand.

## D-VOM-02 — Source Figure is not an independence boundary

**Decision.** Vomhoff records from different source Figures must not be counted as independent merely because they originate from different CSV/Figure contexts. Cross-Figure parent-run/source-segment reuse must be audited before final Stage-2 evidence materialisation.

**Evidence.** In the reviewed multi-segment export, all 118 NB-IoT/HTTP `Data Request` source segments from Figure 4 runs 2--60 are exactly matched by Figure 5 NB-IoT/HTTP segments on timestamp, duration, energy, payload and protocol metadata. Source-reproduction summaries likewise show identical values for several HTTP phases, while Figure-specific preprocessing can still differ for phases such as Idle.

**Consequence.** `v0.1.10.post2` adds a non-destructive exact-segment/run-overlap audit. Final deduplication is intentionally not authorised until the full 1,671-row cross-Figure report is reviewed. Distinct Figure-specific transformations may later be retained as derived records sharing the same parent-run lineage rather than as independent empirical units.


## D-VOMHOFF-03 — Figure 4/5 source reuse defines dependence, not extra replication

**Decision.** The 59 NB-IoT/HTTP `1K.data` run pairs shared by Figures 4 and 5 are one physical/source-run population. For the five non-Idle phases whose source segments are exactly reused, Stage 2 retains one canonical run/phase value and keeps both Figure contexts in lineage.

**Reason.** The production independence audit found 354 exact cross-Figure segment signatures, five shared events per run, and 59/59 strong reuse pairs. Figure/file identity is therefore not an independence boundary.

**Consequence.** Figure-specific derived views may coexist only when their preprocessing semantics differ; they share the same physical-run dependence.

## D-VOMHOFF-04 — Figure-5 Idle and Standby follow explicit applicability policy

**Decision.** Figure-5 MQTT `Idle` remains in source reproduction but is excluded from decision evidence because the source README explicitly states that those values are discarded when the device disconnects. Figure-5 HTTP `Idle` is retained only as an alternate source-filtered view dependent on the same Figure-4 parent runs. The README-only 10 s MQTT `Standby` normalisation is not imposed because `fig5.R` does not implement it.

**Reason.** Source reproduction and STACKWISE analysis-ready evidence have different responsibilities: the former reproduces executable source logic; the latter must not promote source-declared invalid observations or silently repair ambiguous source code.

## D-VOMHOFF-05 — Corrected run/phase estimand is separate from source-script segment mean

**Decision.** Stage 2 reports both the original source-segment estimand and the corrected logical run/phase estimand. Contiguous `Data Request` pieces are summed within run before any across-run summary.

**Reason.** The authors' scripts group by `run + event + diff_time` and then average by event; when one event is split into two contiguous `diff_time` segments, treating both as separate replicates changes the estimand and creates pseudo-replication.


## D-2026-08-11 — Preserve implementation context before cross-technology evidence materialisation

**Decision.** Add structured implementation context (`device_model`, `radio_module`, `firmware_version`, `measurement_instrument`, optional stable context ID) to Stage-2 evidence. An implementation mismatch is C2 conditional unless explicitly declared as a comparison factor.

**Reason.** InSecTT changes hardware for the UWB configuration. Omitting implementation context would conflate protocol/radio effects with device/platform effects and would prevent the planned Stage-3 study/device-effects model from being reproduced.

**Consequence.** C0 means direct estimand comparability only; it does not authorise naive pooling across studies, devices or dependent evidence records.


## D-INSECTT-01 — InSecTT independent unit is one configuration trace

**Decision.** Each technology x reporting-period configuration contributes one independent approximately 60 s trace. The approximately six million current samples within that trace are source observations, not experimental replicates.

**Reason.** The public dataset contains one separately measured trace per configuration. Treating samples as independent would create severe pseudo-replication and artificial precision.

**Consequence.** Stage-2 evidence records set `n_independent_units=1`; no sample-level confidence interval is authorised.

## D-INSECTT-02 — Inferred source voltage is one shared derivation parameter

**Decision.** The median implied PPK II source voltage from the 20 publication Table-1 scale checks is materialised once as `insectt_ppk2_source_voltage_v`. Derived power and capture-energy records reference this parameter through `shared_parameter_ids`.

**Reason.** The dataset README does not state the source voltage. The 20 implied values validate a common scale but are not independent measurements of voltage; copying an independent voltage uncertainty into every configuration would destroy the correlation structure.

**Consequence.** Stage 3 must propagate this calibration jointly across all derived InSecTT records. The diagnostic spread is not a confidence interval.

## D-INSECTT-03 — Cross-technology InSecTT effects include implementation context

**Decision.** InSecTT evidence describes measured technology-plus-implementation configurations. UWB uses nRF52832 + DW1000, while BLE, Thread and EPhESOS use nRF52840-based implementations.

**Reason.** Hardware changes are inseparable from the observed current/power differences in this dataset.

**Consequence.** Cross-technology comparisons are valid as system/configuration observations but must not be presented as identified protocol-only effects.


## D024 — LR-FHSS transaction baseline is a within-trace proxy, not replication

**Decision:** `radio_incremental_transaction_energy_j` subtracts the trace-specific mean of the validated low-current band over the full capture duration, after confirming exactly one TX burst.

**Reason:** This preserves the measured trace baseline and avoids treating the rounded publication sleep-current value as an exact universal constant. The low-current samples are repeated observations within one trace and do not increase `n_independent_units`.

**Consequence:** Stage 3 must model baseline/capture uncertainty externally; within-trace samples cannot produce a technology-level confidence interval.

## D025 — LR-FHSS confirmed-minus-unconfirmed is descriptive, not population ACK overhead

**Decision:** Matched-DR confirmed-minus-unconfirmed transaction-energy differences are stored as `radio_ack_rx_overhead_energy_j` with one contrast replication and `intended_use=descriptive`.

**Reason:** Each side of the contrast is represented by one source trace. The difference may include capture-specific RX-window/ACK state behaviour and does not identify a population mean or causal ACK effect.


## 2026-08-11 — LoED Stage-2 summary units and no-independent-n policy (v0.1.14)

**Decision.** Materialise LoED as compact hierarchical evidence summaries, not as 11.26 million evidence records. Direct reception evidence is stratified by exact `SF x frequency x bandwidth`; gateway x PHY and existing gateway/day tables retain implementation/spatial and temporal variability. CRC-valid exact-PHY logical-frame diversity is summarised separately.

**Statistical consequence.** Every LoED evidence record has `n_independent_units = null` and `uncertainty_basis = hierarchical_observational`. Reception rows and logical frames are not treated as independent replications. Descriptive corpus standard deviations are not standard errors.

**Reliability consequence.** `gateway_crc_valid_fraction_of_receptions` and `logical_frame_multi_gateway_fraction` are explicit descriptive metrics and are hard-incompatible with `delivery_probability`. No PDR or delivery denominator is reconstructed.


## 2026-08-11 — Unified core-four matrix preserves heterogeneity and explicit gaps (v0.1.15)

**Decision.** Assemble the four validated source-level evidence artifacts by concatenating typed evidence records under one schema; do not pre-normalise or convert them to MCDA criteria. Preserve one unified shared-parameter registry and validate all parent/shared references globally.

**Reason.** Cross-source values have incompatible or bridgeable accounting boundaries. A canonical inventory must expose those differences before Stage 3 rather than hiding them behind common units or scores.

**Gap policy.** Five future target estimands are audited against all four core datasets. `E0_MISSING` is an explicit absence state, not a value. LoED RSSI/SNR may bridge to a technology-specific feasible-link model; LoED CRC-valid reception fraction and logical-frame diversity remain prohibited proxies for delivery probability. Vomhoff phase duration is recognised only as a bridgeable component of future end-to-end latency.

**LoED stratification note.** One SF7 / 868.3 MHz / 250 kHz reception stratum contains 65,498 recorded receptions and zero CRC-valid receptions. It is retained without causal interpretation and therefore has no CRC-valid logical-frame stratum.


## D-UNC-001 — Stage 3 starts with identifiability, not default distributions

**Decision.** Every dataset/metric group in the 398-record core-four matrix receives an explicit uncertainty specification before any stochastic sampling. No default standard deviation, coefficient of variation or distribution family is permitted.

**Reason.** Replication structure differs radically across sources: replicated physical runs in Vomhoff, one trace per InSecTT/LR-FHSS configuration, and hierarchical dependent observations in LoED. A common fallback distribution would create artificial precision.

## D-UNC-002 — Generic study random effects are not identifiable from core-four

**Decision.** Do not estimate a generic `study_id` random-intercept variance from the four core studies.

**Reason.** Study identity is confounded with technology, hardware implementation, measurement boundary, workload and deployment environment. The current matrix is not a crossed multi-study design. Cross-study variance requires overlapping comparable studies or an explicitly justified prior/sensitivity range.

## D-UNC-003 — Vomhoff calibration unit is the physical/source run

**Decision.** Vomhoff empirical uncertainty may be calibrated using physical-run cluster resampling within matched configurations. All phases belonging to the same run must be resampled jointly and Figure-4/Figure-5 dependent views must remain dependent.

**Reason.** This preserves the Stage-2 anti-pseudoreplication decisions and allows the only immediately identifiable between-run variability in the core-four.

## D-UNC-004 — Single-trace sources require repeatability evidence or priors

**Decision.** InSecTT and LR-FHSS do not receive population confidence intervals from within-trace samples. Population variability remains external-prior/repeatability-evidence dependent.

**Reason.** Each configuration has one independent physical trace. High-frequency sample count is not experimental replication.

## D-UNC-005 — LoED uncertainty requires hierarchical grouped calibration

**Decision.** Do not use reception-row IID bootstrap or sqrt(n) uncertainty for LoED. Future RSSI/SNR uncertainty must be calibrated from grouped campaign structure while preserving joint RSSI/SNR dependence.

**Reason.** Receptions and logical frames are nested/repeated across days, gateways, devices and repeated/retransmitted observations.

## D-UNC-006 — Shared and parent-derived uncertainty must remain correlated

**Decision.** InSecTT derived power/energy share one voltage draw; LR-FHSS parent/child energy records and ACK contrasts retain parent-trace dependence; future Vomhoff phase bridges use joint run-level draws.

**Reason.** Treating these records as independent would double-count information and understate uncertainty.


## D031 — Separate Vomhoff marginal empirical calibration from final joint bootstrap

**Decision.** Calibrate observed conditional run-to-run distributions for each Vomhoff evidence record directly from `physical_run_id`, but do not yet materialise a final joint bootstrap distribution.

**Reason.** Related phase/metric evidence records can share physical runs without necessarily having identical run sets. Independent marginal bootstrap would destroy dependence, while forcing a rectangular joint block before auditing missingness/overlap would introduce an untested assumption.

**Consequence.** v0.1.17 emits run-level samples, marginal dispersion, candidate resampling blocks, run-set overlap and paired-dependence diagnostics. Joint cluster bootstrap is authorised only after production block structure is reviewed.

## D032 — Vomhoff empirical variability is conditional within-study variability

**Decision.** Sample SD/quantiles derived from replicated Vomhoff physical runs describe variability conditional on the original laboratory/source configuration.

**Reason.** The core-four does not identify generic device, implementation or cross-study variance for this estimand.

**Consequence.** Stage-3A may use empirical physical-run distributions but may not relabel them as device-population or cross-study uncertainty.


## DR — 2026-08-11 — Preserve partial Vomhoff run-set missingness in joint bootstrap

**Decision.** Authorise within-block nonparametric physical-run bootstrap for all five Vomhoff experimental blocks. Four blocks use a standard shared-run rectangular resample. The NB-IoT/MQTT block uses union-run resampling over 45 physical runs while preserving the single missing `Data Download` phase value.

**Evidence.** Production Stage-3A has one partial block only: `Data Download` contains 44 runs, all other records contain 45, with pairwise overlap 44/45 = 0.97778. No broader metadata inconsistency or duplicate run sample is present.

**Rejected alternatives.** (i) listwise deletion to 44 runs, because this discards valid observations in all other phases solely to force rectangularity; (ii) imputation of the missing phase, because there is no source-backed value or missingness model; (iii) independent phase bootstraps, because they destroy within-run dependence.

**Consequence.** v0.1.18 materialises block-local bootstrap mean draws and complete-case sensitivity diagnostics. Replicate indices have no cross-block joint meaning, so cross-block dependence remains unidentified rather than silently set by row alignment.

### D-3C-01 — LoED grouped cells are calibration blocks, not IID replicates

**Decision.** Materialise LoED RSSI/SNR at `source day × gateway × exact PHY stratum`, preserving paired first/second/cross moments. Treat these cells as hierarchical calibration blocks, not independent replicates.

**Rationale.** LoED rows are nested across devices, gateways, days and repeated/retransmitted observations. Row-count standard errors are invalid; cell-level aggregation reduces the corpus to a tractable artifact without erasing the principal deployment/time hierarchy.

**Consequence.** Stage 3C may estimate descriptive within-cell/between-cell variance structure and temporal diagnostics, but it does not authorise IID cell/day bootstrap or publication uncertainty sampling. A later resampling/model decision must use the production coverage and autocorrelation outputs.

## D-3D-01 — LoED acquisition campaigns are not exchangeable day replicates

**Decision.** Treat the two separated LoED source-day windows as distinct observed acquisition campaigns. Do not pool source days across the inter-campaign gap and do not estimate a campaign random-effect variance from two campaigns.

**Evidence.** The Stage-3C production day coverage contains 188 unique source days with 186 consecutive one-day transitions and one 386-day gap. This partitions the observed source files into 57 days (2019-02-08 to 2019-04-05) and 131 days (2020-04-25 to 2020-09-02).

**Reason.** A temporal bootstrap that crosses the 386-day gap would create synthetic adjacency unsupported by the source record. Two campaigns are also insufficient to identify an exchangeable campaign-population variance.

**Consequence.** Stage-3D audits autocorrelation separately within each campaign. Any later block resampler must be campaign-stratified; if within-campaign stationarity is not defensible, the two campaigns remain explicit sensitivity/domain-shift scenarios rather than being forced into one random-effects model.

## D-3D-02 — LoED gateways remain observed infrastructure, not an IID bootstrap population

**Decision.** Preserve the complete gateway set attached to each sampled source day. Do not independently bootstrap gateway IDs.

**Evidence.** Stage-3C day coverage varies from two to five observed gateways per source day, while RSSI/SNR between-cell variance is substantial and therefore partly reflects deployment/time composition.

**Reason.** The nine gateways are recurring infrastructure in one deployment, not a random sample from a defined gateway population. Independent gateway resampling would invent a population estimand and break the observed day/gateway composition.

**Consequence.** Stage-3D quantifies gateway-set transitions and campaign-specific gateway coverage. A future source-day block sampler, if authorised, will carry all gateway×PHY cells belonging to each selected day as one dependent cluster.

## D-028 — Full LoED campaign shift is confounded by changing gateway support

**Date:** 2026-08-11  
**Status:** Accepted

**Context.** Stage-3D identified two separated LoED acquisition campaigns and sizeable 2019-vs-2020 RSSI/SNR differences. Production gateway coverage shows 6 gateways in campaign 1 and 5 in campaign 2, with only 2 shared gateways across a 9-gateway union (Jaccard 2/9).

**Decision.** Do not interpret the full-campaign RSSI/SNR difference as a pure temporal effect. Before selecting any campaign-stratified temporal bootstrap, compare the campaigns on common gateway support and quantify within-campaign gateway heterogeneity. Same-gateway and equal-shared-gateway summaries are sensitivity analyses only; they do not identify causal gateway effects because gateway identity remains entangled with location/hardware, traffic, devices and observation timing.

**Consequences.** Campaign random effects, independent gateway bootstrap, causal gateway-composition attribution, block-length selection, publication uncertainty sampling and MCDA remain blocked.


## D-3E-02 — Retain LoED campaigns as fixed deployment scenarios

**Decision.** Treat the 2019 and 2020 LoED acquisition windows as two fixed observed deployment scenarios, not exchangeable campaign draws and not one pooled time series.

**Evidence.** Stage-3E has 6 gateways in campaign 1 and 5 in campaign 2, with only 2 shared across a 9-gateway union. Common-gateway sensitivity changes the magnitude and frequently the sign of the full-campaign shift; the two shared gateways also show heterogeneous cross-campaign RSSI changes.

**Consequence.** No scalar campaign random effect or pure temporal campaign effect is identified. Any stochastic calibration must be conditional within campaign.

## D-3F-01 — Audit within-campaign block length before authorising LoED sampling

**Decision.** Materialise non-circular overlapping source-day moving-block bootstrap sensitivity at 3, 7 and 14 days separately within each fixed campaign. The complete source-day cluster (all observed gateway composition, PHY strata and both RSSI/SNR metrics) moves together.

**Reason.** Stage-3D shows persistent autocorrelation after detrending, including weekly-scale structure, while Stage-3E prohibits cross-campaign pooling and independent gateway resampling. A single block length cannot be selected from intuition alone.

**Consequence.** Stage-3F is diagnostic only. Seven days is a comparison reference, not an authorised final block length. Publication uncertainty sampling and MCDA remain blocked.


## D-3G-01 — Retain LoED block length as unweighted model uncertainty

**Decision.** Do not select 3, 7 or 14 days as a unique LoED temporal block length. Retain all three as an unweighted robustness set within each fixed deployment campaign.

**Evidence.** Stage-3F production medians show systematic width changes with block length: 3-day intervals are generally narrower than 7-day intervals, while 14-day intervals remain materially wider for campaign-2 RSSI/SNR and campaign-1 RSSI. Individual PHY-stratum width ratios are even less stable.

**Consequence.** STACKWISE will not tune a single LoED uncertainty sampler to one arbitrary temporal scale. Later link-feasibility results must be checked across campaign x block-length scenarios. No probabilities are assigned to block-length assumptions.

## D-3G-02 — Center non-circular MBB draws without claiming stationarity correction

**Decision.** Materialise both the raw Stage-3F resampler bias and centered block-bootstrap draws. Centering uses `point estimate + raw draw - mean(raw draws)` separately for each campaign x block-length x PHY x metric.

**Reason.** The non-circular overlapping MBB has finite-sample edge weighting, especially for 14-day blocks in the 57-day campaign. The resulting raw location bias is a resampling artifact for the fixed observed campaign mean. Subtracting a constant preserves within-scenario covariance and shape.

**Guardrail.** Centering does not correct trend/nonstationarity, gateway composition, device/traffic mix or cross-campaign domain shift. The outer block-length robustness envelope is not a probability interval.

## D-3G-03 — Report temporal support independently of reception count

**Decision.** Every LoED campaign x PHY x RSSI/SNR uncertainty record must report observed source-day count and source-day support fraction.

**Reason.** Reception count can be large while temporal support is sparse; conversely, some rare PHY strata may occur on only a small subset of campaign days. Reception rows therefore remain an invalid proxy for temporal replication.


## D-3H-01 — Do not manufacture numeric priors from single-trace source descriptions

**Decision.** The six InSecTT/LR-FHSS single-trace metric families retain unidentified population variability after targeted primary-source review.

**Reason.** InSecTT reports approximately 60 s averaged measurements but no independent replicate-run dispersion. LR-FHSS reports qualitatively negligible differences across several transmission processes but no repeat count, SD, CV or CI. Neither statement identifies a numerical population distribution.

**Consequence.** Default CV/SD is forbidden. The LR-FHSS word `negligible` is not mapped to a numerical CV. Instrument accuracy is not converted to run-to-run or device-population SD. Any later uncertainty envelope for these metrics is a model-sensitivity assumption and must not be cited as empirical repeatability.

## D-3H-02 — Reconcile LR-FHSS measurement hardware and acquisition software

**Decision.** Store `Keysight N6705A DC Power Analyzer` as `measurement_instrument` and `Keysight 14585A Control and Analysis Software` as `acquisition_software`. Preserve the Zenodo wording `Power Analyzer: Keysight 14585A` in provenance notes.

**Reason.** The associated paper identifies N6705A as the measurement hardware, while Keysight documentation identifies 14585A as software used with N6705-family analyzers.

**Consequence.** Re-materialise the 20 LR-FHSS evidence records and unified core-four matrix so structured metadata is corrected. No numerical evidence, boundary, configuration count or uncertainty estimate changes.

## D-3I-01 — Close Stage 3 with mixed uncertainty semantics

**Decision.** Close Stage 3 for the validated core-four evidence without forcing all metric families into one stochastic distribution family.

**Evidence.** Vomhoff supports replicated physical-run nonparametric uncertainty; LoED supports an unweighted campaign × temporal-scale robustness family; targeted primary-source review identifies no defensible numerical population-repeatability prior for the six InSecTT/LR-FHSS single-trace families; CRC/diversity and ACK contrast quantities remain descriptive.

**Rejected alternatives.** (i) default CV/SD for single-trace evidence; (ii) converting instrument accuracy to run-to-run SD; (iii) translating qualitative `negligible` LR-FHSS repeatability into a numerical prior; (iv) assigning probability weights to LoED campaigns or block lengths; (v) a generic study random effect estimated from the four confounded source studies.

**Consequence.** Stage 4 stack-definition and hard compatibility work may proceed. Publication-wide uncertainty sampling, rankings and MCDA remain blocked until common decision estimands and bridge models are defined. Any future single-trace uncertainty envelope must be labelled model sensitivity unless supported by new quantitative repeatability evidence.


## 2026-08-11 — Stage 4A canonical stack representation

**Decision.** Represent a stack as a graph of placed component instances with typed `provides`/`requires` interfaces, not as one technology label or a rigid five-cell table. Functional roles are not mutually exclusive. Native access security and end-to-end security may coexist; gateway/backend mediation is explicit.

**Reason.** A rigid layer table cannot represent non-IP access termination, multiple security mechanisms or management overlays without creating false protocol combinations.

**Hard-feasibility rule.** Feasibility is non-compensatory and tri-state. Unknown required facts block a positive feasible claim.

**Scope.** v0.1.26 defines the contract only. Real protocol capability/compatibility claims require Stage 4B primary-source verification.


## D-4B-01 — Separate protocol variants before stack enumeration

**Decision.** Model NB-IoT/LTE-M IP and Non-IP operation, bare BLE versus IPSP/IPv6, and LoRaWAN LoRa versus LR-FHSS as distinct component variants.

**Reason.** Primary specifications expose materially different upper interfaces. Treating each family as one interchangeable technology label would create false compatibility edges.

**Consequence.** UDP/TCP cannot bind to cellular Non-IP or bare BLE without an explicitly verified adaptation/binding; LoED classical LoRa link evidence is not transferred to LR-FHSS.

## D-4B-02 — Add alternative requirement groups

**Decision.** Extend stack components with `requires_any` OR-groups.

**Reason.** CoAP and LwM2M have multiple legitimate underlying transports/security bindings. Encoding all alternatives as mandatory `requires` would be false, while duplicating every semantic protocol solely for transport choice would obscure the model.

**Consequence.** Every binding still has to be explicit; an OR-group passes only when at least one verified interface is actually bound or supplied by the declared environment.

## D-4B-03 — Separate evidence alignment from standards compatibility

**Decision.** Maintain explicit evidence-to-component alignment records independently of compatibility edges.

**Reason.** A standards-compatible component does not imply that a given empirical dataset measured the same boundary/version/profile.

**Consequence.** Vomhoff remains whole-device/application-context evidence; InSecTT BLE is not IPSP energy; LR-FHSS and LoED remain mode-specific.

## D-4B-04 — Keep EPhESOS evidence-only

**Decision.** Do not promote EPhESOS to a verified interoperable stack component in Stage 4B.

**Consequence.** Its empirical energy evidence remains in the evidence matrix, but verified publication stack enumeration must exclude it unless a separate protocol/interop contract is established.


### v0.1.28 — verified-edge gating for real candidate stacks

**Decision.** A Stage-4C `verified_candidate` passes only when every component is primary-source verified and every explicit binding exactly matches a `primary_source_verified_compatible` Stage-4B edge (source component, target component, interface and relation). Generic `provides/requires` compatibility is necessary but no longer sufficient for real candidates.

**Reason.** Otherwise an interface-name coincidence could silently create a standards claim that was never verified.

**Evidence policy.** Candidate membership does not require complete empirical evidence, but evidence incompleteness is explicit and may not be promoted to a whole-stack cost.

## DR-Stage4D-01 — Quantitative context is not automatically a hard constraint

**Decision.** Benchmark scenarios store payload, reporting interval, latency target and optional
energy budget, but a value affects feasibility only if the scenario explicitly lists the
corresponding hard predicate.

**Rationale.** This prevents a narrative scenario field from silently becoming a rejection
criterion and keeps benchmark assumptions auditable.

## DR-Stage4D-02 — Unknown candidate capability blocks only when decision-relevant

**Decision.** Missing verified capability produces an `unknown` predicate. The overall result is
`unresolved` only if no other hard predicate already fails; otherwise the candidate remains
`infeasible` and the unknown is recorded as non-decision-blocking.

**Rationale.** This preserves scientific honesty without prioritising unnecessary capability
research for candidates already excluded by independent hard constraints.

### D-4E-01 — Do not collapse mobility into one boolean hard capability
**Date:** 2026-08-11

Stage-4D `mobility_supported_verified` was found to be operationally underspecified. Standards distinguish at least idle-mode cell reselection from network-managed connected-mode handover. Forward benchmark analysis therefore keeps two explicit asset-tracking mobility variants rather than selecting one interpretation post hoc.

### D-4E-02 — Do not infer Thread 500-ms guarantee from qualitative low-latency claims
**Date:** 2026-08-11

Thread primary material supports a qualitative low-latency characterization but the reviewed sources do not establish the candidate stack's guaranteed maximum end-to-end latency at 500 ms. The hard predicate remains unresolved.

### D-4E-03 — Do not bridge radio-only LoRaWAN energy to whole-device report energy without a model
**Date:** 2026-08-11

LoED has no device-energy measurement and LR-FHSS energy is radio-interface-only. Neither can directly verify a 0.2 J whole-device/report hard limit. Both agriculture blockers remain unresolved.

### D-4F-01 — Freeze the three remaining hard unknowns rather than invent scalar capabilities
**Date:** 2026-08-11

The remaining Thread latency and LoRaWAN report-energy blockers are configuration/profile dependent and are not identified by the current evidence at the benchmark boundary. Stage 4 closes with these rows unresolved. Hard unknowns cannot be converted to pass/fail by preference or default assumptions.

### D-4F-02 — Separate stack composition from operating profile
**Date:** 2026-08-11

A verified protocol graph does not uniquely determine latency or energy. Future benchmark bridges must bind a stack to an explicit operating profile (for example device role/sleep policy/topology for Thread, or DR/ACK/TX power/payload/retry/device boundary for LoRaWAN).

### D-4F-03 — LR-FHSS radio energy is diagnostic, not the agriculture whole-device hard fact
**Date:** 2026-08-11

The eight validated LR-FHSS transaction-energy records are retained as mode-specific diagnostics. The remote-agriculture benchmark is 16-byte whole-device/report while the source records are 4-byte radio-interface-only measurements. No direct hard-feasibility transfer is authorised.


## D-Stage5A — profile provenance before bridge computation

Decision: do not use protocol defaults, best-performing measured modes, or source capture settings to complete benchmark operating profiles implicitly. Scenario-derived values are labelled as assumptions, not evidence. A bridge may not materialise a numerical decision metric until its required profile fields and source-to-target boundary mapping are explicitly satisfied. The Stage-4 matrix remains frozen while bridge contracts are developed.

## D-Stage5B-01 — Validate the source radio model before payload extrapolation

**Decision.** A Stage-5 LR-FHSS payload bridge must first reproduce the existing 4-byte source traces. A versioned 2% absolute-relative-error threshold is used as a deterministic model-audit tolerance, not as a confidence interval or hypothesis test.

**Result.** Unconfirmed DR8--DR11 pass; confirmed DR8--DR11 fail materially. Confirmed payload extrapolation is therefore prohibited until the source/model mismatch is explained or a better matched model is validated.

## D-Stage5B-02 — Keep the Eq. (6)/Table-6 discrepancy explicit

**Decision.** Use the payload-duration convention that reproduces Table 6 numerically (`effective +3 B`) while separately retaining the equation as rendered (`+2+6/8 B`). Frequency-hop count follows the rendered floor expression. This is an operationalisation for reproducibility, not a causal correction of the publication.

## D-Stage5B-03 — Permit only one-sided component-bound feasibility statements

**Decision.** A validated radio-component value greater than the whole-device budget may reject an exactly matched operating-profile variant because additional device contributions cannot reduce total energy. A radio-component value below the budget cannot prove whole-device feasibility. The generic LR-FHSS candidate remains unresolved until DR/confirmation/profile semantics are explicitly versioned. Best-DR selection after observing model energy is prohibited.

### DR: Stage-5C variants are conditional profiles, not candidate choices

**Decision.** Enumerate all source-aligned LR-FHSS DR/confirmation variants without choosing among them. A variant may inherit a one-sided radio lower-bound exclusion even while its whole-device profile remains incomplete, provided the matched radio lower bound already exceeds the whole-device budget.

**Rationale.** Unknown residual energy and additional retries are non-negative and cannot rescue an already-over-budget radio transaction. The reverse implication is invalid: a below-budget radio component cannot establish whole-device feasibility.

**Consequence.** DR8/DR10 unconfirmed are conditionally infeasible only when the deployment profile explicitly matches the source-aligned variant; DR9/DR11 and all confirmed variants remain unresolved. The generic LR-FHSS candidate stays unresolved.



### D-Stage5D — Protocol control mechanisms are not deployment-selection evidence
**Decision.** Do not infer the LR-FHSS DR, confirmation mode, TX power or radio-hardware deployment choice from standards capability or modeled energy. Retain Stage-5C variants as an unweighted robustness family until explicit deployment/profile evidence exists. Mixed variant outcomes do not update the generic LR-FHSS candidate.

**Rationale.** ADR/LinkADRReq can control radio parameters but requires deployment/network context; confirmed/unconfirmed are distinct message semantics. Selecting a favorable or unfavorable variant after observing energy would be post-hoc conditioning.

### D-Stage5E-01 — Bridgeable evidence is not a decision-ready target
**Date:** 2026-08-12

**Decision.** Separate source-evidence relation from target readiness. A C1/`BRIDGEABLE` source quantity may identify a valid future bridge but is not counted as `READY` until the canonical target estimand is materialised under an explicit operating profile and its parent uncertainty semantics are preserved.

**Rationale.** Counting Vomhoff phase energy, InSecTT capture energy or LR-FHSS radio energy directly as `expected_device_energy_per_application_report_j` would silently change accounting boundaries.

### D-Stage5E-02 — Use feasibility-conditioned energy + lifecycle cost as the first decision-readiness lens
**Date:** 2026-08-12

**Decision.** For the first publication decision slice, treat expected whole-device energy/report and lifecycle cost as mandatory soft decision quantities after hard feasibility. Do not automatically re-score latency, coverage or delivery when the same concept has already acted as a hard screen or when comparable target evidence is absent.

**Rationale.** This avoids double counting and prevents missing cross-RAT coverage/reliability evidence from being replaced by arbitrary normalised scores. The lens is for gap planning only and does not authorise MCDA.

### D-Stage5E-03 — Prioritise the cellular-IP report-energy bridge before further LR-FHSS subdivision
**Date:** 2026-08-12

**Decision.** Stage 5F should target the Vomhoff-based IP-cellular phase-to-application-report energy bridge for the four IP cellular candidates. Lifecycle cost is developed as a separate mandatory cross-cutting contract.

**Rationale.** The bridge uses already replicated Grade-A empirical evidence and affects 10 feasible candidate incidences. If validated, it creates at least two energy-comparable candidates in three frozen scenarios. Additional LR-FHSS profile subdivision has lower immediate decision-unlock value and remains frozen unless new deployment evidence appears.

## D-5F-01 — Do not promote Vomhoff 1 KB phase energy to 64/200 B candidate report energy

**Decision:** The Stage-5F canonical cellular-IP report-energy bridge remains blocked for all ten feasible IP-cellular incidences.

**Reason:** Retained Vomhoff transfer evidence is 1024 B and incomplete with respect to candidate upper-layer stacks; the source transaction tail also does not identify benchmark reporting-cycle state energy. These are structural transfer gaps, not numerical uncertainty that can be hidden inside a wider CI.

**Allowed:** materialise a 1 KB source-active whole-device transaction component for diagnostic/model-validation use, preserving within-block bootstrap dependence.

**Forbidden:** unvalidated payload scaling, HTTP→CoAP transfer, applying the NB-IoT MQTT/HTTP contrast to LTE-M, treating source MQTT as exact MQTT5/TLS1.3/LwM2M evidence, or scaling source Idle/Standby to 60/900 s benchmark cycles.

**Consequence:** Stage 5G must target payload dependence, upper-layer context and reporting-cycle state accounting; publication MCDA remains blocked.

## D-5G-01 — External state models may support bridge structure without calibrating candidate energy
**Date:** 2026-08-12

**Decision:** Retain Sørensen et al. (IEEE IoT Journal 2022, DOI `10.1109/JIOT.2022.3152173`) as targeted supporting model evidence for payload and report-cycle/state dependence, but prohibit direct absolute recalibration of Vomhoff Stage-5F source-active whole-device energy.

**Reason:** The external model is modem-only, device/network specific and explicitly requires state-power characterization for a new device. It does not exactly identify the candidate CoAP/DTLS/LwM2M or MQTT5/TLS1.3/LwM2M upper-layer contexts. These mismatches are structural, not confidence-interval width.

**Consequence:** all 10 feasible cellular-IP candidate incidences remain blocked for the canonical report-energy target. The model may enter future robustness analysis only with explicit non-empirical-transfer semantics. Preferred closure is matched boundary-compatible measurement/data; lifecycle-cost evidence proceeds independently in parallel.

## D-5H-01 — Lifecycle cost is decomposed before scalarisation (2026-08-12)

**Decision.** The primary lifecycle-cost target is a five-year constant-2026-EUR differential cost, but fixed private infrastructure remains site-level until deployment scale is frozen. Operator subscriptions and private infrastructure are different accounting modes. Smoke/test prices are not evidence.

**Reason.** Converting shared infrastructure immediately to a per-device number would embed an arbitrary fleet size and could reverse technology rankings. The cost boundary must therefore be explicit before price collection or optimisation.

## ADR — 2026-08-12 — Stage 5I does not equate tariff sticker price with lifecycle connectivity cost

**Decision.** Dated hardware/SIM/tariff observations may be materialised before full lifecycle cost is identified, but a finite-volume operator tariff is not considered a complete five-year cost until candidate transport/session traffic is bounded. Source-published billing granularity must not be assigned a per-report/per-packet rounding interpretation unless the aggregation interval is documented.

**Rationale.** The 1NCE reference plan contains finite included data and protocol overhead is part of transferred traffic. STACKWISE candidate definitions do not yet freeze connection persistence, keep-alives, handshake reuse, acknowledgements or management traffic. Treating EUR 12 as the exact five-year service cost for every reporting profile would therefore hide a decision-relevant usage dependency. Payload-only volume remains below the included 500 MB in the current IP-cellular scenarios, but this does not establish sufficiency once bidirectional protocol/security/session traffic is included.

**Consequences.**

1. The 1NCE IP tariff is applied only to the four IP cellular stack definitions and must not leak to Non-IP/NIDD candidates.
2. The dual-mode BG95-M3 reference price is shared across NB-IoT and LTE-M; no RAT-specific hardware price difference is invented.
3. A 10-year prepaid tariff is accounted as the full cash purchase within the five-year horizon, not annualised/prorated.
4. EUR 46.41 is labelled a hardware + standard-SIM + base-plan reference cash-cost floor, not canonical `lifecycle_cost_eur`; TopUp count is not inferred before the session/transport profile is frozen.
5. Stage 5J must define one common family of candidate IP session/transport profiles for both tariff-volume and energy-transfer analysis.

## 2026-08-12 — Stage 5J: use one cross-binding LwM2M Send semantic, not one guessed byte overhead

Decision: define the synthetic cellular telemetry benchmark transaction as LwM2M `Send` for both CoAP and MQTT candidate families, and define scenario payload bytes as application data before LwM2M/transport/security overhead. This is a benchmark semantic decision, not empirical evidence.

Reason: cost and energy were beginning to require the same missing session assumptions. Freezing the transaction semantic removes one ambiguity while retaining implementation-dependent dimensions explicitly. OMA LwM2M 1.2.2 supports Send in both bindings; CoAP Send may be Non-Confirmable, so confirmability is deliberately not best-case selected.

Consequence: ten IP-cellular profiles are materialised, but exact tariff volume and canonical report energy remain blocked. Future Stage-5K work must use parameterised sensitivity variants for encoding, IP family, CoAP/DTLS and MQTT/TLS session fields. No deployment probabilities may be assigned without evidence.

Standards maintenance decision: refresh TLS 1.3 reference from obsolete RFC 8446 to RFC 9846 and LwM2M Transport from 1.2.1 to 1.2.2; no candidate graph or Stage-4 feasibility result changes.

## 2026-08-12 — Stage 5K: use a compact unweighted protocol envelope, not a guessed profile or Cartesian distribution

**Decision.** Represent the unresolved Stage-5J cellular-IP session dimensions by nine deterministic sensitivity anchors applied to all ten feasible IP-cellular profiles. Do not assign probabilities, empirical frequencies, preference weights or a "typical" label to any anchor. Do not enumerate the full Cartesian product.

**Reason.** The missing fields are implementation/deployment choices, not random variables identified by the current evidence. A single default profile would hide structural sensitivity, while a full Cartesian product would create thousands of combinations with no evidential basis for their joint occurrence. A compact one-factor/structural stress family preserves the relevant axes while remaining auditable.

**Tariff consequence.** The 500-MB allowance is converted only to an aggregate raw-byte headroom per report. The resulting approximately 2651.93 B/report (900 s / 200 B) and 126.13 B/report (60 s / 64 B) are ceilings before unknown tariff-accounting rounding and must not be called measured protocol overhead or tariff sufficiency.

**Protocol consequence.** Exact wire volume is still prohibited until LwM2M serialization and complete transport/security/session traffic are accounted. Byte counts may later constrain tariff use, but they may not be converted directly to device energy without a boundary-compatible energy/state model.

**Next decision gate.** Stage 5L must keep steady-state application transaction bytes separate from handshake/resumption/keep-alive/retry increments and report uplink/downlink components explicitly.


## 2026-08-12 — Stage 5L: separate strict transport floors from deterministic anchor accounting

**Decision.** Do not equate the benchmark 64/200-B pre-LwM2M application payload with the serialized LwM2M Send payload. Materialise two byte-accounting layers instead: (1) a strict primary-exchange known-component floor with unresolved serialized payload set to zero only for the one-sided diagnostic, and (2) a deterministic Stage-5K anchor accounting that adds the selected response/QoS/keep-alive/retry components under an explicit packetisation convention.

**Reason.** OMA defines the allowed LwM2M Send representations and MQTT/CoAP wrappers, but the current benchmark does not define the underlying LwM2M resource/value structure needed to identify encoded length. Treating 64/200 B as post-serialization bytes would fabricate comparability.

**Tariff decision.** Compare strict raw transport bytes with the nominal 500-MB allowance only as a raw-volume diagnostic. Do not infer exact billed volume or TopUp count because 1NCE documents nearest-1-kByte measurement/billing but the reviewed material does not define the aggregation interval. Exclude IP headers from the tariff-side floor because the tariff text explicitly names TCP/UDP overhead but does not explicitly identify IP-header accounting; report IP-wire bytes separately.

**Consequence.** Twenty-seven MQTT/TLS variants in the two 60-s tracking scenarios already exceed the nominal allowance at the strict raw transport-component floor, but this remains a warning rather than a final tariff-cost result. Stage 5M must address serialized LwM2M payload and security/session increments before exact tariff or energy materialisation.


## 2026-08-12 — Stage 5M: use explicit test-object serialization surrogates, not an invented application model

**Decision.** Preserve `64/200 B` as pre-LwM2M application data and materialise exact serialization only for two declared synthetic Opaque-Resource shapes under OMA test Object ID 42769. Do not infer a real Object, Resource count, data type distribution or deployment frequency.

**Reason.** OMA specifies the legal LwM2M CBOR/SenML representations but the benchmark does not specify the real Resource/value structure. An exact application encoding would therefore be fabricated. Opaque Resource surrogates preserve the original application byte count and permit deterministic encoding arithmetic; the test-only Object range makes their non-production semantics explicit.

**Consequence.** Exact surrogate serialization may be used for sensitivity and one-sided raw-volume diagnostics. It may not be called canonical wire volume or empirical protocol overhead. The result demonstrates a real decision sensitivity: all MQTT/TLS 60-s tracking surrogate rows exceed the nominal raw allowance, while CoAP/DTLS SenML-JSON tracking changes classification between the one- and three-Resource surrogates. Stage 5N must keep security-session and TCP-control traffic as separate increments.

## D-5N-01 — Use a compact PSK session/control envelope, not a canonical handshake trace
**Date:** 2026-08-12

**Decision:** Stage 5N uses two deterministic LwM2M-valid PSK session/control surrogates: compact `psk_ke` and expanded `psk_dhe_ke` + X25519. They are not assigned probabilities and are not interpreted as lower/upper bounds on all deployments.

**Reason:** LwM2M permits PSK, RPK and certificate security modes. Credential mode, identity length, record packing and transport implementation are deployment-specific. A compact PSK family is sufficient to test whether reasonable session/control detail changes the tariff-side qualitative conclusions without pretending to reconstruct an unknown deployment.

## D-5N-02 — Keep TCP ACK count as sensitivity, not exact packet accounting
**Date:** 2026-08-12

**Decision:** MQTT/TCP uses two ACK-only anchors: zero standalone ACK-only segments and one standalone ACK-only segment per modeled data-carrying TCP segment.

**Reason:** TCP delayed/cumulative/piggybacked ACK behaviour is implementation/timing dependent. The two anchors expose sensitivity but are not empirical counts or protocol-wide bounds.

## D-5N-03 — Freeze further transport-detail expansion after Stage 5N
**Date:** 2026-08-12

**Decision:** Stage 5N is the last planned transport/accounting refinement. New transport sub-stages require a material methodological error or a directly decision-blocking gap that cannot be treated in robustness analysis.

**Reason:** The E0/E1 session/control sensitivity does not flip any of the 180 Stage-5M source rows across the nominal 500-MB threshold: 81 are above and 99 below under both. Further packet-level elaboration is therefore lower-value than consolidating the first decision-ready slice. Exact billing and device-energy inference remain separately blocked.

## D-6A-01 — Separate decision-usable targets from contextual robustness evidence
**Date:** 2026-08-12

**Decision:** A Stage-5 result may be retained as `CONTEXT_ONLY` without being promoted to an MCDA criterion. In particular, dated cellular cost floors plus Stage-5N tariff-volume robustness do not yet identify `lifecycle_cost_eur`.

**Reason:** STACKWISE uses mixed uncertainty semantics, but an unweighted robustness family is decision-usable only after the target quantity itself is numerically identified. Raw transport-volume classes are informative about tariff risk but are not EUR lifecycle cost and cannot be scored as if they were.

## D-6A-02 — Keep energy/report and lifecycle cost as the only mandatory first-slice soft targets
**Date:** 2026-08-12

**Decision:** Latency and feasible-link/coverage remain upstream hard/contextual dimensions; delivery probability is deferred. They are not re-scored in the first soft slice.

**Reason:** Re-scoring hard feasibility dimensions would introduce compensation and double counting. Delivery probability lacks attempted-transmission denominators for the candidate set.

## D-6A-03 — Use periodic tracking IP-cellular 2×2 only as a development subset
**Date:** 2026-08-12

**Decision:** Use the four feasible IP candidates in `asset_tracking_periodic_cross_cell` as the preferred Stage-6B development benchmark. Do not describe it as the optimum over the full scenario, because two feasible Non-IP candidates remain outside the subset.

**Reason:** The 60-s/64-B profile offers a common 2×2 NB-IoT/LTE-M × CoAP/MQTT comparison and non-degenerate tariff-volume robustness, making it the highest-leverage subset for closing the remaining energy and cost inputs without cherry-picking a winning stack.

## D-6B-01 — Do not synthesize candidate energy from heterogeneous cellular studies

**Decision:** External cellular-energy studies may support source-level cross-checks, model structure and sensitivity claims, but none is authorised to materialise `expected_device_energy_per_application_report_j` for the preferred 64-B/60-s IP-cellular 2×2 subset.

**Reason:** The reviewed evidence fails at least one mandatory dimension: payload/cycle, RAT coverage, upper-layer context or whole-device boundary. A small matched experiment is methodologically cheaper than another layer of unvalidated transfer assumptions.

## D-6B-02 — Freeze the minimum matched measurement design before collecting data

Use one dual-mode DUT and one operator/SIM supporting both RATs; measure complete scheduled 60-s cycles; randomize the four primary conditions within time blocks; run five pilot blocks; freeze the main replication count after observing between-block variability. Failed reports remain in the dataset. If failures are material, delivery probability returns to the decision slice.

## v0.1.58 — stop experimental expansion and split publication package

Decision: stop after Experiment 5. No Experiment 6 is justified by the current claims. Publish Benchmark v1.0.0 as a distinct data/benchmark contribution and use it as the cited frozen input for the STACKWISE methodology/results paper. Do not duplicate Experiments 1–5 in the data paper and do not claim global stochastic ranking or matched cellular whole-device energy.

## D-PUB-02 — Close coding after deterministic deposit packaging

Decision: after v0.1.59, do not create Experiment 6. Treat Benchmark v1.0.0 and Experiments 1–5 as frozen inputs to two distinct manuscripts. Dataset creators must be confirmed manually before Zenodo publication; article authorship is a separate decision.
