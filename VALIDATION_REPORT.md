# STACKWISE validation report

Current project version: v0.1.52  
Latest validation date: 12 August 2026

## Automated checks

- Python package compilation succeeded for `src/`, `scripts/` and `tests/`.
- Dataset registry validation succeeded with 12 empirical public-data records.
- All 32 automated tests passed.
- The self-contained smoke pipeline completed successfully.
- The Vomhoff adapter regression suite remains green.
- The InSecTT nested-ZIP adapter regression suite remains green.
- The LR-FHSS adapter is covered by metadata, ACK/noACK, DR8--DR11, voltage, payload, sampling, integration and negative-instrument-noise tests.

## Production validations completed outside the repository

### Vomhoff NB-IoT/LTE-M

The production harmonisation produced 1,671 unique run/phase observations with zero duplicate IDs after correcting chunk-boundary NaN grouping. Source reproduction of Figures 3--5 was used to audit the adapter before analysis-ready aggregation.

### InSecTT

The production scale check used all 20 technology/period configurations. The inferred constant source voltage from the publication's independent average-power table clustered around 3.300055 V, with approximately 0.0785% coefficient of variation and approximately 0.0348% MAPE when power was reconstructed with the median inferred voltage. The inferred voltage remains validation metadata and is not written back into the raw-derived observations.

## v0.1.5 LR-FHSS integration

The LR-FHSS dataset-specific adapter was developed from the public Zenodo metadata and diagnostic source headers. The raw files contain eight current traces (ACK/noACK x DR8--DR11), 20.48 us sampling, a 4-byte FRM payload and +14 dBm transmit power. The associated publication documents that the measured LR1121 radio interface is supplied from a dedicated 3.3 V rail. The adapter therefore integrates full-trace charge and energy with explicit voltage provenance.

The adapter has been tested against synthetic traces and all eight diagnostic file headers. The full 784 MB raw dataset is not bundled in this repository and must be harmonised on the user's machine. `scripts/validate_lrfhss_reference.py` performs the production structural and current-scale checks after that run.

## Measurement-boundary caution

LR-FHSS `energy_j` is the energy of the entire recorded radio-interface trace. It must not be treated as energy per transmitted message until the number and boundaries of transactions in each capture have been validated. This prevents capture-window length from being mistaken for protocol energy.

## External-data boundary

Large third-party datasets are not included. Raw files remain under `data/raw/`; patch application does not modify or delete them.

## Production validation update — 8 August 2026

### LR-FHSS full-data run

The production harmonisation generated 8 observations with zero warnings and zero schema-validation errors. Every source trace had approximately 60 s duration, 20.48 microsecond sampling and exactly one detected TX burst.

The unconfirmed DR8 TX plateau was approximately 25.468 mA, within about -0.90% of the 25.7 mA publication reference. The unconfirmed DR8 low-current band was approximately 0.424 microampere versus the publication's 0.5 microampere sleep-state reference.

The mean thresholded plateau across all eight traces is not treated as a universal TX-state current because confirmed traces contain receive/ACK activity. Derived confirmed-minus-unconfirmed energy is labelled capture-specific ACK/RX overhead because the dataset provides only one trace per configuration.

### Documentation checkpoint

Version 0.1.6 adds structured dataset cards, a chronological research log, a methodological decision log and a reproducibility workflow. No scientific transformation code changed in this checkpoint.

## v0.1.7 LoED adapter validation

- Registry validation: 12 active empirical datasets.
- Automated tests: 38 passed.
- Smoke pipeline: passed.
- Dataset-specific LoED adapter was additionally exercised against 300 real rows sampled from three daily files supplied in the diagnostic archive.
- Result on the diagnostic rows: 300 gateway observations, 0 adapter warnings, 0 canonical-schema errors, 0 populated `delivery_success` values, CRC states {-1, 1}, SF7--SF12, expected EU868 frequencies, and deterministic unique observation identifiers.
- Packet clustering on the diagnostic rows reconstructed 255 candidate transmissions, including 4 multi-gateway clusters; this is a structural check only, not a paper result.
- The official six-day sample and complete archive must be validated on the user's local data before LoED is marked production-validated.


