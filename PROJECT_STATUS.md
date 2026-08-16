# STACKWISE project status

Last updated: 16 August 2026

## Research objective

STACKWISE is developing an open, layer-aware and uncertainty-aware framework for selecting end-to-end IoT communication stacks and heterogeneous fleet architectures from empirical evidence under hard feasibility constraints, correlated uncertainty and lifecycle cost.

**Stage 2 — Empirical Evidence Matrix is complete for the validated core-four.** v0.1.16 fixed the **Stage 3 — Uncertainty specification and identifiability** contract. v0.1.17–v0.1.18 close the identifiable within-study Vomhoff uncertainty layer with physical-run nonparametric resampling. v0.1.19 materialises the LoED source-day × gateway × PHY grouped calibration layer, and v0.1.20 audits the two separated acquisition campaigns, multi-lag temporal dependence and gateway-set stability before any LoED block sampler is selected. No publication-wide stochastic decision model or publication-level MCDA ranking is authorised yet.


## Paper B external-validation closure - v0.1.62

The Paper B methodology validation campaign is closed under a checksum-pinned pre-data freeze. Five independently authored use cases were evaluated without post-outcome ontology extension; 46 hard requirements yielded 10 exact mappings, 11 interpretable mappings and 25 unavailable mappings, and the resulting 45 case-candidate assessments were 38 `UNRESOLVED` and 7 `INFEASIBLE` with no forced `DECISION_READY` state. Three held-out public sources were evaluated under frozen boundary rules; the LoRaWAN reception negative control produced no inappropriate direct delivery-probability transition. Preference-ordering robustness now covers weighted sum, TOPSIS and weighted Chebyshev. Boundary-aware accounting was expanded to 1,350 regimes / 388,800 deterministic states and reproduces the original 288-state point exactly. A blinded semantic audit with four independent expert groups achieved Fleiss kappa 0.537; 32/35 items had at least 3/4 expert consensus and 27/32 of those consensus labels matched the frozen classifier.

The benchmark dataset itself remains **v1.0.0 unchanged**. External scenario validation demonstrates ontology portability/abstention behavior rather than winner reproduction. External portfolio analysis was withheld because no case met the pre-specified Tier-C portability rule. Global stochastic ranking and matched four-stack cellular whole-device report-energy claims remain blocked.

## Current core evidence status

| Dataset | Technology evidence | Source/harmonisation status | Analysis-ready status | Main scientific role |
|---|---|---|---|---|
| `vomhoff_nbiot_ltem_energy_2023` | NB-IoT, LTE-M; HTTP/MQTT | validated | Stage-2 run/phase materialisation implemented in v0.1.11; verified cross-Figure source reuse is collapsed at physical/source-run level | whole-device cellular energy and phase decomposition |
| `insectt_wsn_power_2023` | BLE, Thread, UWB, EPhESOS | validated | Stage-2 configuration evidence materialised in v0.1.12 with shared-voltage lineage | whole-device current/charge and reporting-interval scaling |
| `lorawan_lrfhss_energy_2024` | LoRaWAN LR-FHSS DR8–DR11, ACK/noACK | validated with replication limitations | Stage-2 full-capture, incremental-transaction and matched-DR ACK/RX contrast evidence materialised in v0.1.13 | radio-rail transaction energy and capture-specific ACK/RX overhead |
| `loed_lorawan_edge_2020` | LoRaWAN gateway receptions | full corpus validated | Stage-2 reception-PHY and logical-frame diversity evidence materialised in v0.1.14; no independent-unit count or PDR inferred | reception-side RSSI/SNR/SF/channel/gateway/time variability and observation diversity |

## Frozen quantitative checkpoints

### Vomhoff NB-IoT/LTE-M

- Harmonised source-reproduction table: 1,671 unique source-segment run/phase observations.
- Duplicate observation identifiers: 0.
- Source grouping includes `run + event + diff_time` semantics.
- The 1,671 rows are not automatically 1,671 independent physical runs.
- Stage 2 aggregates to a defensible logical run/phase unit before inferential cross-study use; this was materialised in v0.1.11.
- Production `v0.1.10.post1` audit: 1,449 candidate source-Figure/run/phase groups; 222 groups contain exactly two segments, all in `Data Request`; metadata inconsistency count is zero.
- All 222 repeated pairs are contiguous within a 6 ms audit tolerance; maximum observed absolute continuity residual is approximately 5.22 ms.
- For the estimand `total phase within one experimental run`, contiguous repeated `Data Request` segments are therefore additive; source segments remain lineage parents, not independent replicates.
- Figure 4 and Figure 5 reuse 59 NB-IoT/HTTP physical/source runs. Stage-2 materialisation resolves this dependence: exact non-Idle duplicates are collapsed, Figure-specific Idle views remain dependent lineage, and 52 typed evidence records are emitted from 192 physical/source runs.

### InSecTT

- 20 configurations: 4 technologies × 5 reporting periods.
- Reporting periods: 100, 200, 400, 800 and 1600 ms.
- Payload mapping: 2, 4, 8, 16 and 32 bytes.
- Median independently implied source voltage: 3.3000554 V.
- Implied-voltage CV: 0.0785%.
- Power reconstruction RMSE: 0.1974 microW.
- Power reconstruction MAPE: 0.03475%.
- The inferred voltage is validated derived provenance, not raw metadata.
- There is one approximately 60 s trace per configuration; high-frequency samples are not independent experimental replicates.

### LoRaWAN LR-FHSS

- 8 complete traces: ACK/noACK × DR8–DR11.
- Sampling period: approximately 20.48 microseconds.
- Trace duration: approximately 60 s.
- Radio supply: 3.3 V.
- One TX burst per trace.
- Unconfirmed DR8 TX plateau: approximately 25.47 mA versus 25.7 mA publication reference.
- Full-capture energy and baseline-subtracted incremental transaction energy remain separate metrics.
- ACK/noACK differences are capture-specific contrasts, not population estimates, because there is one source trace per configuration.

