# STACKWISE research plan — active roadmap after v0.1.40

## Objective

Develop and validate an open, layer-aware and uncertainty-aware framework for selecting end-to-end IoT communication stacks and heterogeneous fleet architectures from heterogeneous evidence under hard feasibility constraints, explicit uncertainty semantics and lifecycle cost.

## Research questions

1. Can heterogeneous public IoT measurements be represented as decision evidence without erasing accounting-boundary, implementation and statistical-unit differences?
2. How much do feasibility-first screening, uncertainty semantics and boundary-aware bridges change stack decisions relative to simplified deterministic scoring?
3. When do heterogeneous fleets outperform single-technology or limited-technology policies once infrastructure and lifecycle costs are included?
4. Which evidence gaps are decision-critical enough to justify targeted new measurement or external evidence acquisition?

## Completed foundation

### Stage 0 — repository, provenance and canonical observation layer — complete

Registry, provenance/download workflow, canonical schemas, adapters, quality/audit utilities, tests, CI and reproducibility tooling are established.

### Stage 1 — core-four ingestion and source reproduction — complete

Validated sources:

- Vomhoff NB-IoT/LTE-M whole-device phase energy;
- InSecTT BLE/Thread/UWB/EPhESOS whole-device power traces;
- LoRaWAN LR-FHSS radio-interface energy;
- LoED classical-LoRa gateway-reception/link evidence.

### Stage 2 — empirical evidence matrix — complete for core-four

398 typed evidence records, 14 empirical metrics, explicit measurement boundaries, lineage, implementation context, applicability and decision-target gaps.

### Stage 3 — uncertainty semantics and identifiable calibration — closed with explicit non-identifiability

- Vomhoff: dependence-preserving physical-run nonparametric uncertainty;
- LoED: fixed deployment campaigns × unweighted 3/7/14-day block-length robustness family;
- InSecTT/LR-FHSS: explicit single-trace epistemic gaps with no invented population SD/CV;
- no generic cross-study random effect is inferred from confounded core-four evidence.

### Stage 4 — layer-aware stack model and hard feasibility — complete/frozen

- 25 component catalogue;
- verified compatibility edges;
- 9 reference end-to-end candidate stacks;
- 7 refined quantitative benchmark scenarios;
- frozen hard-feasibility result: **21 feasible / 39 infeasible / 3 unresolved**.

### Stage 5A–5D — operating-profile/bridge contracts and LR-FHSS closure — complete

The three Stage-4 unresolved hard facts have explicit operating-profile/bridge contracts. LR-FHSS source-model, profile variants and deployment-selection identifiability were audited. The generic LR-FHSS agriculture candidate remains unresolved; the source-aligned variant family is unweighted and no post-hoc mode selection is allowed.

### Stage 5E — decision-readiness and gap prioritisation — complete in v0.1.36

- 24 non-infeasible scenario-stack incidences × 5 canonical targets = 120 audited cells;
- 0 target cells are currently decision-ready at the canonical boundary;
- 0/21 feasible candidates are fully ready for the first energy/report + lifecycle-cost slice;
- the preferred next bridge using current empirical data is `cellular_ip_report_energy_bridge` (10 feasible incidences; 3 scenarios with potential multi-candidate energy comparison);
- lifecycle cost is a mandatory parallel cross-cutting contract affecting all 21 feasible candidates.

## Active next work

### Stage 5F — cellular-IP whole-device energy/report bridge

Goal: materialise `expected_device_energy_per_application_report_j` for defensible IP cellular candidate/scenario combinations from Vomhoff evidence.

Required sequence:

1. define scenario-specific cellular operating profiles: payload/report semantics, connection/session reuse, request/download direction, reporting-cycle boundary, idle/standby inclusion, retry assumptions and source application-context mapping;
2. define a versioned phase-composition bridge from Vomhoff source phases to application-report energy;
3. prohibit direct transfer to CIoT Non-IP candidates;
4. preserve physical-run/block dependence and the Stage-3B bootstrap semantics;
5. represent source-stack mismatch as explicit structural uncertainty/sensitivity rather than silently treating HTTP/MQTT source runs as exact CoAP/LwM2M or MQTT5/TLS/LwM2M measurements;
6. validate every emitted target value against source phase accounting and lineage;
7. do not score or rank candidates.