## v0.1.8 full-scale LoED execution

The six-day LoED sample is frozen as a validated checkpoint: 326,870 canonical reception rows, zero duplicate observation IDs, zero artificial delivery-success labels, and structural validation passed after preserving six out-of-range source SNR values in provenance. The full archive is processed using a direct ZIP-to-Parquet bounded-memory path. Streaming regression tests are included; in the build sandbox the two PyArrow-dependent tests are skipped when PyArrow is unavailable, while the base test suite and registry validation pass. PyArrow remains a required project dependency and is present in normal project installations.


## v0.1.9 LoED logical-frame audit

- Registry validation: 12 empirical datasets.
- Test collection: 44 tests.
- Local container result: 42 passed, 2 skipped because PyArrow is unavailable in the container runtime; the skipped tests are the PyArrow-dependent streaming LoED tests.
- Python compileall passed for `src` and `scripts`.
- Smoke reproduction pipeline passed.
- Full-corpus long-cluster diagnostic reviewed: 865 previous >1 s clusters, including 91 CRC-invalid clusters and 774 CRC-valid uplink clusters.
- Resulting decision: LoED analysis-ready identity is a CRC-valid logical frame (exact PHY fingerprint within source day), not a reconstructed physical RF emission.

## v0.1.10 Stage-2 evidence-contract validation — 10 August 2026

The Stage-2 contract was validated in the reduced source archive supplied without the `data/` directory.

Checks completed in this environment:

- JSON Schema Draft 2020-12 meta-validation passed for `evidence_record.schema.json`.
- Evidence metric catalogue and boundary taxonomy parse successfully as YAML.
- New evidence-contract regression suite passed, including direct/bridgeable/conditional/incompatible cases and metric-specific direct-condition requirements.
- InSecTT adapter regression confirms UDP is now stored under `transport_protocol` and `application_protocol` remains null.
- Python `compileall` passed for `src/` and `scripts/`.
- Data-independent test suite result: 47 passed, 4 skipped. The four skips are PyArrow-dependent LoED tests because PyArrow is unavailable in this sandbox.
- The two pre-existing smoke/schema tests that require `data/examples/smoke_observations.csv` were not used as sandbox pass/fail criteria because the user intentionally omitted the full `data/` directory from the shared archive.

The PowerShell patch installer still runs the complete local `pytest -q` suite after installing project dependencies and fails on any non-zero exit code. No heavy empirical recomputation is triggered by this patch.


## v0.1.10.post1 Stage-2A audit validation

The patch adds only analysis/audit code over the already validated Vomhoff harmonised table. Unit tests verify target-phase classification, repeated-segment detection without implicit aggregation, preservation of protocol/payload condition boundaries, metadata inconsistency reporting, Figure 5 Standby discrepancy reporting and wrong-dataset rejection. Production execution must be performed against `data/processed/vomhoff_nbiot_ltem_energy_2023/observations.parquet`; the resulting compact audit artifacts are reviewed before any logical aggregation is authorised.


## v0.1.10.post2 Vomhoff independence-audit validation — 10 August 2026

The production `v0.1.10.post1` output was reviewed before this patch was prepared. The repeated-segment table contains 444 rows representing 222 two-segment candidate groups. All repeated groups are `Data Request`; all are metadata-consistent. Direct temporal checking showed 222/222 adjacent pairs within 6 ms, with maximum absolute continuity residual approximately 5.22 ms. This authorises additive within-run aggregation for the explicit total-phase estimand.

The same review found exact duplication of the 118 NB-IoT/HTTP `Data Request` segments from Figure 4 runs 2--60 in Figure 5. `v0.1.10.post2` therefore adds a full-table cross-Figure source-reuse audit. Regression tests verify both the adjacency guard and detection of cross-Figure exact segment reuse. The audit is non-destructive and intentionally leaves final cross-Figure deduplication pending production review.


## Vomhoff Stage-2 materialisation checkpoint — v0.1.11