### LoED full corpus

- 11,263,001 gateway-reception rows.
- 188 source files and all 9 documented gateways.
- 145,023 non-sentinel device addresses.
- 0 duplicate observation IDs.
- 8,327,571 CRC-valid and 2,935,430 CRC-invalid recorded receptions.
- Canonical physical SNR approximately -32 to 31.8 dB.
- 130 raw SNR values are outside the canonical range and are retained separately in `source_snr_db_raw`.
- 5,378,763 CRC-valid exact-PHY logical-frame groups within source day.
- 506,441 logical frames have observations from more than one distinct gateway (9.42%).
- Maximum distinct gateways per logical frame: 4.
- 2,055,213 logical frames contain repeated receptions; 105,872 span more than 1 s.

Interpretation is frozen: LoED rows are gateway receptions. Logical-frame `gateway_count` is distinct-gateway observation diversity. It is neither simultaneous RF reception multiplicity nor packet-delivery probability. `delivery_success` remains null because the transmission-attempt denominator is absent.

## Stage 2 contract — v0.1.10

The Stage-2 evidence layer is formally separated from the harmonised observation layer.

New contract artifacts:

- `datasets/schema/evidence_record.schema.json`;
- `datasets/evidence_metric_catalog.yml`;
- `datasets/evidence_boundary_taxonomy.yml`;
- `docs/EMPIRICAL_EVIDENCE_MODEL.md`;
- `src/stackwise/evidence.py`.

Key rules:

1. An evidence record is a typed claim about one metric under an explicit measurement boundary, statistical unit, derivation lineage and applicability domain.
2. `source_grade` describes provenance/source quality and does not encode inferential strength.
3. Measurement boundary is decomposed into system scope, temporal scope, accounting basis, conditioning/denominator, payload basis, baseline/ACK/retry accounting and path endpoints.
4. Compatibility is classified conservatively as C0 direct, C1 bridgeable, C2 conditional or C3 incompatible.
5. Unknown critical boundary fields prohibit C0 direct comparison.
6. Parent evidence and shared uncertain parameters must be retained to support correlated uncertainty in Stage 3.
7. Existing `models.py`, `mcda.py` and `optimizer.py` remain prototype/smoke infrastructure only until Stage 2 and Stage 3 are validated.

## Known evidence gaps before MCDA

The core four sources do not yet provide a common evidence basis for:

- absolute delivery probability / PDR;
- scenario-conditioned coverage probability;
- end-to-end application latency;
- common whole-device energy per application report across all technologies;
- comparable infrastructure and lifecycle cost;
- standards-backed payload/regulatory/operator feasibility;
- transport/security/application/management overhead for complete end-to-end stacks.

These gaps must not be filled with arbitrary scores or artificial confidence intervals.

## Next controlled step

The production v0.1.15 unified matrix is accepted: 398 records across 14 empirical metrics, 20 boundary signatures, one shared parameter, clean lineage and explicit decision-target gaps. v0.1.16 therefore formalises Stage-3 uncertainty without fitting distributions. Two Vomhoff metric families are immediately calibratable at physical-run level; six InSecTT/LR-FHSS families require external repeatability evidence or priors; LoED RSSI/SNR require grouped hierarchical calibration; four additional quantities remain descriptive-only. Generic study random effects, default SD/CV and publication MCDA remain blocked.

## Vomhoff Stage-2 materialisation — v0.1.11

The remaining independence policy is resolved. Fifty-nine Figure-4/Figure-5 NB-IoT/HTTP `1K.data` run pairs are verified source reuse. Exact non-Idle phase views are collapsed to one physical/source-run value; Figure-specific Idle views remain dependent derivations.