Primary success criterion: obtain at least two boundary-compatible energy/report estimates in each of the three cellular multi-candidate scenarios identified by Stage 5E, subject to bridge validity.

### Stage 6 — lifecycle-cost evidence contract

Define a dated common boundary, likely including:

- device/hardware cost;
- access/service subscription;
- owned infrastructure/gateway cost;
- installation/commissioning where relevant;
- maintenance/replacement;
- battery/replacement implications where supported;
- analysis horizon and fleet allocation rules.

Use source-backed ranges/scenarios rather than one fictitious exact price. Keep smoke-test costs outside the publication pipeline.

### Stage 7 — first publication decision experiment

Entry conditions:

- at least one frozen scenario has >=2 feasible candidates with compatible materialised mandatory targets;
- lifecycle-cost contract is available;
- every target carries its Stage-3 uncertainty semantics or an explicit non-probabilistic sensitivity state.

Compare, at minimum:

- deterministic point decision baseline;
- uncertainty-aware decision analysis;
- alternative stakeholder weight distributions;
- explicit epistemic/bridge sensitivity;
- feasibility-first versus a deliberately simplified score-first baseline, without allowing infeasible candidates to masquerade as preferred solutions.

Do not force all uncertainty sources into one probability distribution.

### Stage 8 — heterogeneous fleet optimisation and cost of simplification

After a valid individual decision layer exists, optimise device-group × stack assignment with infrastructure activation variables and compare:

- unrestricted heterogeneous fleet;
- one-technology fleet;
- <=2 technologies;
- ownership/service restrictions;
- budget/lifecycle-cost restrictions.

Primary result: utility/cost/regret penalty caused by simplification constraints.

### Stage 9 — targeted evidence additions only when decision-critical

New datasets or measurements are justified only when Stage-5E/7 sensitivity shows that a missing quantity materially changes a decision. Current likely gaps include classical-LoRa whole-device/report energy, cellular Non-IP evidence, Thread end-to-end latency for the industrial blocker, and candidate-specific delivery/coverage evidence if those become soft decision targets.

### Stage 10 — publication and reproducibility release

- tagged code release;
- Zenodo DOI;
- citable STACKWISE harmonised evidence resource with redistribution/licence audit;
- immutable schemas and manifests;
- scripts generating every paper table/figure;
- explicit source/derived-data licensing and provenance;
- main framework paper; optional separate data/resource publication only if the evidence resource becomes sufficiently broad and independently useful.

## Current prohibitions

Until the relevant entry conditions are satisfied, do not:

- run publication MCDA/ranking;
- use default SD/CV fallbacks;
- call LoED CRC fraction PDR;
- treat radio-only LR-FHSS energy as whole-device energy;
- transfer Vomhoff IP evidence to cellular Non-IP;
- use `configs/fleet.yml` smoke costs as lifecycle evidence;
- automatically score latency/coverage again after hard feasibility;
- select LR-FHSS DR/confirmation mode post hoc from energy results;
- add datasets for coverage breadth without a decision-critical gap.


### Stage 5G — targeted cellular transfer-evidence admissibility

**Status: closed in v0.1.38.** A targeted validated external NB-IoT/LTE-M state/procedure model supports payload and report-cycle/state dependence structurally, but cannot serve as an absolute calibration bridge to Vomhoff because its boundary is modem-only and its quantitative parameters are device/network specific. Exact candidate upper-layer contexts remain unmatched. No canonical report-energy target is materialised.

### Stage 5H — next execution decision

Proceed on two parallel workstreams:

1. **Cellular matched bridge evidence:** search/acquire a same-device or boundary-compatible dataset, or perform a minimal matched measurement campaign, spanning 64/200/1024 B and the required application/report-cycle contexts. If unavailable, retain the external model only as an explicitly labelled robustness family.
2. **Lifecycle-cost evidence contract:** build dated, provenance-backed device/infrastructure/subscription/maintenance/replacement/energy cost ranges because cost is missing for every feasible candidate and is independent of the cellular energy bridge.