The installer requires the validated 1,671-row source-reproduction input, 1,449 within-Figure logical phase groups, 222 additive multi-segment groups, 59 strong Figure-4/Figure-5 reuse pairs and 295 collapsed duplicate non-Idle phase views. All generated evidence records must validate against the Stage-2 evidence schema and metric catalogue.

The materialisation is fail-fast: unexpected cross-Figure differences outside the known Idle derivation are an error. Figure-5 MQTT Idle is excluded only from decision evidence, not deleted from source reproduction.


## InSecTT Stage-2 materialisation validation — v0.1.12

The materialiser is fail-fast on the validated 20-configuration design (4 technologies x 5 reporting periods), duplicate observation IDs, payload/reporting-period mapping, evidence-schema validity and the previously established power-scale checkpoint. It emits 80 evidence records: 40 direct empirical and 40 validated-derived. All records retain `n_independent_units=1` per configuration.

The inferred source voltage is represented by one shared-parameter record and is referenced by all derived power/energy records. The validation spread across 20 implied values is explicitly not interpreted as independent calibration replication or a confidence interval. Regression tests cover complete-design checks, parent lineage, shared-parameter lineage and implementation-aware compatibility.


## v0.1.14 LoED Stage-2 materialisation

The validated full LoED corpus is consumed without rebuilding the expensive logical-frame artifact. Stage-2 summarisation is bounded-memory over Parquet row groups and is checkpointed against the frozen 11,263,001 reception rows and 5,378,763 CRC-valid exact-PHY logical frames. Evidence records are reception-conditioned/hierarchical; `n_independent_units` is deliberately null and no PDR, delivery probability or sqrt(n) confidence interval is generated. Synthetic regression tests cover PHY-stratum RSSI/SNR/CRC summaries, logical-frame observation diversity and hard incompatibility with delivery probability.


## v0.1.15 unified core-four evidence-matrix validation

The matrix assembler is validated against the reviewed production Stage-2 exports: 52 Vomhoff, 80 InSecTT, 20 LR-FHSS and 246 LoED records (398 total) spanning 14 empirical metric IDs. All evidence IDs are unique; parent evidence references and the single InSecTT shared-voltage parameter resolve globally. No target-only metric is materialised as empirical evidence.

The generated audit includes 20 distinct measurement-boundary signatures and a complete 5-target x 4-dataset gap matrix. The gap policy explicitly keeps LoED CRC-valid reception fraction and logical-frame gateway diversity from being used as PDR proxies. The 246 LoED records retain `n_independent_units=null`.

Review of the production LoED summary also identified one reception-only PHY stratum (SF7 / 868.3 MHz / 250 kHz) with 65,498 recorded receptions and zero CRC-valid receptions; therefore 49 reception strata produce only 48 CRC-valid logical-frame strata. The matrix preserves this observation without causal interpretation.

In the reduced build environment, targeted evidence-matrix and evidence-contract regression tests pass. The patch installer runs the complete local test suite and then the production matrix builder, failing on any checkpoint mismatch.


## v0.1.16 Stage-3 uncertainty-contract validation

The production v0.1.15 unified-matrix review is accepted as the Stage-2 closure checkpoint: 398 evidence records across four validated datasets, 14 empirical metric IDs, 20 measurement-boundary signatures and one shared parameter. Dataset, metric, uncertainty-basis and boundary record totals reconcile exactly. The 5-target x 4-dataset gap table has 20 rows and retains explicit missing/bridgeable/conditional states rather than imputing scores.

The Stage-3 contract maps every dataset/metric group exactly once. Expected policy counts are:

- 14 uncertainty specifications;
- 8 explicit dependence groups;
- 7 calibration gaps;
- 2 `calibratable_now` metric groups;
- 6 `external_prior_required` metric groups;
- 2 `grouped_artifact_required` metric groups;
- 4 `descriptive_only` metric groups.

Regression tests require all 398 Stage-2 records to resolve to one uncertainty specification and all shared/dependence references to resolve. The policy explicitly rejects default SD/CV, population CI from one trace, reception-row IID bootstrap, independent sampling of shared/parent-derived records and generic study random effects from the confounded core-four design.