The materialiser writes:
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/logical_phase_observations.parquet`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/evidence_records.jsonl`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/evidence_records.csv`;
- `results/validation/vomhoff_stage2_materialisation/source_vs_analysis_ready_comparison.csv`;
- `results/validation/vomhoff_stage2_materialisation/summary.json`.

The evidence layer excludes source-declared invalid Figure-5 MQTT Idle and introduces no source-unsupported 10 s Standby correction. Publication MCDA remains blocked until the other core evidence sources are materialised and Stage 3 uncertainty is defined.


## Evidence implementation-context extension — v0.1.11.post1

The evidence schema now preserves device/radio/firmware/instrument context. The compatibility layer treats implementation differences as C2 conditional by default; callers may allow such variation only when the compared candidate explicitly includes that implementation change. `C0_DIRECT` is documented as estimand comparability, not automatic statistical poolability.

This extension is motivated by InSecTT, where UWB is measured on nRF52832 + DW1000 while BLE/Thread/EPhESOS use nRF52840. The next version may now materialise InSecTT without erasing that confounder.


## InSecTT Stage-2 materialisation — v0.1.12

The 20 technology x reporting-period configurations are materialised as configuration-level analysis-ready observations. Each configuration has one independent approximately 60 s source trace; high-frequency samples remain source observations only.

The materialiser writes:
- `data/analysis_ready/insectt_wsn_power_2023/configuration_observations.parquet`;
- `data/analysis_ready/insectt_wsn_power_2023/evidence_records.jsonl`;
- `data/analysis_ready/insectt_wsn_power_2023/evidence_records.csv`;
- `data/analysis_ready/insectt_wsn_power_2023/shared_parameters.json`;
- `results/validation/insectt_stage2_materialisation/power_scale_validation.csv`;
- `results/validation/insectt_stage2_materialisation/summary.json`.

Four evidence families are emitted for every configuration: direct trace mean current, direct integrated charge, validated-derived mean power and validated-derived capture energy. All 40 derived records reference the same `insectt_ppk2_source_voltage_v` parameter. The 20 implied voltages used for validation are not treated as 20 independent voltage measurements and do not generate a confidence interval. Cross-technology differences preserve measured implementation context; they are configuration-level effects, not identified protocol-only causal effects.


## LR-FHSS Stage-2 materialisation — v0.1.13

The eight confirmed/unconfirmed x DR8--DR11 radio-interface traces are materialised with one independent source trace per configuration. Full-capture energy remains distinct from the derived incremental transaction estimand.

The transaction derivation subtracts a trace-specific low-current baseline over the complete capture only after the validated one-TX-burst checkpoint. The baseline is the within-trace mean for samples in the configured low-current band and is treated as an empirical baseline proxy, not a replicated sleep-state experiment. In the validated traces, baseline energy is less than 0.1% of total full-capture energy.

The materialiser emits 20 typed evidence records:
- 8 `radio_full_capture_energy_j` records;
- 8 `radio_incremental_transaction_energy_j` records;
- 4 `radio_ack_rx_overhead_energy_j` matched-DR contrasts.

Every configuration has `n_independent_units=1`. The four ACK/RX contrasts each have one contrast replication and are marked descriptive; no population confidence interval is authorised. The implementation context records the LR1121DVK1TBKS/LR1121 radio and Keysight N6705A DC Power Analyzer as measurement hardware and Keysight 14585A Control and Analysis Software as acquisition/control software; the Zenodo record's original `Power Analyzer: Keysight 14585A` wording is retained as a provenance discrepancy. Publication MCDA remains blocked.


## LoED Stage-2 materialisation — v0.1.14

The validated full LoED corpus is materialised as compact, bounded-memory evidence summaries rather than millions of evidence records. Reception-side RSSI, canonical SNR and CRC-valid fraction are summarised by exact PHY stratum (`SF x frequency x bandwidth`), with a companion gateway x PHY table preserving deployment heterogeneity. The existing gateway/day artifact remains the temporal-variability companion.

CRC-valid exact-PHY logical frames are summarised separately by PHY stratum for mean distinct-gateway count and multi-gateway observation fraction. These remain observation-diversity quantities only. The materialiser explicitly sets `n_independent_units = null` for every LoED evidence record because receptions/logical frames are dependent across devices, gateways, days and repeated/retransmitted frames. No delivery probability or PDR is emitted.

Outputs:
- `data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv`;
- `data/analysis_ready/loed_lorawan_edge_2020/gateway_phy_summary.csv`;
- `data/analysis_ready/loed_lorawan_edge_2020/logical_frame_phy_summary.csv`;
- `data/analysis_ready/loed_lorawan_edge_2020/evidence_records.jsonl`;
- `data/analysis_ready/loed_lorawan_edge_2020/evidence_records.csv`;
- `results/validation/loed_stage2_materialisation/summary.json`.


## Unified core-four matrix — v0.1.15

The unified Stage-2 assembler consumes only the four already validated evidence JSONL artifacts plus the InSecTT shared-voltage parameter. Frozen expected composition is 52 Vomhoff + 80 InSecTT + 20 LR-FHSS + 246 LoED = 398 evidence records, 14 empirical metric IDs and one shared parameter.

The assembler emits canonical JSONL/Parquet/CSV matrices, a dataset/technology/metric coverage table, 20 unique measurement-boundary signatures, a 5-target x 4-dataset decision-target gap matrix and non-metric evidence gaps. It fails on duplicate IDs, unresolved lineage, target-only empirical records or evidence-gap policies that reference unavailable metrics. No missing criterion is assigned a default value.

A reviewed LoED stratification detail is preserved: 49 reception PHY strata versus 48 CRC-valid logical-frame PHY strata because SF7 / 868.3 MHz / 250 kHz contains 65,498 recorded receptions and zero CRC-valid receptions. No causal interpretation is inferred from this fact.


## Stage-3 uncertainty contract — v0.1.16

The unified matrix review confirms that Stage 2 is internally consistent. The Stage-3 contract now separates measurement/calibration, within-unit, between-unit, study/implementation, shared-parameter and bridge-structural uncertainty.

Key identifiability decisions:

- Vomhoff energy and duration can be calibrated from replicated `physical_run_id` units using dependence-preserving cluster resampling.
- InSecTT has one independent trace per configuration; millions of electrical samples cannot identify population repeatability.
- InSecTT derived power/energy share one voltage calibration parameter and must be sampled correlatively.
- LR-FHSS has one trace per configuration and one matched contrast per DR; population variance is not identified.
- LoED is a hierarchical campaign; RSSI/SNR require grouped/block calibration and reception-row IID uncertainty is prohibited.
- A generic `study_id` random effect is not identifiable from core-four because study, technology, implementation and measurement boundary are confounded.
- Vomhoff structured implementation metadata remains unknown in the retained source materials; no device effect is invented.

The contract maps all 398 evidence records through 14 dataset/metric uncertainty specifications and records seven explicit calibration gaps. No stochastic draws are produced by v0.1.16.


## Stage-3A Vomhoff run-level calibration — v0.1.17

The production v0.1.16 uncertainty audit is accepted: all 398 core-four evidence records are mapped, with 14 uncertainty specifications, eight dependence groups and seven explicit calibration gaps. No artificial variance or publication sampling is authorised.

v0.1.17 begins calibration only where replication is actually identified. Vomhoff energy/duration are mapped back to physical/source-run values, producing marginal empirical run-to-run dispersion and a candidate joint-resampling-block audit. Every run-level mean and independent-unit count must reproduce the corresponding Stage-2 evidence record exactly.

The output is conditional within-study uncertainty, not a generic device/study random effect. A final joint bootstrap is deferred until production run-set overlap is reviewed. InSecTT/LR-FHSS population variability and LoED hierarchical RSSI/SNR calibration remain unresolved Stage-3 tasks.


## Stage-3B Vomhoff joint bootstrap — v0.1.18

Production Stage-3A outputs resolve the only non-rectangular block. `NB-IoT/MQTT Data Download` has 44 physical runs; all other evidence records in that block have 45. Pairwise overlap is therefore 44/45 rather than evidence of a broader missing-data problem.

The approved resampler uses the 45-run union as the cluster population. The same sampled run indices are applied to every phase/metric in the block. When the one run without `Data Download` is drawn, that phase remains missing and its bootstrap mean is computed from the observed sampled positions. No imputation or listwise deletion is used.

For all five blocks, bootstrap replicate identifiers are local to the block. STACKWISE does not infer cross-block correlation from reused run numbers or source-study membership. The output quantifies epistemic uncertainty of the conditional within-study phase means; it does not provide generic device or cross-study variance.

### v0.1.19 Stage-3C LoED

LoED now has a materialised hierarchical calibration structure for RSSI/SNR using source-day × gateway × PHY cells. The artifact preserves joint RSSI/SNR moments and reconciles exactly to the validated Stage-2 reception summaries. This closes the “grouped artifact missing” gap but does **not** yet authorise a hierarchical sampler: temporal autocorrelation and gateway/day coverage must be reviewed first. Publication uncertainty sampling and MCDA remain blocked.

## Stage-3D LoED campaign/nonstationarity audit — v0.1.20

Stage-3C production outputs reveal two separated acquisition windows rather than one exchangeable 188-day series. v0.1.20 therefore performs a lightweight audit on the compact Stage-3C artifacts; it does not rescan the 11.26M reception corpus.

The audit identifies campaigns only when an observed source-day gap exceeds the declared 30-day audit threshold, calculates campaign-local raw and linearly detrended ACF through 14 days, preserves source-day gateway sets, quantifies campaign-specific gateway coverage, and reports descriptive RSSI/SNR shift between the two observed campaigns.

No stochastic sampler is authorised by this step. Cross-campaign day pooling, a campaign random effect, independent gateway bootstrap, IID day bootstrap and campaign-stratified block bootstrap all remain disabled until the production diagnostics are reviewed and a block length/stationarity policy is selected.

## Stage-3E LoED gateway-composition/campaign confounding audit — v0.1.21

Stage-3D production review shows that the two temporal acquisition campaigns do not share a stable infrastructure support. Campaign 1 contains 6 observed gateways, campaign 2 contains 5, but only 2 gateways occur in both campaigns; the union contains 9 gateways, giving a cross-campaign gateway-set Jaccard of 2/9 (~0.222). Consequently, the observed 2019-vs-2020 RSSI/SNR shift is not identified as a pure temporal effect.

v0.1.21 therefore materialises three descriptive sensitivity views before any temporal block length is selected: (1) same-gateway campaign shifts for the two shared gateways, (2) equal-weight shared-gateway campaign shifts, and (3) reception-weighted shared-gateway campaign shifts. A companion within-campaign table quantifies heterogeneity across gateway-level means for each PHY stratum. These summaries do not causally decompose gateway composition, time, placement/hardware, traffic mix or device-population changes.

Campaign-stratified block bootstrap, gateway bootstrap, campaign random effects, publication uncertainty sampling and MCDA remain unauthorised until the production confounding audit is reviewed.


### Stage-3F checkpoint

LoED Stage-3E established strong gateway-composition confounding between the 2019 and 2020 acquisition windows. The campaigns are now treated as fixed deployment scenarios. Stage-3F evaluates 3/7/14-day within-campaign source-day moving-block sensitivity; final block-length selection and publication stochastic sampling remain pending.


## Stage-3G LoED uncertainty robustness closure — v0.1.23

Stage-3F production output does not support selecting one temporal block length. v0.1.23 therefore closes the identifiable LoED RSSI/SNR layer as two fixed deployment campaigns crossed with an unweighted 3/7/14-day block-length robustness set. Joint centered draws preserve within-scenario RSSI/SNR and cross-PHY dependence, while source-day support is reported separately from reception counts.

This is **not** a single LoED probability distribution. Campaigns and block lengths have no assigned probabilities, cross-scenario replicate alignment has no joint meaning, and the outer robustness envelope is non-probabilistic. Remaining Stage-3 uncertainty gaps are now concentrated in single-trace InSecTT/LR-FHSS repeatability/calibration, generic cross-study variance and downstream bridge-model structural uncertainty. Publication-wide stochastic sampling and MCDA remain blocked.


## Stage-3H single-trace primary-source review — v0.1.24

Stage-3G closes the identifiable LoED RSSI/SNR layer as a scenario-indexed robustness family. The remaining six single-trace metric families are four InSecTT current/charge/power/energy metrics and two LR-FHSS full-capture/incremental-transaction energy metrics. v0.1.24 performs a targeted primary-source repeatability/metrology review rather than inventing a default CV.

For InSecTT, the associated publication documents PPK II measurement at 100 kS/s and reports power averaged over approximately 60 s, but it does not report independent repeated configuration runs or numerical between-run dispersion. Nordic's PPK II accuracy specification is retained as metrology information only and is not converted to a population SD.

For LR-FHSS, the associated publication reports several individual transmission processes with negligible differences but gives no repeat count or numerical dispersion. This is retained as qualitative repeatability evidence only. The instrumentation metadata is also corrected without changing empirical values: N6705A is the measurement hardware; 14585A is acquisition/control-analysis software.

The targeted review identifies **zero defensible numerical population priors** for the six single-trace metric families. Their population variability therefore remains explicitly unidentified. Publication-wide uncertainty sampling and MCDA remain blocked; any later conservative stress-test envelope for these metrics must be labelled model sensitivity rather than an evidence-derived prior.

## Stage-3 closure — v0.1.25

Stage 3 is closed for the current validated core-four evidence using **mixed uncertainty semantics** rather than a forced common probability model.

The 14 empirical metric families resolve as follows:

- 2 Vomhoff energy/duration families: dependence-preserving empirical nonparametric uncertainty within the source study;
- 2 LoED RSSI/SNR families: unweighted campaign × block-length robustness scenarios, with no single probability distribution;
- 6 InSecTT/LR-FHSS single-trace families: explicit epistemic non-identifiability of population repeatability; no default CV/SD or source-unsupported numerical prior;
- 4 CRC/diversity/ACK-contrast families: descriptive quantities without a population distribution.

Six residual gaps remain documented, but none can be resolved from the current evidence without either new measurements, new external quantitative evidence, or a later explicitly labelled model-sensitivity assumption. They therefore remain visible rather than blocking progression to the structural stack-definition stage.

Stage 4 is authorised only for layer-aware candidate-stack definition and hard compatibility/feasibility constraints. Publication-wide stochastic sampling, ranking and MCDA remain unauthorised.

Materialised closure outputs:

- `data/analysis_ready/core_four_uncertainty/stage3_uncertainty_state.csv`;
- `data/analysis_ready/core_four_uncertainty/stage3_uncertainty_state.json`;
- `results/validation/stage3_closure/summary.json`;
- `results/validation/stage3_closure/residual_gaps.csv`;
- `results/validation/stage3_closure/stage4_handoff_rules.csv`.

## Stage 4A — typed stack contract (v0.1.26)

Stage 3 remains closed with mixed uncertainty semantics. Stage 4A defines the canonical end-to-end stack representation as a graph of placed component instances with explicit `provides`/`requires` interfaces, compositional security, explicit gateway/backend mediation, and non-compensatory tri-state hard feasibility. The fixtures in v0.1.26 are synthetic contract tests only. No real protocol catalog or standards compatibility claim is materialised until Stage 4B primary-source verification. MCDA, rankings, stakeholder weights and default stochastic priors remain blocked.


## Stage 4B — primary-source component catalog (v0.1.27)

The Stage-4A graph contract is now populated with a bounded verified core catalog. Twenty-four components have primary-source-backed interface claims; EPhESOS remains evidence-only/pending. Cellular IP/Non-IP, BLE bare/IPSP and LoRaWAN LoRa/LR-FHSS variants are kept distinct. The catalog contains 32 verified compatibility edges, 8 explicit evidence-alignment records and 6 unresolved catalog gaps. Alternative real protocol bindings use `requires_any` OR-groups. No empirical measurement is promoted to a component-level cost solely because a protocol name matches. Stage 4C may assemble candidate stacks from verified components and then add hard scenario facts/constraints; ranking remains blocked.


## Stage 4C — verified reference candidate stacks — v0.1.28

Nine bounded reference candidates are assembled from the Stage-4B catalog. Every binding is checked against a primary-source-verified compatibility edge, not merely by interface-name matching. No candidate has complete end-to-end core-four empirical support; empirical alignments remain component/boundary-limited. BLE remote, UWB remote and EPhESOS families remain deferred where mediation/profile/standardisation gaps are unresolved. Stage 4D may now define scenario facts and hard constraints; scoring/ranking remains blocked.

## Stage 4D — quantitative benchmark hard screening — v0.1.29

Six synthetic reproducible scenarios are now frozen for feasibility testing of the nine
Stage-4C verified reference candidates. Screening is non-compensatory and tri-state. Of 54
scenario×candidate pairs, 12 pass the explicitly declared hard predicates, 33 fail at least
one hard predicate, and 9 remain unresolved because a decision-blocking candidate capability
is not currently source-backed. There are 27 unknown hard-result occurrences in total, but
only 9 are decision-blocking because other candidates are already infeasible on independent
hard grounds.

A Stage-4D `feasible` status is not a ranking and does not imply complete empirical support.
Numeric payload, latency and energy context is retained without being silently promoted to a
hard requirement. Stage 4E should target only capability facts that actually block a scenario
decision. MCDA remains unauthorised.

## Stage 4E — decision-blocker review — v0.1.30

Status: **targeted blocker review complete; mobility ambiguity externalised as benchmark variants**.

- original Stage-4D decision blockers: 9;
- primary/evidence capability claims reviewed: 7;
- forward benchmark scenarios: 7 (the original binary-mobility asset case is replaced by two explicit variants);
- refined scenario×candidate rows: 63;
- feasible / infeasible / unresolved: 21 / 39 / 3;
- remaining decision blockers: 3 across 2 dimensions (Thread latency; LoRaWAN whole-device report energy);
- MCDA/ranking: not authorised.

Next: Stage 4F should decide whether the three remaining blockers can be closed by a defensible stack-level latency bridge/testbed and a whole-device LoRaWAN energy bridge/testbed. If not, freeze them as unresolved feasibility boundaries rather than assign assumptions.

## Stage 4F — hard-feasibility closure — v0.1.31

Status: **closed with explicit operating-profile and measurement-boundary unknowns**.

The refined Stage-4E matrix is frozen at 7 scenarios × 9 candidates = 63 rows: 21 feasible under declared hard predicates, 39 infeasible, and 3 unresolved. Targeted review does not defensibly resolve the final Thread latency or LoRaWAN whole-device energy predicates from existing core-four evidence. All three blockers require a more explicit operating profile and/or matched stack-level measurement/bridge.

An LR-FHSS diagnostic retains the eight validated 4-byte radio transaction energies and notes which measured radio values exceed the 0.2 J benchmark, but no row is promoted to whole-device 16-byte feasibility because both payload and accounting boundary differ.

Stage 4 is therefore closed without forcing these unknowns. Stage 5A is authorised to define operating-profile records and bridge contracts. Preference scoring and MCDA remain blocked.


## Stage 5A — operating profiles and bridge contracts — v0.1.32

Stage 4 remains frozen at 21 feasible / 39 infeasible / 3 unresolved. Three scenario-specific operating profiles and three typed evidence-to-decision bridge contracts are now materialised for the remaining blockers. The profiles contain 26 fields: six scenario-derived known context values and 20 unresolved profile values. All three bridges remain blocked; no numeric bridge output is produced. LR-FHSS retains single-trace epistemic uncertainty and its 4-byte radio-only measurements are not coerced to 16-byte whole-device/report energy. Stage 5B may refine profiles or validate one bridge at a time; scoring/ranking remains blocked.

## Stage 5B — LR-FHSS source-model bridge audit — v0.1.33

Stage 5A identified LR-FHSS as the only current blocker with a matched component-energy source but an unresolved boundary transform. Stage 5B therefore audits the associated published radio-state model at the existing 4-byte source point before permitting any payload extrapolation.

The Table-6 numerical airtime values are reproduced exactly at their published precision under a documented table-consistent payload-duration convention. The publication's rendered Eq. (6) and Table-6 payload-duration values are not silently reconciled: both are retained and the source-internal discrepancy remains causally unresolved.

All four unconfirmed DR8--DR11 traces reproduce within 1.39% absolute relative energy error. All four confirmed traces fail the same deterministic audit by roughly 43--52%. The confirmed source captures also have an approximately 50 mA TX plateau while the published state model uses 25.7 mA; no causal explanation is inferred.

Consequently, only the unconfirmed radio-component model is permitted to extrapolate from 4 to 16 bytes, and only as a component diagnostic. The conservative incremental transaction model gives about 0.2044 J for DR8/DR10 and 0.1141 J for DR9/DR11. An exactly matched unconfirmed DR8/DR10 profile could therefore be rejected by the 0.2 J whole-device budget using a one-sided component lower bound. DR9/DR11 cannot be declared feasible because unmodelled device energy is non-negative. The generic Stage-4 candidate remains unresolved because DR, confirmation mode, hardware and other operating-profile fields are not selected.

No whole-device energy estimate, population uncertainty distribution, preference score or MCDA ranking is materialised.

## Stage 5C — LR-FHSS profile variants (v0.1.34)

Stage 5C materialises eight source-aligned LR-FHSS variants (`DR8–DR11 × confirmed/unconfirmed`) but does not select or weight them. Two unconfirmed variants (DR8/DR10) inherit a conditional one-sided infeasibility result because the validated radio-component lower bound alone exceeds the 0.2 J whole-device budget. DR9/DR11 remain residual-energy unresolved; confirmed variants remain source-model unresolved. The generic LR-FHSS candidate and the frozen Stage-4 matrix remain unchanged.



## Stage 5D — LR-FHSS variant selection (v0.1.35)

Production target: retain the eight Stage-5C source-aligned variants as an unweighted robustness family unless deployment-specific selection evidence exists. ADR/LinkADRReq support is not itself evidence that the agriculture benchmark uses a particular DR. Confirmed/unconfirmed policy is also not inferred from energy. Expected family outcome: 2 conditional-infeasible, 0 feasible, 6 unresolved; generic LR-FHSS remains unresolved; Stage-4 remains 21/39/3.

## Stage 5E — decision-readiness and gap prioritisation — v0.1.36

Stage 5E audits the frozen non-infeasible candidate set against the five canonical decision targets without scoring stacks. The audit covers 24 scenario-stack candidate incidences (21 feasible + 3 unresolved) and 120 candidate-target rows.

Current checkpoint:

- target rows already ready at the canonical decision boundary: 0;
- feasible candidates fully ready for the first energy/report + lifecycle-cost decision slice: 0/21;
- feasible IP-cellular candidate incidences with bridgeable Vomhoff report-energy evidence: 10;
- scenarios that would gain at least two energy-comparable candidates after a validated cellular-IP energy bridge: 3.

The preferred next existing-evidence bridge is therefore `cellular_ip_report_energy_bridge`, using Vomhoff physical-run/phase evidence while preserving source application-context mismatch and joint bootstrap semantics. Lifecycle cost is a separate mandatory cross-cutting contract and remains missing for all 21 feasible candidates. `configs/fleet.yml` smoke costs are not publication evidence.

Stage 5E does not reopen the 21/39/3 feasibility matrix and does not authorise preference scoring, publication MCDA or fleet optimisation. See `docs/DECISION_READINESS_AUDIT.md`.

## Stage 5F — cellular-IP application-report energy bridge audit — v0.1.37

Stage 5F audits the highest-leverage Stage-5E gap without coercing the Vomhoff source into a scenario-matched estimand. Ten feasible IP-cellular scenario×candidate incidences are checked. All ten benchmark payloads (64 B or 200 B) differ from the retained 1024 B Vomhoff transfer context, and none has exact application-stack alignment with the source evidence. LTE-M has no retained MQTT source context; HTTP is not transferred to CoAP/DTLS/LwM2M; NB-IoT MQTT remains only partial upper-stack context.

A dependence-preserving 1 KB whole-device **source active transaction component** is authorised as a diagnostic for NB-IoT/HTTP, LTE-M/HTTP and NB-IoT/MQTT by summing Connection Establishment, Data Request, Data Download and Postprocessing within the same Stage-3B bootstrap replicate. Standby and Idle are excluded because their source timing does not define the benchmark reporting-cycle tail/PSM/eDRX boundary.

Canonical `expected_device_energy_per_application_report_j` materialisation remains 0/10. Stage 5G must close payload, upper-layer and reporting-cycle transfer gaps with targeted model/testbed/external evidence. Lifecycle cost remains mandatory in parallel. MCDA and fleet optimisation remain blocked. See `docs/CELLULAR_IP_ENERGY_BRIDGE_AUDIT.md`.

### Stage 5G update (v0.1.38)

A targeted external NB-IoT/LTE-M state/procedure energy model now provides structural support for payload and report-cycle dependence, but not boundary/device-compatible absolute calibration. All 10 feasible cellular-IP report-energy targets remain blocked. Preferred next closure is matched bridge evidence; lifecycle-cost evidence can proceed independently in parallel.

## Stage 5H update — lifecycle-cost contract (v0.1.39)

The lifecycle-cost accounting boundary is now frozen, but numerical publication cost evidence is intentionally not materialised. Of 21 feasible candidate incidences, 17 are operator-managed, 2 private-owned, and 2 urban LoRaWAN ownership modes remain unresolved. Private shared infrastructure requires a deployment scale before allocation. `configs/fleet.yml` remains smoke-only. Publication MCDA and fleet optimisation remain blocked.

## Stage 5I update — dated cellular cost evidence (v0.1.40)

The first dated lifecycle-cost evidence tranche is materialised for the ten feasible IP-cellular candidate incidences. A single dual-mode Quectel BG95-M3 reference hardware observation is used for both NB-IoT and LTE-M, together with an official 1NCE prepaid IP-connectivity tariff and SIM price. Non-IP/NIDD service pricing is not inferred from IP tariff evidence.

The tariff audit exposes an additional decision-critical boundary: finite included data must be reconciled with candidate transport/session traffic. The source states 1-kByte measurement/billing granularity but does not identify the aggregation interval, so STACKWISE does not assume one 1-kByte unit per report. Five-year application payload alone is 35.064 MB for the 900-s smart-meter profile and 168.3072 MB for the 60-s tracking profiles; both are below 500 MB, but transport/security/application overhead and session maintenance are unresolved.

Accordingly, Stage 5I materialises a source-backed EUR 46.41 hardware + standard-SIM + base-plan reference cash-cost floor for all ten IP-cellular incidences but authorises **zero canonical lifecycle-cost targets**. Stage 5J should freeze shared candidate-specific IP session/transport profiles for both tariff-volume and energy-bridge work. Publication MCDA remains blocked.

## Stage 5J — cellular IP session/transport profile contract — v0.1.41

Status: **common transaction semantics frozen; exact wire/session volume and canonical report energy remain explicitly unresolved**.

- feasible IP-cellular profiles: 10;
- CoAP/DTLS/UDP profiles: 5;
- MQTT/TLS/TCP profiles: 5;
- profile fields: 200;
- known/frozen fields: 70;
- unresolved fields: 130;
- profiles complete for exact tariff volume: 0;
- profiles complete for canonical report energy: 0;
- publication MCDA: not authorised.

The common benchmark telemetry transaction is now LwM2M `Send`. Scenario `payload_bytes` is explicitly interpreted as pre-LwM2M application data, not serialized wire payload, and future tariff accounting must include both uplink and downlink. Standards review confirms that CoAP/DTLS and MQTT/TLS overhead cannot be represented by one universal constant because token/topic/identifier lengths, security record parameters, IP family, connection/session persistence, padding and retry behaviour are profile dependent. Stage 5K should therefore create an unweighted parameterised envelope family rather than a single guessed profile.

The primary standards catalogue was refreshed from RFC 8446 to RFC 9846 for TLS 1.3 and from LwM2M Transport 1.2.1 to 1.2.2. Stage-4B catalogue validation still passes with unchanged structural counts.

## Stage 5K — parameterised cellular IP protocol-envelope variants — v0.1.42

Status: **compact deterministic sensitivity family materialised; exact byte and energy accounting remain blocked**.

Stage 5K converts the 130 unresolved Stage-5J profile fields into a small versioned family of explicit benchmark anchors rather than a guessed deployment profile or a full Cartesian product. The ten feasible IP-cellular profiles are crossed with nine anchor designs, yielding 90 scenario–stack–variant rows: 45 CoAP/DTLS/UDP and 45 MQTT/TLS/TCP. Every Stage-5J unresolved field is assigned in every variant. No probabilities, frequencies or preference weights are attached to the variants.

The nine anchors are: compact persistent reference, IPv6, acknowledged delivery, LwM2M CBOR, SenML JSON, per-report security resumption, per-report full security re-establishment, one full transaction retry, and a binding-expanded stress anchor. The chosen values are standards-bounded sensitivity endpoints or explicit benchmark conventions; they are not claims about deployment prevalence.

A tariff headroom diagnostic is also materialised. Under the Stage-5I 500-MB aggregate allowance and before any unknown tariff-accounting rounding, the raw non-application headroom is approximately 2651.93 B/report for the 900-s / 200-B smart-meter profile and 126.13 B/report for the 60-s / 64-B tracking profiles. These are one-sided aggregate byte budgets, not protocol-volume estimates and not proof of tariff sufficiency.

Stage 5K itself materialises no wire volume. Stage 5L (v0.1.43) now supplies standards-known component floors and deterministic anchor accounting, while exact wire volume remains blocked by LwM2M serialization and session/transport increments. Canonical report energy remains blocked. Publication MCDA and fleet optimisation remain disabled. See `docs/CELLULAR_IP_PROTOCOL_ENVELOPE_VARIANTS.md` and `docs/CELLULAR_IP_WIRE_VOLUME_ACCOUNTING.md`.


## Stage 5L update — standards-based wire-volume accounting (v0.1.43)

Stage 5L materialises byte-level known-component accounting for all 90 Stage-5K cellular-IP variants while preserving the pre-LwM2M/serialized-payload distinction. Every variant receives a strict primary-exchange transport floor and a separate deterministic anchor-accounting value; exact wire volume remains 0/90. LwM2M serialization remains unresolved for 90/90 variants, MQTT pure-TCP ACK/segmentation remains unresolved for 45/45 MQTT variants, and per-report security resumption/full-establishment increments remain unresolved for 20 variants.

Under the strict raw transport floor, 27/90 variants exceed the nominal 500-MB five-year allowance: all MQTT/TLS variants in the two 60-s tracking scenarios. The compact persistent MQTT tracking floor is 205 B/report, or 539.109 MB over five years, before serialized LwM2M payload, pure TCP ACKs and session-handshake increments. This is a raw-volume warning, not an exact billed-volume or TopUp claim, because 1NCE nearest-1-kByte aggregation remains unspecified.

Stage 5M (v0.1.44) now closes a synthetic LwM2M serialization envelope while leaving the canonical application object model and session increments unresolved. No wire-byte result may be converted directly to device energy without a validated boundary-compatible state/energy bridge. Publication MCDA remains blocked. See `docs/CELLULAR_IP_WIRE_VOLUME_ACCOUNTING.md` and `docs/LWM2M_SERIALIZATION_ENVELOPE.md`.


## Stage 5M update — LwM2M serialization surrogate envelope (v0.1.44)

Stage 5M materialises exact serialization lengths for two explicitly synthetic Opaque-Resource surrogates across all 90 Stage-5K variants, yielding 180 serialization rows. The OMA test-only Object ID 42769 is used to prevent accidental production/application interpretation. One surrogate carries all 64/200 application octets in a single Resource; the other splits the same bytes across three Resources.

Exact surrogate serialization is identified for 180/180 rows, but canonical application serialization remains 0/180. Strict raw surrogate transport volume exceeds the nominal 500-MB allowance in 57/180 rows; deterministic anchor accounting exceeds it in 69/180 rows. All MQTT/TLS 60-s tracking rows exceed under both surrogates. CoAP/DTLS tracking demonstrates resource-structure sensitivity: SenML JSON is approximately 478.624 MB/5y for the one-Resource surrogate and 594.335 MB/5y for the three-Resource surrogate at the strict primary-exchange layer.

Billing-rounding aggregation, security establishment/resumption, MQTT pure TCP ACK/segmentation, the real application resource model and canonical report energy remain unresolved. Stage 5N should address session/control-traffic increments before lifecycle connectivity cost is finalised.

## Stage 5N update — security-session/control envelope (v0.1.45)

Stage 5N is closed as the final planned transport/accounting refinement. Two deterministic standards-bounded PSK/session-control designs are applied to the 180 Stage-5M serialization rows, yielding 360 envelope rows. Current TLS 1.3 PSK grammar surrogates are 311 B (`psk_ke`, 16-B identity) and 449 B (`psk_dhe_ke` + X25519, 64-B identity) before TCP/IP; DTLS 1.3 surrogates including final-flight ACK and modeled UDP headers are 431 B and 589 B. MQTT/TCP additionally receives minimal CONNECT/CONNACK traffic for rebuilt connections and a zero-versus-one standalone ACK-only sensitivity.

At the raw five-year allowance layer, 81/180 Stage-5M source rows exceed 500 MB under both session/control surrogates, 99/180 remain within under both, and 0/180 cross the threshold solely because E0 versus E1 is selected. All 54 MQTT/TLS tracking source rows robustly exceed across the compact session/control family. These are deterministic surrogate results, not billed-volume or deployment-frequency claims.

Canonical application serialization, certificate/RPK session traffic, exact TCP packetisation, tariff rounding, report energy, stochastic MCDA and fleet optimisation remain unresolved. Further packet-level refinement is frozen unless a material error is found. The project now moves to Stage 6A first decision-ready slice consolidation. See `docs/SECURITY_SESSION_CONTROL_ENVELOPE.md`.

## Stage 6A update — first decision-slice consolidation (v0.1.46)

Stage 6A closes the Stage-5 preparation sequence and consolidates current decision usability without scoring. The frozen Stage-4 matrix remains 21 feasible / 39 infeasible / 3 unresolved. Across 21 feasible candidates × five canonical targets there are 105 criterion rows; the first slice requires energy/report and lifecycle cost, giving 42 mandatory soft-target rows. None is yet decision-ready: 10 lifecycle-cost rows have context-only dated price + tariff-volume robustness evidence, while 32 required rows remain blocked. Candidate-boundary report energy remains blocked for all 21 feasible candidates.

For the ten feasible IP-cellular incidences, Stage-5N collapses to 4 profile-level robust-within, 3 robust-exceed and 3 protocol-envelope-sensitive tariff-volume contexts. These are not exact billed-volume or EUR cost targets and therefore are not scored.

The four IP-cellular candidates in `asset_tracking_periodic_cross_cell` are selected as the preferred **development** subset for Stage 6B because they form a common 60-s/64-B 2×2 NB-IoT/LTE-M × CoAP/MQTT comparison with non-degenerate cost context. The two feasible Non-IP candidates remain outside this subset; no full-scenario optimum may be claimed. Publication MCDA and fleet optimisation remain blocked.

## Stage 6B update — matched cellular energy evidence (v0.1.47)

The first decision slice still has no score-ready energy target. A targeted primary-source audit reviewed Vomhoff 2023, Sørensen 2022, Michelinakis 2020/2021 and Lukic 2020. Zero sources match the complete 64-B/60-s, dual-RAT, dual-binding, whole-device report-cycle boundary. The literature-search branch is therefore closed with an explicit negative result rather than an extrapolation.

A minimal measurement contract is frozen for the four periodic-tracking IP candidates on one dual-mode DUT and one operator, with full 60-s cycles as the replication unit, randomized time blocks, a five-block pilot, and the final replication count frozen only after pilot variance is observed. Failed cycles are retained. Publication MCDA remains blocked.

## v0.1.58 publication finalisation

The publication experiment programme is closed after Experiments 1–5. Six claims are publication-authorised (benchmark resource plus five methodology/result contributions); two remain explicitly outside scope: global stochastic ranking and matched whole-device cellular report energy. The recommended next activity is manuscript preparation, not a new experiment.

## v0.1.59 publication handoff

Research experiments 1–5 are closed. Benchmark v1.0.0 is frozen and ready for deterministic deposit packaging. The next work is DOI/deposit finalisation and drafting two non-overlapping manuscripts; no Experiment 6 is planned.