Publication MCDA remains blocked until at least one multi-candidate scenario has a defensible common energy target plus lifecycle-cost evidence.


### Stage 5H — lifecycle-cost accounting/evidence contract

**Status: closed in v0.1.39.** The primary cost boundary is frozen as five-year cumulative differential lifecycle cost in constant 2026 EUR. Per-device hardware/service and private shared infrastructure are separated; shared costs cannot be scalarised without deployment scale. No market prices are yet materialised. Two urban LoRaWAN cost ownership modes remain unresolved rather than inferred.

### Stage 5I — targeted dated cellular cost evidence

**Status: closed in v0.1.40.** Dated module/SIM/operator-tariff evidence is materialised for the ten feasible IP-cellular incidences. A dual-mode BG95-M3 reference is shared by NB-IoT/LTE-M. The reviewed IP tariff is not transferred to Non-IP/NIDD candidates. Finite data allowance introduces an explicit tariff-volume bridge. The published 1-kByte measurement/billing granularity is not interpreted as per-report rounding; payload-only five-year volume remains below the base allowance for both 900-s smart metering and 60-s tracking, while full session/transport usage remains unresolved. The EUR 46.41 reference purchase floor is non-canonical.

### Stage 5J — common cellular IP session/transport profile contract

**Status: closed in v0.1.41.** Ten feasible IP-cellular profiles now share a frozen LwM2M Send telemetry semantic and an explicit pre-LwM2M application-payload boundary. The contract materialises 200 profile fields: 70 known/frozen and 130 unresolved. Exact tariff volume and canonical report energy remain blocked because encoding, IP version, security-context lifecycle, retries and binding-specific CoAP/DTLS or MQTT/TLS parameters are not silently inferred. Standards references are refreshed to RFC 9846 and LwM2M Transport 1.2.2.

### Stage 5K — parameterised protocol-envelope variants

**Status: closed in v0.1.42.** Ten feasible IP-cellular profiles are crossed with nine deterministic anchor designs, producing 90 variants (45 CoAP/DTLS/UDP and 45 MQTT/TLS/TCP). The grid covers all Stage-5J unresolved fields without enumerating the full Cartesian product and without assigning probabilities, frequencies or stakeholder weights. Standards-bounded alternatives include IP family, LwM2M Send representation, CoAP confirmability/token/DTLS header choices, MQTT QoS/topic/TCP choices, security-context persistence/resumption/re-establishment and one-retry stress.

Stage 5K also materialises an aggregate 500-MB headroom diagnostic: approximately 2651.93 B/report of raw non-application headroom for the 900-s / 200-B smart-meter profile and 126.13 B/report for the 60-s / 64-B tracking profile, before unknown tariff-accounting rounding. This is not a protocol-volume estimate and does not classify the tariff. Exact wire-volume and canonical report-energy rows remain zero.

### Stage 5L — standards-based wire-accounting engine

**Status: closed in v0.1.43.** All 90 Stage-5K variants now have a strict primary-exchange transport known-component floor and a separate deterministic anchor-accounting quantity. The implementation does not equate pre-LwM2M 64/200-B benchmark payloads with serialized LwM2M data. Exact wire-volume rows therefore remain zero.

The strict raw transport floor exceeds the nominal 500-MB five-year allowance for 27 variants: all MQTT/TLS variants in the two 60-s tracking scenarios. This is not promoted to an exact billing/TopUp result because nearest-1-kByte aggregation is unresolved. MQTT pure-TCP ACK/segmentation traffic remains explicit, as do per-report security resumption/full-establishment increments.

### Stage 5M — LwM2M serialization surrogate envelope

**Status: closed in v0.1.44.** Exact serialization lengths are materialised for two explicit Opaque-Resource benchmark surrogates under OMA test Object ID 42769: one Resource and three Resources carrying the same total 64/200-B pre-LwM2M payload. LwM2M CBOR, SenML CBOR and SenML JSON are evaluated without inferring a real application resource model. The resulting 180 variant×surrogate rows identify serialization-shape sensitivity while keeping canonical application serialization at 0 ready.