The audit does not fit distributions or generate stochastic publication samples. Publication MCDA remains blocked.


## v0.1.17 Vomhoff Stage-3A run-level calibration validation

The calibration builder operates on the Stage-2 logical-phase Parquet and 52 Vomhoff evidence records. It fails on duplicate evidence/run samples, unresolved evidence IDs, disagreement with Stage-2 `n_independent_units`, or any run-level mean that does not reproduce the Stage-2 estimate.

Regression tests cover both a complete rectangular repeated-run block and a deliberately partial run-set case. The latter must block final joint bootstrap authorisation while still permitting marginal empirical run-to-run calibration. No parametric distribution, default variance, generic study/device random effect or publication stochastic sample is generated.


## v0.1.18 Vomhoff Stage-3B joint bootstrap validation

Production Stage-3A review found five experimental blocks: four complete rectangular repeated-run blocks and one NB-IoT/MQTT block with a single missing `Data Download` run. The partial block has 45 union runs and 44 complete-case runs; every pair involving `Data Download` has Jaccard overlap 44/45 = 0.97778.

The approved policy is a physical-run cluster bootstrap. A shared run-index draw is used for every evidence record within a block. The partial block is sampled from its 45-run union while the observed missing phase remains missing when that run is drawn. No value is imputed and the 45th run is not discarded from the other phases.

The bootstrap materialises 10,000 within-block draws of the conditional mean for each of the 52 Vomhoff evidence records. Replicate IDs are local to a block; cross-block joint dependence is not identified or asserted. No parametric family, generic device/study effect, publication-wide uncertainty sampler or MCDA ranking is introduced.

## v0.1.19 — LoED Stage-3C hierarchical calibration validation

The Stage-3C builder performs a single bounded-memory pass over the validated processed LoED Parquet, reconstructing complete source-day frames and grouping them by gateway and exact PHY configuration. It must reconcile PHY and gateway-PHY RSSI/SNR counts and means to the Stage-2 artifacts, retain all 188 source days, 9 gateways and 49 PHY strata, and reproduce the Stage-2 complete-PHY reception count. No stochastic sampler is executed by this stage.


## v0.1.23 LoED Stage-3G robustness-family validation

Production Stage-3F shows material block-length sensitivity rather than a stable single choice. Median 3-day 95%-widths are roughly 20--26% narrower than 7-day reference widths, while 14-day widths are materially wider for campaign-2 RSSI/SNR and campaign-1 RSSI. Campaign-1 SNR is the only aggregate case where 7- and 14-day median widths are essentially equal. Several individual PHY strata show still larger model sensitivity.

The non-circular MBB also exhibits finite-sample edge-location bias that grows with block length, reaching approximately 0.59 dB in the 57-day campaign. Stage-3G therefore retains the raw bias as a diagnostic and materialises centered draws using `point estimate + raw draw - mean(raw draws)`. This constant per-record shift preserves covariance and distributional shape within each campaign x block-length scenario; it is not a stationarity correction.

No single block length is selected. The two campaigns remain fixed deployment scenarios and the 3/7/14-day block lengths remain an unweighted model-robustness set. The outer q2.5--q97.5 envelope across block lengths is explicitly non-probabilistic. Exact observed source-day support is reported for every campaign x PHY x metric; reception counts are not interpreted as temporal replication.


## v0.1.24 Stage-3H single-trace evidence-review validation

The review audit covers exactly six metric families: four InSecTT metrics and two LR-FHSS energy metrics. Every corresponding Stage-2 record must retain `n_independent_units=1`. The policy must identify zero numerical population priors and must keep default SD/CV, inference of CV from qualitative `negligible`, conversion of instrument accuracy to population SD, publication uncertainty sampling and MCDA disabled.

LR-FHSS metadata is re-materialised with `measurement_instrument = Keysight N6705A DC Power Analyzer` and `acquisition_software = Keysight 14585A Control and Analysis Software`. The unified 398-record core-four matrix is rebuilt and must preserve all record/metric/boundary counts. The subsequent Stage-3 uncertainty audit must preserve the six unresolved single-trace calibration gaps and all publication-sampling guards.

## v0.1.25 Stage-3 closure checkpoint

- Stage-3 status: `closed_with_explicit_nonidentifiability`.
- Core-four evidence records represented: 398.
- Metric families: 14.
- Resolution classes: 2 empirical probability, 2 scenario robustness, 6 explicit epistemic gaps, 4 descriptive nonprobability.
- Numerical population priors introduced for single-trace evidence: 0.
- LoED scenario probability weights: none.
- Residual explicit gaps: 6; Stage-3 closure-blocking gaps: 0.
- Stage-4 stack definition authorised: yes.
- Publication-wide uncertainty sampling: no.
- Publication MCDA/ranking: no.


## Stage 4C — verified reference candidate stack assembly

`v0.1.28` validates nine candidate graphs against the Stage-4B primary-source edge catalog. Every one of 27 bindings must match an exact verified edge. Candidate-level evidence support is separately audited: 5 partial-stack-context, 2 component-direct-boundary-only and 2 with no direct core-four alignment; 0 candidates are treated as having complete end-to-end empirical support. Four access/service families remain deferred. Hard scenario screening and MCDA are not authorised by this stage.

## Stage-4D benchmark hard-feasibility validation

- benchmark scenarios: 6;
- frozen verified candidates: 9;
- scenario×candidate rows: 54;
- feasible under declared hard constraints: 12;
- infeasible: 33;
- unresolved: 9;
- unknown hard results: 27;
- decision-blocking unknown results: 9;
- quantitative context auto-promoted to hard: no;
- feasible interpreted as full empirical support: no;
- MCDA/ranking: unauthorised.

## v0.1.31 Stage-4F closure

Expected production checkpoints:
- refined scenarios: 7; candidates: 9; screening rows: 63;
- feasible / infeasible / unresolved: 21 / 39 / 3;
- frozen decision blockers: 3; resolved from existing evidence: 0;
- all three blockers require explicit operating-profile fields;
- LR-FHSS incremental radio-energy diagnostic: 8 rows; 3 measured 4-byte radio profiles exceed 0.2 J; 0 payload matches to the 16-byte benchmark; 0 whole-device feasibility rows resolved;
- Stage-4 feasibility layer closed; Stage-5A operating-profile contract authorised; publication MCDA unauthorised.


## Stage 5A — v0.1.32

- Stage-4 matrix preserved: 21 feasible / 39 infeasible / 3 unresolved.
- Operating profiles: 3; field records: 26; known: 6; unresolved: 20.
- Stage-4F required fields: 22; satisfied from scenario: 2; unresolved: 20.
- Bridge contracts: 3; ready for numerical evaluation: 0.
- No matched source: 2 bridges; explicit boundary transform required: 1 bridge.
- Numeric bridge outputs: 0. Preference scoring / publication MCDA: not authorised.

## Stage 5B — v0.1.33

Expected production checkpoints:
- source-publication Table-6 timing reproduction: 4/4 rows;
- 4-byte source-trace energy audit: 8 rows;
- unconfirmed close reproduction: 4/4, maximum absolute relative error < 2%;
- confirmed close reproduction: 0/4, absolute relative error > 43%;
- confirmed measured TX plateau approximately 50 mA versus 25.7 mA published model state current; causal explanation not identified;
- 16-byte benchmark variants: 8 rows; payload extrapolation authorised only for 4 unconfirmed variants;
- unconfirmed DR8/DR10 radio component exceeds the 0.2 J whole-device budget; DR9/DR11 remains whole-device unresolved;
- confirmed 16-byte model values are diagnostic only and cannot be used for payload extrapolation;
- generic LR-FHSS candidate feasibility unresolved; Stage-4 matrix remains 21/39/3;
- Stage-3 single-trace epistemic gap preserved; no whole-device numeric bridge, scoring or MCDA.

## Stage-5C LR-FHSS profile-variant validation

Expected production checkpoint: 8 variants, 96 field records (72 known / 24 unresolved), 2 monotone-lower-bound decision-sufficient variants, 2 residual-energy unresolved unconfirmed variants, 4 confirmed-model unresolved variants, 0 whole-device-complete variants, and the frozen Stage-4 matrix preserved at 21/39/3.