All MQTT/TLS 60-s tracking surrogate rows remain above the nominal 500-MB raw transport allowance. CoAP/DTLS tracking is conditional on representation: the three-Resource SenML-JSON surrogate crosses the nominal raw allowance whereas the one-Resource SenML-JSON surrogate remains below it. Exact billing/TopUp and report energy remain blocked.

### Stage 5N — security-session and TCP-control increment envelopes

**Next.** Materialise DTLS/TLS establishment/resumption traffic under explicit authentication/session anchors, and bound MQTT pure-TCP ACK/segmentation traffic. Keep these increments separate from steady-state LwM2M Send bytes. Do not translate byte counts directly to device energy. Do not declare exact billed volume until billing aggregation semantics are resolved or explicitly sensitivity-modelled.

### Stage 5N — Security-session and MQTT/TCP control envelope

**Status: closed in v0.1.45.** Two deterministic PSK/session-control surrogates close the planned transport-detail sequence without claiming a canonical deployment trace. Across 180 Stage-5M source rows, 81 exceed and 99 remain within the nominal raw 500-MB allowance under both E0/E1; no row changes threshold side solely due to this session/control sensitivity. Exact billing and report energy remain blocked.

### Stage 6A — First decision-ready slice consolidation

**Next.** Freeze the Stage-5 transport branch and recompute decision readiness from the frozen Stage-4 feasibility matrix plus the Stage-5 evidence, energy-transfer, cost, protocol-volume and uncertainty artifacts. The goal is not yet a final ranking: it is to define the first scenario/candidate/criterion slice that can be evaluated without boundary violations, identify any residual non-probabilistic robustness dimensions, and specify the minimum stochastic decision experiment. Do not open additional transport sub-stages unless a material methodological error requires it.

## Stage 6A — first decision-slice consolidation — v0.1.46

**Status: closed.** The frozen Stage-4 matrix remains 21/39/3. Stage 6A consolidates 105 feasible candidate×criterion rows and confirms that no candidate currently has both mandatory first-slice soft targets ready. Ten IP-cellular lifecycle-cost rows are context-only; candidate-boundary report energy is blocked for all feasible candidates. Publication scoring remains prohibited.

The preferred Stage-6B development benchmark is the four-candidate IP-cellular 2×2 subset of `asset_tracking_periodic_cross_cell`. This is a development subset, not a full-scenario optimum; the two feasible Non-IP candidates remain outside until their evidence gaps are closed.

### Stage 6B — cellular IP decision-input closure

Priority 1: obtain matched candidate-boundary whole-device energy/report evidence or a validated model for the 60-s/64-B and 900-s/200-B IP-cellular profiles. Do not payload-scale Vomhoff 1-KB source components.

Priority 2: materialise a EUR lifecycle-cost robustness family from dated price observations plus the Stage-5 traffic envelope, resolving or explicitly bracketing tariff billing aggregation and market-price variation without assigning unsupported probabilities.

Only after at least two candidates in one declared subset have both required targets as `READY_PROBABILISTIC` or `READY_ROBUSTNESS_FAMILY` may candidate scoring be enabled. Further transport-detail expansion remains frozen by default.

## Stage 6B — matched cellular-IP report-energy closure — v0.1.47

Status: **public-evidence search closed; targeted measurement required**.

The preferred periodic-tracking 2×2 IP-cellular subset cannot be given candidate-boundary whole-device energy from the existing literature without an inadmissible transfer. Prepare the frozen four-cell matched experiment in `datasets/stage6b_matched_cellular_energy.yml`. The first required action is a five-block pilot; do not freeze the final replication count before pilot variance is available.

The lifecycle-cost robustness family may proceed independently while measurement hardware/operator access is arranged.

## Next phase after v0.1.58

Do not add Experiment 6 unless a reviewer or a clearly identified research gap requires it. Freeze Benchmark v1.0.0 and Experiments 1–5. Prepare two manuscripts with non-overlapping primary questions: a benchmark/data paper and the STACKWISE methodology/results paper. Deposit/cite the benchmark release before final submission where practical.

## Post-experiment plan (v0.1.59)

Do not add Experiment 6. Package and deposit Benchmark v1.0.0, reserve/finalise its DOI, then draft the benchmark/data paper and methodology/results paper under the frozen scope split.