## v0.1.35 Stage-5D expected checkpoint

- 8 source-aligned LR-FHSS variants; 0 selected and 0 weighted.
- 2 conditional-infeasible, 0 feasible, 6 unresolved.
- 4 selection dimensions reviewed and 5 deployment-selection evidence requirements materialised.
- ADR/LinkADRReq mechanism verified, deployment DR selection unidentified.
- Confirmed/unconfirmed semantics verified, deployment confirmation policy unidentified.
- Generic LR-FHSS candidate remains unresolved and frozen Stage-4 matrix remains 21/39/3.

## Stage 5F cellular-IP bridge audit — v0.1.37

Contract checkpoint: 10 feasible cellular-IP incidences audited; 3 source reference contexts; 0 canonical report-energy targets ready; 10 payload mismatches; 0 exact application-context matches. Source-active numeric components are materialised only when local Stage-3B artifacts are present and remain diagnostic.


## Stage 5G targeted cellular transfer-evidence audit — v0.1.38

- feasible cellular-IP incidences audited: **10**
- targeted external sources reviewed: **1**
- payload structural-support rows: **10/10**
- reporting-cycle structural-support rows: **10/10**
- exact candidate upper-layer support rows: **0/10**
- external absolute-calibration rows authorised: **0/10**
- canonical report-energy rows ready: **0/10**
- publication MCDA authorised: **no**

Interpretation: the reviewed state/procedure model is valid supporting evidence that payload and reporting-cycle/state effects must be modelled, but it is not a boundary- and device-compatible numerical calibration of the retained Vomhoff whole-device source-active component.


## Stage 5H lifecycle-cost accounting/evidence contract — v0.1.39

Status: **PASS**.

- feasible candidate incidences audited: 21;
- operator-managed / private-owned / unresolved ownership: 17 / 2 / 2;
- complete required price-evidence rows: 0;
- rows requiring shared-infrastructure deployment scale: 2;
- canonical lifecycle-cost targets ready: 0;
- smoke-price rows authorised for publication: 0.

Interpretation: the accounting boundary is frozen, not the prices. Publication MCDA and fleet optimisation remain blocked until dated cost evidence is populated and shared-cost allocation assumptions are explicit.


## Stage 5I dated cellular cost evidence — v0.1.40

Status: **PASS**.

- feasible / operator-managed candidate incidences: 21 / 17;
- feasible IP / Non-IP cellular incidences: 10 / 7;
- IP-cellular rows with dated module + standard-SIM price evidence: 10;
- IP-cellular rows with dated operator tariff evidence: 10;
- smart-meter IP rows where base allowance is not disproven from payload-only volume: 4;
- 60-s tracking IP rows where base allowance is not disproven from payload-only volume: 6;
- rows where base allowance is proven insufficient before a session/transport model: 0;
- canonical lifecycle-cost targets ready: 0.

Interpretation: Stage 5I validates price provenance and one-sided tariff-volume consequences without promoting a price floor to an exact five-year lifecycle cost. Non-IP/NIDD operator service evidence remains missing. Publication MCDA remains unauthorised.

## Stage 5J cellular IP session/transport profile contract — v0.1.41

Status: **PASS**.

- feasible IP-cellular profile rows: 10;
- CoAP/DTLS/UDP / MQTT/TLS/TCP profiles: 5 / 5;
- typed profile fields: 200;
- known or frozen / unresolved fields: 70 / 130;
- profiles complete for exact tariff volume: 0;
- profiles complete for canonical report energy: 0;
- canonical tariff-volume / report-energy rows: 0 / 0;
- publication MCDA authorised: no.

Interpretation: Stage 5J freezes one reproducible cross-binding telemetry semantic (LwM2M Send) and the application-payload accounting boundary while explicitly retaining implementation-dependent session dimensions. Exact protocol/session bytes and report energy are not fabricated. Primary standards references were refreshed to RFC 9846 for TLS 1.3 and LwM2M Transport 1.2.2; Stage-4B structural validation still passes with unchanged catalogue counts.

## Stage 5K parameterised cellular IP protocol-envelope variants — v0.1.42

Status: **PASS**.

- source Stage-5J profiles: 10;
- anchor designs: 9;
- protocol-envelope variant rows: 90;
- CoAP/DTLS/UDP / MQTT/TLS/TCP variants: 45 / 45;
- variants with complete assignments for all Stage-5J unresolved fields: 90;
- raw tariff-overhead budget rows: 10;
- unique reporting profiles: 2;
- raw non-application headroom, 900 s / 200 B: approximately 2651.927903 B/report;
- raw non-application headroom, 60 s / 64 B: approximately 126.128527 B/report;
- exact wire-volume variants ready: 0;
- canonical report-energy variants ready: 0;
- variant probabilities/frequency weights: none;
- publication MCDA authorised: no.

Interpretation: Stage 5K closes the assumption-management problem, not the byte-accounting problem. The compact envelope is an auditable sensitivity family, not an empirical distribution of deployments. Stage 5L (v0.1.43) subsequently materialises standards-known component floors while preserving unresolved LwM2M serialization and session-establishment traffic.


## Stage 5L standards-based wire-volume accounting — v0.1.43

Status: **PASS**.

- Stage-5K variant rows audited: 90;
- CoAP/DTLS/UDP / MQTT/TLS/TCP variants: 45 / 45;
- strict primary-exchange transport floors materialised: 90;
- deterministic anchor known-component accounting rows: 90;
- exact wire-volume rows: 0;
- unresolved LwM2M serialization rows: 90;
- MQTT rows with unresolved pure-TCP ACK/segmentation traffic: 45;
- variants with unresolved per-report security resumption/full-establishment increment: 20;
- strict raw transport floors above nominal 500-MB allowance: 27;
- strict raw transport floors within nominal allowance: 63;
- exact billed-volume / TopUp rows: 0;
- publication MCDA authorised: no.

Interpretation: standards-known protocol components can already constrain the finite connectivity allowance without fabricating a serialized LwM2M payload. All MQTT/TLS variants in the two 60-s tracking scenarios have a strict raw transport floor above 500 MB over five years (compact persistent anchor: 205 B/report = 539.109 MB/5y before serialized LwM2M payload). Billing aggregation remains unresolved, so this is not an exact billed-volume or TopUp conclusion. Stage 5M must address LwM2M serialization and security-session increments.

## v0.1.45 Stage-5N validation

Command:

```text
python scripts/audit_security_session_control_envelope.py
```

Expected scientific checkpoint:

```text
Stage-5N security-session/control envelope audit: OK
Source serialization rows / envelope designs / envelope rows: 180 / 2 / 360
CoAP/DTLS / MQTT/TLS envelope rows: 180 / 180
Rows with security-session / MQTT TCP-ACK surrogate increments: 80 / 90
Canonical security-session / TCP-ACK rows: 0 / 0
Augmented raw-volume rows exceeding / within nominal 500-MB allowance: 162 / 198
Source rows robust-exceed / robust-within / session-control-sensitive: 81 / 99 / 0
MQTT tracking robust-exceed source rows / CoAP tracking session-control-sensitive source rows: 54 / 0
```

The audit must not authorise canonical security-session traffic, exact TCP ACK counts, exact billed volume, report energy or publication MCDA. The two envelope designs are deterministic sensitivity surrogates with no probability/frequency interpretation.

## Stage 6A first decision-slice consolidation — v0.1.46

Status: **PASS**.

Expected checkpoint:

```text
Stage-6A first decision-slice consolidation: OK
Frozen Stage-4 feasible / infeasible / unresolved: 21 / 39 / 3
Feasible candidates / criterion rows / required soft rows: 21 / 105 / 42
Required soft rows ready / context-only / blocked: 0 / 10 / 32
Feasible candidates ready for first slice / with cost context: 0 / 10
IP cost context robust-within / robust-exceed / protocol-envelope-sensitive candidates: 4 / 3 / 3
Preferred periodic-tracking IP development subset rows / ready rows: 4 / 0
Publication MCDA authorised: no
```

Interpretation: Stage 6A does not create a ranking. It distinguishes scoreable targets from contextual robustness evidence and confirms that the current Stage-5 transport/cost work is informative but not yet a canonical EUR lifecycle-cost input. Report energy remains the dominant common blocker. The periodic tracking IP 2×2 subset is a development benchmark only; full-scenario optimisation remains prohibited.

## v0.1.48 / Stage 6C

- preferred subset candidates: 4;
- Stage-5N source rows retained: 144;
- PDP billing anchors: 2;
- procurement anchors: 2;
- lifecycle-cost robustness rows: 576;
- cost-ready candidates: 4;
- energy-ready candidates: 0;
- first-slice-ready candidates: 0;
- publication MCDA authorised: no.

## v0.1.49 / Stage 6D

Stage-6D synthetic decision-engine audit passes with 4 preferred candidates, 144 aligned cost states, 3 synthetic energy fixtures, 64 paired draws per fixture and 21 deterministic weight anchors. The engine performs 9,072 conditional cost-state × weight × fixture evaluations and writes 252 weight-sensitivity envelope rows plus 12 fixture-level rank-envelope rows. All 13 invariants pass. Cost states and weights are not probabilistically pooled; exact ties use fractional rank mass; fixed external value anchors avoid alternative-set min/max normalisation. Synthetic fixtures are validation-only and publication ranking remains disabled until matched Stage-6B whole-device energy is available.



## v0.1.50.post2 benchmark RC QA checkpoint — 12 August 2026

- Corrected false-zero Parquet row counts in the release table manifest by using Parquet metadata.
- Added standalone RC self-description assets: dataset card, eight canonical schemas and four upstream dataset cards.
- Added a release-level integrity audit for three-format evidence equivalence, full scenario×stack feasibility coverage, checksums, source licences and raw-archive exclusion.
- Benchmark scientific content remains v1.0.0-rc1; Zenodo finalisation is still blocked pending explicit release-licence declaration and manual scientific/attribution sign-off.

## v0.1.51 final benchmark release checkpoint — 12 August 2026

- Final benchmark version: `1.0.0`; scientific tables and frozen counts unchanged from validated RC1.
- Dataset licence: CC BY 4.0 for STACKWISE-authored benchmark material; software remains Apache-2.0.
- Source attribution: four core datasets, creators, dataset DOIs, related-publication DOIs, source licences and STACKWISE roles materialised and marked verified.
- Final build/audit scripts added; the final audit requires table integrity, 7×9 feasibility coverage, source licences, source attribution, CC BY licence declaration, metadata assets, checksums and absence of raw external archives.
- Publication MCDA remains unauthorised by the benchmark release itself.


## v0.1.52 Experiment 1 checkpoint — 13 August 2026

The first publication-oriented experiment uses only frozen Benchmark v1.0.0 structural definitions and the complete 7×9 hard-feasibility matrix. Four fully observed structural preference features are crossed with 35 deterministic simplex anchors. No missing empirical energy, cost, reliability, latency or coverage metric is imputed. Across 245 scenario-anchor evaluations, score-first top sets contain at least one hard-infeasible candidate in 193 cases and are exclusively infeasible in 159. Among the 175 evaluations in scenarios that do contain feasible candidates, contamination remains 142 and exclusively infeasible top sets 115. In the two scenarios with no feasible candidate, score-first still returns a top set for all 70 anchors; feasibility-first returns `NO_FEASIBLE_DECISION` for all 70. Anchor coverage is not a stakeholder probability model.

## v0.1.58 final publication consolidation

The final consolidation fail-closes on frozen checkpoints from Experiments 1–5 and materialises a claim/evidence matrix, two-paper split matrix, figure plan and table plan. It changes no Benchmark v1.0.0 data and performs no new ranking, imputation or empirical inference.

## v0.1.59 publication packaging validation

Deposit packaging fails closed unless Benchmark v1.0.0 final QA and Zenodo-finalisation gates are true. Archive creation is deterministic, includes a SHA-256 sidecar, preserves the frozen release directory as a single top-level folder, and does not authorise publication MCDA.
