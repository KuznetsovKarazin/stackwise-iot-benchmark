# STACKWISE research log

This is the chronological human-readable record of dataset integration, debugging and validation. Generated manifests and result files remain the machine-readable provenance record.

## 2026-08-06 — repository scaffold

Created the initial STACKWISE research repository with:

- public dataset registry and exclusion list;
- licence-aware download layer;
- canonical observation schema;
- provenance manifests;
- generic harmonisation/adapters;
- evidence audit;
- provisional energy modelling;
- stochastic MCDA;
- fleet optimiser;
- smoke pipeline and tests.

The initial dataset registry contained 12 public empirical sources. Synthetic observations were retained only as smoke-test fixtures and explicitly excluded from research evidence.

## 2026-08-06 — Vomhoff NB-IoT/LTE-M ingestion

Downloaded DOI `10.5281/zenodo.7603641` and verified source checksums. Initial harmonisation returned zero rows because the generic adapter did not recognise the actual source columns.

Diagnostic inspection established that the CSVs contain high-frequency samples with source fields including `current`, `voltage`, `current_As`, `consumption_Ws`, `diff_time`, `run`, `event`, `rat_type`, `application_protocol` and optional `data`.

Implemented a dataset-specific adapter using the grouping and normalisation logic in the authors' `fig3.R`, `fig4.R` and `fig5.R` scripts.

Two integration bugs were then identified and corrected:

1. repeated `Data Request` labels with different `diff_time` values had initially been collapsed; `diff_time` was added to the source grouping key;
2. a logical group crossing a CSV chunk boundary was split because missing values were used directly in Python dictionary keys (`NaN != NaN`); missing-key values were canonicalised before accumulation.

Final production result: 1,671 unique run/phase observations, zero duplicate IDs and clean schema validation.

Source Figures 3–5 were reproduced to validate the source processing logic. For new STACKWISE analyses, repeated source segments belonging to one experimental run must be aggregated to the independent run level to avoid pseudoreplication.

## 2026-08-08 — InSecTT ingestion and independent scale validation

Downloaded DOI `10.5281/zenodo.7762712`. The source archive contains four high-resolution traces: BLE, OpenThread, EPhESOS and UWB. Each trace has one timestamp column and current columns for communication periods of 100, 200, 400, 800 and 1600 ms.

Source documentation established:

- 100 kS/s measurement rate;
- timestamp increments representing 10 microseconds;
- current in microamperes;
- approximately 60 s per configuration;
- 2 bytes acquired every 100 ms, accumulated to 2/4/8/16/32-byte payloads at the five communication periods.

Because source voltage is absent from the dataset README, canonical harmonisation records current and integrated charge but does not guess joules.

An independent validation against Table 1 of the associated publication used all 20 technology/period configurations. The implied constant source voltage was tightly clustered:

- median 3.3000554 V;
- range 3.2990682–3.3112278 V;
- coefficient of variation 0.0785%;
- power reconstruction RMSE 0.1974 microW;
- power reconstruction MAPE 0.0348%.

The inferred 3.3 V value is retained as validation/analysis provenance rather than rewritten as raw source metadata.

An analysis-ready layer derives mean power and energy using the validated inferred voltage with explicit provenance. One 60 s trace per configuration is treated as one experimental observation; millions of within-trace samples are not independent replicates.

## 2026-08-08 — LoRaWAN LR-FHSS ingestion

Downloaded DOI `10.5281/zenodo.13838241`. Eight source traces cover confirmed/unconfirmed LoRaWAN LR-FHSS DR8–DR11.

Source and publication metadata established:

- 20.48 microsecond sampling period;
- 4-byte FRM payload;
- +14 dBm transmit power;
- radio-interface-only measurement boundary;
- dedicated 3.3 V supply for the measured LR1121 radio interface.

The adapter streams the raw traces and calculates current statistics, charge and full-capture energy. Structural production validation found:

- 8 configurations;
- no warnings or schema errors;
- approximately 60 s duration for every capture;
- exactly one TX burst in every capture.

Scale diagnostics found an unconfirmed DR8 TX plateau of approximately 25.47 mA versus the publication reference 25.7 mA. The corresponding low-current band was approximately 0.424 microampere versus a 0.5 microampere reference.

The mean plateau across all traces was not used as a universal TX-current validation because confirmed traces contain additional receive/ACK activity.

An analysis-ready transaction metric subtracts the trace-specific sleep baseline from full-capture energy. Paired confirmed-minus-unconfirmed values were computed by DR. These are described as capture-specific ACK/RX overheads, not expected population effects, because only one source trace exists for each configuration.

## 2026-08-08 — LoED diagnosis

Downloaded the official LoED sample, DOI `10.5281/zenodo.4121430`, with source checksums verified. The local download includes the source README, parser and six-day sample ZIP.

Diagnostic parsing established a consistent daily CSV schema:

- timestamp;
- device address and physical payload;
- gateway identifier;
- CRC status;
- frequency;
- spreading factor;
- bandwidth and coding rate;
- RSSI and SNR;
- message metadata (`size`, `mtype`, `fcnt`, `fport`).

The source README documents nine gateways in heterogeneous urban locations and a larger complete archive with one file per collection day.

Decision: use the official sample only for adapter development. Production results must be regenerated from the complete archive. LoED will contribute gateway-observation/link-quality evidence and gateway diversity. It will not be used to claim absolute packet-delivery probability unless a defensible transmission denominator is introduced.

## 2026-08-08 — LoED adapter implementation checkpoint (v0.1.7)

- Inspected the official six-day LoED sample, source README and `LoED_parser.py`.
- Confirmed a stable 15-column schema across six daily CSV files.
- Implemented one canonical observation per source gateway reception.
- Preserved timestamp, gateway ID, CRC state, frequency, SF, bandwidth, code rate, RSSI, SNR, frame counter, FPort and MType provenance.
- Added deployment metadata for the nine gateways from the dataset README.
- Added SHA-256 packet fingerprints while intentionally excluding the raw physical payload from processed output.
- Kept `delivery_success` null because the dataset is reception-side and has no denominator of attempted transmissions.
- Added analysis-ready packet reception clustering and gateway/day summaries.
- Added a generic `--file-glob` download override so the complete LoED archive can later be fetched without creating a duplicate registry record.
- Next action: strict sample harmonisation and validation; then freeze the adapter and run the same pipeline on the complete archive.

## 2026-08-09 — LoED sample production harmonisation and AppleDouble hotfix

- Strict harmonisation of the official six-day sample produced 326,870 canonical gateway-reception rows with zero schema validation errors.
- Six warnings were traced exclusively to macOS AppleDouble resource-fork entries named ``._*.csv`` inside the source archive; these are not scientific data.
- The adapter now excludes ``._*.csv`` and ``__MACOSX`` artefacts before header inspection, so archive metadata cannot contaminate scientific warning counts.
- The six-day sample contains six observed gateway IDs. The source README documents nine gateways for the complete campaign; therefore sample gateway count must not be treated as the campaign-wide deployment count.
- Next action: rerun strict harmonisation, require zero warnings, validate packet clustering, then build the analysis-ready reception-cluster layer before downloading the complete archive.



## 2026-08-09 — LoED SNR quality-control rule (v0.1.7.post2)

- Sample validation found rare source SNR values as low as `-128 dB`, outside the broad physical range used by the project for LoRa link-quality statistics.
- The source value is not deleted or rewritten: it is retained as `source_snr_db_raw`.
- Canonical `snr_db` maps source values outside `[-50, 50] dB` to missing so they cannot distort packet-cluster or gateway/day SNR summaries.
- Validation reports the count and fraction of such source values explicitly.
- This is a quality-control transformation, not a claim that `-128` has a vendor-defined sentinel meaning; the public LoED README does not document that encoding.


## 2026-08-09 — LoED sample frozen and full-scale execution design (v0.1.8)

- Final sample validation passed on 326,870 gateway-reception rows from six daily files and six observed gateways.
- Canonical SNR after QC spans -25 to 15 dB; six source values at -128 dB are retained in `source_snr_db_raw` and excluded from physical SNR summaries.
- Sample packet reconstruction produced 165,626 reception clusters, including 1,700 multi-gateway clusters; these remain reception-diversity evidence, not absolute PDR.
- The complete LoED archive was downloaded with source checksum verification.
- Before full processing, the pipeline was changed from whole-DataFrame accumulation to direct ZIP-to-Parquet streaming because paper-scale LoED contains far more rows than the six-day sample.
- Validation and analysis-ready construction now operate one source day at a time and write packet clusters incrementally to Parquet. This keeps memory bounded and preserves the exact same packet-clustering semantics.
- A checkpoint script records the validated sample reports and SHA-256 hashes of large reproducible artifacts before full-corpus outputs overwrite the sample processed path.
- Next action: checkpoint sample, harmonise full archive in strict mode, validate full corpus, build analysis-ready full LoED tables.

### 2026-08-09 — LoED full-corpus validation performance correction

The first v0.1.8 full-corpus validation attempt was stopped after a multi-hour runtime. Investigation showed that `_read_source_file()` applied a filtered Arrow dataset scan separately for every source day against one monolithic Parquet file. This was bounded in memory but computationally inefficient because the corpus could be rescanned roughly once per day. v0.1.8.post1 replaces this with a single sequential Parquet pass, buffering only the current source day. The already harmonised full LoED Parquet is retained and does not need to be rebuilt.


## 2026-08-10 — Full LoED long-cluster audit and semantic correction (v0.1.9)

The full-corpus v0.1.8 output produced 5,779,010 provisional packet clusters. A targeted audit exported all 865 clusters with spans above 1 s. Ninety-one were CRC-invalid and shared one Join Request fingerprint. The remaining 774 were CRC-valid uplinks. Several gateway combinations showed systematic spans around one second even when each gateway contributed only one reception row, demonstrating that public gateway UTC timestamps are not sufficiently synchronized to support physical-emission clustering by a small fixed window. Other clusters contained 3–6 rows for the same exact frame over several seconds, consistent with retransmission/repeat observation.

Decision: replace temporal physical-emission reconstruction with CRC-valid logical-frame reconstruction by exact PHY fingerprint within source day. CRC-invalid gateway receptions remain in the harmonised table but are excluded from identity clustering. Full LoED analysis-ready outputs must be regenerated under v0.1.9 before cross-study modelling.


## 2026-08-10 — LoED validation cache separation (v0.1.9.post1)

Repeated full-corpus validation under v0.1.9 took about three hours because validation rebuilt the complete logical-frame table even though the identical analysis-ready artifact had already been generated. Profiling of the implementation showed repeated Python-level group aggregation (`first_nonmissing` and gateway-list aggregation) across roughly 5.38 million logical-frame groups.

Decision: validation is now split into two independently reusable layers. Gateway-level structural checks are cached against a local Parquet signature after a successful pass. Logical-frame statistics are read from the already-built analysis-ready Parquet using only the three required numeric columns. Full logical-frame reconstruction remains available only as an explicit semantic-audit operation (`--rebuild-clusters`). This prevents routine validation from duplicating the most expensive transformation in the pipeline.


## 2026-08-10 — LoED validation cache-isolation correction (v0.1.9.post2)

A Windows regression test exposed cross-input cache leakage in the v0.1.9.post1 fast-validation path: a temporary six-row pytest fixture silently reused the repository-level full-LoED logical-frame Parquet and therefore reported 5,378,763 logical frames instead of two. The scientific full-LoED artifact was not affected, but the validation API was not input-safe.

Decision: implicit reuse of the repository analysis-ready LoED artifact is allowed only when the validated input resolves to the canonical repository `data/processed/loed_lorawan_edge_2020/observations.parquet`. Noncanonical inputs must reconstruct their own logical frames unless the caller explicitly supplies a matching analysis-ready artifact. A dedicated cache-isolation regression test was added. The PowerShell patch installer was also hardened to fail on non-zero external-command exit codes.

## 2026-08-10 — Stage-2 empirical evidence contract (v0.1.10)

The four core empirical sources are treated as validated inputs with intentionally different measurement boundaries. Before any cross-study uncertainty model or MCDA, STACKWISE introduced a separate typed evidence layer.

Implemented:

- `evidence_record.schema.json` with metric, boundary, statistical-unit, lineage, uncertainty and applicability fields;
- canonical evidence metric catalogue, including explicit target-only metrics that are not yet empirically supported;
- structured boundary taxonomy and conservative C0/C1/C2/C3 compatibility classes;
- `stackwise.evidence` validation and compatibility helpers;
- regression tests for schema/catalog consistency, direct comparison requirements, bridgeable energy boundaries, unknown-boundary blocking and the LoED CRC/PDR incompatibility;
- metadata-only correction that places Thread UDP under `transport_protocol`.

Methodological outcome: the Stage-2 evidence matrix will not be a technology scoreboard. It will be a long-form set of typed claims with explicit denominators, statistical units and derivation lineage. Source grade is separated from inferential strength, and shared parameters are retained for correlated uncertainty in Stage 3.

No MCDA or fleet-ranking logic was changed and no new empirical dataset was added.


## 2026-08-10 — Stage 2A: Vomhoff logical-unit audit introduced

- Confirmed that the v0.1.10 evidence contract, registry validation and complete local pytest suite pass on the production workstation.
- Re-read the retained source Figure 3--5 R scripts before implementing analysis-ready aggregation.
- Identified that the harmonised table intentionally contains both publication target phases and auxiliary instrumentation/log events; the latter must not be promoted automatically to Stage-2 phase evidence.
- Identified an unresolved inferential question for repeated target events inside one source run: `diff_time` segments may be additive subsegments or repeated phase occurrences. Either blind row-level inference or blind summation could be wrong.
- Added `src/stackwise/vomhoff_audit.py` and `scripts/audit_vomhoff_logical_units.py` to inspect the real validated 1,671-row table without modifying it.
- Added outputs for candidate target-phase groups, every multi-segment target group, non-target event counts, Figure 5 Standby durations and provenance manifest.
- Recorded the Figure 5 README/R-script discrepancy: README states Standby is calculated for 10 s; the source R code has an explicit normalisation transformation only for Idle. Source reproduction remains unchanged pending audit.
- No Stage-2 evidence values, uncertainty model or MCDA ranking were produced.


## 2026-08-10 — Stage 2A: Vomhoff logical-unit audit reviewed; independence audit added

Production `v0.1.10.post1` output was reviewed.

Observed:

- 1,671 validated source-segment observations and zero duplicate observation IDs;
- all 1,671 rows correspond to source Figure target phases;
- 1,449 candidate source-Figure/run/phase groups;
- 222 groups contain two source segments and no group contains more than two;
- every multi-segment group is `Data Request` (119 Figure 4; 103 Figure 5);
- metadata conditions are constant within all candidate groups;
- Figure 5 Standby remains a source-documentation discrepancy rather than a silently corrected transformation.

The 444 exported repeated segments were then checked temporally. For every pair, the second segment starts within 6 ms of the expected end of the first segment; the maximum absolute continuity residual is approximately 5.22 ms. This supports additive aggregation for the explicit Stage-2 estimand `total phase within one run`.

A second dependence issue was discovered during review: the Figure 4 and Figure 5 NB-IoT/HTTP `Data Request` rows for runs 2--60 are exact duplicates across source Figure contexts. Therefore source Figure cannot define independent replication. A new audit was added to quantify exact cross-Figure segment reuse and run-level overlap across the full processed table before final Vomhoff evidence is materialised.

No final cross-Figure deduplication, uncertainty model, or MCDA is authorised yet.


## 2026-08-10 — Vomhoff Stage-2 materialisation decision

Reviewed the production `v0.1.10.post2` independence audit. All 59 Figure-4/Figure-5 NB-IoT/HTTP `1K.data` run pairs show strong source reuse; each shares five events and 354 exact segment signatures in total. Cross-Figure Figure labels are therefore not independent replicates.

Source scripts/README were re-audited. Figure 5 applies an Idle-specific filter to HTTP and MQTT; the README states MQTT Idle is discarded because the device disconnects, while `fig5.R` still carries it into the aggregation. The README also states MQTT Standby is normalised to 10 s, but `fig5.R` contains no such transform. Stage 2 excludes MQTT Idle from decision evidence, retains HTTP Idle as an alternate dependent view, and does not invent a Standby correction.

Next output is the run/phase analysis-ready artifact and validated Vomhoff evidence records. MCDA remains blocked.


### 2026-08-11 — Vomhoff Stage-2 review and implementation-context gap

Reviewed the v0.1.11 Vomhoff outputs. The run-level correction is localised to `Data Request`; evidence IDs are unique; source-segment counts are not used as independent-unit counts; Figure-4/Figure-5 reuse is represented as one physical run with dependent views. Vomhoff is accepted as the first materialised Stage-2 source.

Before InSecTT materialisation, identified a schema gap: nominal technology is insufficient to represent the measured implementation because UWB uses nRF52832 + DW1000 while the other InSecTT configurations use nRF52840. Added implementation-context fields and a conservative compatibility rule. No empirical transformation changed.


## 2026-08-11 — InSecTT Stage-2 materialisation (v0.1.12)

After the implementation-context extension passed the full local test suite, InSecTT was promoted from a validated transformation to a materialised Stage-2 source. The builder requires the complete 4 x 5 design and preserves one independent approximately 60 s trace per configuration. It emits 20 configuration observations and 80 evidence records: 20 trace mean-current, 20 trace charge, 20 validated-derived mean-power and 20 validated-derived capture-energy records.

The voltage used for derived quantities is not written back into harmonised raw-derived metadata. It is represented once as the shared parameter `insectt_ppk2_source_voltage_v`, inferred from the associated publication Table 1 scale check. The configuration-wise implied-voltage spread is retained as a validation diagnostic only; it is not converted into a standard error because the values are not independent voltage replicates.

Implementation context is explicit. The UWB configuration uses nRF52832 + DW1000 while the other technologies use nRF52840-based hardware. Therefore the evidence supports measured configuration-level comparisons but not a causal claim that all observed differences are caused only by the network protocol. Publication MCDA remains blocked.


## 2026-08-11 — LR-FHSS Stage-2 materialisation (v0.1.13)

The validated eight-trace LR-FHSS source was materialised as typed Stage-2 radio-interface evidence. Production checkpoints require exactly one TX burst per trace, 4-byte FRM payload, +14 dBm TX power and the source-backed 3.3 V radio rail.

For each configuration, the materialiser retains full-capture energy and derives incremental transaction energy by subtracting a trace-specific low-current baseline over the capture duration. The low-current baseline is not treated as an independent sleep replicate. The validated baseline contribution is only about 0.027--0.095% of full-capture energy.

Matched-DR confirmed-minus-unconfirmed contrasts are emitted as descriptive ACK/RX overhead records with one contrast replication. Approximate validated overhead ratios versus the unconfirmed transaction are DR8 117.77%, DR9 93.66%, DR10 114.86% and DR11 126.52%. No population CI or expected ACK-overhead distribution is inferred from these four single contrasts.


## 2026-08-11 — LoED Stage-2 evidence materialiser prepared (v0.1.14)

Reviewed the validated full-corpus LoED semantics before Stage-2 integration. The previous logical-frame decision remains unchanged: CRC-valid exact-PHY fingerprint within source day, no wall-clock gap, and no claim that one logical frame equals one RF transmission.

Implemented bounded-memory evidence summarisation from the existing processed reception Parquet and logical-frame Parquet. The materialiser emits reception PHY-stratum summaries, gateway x PHY summaries, logical-frame PHY summaries and typed evidence records. It reuses the fast validated LoED checkpoint and does not rebuild logical-frame clustering.

No independent-unit count, sqrt(n) confidence interval, delivery probability or MCDA score is produced. Documentation was corrected where it still described the pre-audit temporal-gap clustering or full-corpus validation as pending.


## 2026-08-11 — Stage-2 core-four assembly preparation (v0.1.15)

Reviewed the production v0.1.14 LoED artifacts. All 246 evidence IDs are unique, all `n_independent_units` values are null as intended, and evidence estimates/counts reproduce `reception_phy_summary.csv` and `logical_frame_phy_summary.csv`. The 49 reception PHY strata sum to 11,262,834 rows with complete PHY keys; the corpus-level CRC record retains all 11,263,001 receptions. The 167 receptions outside the stratified table have incomplete PHY keys and are CRC-invalid in the corpus accounting.

The 48 logical-frame PHY strata sum exactly to 5,378,763 logical frames and 506,441 multi-gateway logical frames. The sole reception stratum absent from the logical-frame table is SF7 / 868.3 MHz / 250 kHz: 65,498 recorded receptions, all CRC-invalid. No causal explanation is inferred.

Prepared the unified matrix assembler over the four reviewed source artifacts: 52 Vomhoff + 80 InSecTT + 20 LR-FHSS + 246 LoED = 398 records, 14 empirical metric IDs and one shared InSecTT voltage parameter. Added explicit target-gap and non-metric-gap policies; publication MCDA and missing-evidence imputation remain blocked.


## 2026-08-11 — Stage-3 uncertainty contract prepared (v0.1.16)

Reviewed production v0.1.15 outputs: 398 evidence records, 14 empirical metric IDs, 20 boundary signatures and one shared parameter. Dataset/metric counts, boundary totals and the 5 x 4 target-gap matrix are internally consistent. No target-only metric is materialised and LoED retains null independent-unit counts.

Stage 2 core-four evidence modelling is therefore accepted as complete.

The review also showed that a generic mixed-model `study_id` random effect would be unjustified: study identity is confounded with technology, implementation and measurement boundary. The Stage-3 policy instead maps each of the 14 dataset/metric groups to its defensible uncertainty regime.

Expected calibration status under the contract:
- 2 replicated Vomhoff metric families: calibratable now from physical runs;
- 6 InSecTT/LR-FHSS metric families: external repeatability evidence/prior required;
- 2 LoED RSSI/SNR metric families: grouped hierarchical artifact required;
- 4 descriptive quantities/contrasts: descriptive only.

Vomhoff structured device/implementation metadata remains absent in retained primary-source Stage-2 materials and is preserved as unknown rather than filled from secondary descriptions. No uncertainty sampling or MCDA is produced.


## 2026-08-11 — Vomhoff Stage-3A empirical calibration prepared (v0.1.17)

Reviewed the production v0.1.16 uncertainty audit. All 398 evidence records map cleanly to 14 uncertainty specifications; no unresolved dependence or shared-parameter references exist. Only the two replicated Vomhoff metric families are immediately empirically calibratable. Single-trace InSecTT/LR-FHSS population variability remains unidentified, and LoED RSSI/SNR still requires grouped hierarchical calibration.

Stage-3A therefore returns to `logical_phase_observations.parquet` and uses `physical_run_id` as the only replication unit. The calibration materialises observed run-level energy/duration samples and marginal conditional dispersion for every Vomhoff evidence record. Stage-2 means and `n_independent_units` must reconcile exactly or the run fails.

A final joint bootstrap is deliberately not produced in this version. Candidate resampling blocks and pairwise run-set overlaps are audited first because phase groups may not share identical run sets. This preserves within-run dependence without silently assuming a rectangular repeated-measures design. Pairwise Pearson/Spearman values are diagnostics only; empirical block resampling remains the preferred future dependence-preserving mechanism.

No parametric distribution, generic study/device random effect, default CV/SD, publication uncertainty sample or MCDA ranking is authorised.


## 2026-08-11 — Vomhoff Stage-3B resampling policy resolved (v0.1.18)

Reviewed production Stage-3A outputs: 52 evidence records reconcile exactly to Stage 2; 192 physical/source runs yield five candidate blocks. Four blocks are rectangular. The only partial block is NB-IoT/MQTT, where `Data Download` has 44 runs and every other record has 45; overlap is 97.78%.

This structure does not justify deleting the 45th run from all other phases. The Stage-3B builder therefore resamples the 45-run union as physical clusters and preserves the observed missing `Data Download` value. The same run-index draw is shared across every record within the block, retaining multivariate run dependence.

The output is a nonparametric distribution of conditional phase means with deterministic block-specific seeds. Replicate IDs are intentionally local to a block, because cross-block pairing/dependence is not identified. No parametric family, cross-study random effect or publication MCDA is enabled.

### 2026-08-11 — Stage-3C LoED grouped calibration

Decision: build LoED uncertainty inputs from complete source-day blocks rather than individual reception rows. The primary materialised unit is source day × gateway × exact PHY stratum. RSSI/SNR paired moments are retained, and Stage-2 means/counts are used as frozen reconciliation checkpoints. No IID assumption is attached to reception rows, gateway-day cells or days. Temporal dependence is diagnosed before selecting any bootstrap or hierarchical model.

### 2026-08-11 — LoED Stage-3C production review and temporal-campaign decision

Reviewed the Stage-3C production artifacts. The grouped calibration reconciles exactly with Stage 2 and preserves 11,262,834 paired RSSI/SNR observations in 22,347 source-day × gateway × PHY cells. Between-cell variance is non-negligible (RSSI fraction 0.086–0.789; SNR 0.020–0.809), so row-IID uncertainty remains invalid.

The temporal review found that the 188 source days are not one continuous sequence. They form 57 consecutive days from 2019-02-08 through 2019-04-05, followed by a 386-day gap, then 131 consecutive days from 2020-04-25 through 2020-09-02. Raw lag-1 daily-PHY correlations are frequently high, with absolute values up to approximately 0.989. Daily gateway coverage varies between two and five observed gateways.

Decision: do not authorise IID day bootstrap or a moving-block sampler across all 188 days. v0.1.20 will perform a campaign-aware nonstationarity audit: multi-lag raw/detrended ACF, gateway-set transitions/coverage and descriptive 2019-vs-2020 RSSI/SNR shift. Block length and any stochastic LoED sampler remain pending that production audit.

### 2026-08-11 — LoED Stage-3D production review: gateway composition confounds campaign shift

Reviewed the completed two-campaign temporal audit. The 188 source days split into 57 days in 2019 and 131 days in 2020, separated by 386 days. Detrended temporal persistence remains material, especially for campaign-2 SNR. More importantly, infrastructure support changes substantially: campaign 1 observes 6 gateways, campaign 2 observes 5, and only 2 gateway IDs are shared (union 9; Jaccard 2/9). Full-campaign RSSI shifts therefore cannot be labelled temporal/environmental effects without further support analysis.

Decision: do not select a block length yet. Add a same-gateway/equal-shared-gateway sensitivity audit using the existing compact gateway-day-PHY artifact. Treat all resulting campaign-shift comparisons as descriptive and retain the campaigns as fixed observed acquisition contexts. No causal gateway-composition decomposition, campaign random effect or independent gateway bootstrap is authorised.


### 2026-08-11 — Stage-3E review and Stage-3F design

- Reviewed gateway-composition sensitivity for the two LoED campaigns.
- Full-campaign shifts are materially confounded by gateway support; only 2/9 gateway IDs are shared.
- Common-gateway RSSI shifts are heterogeneous in sign/magnitude, so campaigns are retained as fixed deployment scenarios rather than a random campaign population.
- Next calibration step: within-campaign source-day moving-block sensitivity at 3, 7 and 14 days; no block length selected in advance.


### 2026-08-11 — LoED Stage-3F review and Stage-3G robustness-family decision

Reviewed production 3/7/14-day within-campaign moving-block sensitivity. No single block length is stable enough to justify selection as the unique publication sampler. The 3-day model is systematically narrower; 14-day uncertainty is materially wider in most campaign/metric aggregates, with additional stratum-level heterogeneity. Non-circular edge weighting produces visible raw bootstrap location bias that increases with block length.

Decision: close the identifiable LoED RSSI/SNR uncertainty layer as a **scenario-indexed robustness family**, not as one probability distribution. Preserve the two acquisition campaigns as fixed deployment scenarios and the 3/7/14-day block lengths as unweighted model assumptions. Materialise joint centered draws for future bridge-model sensitivity, retain raw bias diagnostics, and report exact source-day support for every PHY stratum. Publication-wide stochastic sampling remains blocked by the InSecTT/LR-FHSS single-trace gaps.


### 2026-08-11 — Stage-3G closure and Stage-3H single-trace evidence review

Reviewed Stage-3G production artifacts. The LoED robustness family contains two fixed campaigns x three unweighted block-length assumptions, 1.47M joint RSSI/SNR draw rows, exact Stage-3F reconstruction and source-day support diagnostics. No single block length or scenario probability is introduced. LoED is therefore closed for Stage 3 as a scenario-indexed robustness family rather than one population distribution.

Targeted primary-source review then focused on the six single-trace InSecTT/LR-FHSS metric families. InSecTT reports PPK II measurements sampled at 100 kS/s and averaged over approximately 60 s but provides no independent replicate-run dispersion. LR-FHSS reports several individual transmission processes with negligible differences, but no repeat count or numerical SD/CV/CI. Result: zero defensible numerical population priors are identified.

A metadata discrepancy was also resolved. The LR-FHSS paper identifies Keysight N6705A as the DC power-analyzer hardware; the Zenodo record labels 14585A as a power analyzer, whereas Keysight identifies 14585A as Control and Analysis Software. STACKWISE now represents N6705A as measurement hardware and 14585A as acquisition software while preserving the original Zenodo label in provenance. No empirical values change.

Decision: do not continue literature searching merely to force a numerical CV. Retain the single-trace population-variability gap explicitly. If a later decision-model sensitivity experiment needs an envelope, it must be labelled a researcher-selected robustness assumption, not an evidence-derived prior.

## 2026-08-11 — Stage-3 closure (v0.1.25)

Reviewed Stage-3H production outputs. Six InSecTT/LR-FHSS single-trace metric families remain `n=1`, with zero source-backed numerical population priors. LR-FHSS instrumentation metadata is reconciled as N6705A measurement hardware plus 14585A control/analysis software, with no numerical evidence change.

Stage 3 is closed using mixed uncertainty semantics: empirical nonparametric Vomhoff uncertainty, unweighted LoED deployment/model robustness scenarios, explicit single-trace epistemic gaps for InSecTT/LR-FHSS, and descriptive-only nonpopulation metrics. Residual gaps remain machine-readable and are not hidden by default distributions.

Next work item: Stage 4 layer-aware end-to-end stack definition and hard compatibility constraints. No MCDA rankings are authorised.


## 2026-08-11 — Stage 4A started

Stage 3 was accepted as closed with explicit non-identifiability. Implemented the first Stage-4 contract for graph-based end-to-end stack composition and hard feasibility. Synthetic fixtures validate compositional security, explicit gateway mediation, incompatibility on interface mismatch, and tri-state hard constraints. Real protocol catalog population is intentionally deferred to a primary-source-verified Stage 4B step.


## 2026-08-11 — Stage 4B primary-source component catalog

Validated the Stage-4A contract and performed a bounded primary-source standards review. Materialised 25 components (24 verified plus EPhESOS pending), 23 primary sources, 23 verified claims, 32 positive compatibility edges, 8 evidence-alignment records and 6 explicit gaps. Added OR-group requirements for multi-binding protocols. Structural verification stacks confirm Thread/CoAP/DTLS, NB-IoT/TLS/MQTT, LoRaWAN-LR-FHSS/LwM2M Non-IP and BLE-IPSP/CoAP paths while rejecting direct UDP over bare LoRaWAN or bare BLE. No ranking or preference model is introduced.


### 2026-08-11 — Stage 4C

Materialised nine non-exhaustive verified reference stacks. Added verified-edge gating and candidate-level evidence-support records. Seven candidates retain some core-four component/access alignment, two cellular Non-IP candidates have none, and zero candidates have full end-to-end empirical support. Deferred BLE/UWB/EPhESOS remote-service families remain explicit rather than being filled by assumptions.

## 2026-08-11 — Stage 4D benchmark hard-feasibility screen

Materialised six synthetic quantitative benchmark scenarios and evaluated the frozen nine
verified Stage-4C candidates. Production checkpoints are 54 screening rows: 12 feasible under
declared hard predicates, 33 infeasible and 9 unresolved. Twenty-seven hard-predicate results
are unknown in total, but only nine are decision-blocking. The unresolved blockers are: one
Thread latency capability in the industrial scenario, six cellular mobility capabilities in
the asset-tracking scenario, and two LoRaWAN common whole-device per-report energy capabilities
in the remote-agriculture scenario. No score/ranking was computed.

## 2026-08-11 — Stage 4E targeted decision-blocker review

Reviewed the nine Stage-4D decision-blocking unknowns against primary standards and existing core-four boundaries. The six cellular mobility blockers were traced to an underspecified scenario predicate rather than one missing universal mobility value. Replaced the forward asset-tracking benchmark with two explicit mobility-semantics variants: idle-reselection-sufficient and connected-handover-required. No variant is privileged.

Resulting refined screen: 7 scenarios × 9 candidates = 63 rows; 21 feasible, 39 infeasible, 3 unresolved. Remaining blockers are Thread stack-level 500-ms latency and two LoRaWAN whole-device per-report energy predicates. No latency or energy bridge was invented.

## 2026-08-11 — Stage 4F feasibility closure

Reviewed the three Stage-4E blockers. The remaining uncertainty is not merely missing a scalar number: the frozen candidate definitions are under-parameterised for these performance predicates. Thread latency depends on device role/sleep behaviour, topology/path and retry behaviour; LoRaWAN report energy depends on operating mode and whole-device accounting boundary.

Stage 4 is closed at 21 feasible / 39 infeasible / 3 unresolved rows. No remaining blocker is resolved from existing core-four evidence. Added a diagnostic over the eight LR-FHSS incremental transaction-energy records; three measured 4-byte radio profiles exceed 0.2 J, but none resolves the 16-byte whole-device benchmark because payload and boundary differ. Next: Stage 5A operating-profile and bridge contracts, still without preference scoring.


## 2026-08-11 — Stage 5A contract materialisation

Accepted Stage-4F closure and preserved the 21/39/3 feasibility matrix. Introduced explicit operating-profile provenance and bridge contracts for Thread latency, classical-LoRa whole-device energy and LR-FHSS radio-to-whole-device energy. Two Stage-4F payload requirements are satisfied directly by the synthetic benchmark scenario; 20 required profile fields remain unresolved. All three bridges are intentionally blocked.

## 2026-08-11 — Stage 5B LR-FHSS model gate

Audited the Sanchez-Vital et al. LR-FHSS radio-state model against the project's own validated 4-byte traces before allowing a 16-byte benchmark extrapolation. The publication Table-6 timing values are reproduced under an explicit table-consistent payload-duration convention; the rendered Eq. (6) discrepancy is retained rather than silently corrected.

Unconfirmed DR8--DR11 source traces reproduce within 0.56--1.39% absolute relative energy error. Confirmed traces do not: model errors are approximately 43--52%, and the measured confirmed TX plateau is approximately 50 mA versus the published 25.7 mA state current. The cause is not identified, so confirmed extrapolation is blocked.

For 16-byte unconfirmed variants, the incremental radio transaction model yields ~0.2044 J for DR8/DR10 and ~0.1141 J for DR9/DR11. The former can only support a one-sided infeasibility result for an explicitly matched profile variant; the latter remain whole-device unresolved. No DR is selected post hoc and the frozen 21/39/3 Stage-4 matrix is unchanged.

### 2026-08-11 — Stage 5C: versioned LR-FHSS profile variants

Materialised the complete eight-cell DR8–DR11 × confirmed/unconfirmed family within the explicitly source-aligned LR1121/+14 dBm model domain. Introduced a distinction between whole-device profile completeness and monotone lower-bound decision sufficiency. Only unconfirmed DR8/DR10 are conditionally infeasible at the variant level; no generic candidate update, variant weighting or ranking is authorised.



### 2026-08-11 — Stage 5D selection-identifiability decision
Reviewed official LoRaWAN material for data-rate control and message confirmation semantics. The standards provide mechanisms for ADR/LinkADRReq and separate confirmed/unconfirmed message types, but the synthetic agriculture benchmark lacks deployment-specific ADR/server policy, observed/assigned DR history and application confirmation policy. Decision: freeze DR8–DR11 × confirmed/unconfirmed as an unweighted source-domain robustness family; do not select or weight variants from energy results.

### 2026-08-12 — Stage 5E decision-readiness audit
Implemented `v0.1.36` decision-readiness auditing over the frozen Stage-4 matrix. The audit covers 24 non-infeasible scenario-stack pairs and 120 canonical target cells. No target is yet decision-ready because no canonical target bridge has been materialised and lifecycle cost is absent. The highest-leverage bridge using current empirical evidence is cellular IP application-report energy from Vomhoff: 10 feasible candidate incidences across three scenarios. Lifecycle cost remains a mandatory separate evidence contract. No ranks, weights, publication MCDA or fleet optimisation were enabled.

## 2026-08-12 — Stage 5F cellular-IP report-energy transfer audit — v0.1.37

Stage 5E prioritised the Vomhoff cellular-IP energy bridge because it touches 10 feasible candidate incidences across three scenarios. Re-auditing the retained source context before numerical composition exposed three structural transfer gaps: the retained data-transfer payload is 1024 B while benchmark payloads are 64/200 B; LTE-M has only HTTP evidence and no retained MQTT context; and the source transaction Idle/Standby timing does not identify a 60/900 s reporting-cycle tail or PSM/eDRX/sleep policy.

Stage 5F therefore does not write the canonical report-energy target. It defines a narrower source-boundary diagnostic: a whole-device active transaction component consisting of Connection Establishment + Data Request + Data Download + Postprocessing. When the Stage-3B bootstrap artifact is present, component draws are composed within the same experimental block/replicate to preserve phase dependence. Three source reference contexts are supported (NB-IoT/HTTP, LTE-M/HTTP, NB-IoT/MQTT). The source component is explicitly not a candidate-stack report-energy estimate.

All 10 feasible cellular-IP incidences remain structurally blocked for the canonical target; 10/10 have payload mismatch and 0/10 exact source application-context alignment. No HTTP→CoAP transfer, NB-IoT→LTE-M MQTT correction, payload scaling, reporting-tail scaling, score or rank is introduced.

### 2026-08-12 — Stage 5G targeted cellular transfer-evidence review

Reviewed a targeted external NB-IoT/LTE-M state/procedure energy model (Sørensen et al., IEEE IoT Journal 2022, DOI `10.1109/JIOT.2022.3152173`) against the exact Stage-5F gaps. The source validates that payload, transmit periodicity, coverage/network parameters and low-power states belong in a report-cycle model, but it does not provide an absolute bridge to the retained Vomhoff whole-device source-active component. Its boundary is modem-only and quantitative application to a new device requires device-specific state characterization.

Stage 5G therefore upgrades payload/report-cycle effects from `missing structure` to `structurally supported / robustness-only`, while keeping exact upper-layer transfer and absolute calibration unresolved. No candidate report-energy values are generated and publication MCDA remains blocked. Next priority: matched bridge evidence or explicitly labelled model robustness; lifecycle-cost contract in parallel.

## 2026-08-12 — v0.1.39 / Stage 5H lifecycle-cost accounting contract

- Froze the first-slice lifecycle-cost boundary as five-year cumulative differential cost in constant 2026 EUR.
- Separated per-device CAPEX/recurring service from shared private infrastructure CAPEX/OPEX; shared costs may not be allocated without an explicit deployment scale.
- Preserved two urban LoRaWAN ownership cases as unresolved instead of inferring public/private service semantics.
- Explicitly prohibited `configs/fleet.yml` smoke prices from publication analysis.
- Deferred battery-replacement and energy-commodity costs until a common whole-device energy/lifetime model exists, preventing double counting.
- Stage 5H intentionally materialises no numerical market prices; targeted dated evidence collection is the next step.

## 2026-08-12 — v0.1.40 / Stage 5I dated cellular cost evidence

- Materialised dated price evidence for the ten feasible IP-cellular incidences using a single dual-mode Quectel BG95-M3 reference module, standard 1NCE SIM and the official 1NCE prepaid IP-connectivity tariff.
- Kept hardware price identical across NB-IoT/LTE-M candidates because the selected reference module supports both RATs; no artificial RAT price delta is introduced.
- Preserved the 10-year prepaid tariff as a full upfront cash payment rather than prorating it to the five-year analysis horizon.
- Did not transfer the IP tariff to seven Non-IP/NIDD cellular candidates because official NIDD service support was not established by the reviewed tariff/support sources.
- Added a tariff-volume identifiability audit. The source's 1-kByte measurement/billing granularity is retained as metadata but is not interpreted as per-report rounding because the aggregation interval is not specified.
- Materialised five-year application-payload volumes of 35.064 MB (900-s smart meter) and 168.3072 MB (60-s tracking). Both are below the base 500-MB allowance at payload-only level, but full transport/session usage and therefore TopUp need remain unresolved.
- Materialised EUR 46.41 as the source-backed hardware + standard-SIM + base-plan reference cash-cost floor for all ten IP-cellular incidences, explicitly marked non-canonical.
- Canonical lifecycle-cost targets remain 0 ready; next closure is a shared IP session/transport profile contract usable by both cost and cellular-energy bridges.

## 2026-08-12 — v0.1.41 / Stage 5J

Implemented a common cellular-IP session/transport profile contract shared by tariff-volume and report-energy work. The ten feasible IP-cellular incidences are split evenly between CoAP/DTLS/UDP and MQTT/TLS/TCP. LwM2M Send is frozen as the benchmark telemetry operation and payload semantics are frozen at the pre-LwM2M application boundary.

Materialised 200 field records: 70 known/frozen and 130 unresolved. The unresolved set is intentionally explicit and includes payload encoding, IP version, security-context lifecycle, re-establishment/resumption cadence, retry behaviour and binding-specific record/topic/session dimensions. No exact traffic volume, TopUp count or report-energy target is produced.

Reviewed primary standards and refreshed the component-catalog TLS reference to RFC 9846 and the LwM2M transport reference to 1.2.2. Re-ran Stage-4B component-catalog validation with unchanged structural checkpoints.

Next: Stage 5K parameterised protocol-envelope variants; use the same variants for tariff-volume and energy sensitivity rather than maintaining separate assumption sets.

## 2026-08-12 — v0.1.42 / Stage 5K

- Converted the Stage-5J unresolved cellular-IP session fields into nine deterministic sensitivity anchors rather than selecting one guessed profile or enumerating the full Cartesian product.
- Materialised 90 variants across ten feasible IP-cellular profiles: 45 CoAP/DTLS/UDP and 45 MQTT/TLS/TCP. All Stage-5J unresolved fields receive an explicit assignment in every variant.
- Assigned no variant probability, empirical frequency or stakeholder weight. The anchors are standards-bounded endpoints or synthetic stress/reference conventions only.
- Preserved all three LwM2M Send representations in the compact family and both IP families; retained CoAP CON/NON and MQTT QoS 0/1/2 sensitivity.
- Added explicit persistent, per-report resumption, per-report full re-establishment and one-retry sensitivity states so tariff-volume and report-energy work use the same session assumptions.
- Materialised raw aggregate tariff headroom from the Stage-5I 500-MB allowance: approximately 2651.93 B/report beyond the 200-B application payload for 900-s smart metering and 126.13 B/report beyond the 64-B application payload for 60-s tracking. The calculation is not billing-rounding adjusted and is not a tariff-sufficiency conclusion.
- Kept exact wire-volume, tariff TopUp count, canonical report energy and publication MCDA disabled.

Next: Stage 5L standards-based byte accounting, separating steady-state LwM2M Send traffic from security/session establishment, resumption, keep-alive and retry increments.


## 2026-08-12 — v0.1.43 / Stage 5L standards-based wire-volume accounting

- Implemented byte-level accounting for all 90 Stage-5K cellular-IP variants using current OMA/IETF/OASIS protocol structures.
- Preserved the Stage-5J payload boundary: 64/200 B remain pre-LwM2M application data and are not silently substituted for serialized LwM2M CBOR/SenML CBOR/SenML JSON length.
- Added two separate quantities: a strict primary-exchange known-component transport floor and a fuller deterministic Stage-5K anchor accounting.
- Kept MQTT pure-TCP ACK/segmentation effects, security establishment/resumption and billing-rounding aggregation explicit rather than assigning default bytes.
- Found 27 MQTT/TLS tracking variants whose strict raw transport-component floor alone exceeds the nominal 500-MB allowance over five years; baseline compact MQTT is 205 B/report = 539.109 MB/5y before serialized LwM2M data.
- Did not promote the raw-volume exceedance to exact billed volume or TopUp count because the reviewed operator source does not state the nearest-1-kByte aggregation interval.
- Exact wire volume remains 0/90 and report-energy transfer remains prohibited. Next: payload-serialization contract/bounds plus security-session increment envelopes.


## 2026-08-12 — v0.1.44 / Stage 5M LwM2M serialization surrogate envelope

- Preserved the 64/200-B pre-LwM2M boundary and declined to infer a real application Object/Resource model.
- Introduced two synthetic Opaque-Resource serialization surrogates under OMA test Object ID 42769: one Resource and three Resources with deterministic byte splitting.
- Materialised exact serialization sizes for LwM2M CBOR, SenML CBOR and SenML JSON, then propagated them through Stage-5L transport accounting for 180 variant×surrogate rows.
- Observed 57/180 strict raw surrogate rows above the nominal 500-MB allowance and 69/180 above it under deterministic anchor accounting.
- Confirmed that all MQTT/TLS 60-s tracking rows remain above the nominal raw allowance. CoAP/DTLS tracking is serialization-shape sensitive: the one-Resource SenML-JSON surrogate remains below the nominal allowance (~478.624 MB/5y), while the three-Resource surrogate exceeds it (~594.335 MB/5y).
- Kept canonical application serialization, billing aggregation, session handshake/resumption traffic, MQTT pure TCP ACK/segmentation, exact TopUp count and report energy unresolved.

Next: Stage 5N security-session and TCP-control increment envelopes.

## 2026-08-12 — v0.1.45 / Stage 5N security-session and MQTT/TCP control envelope

- Added two deterministic, probability-free PSK session/control envelope designs over all 180 Stage-5M serialization rows, yielding 360 rows.
- Derived current TLS 1.3 PSK record-size surrogates: 311 B for compact `psk_ke`/16-B identity and 449 B for expanded `psk_dhe_ke`/X25519/64-B identity before TCP/IP.
- Derived DTLS 1.3 PSK session surrogates including final-flight ACK and UDP headers: 431 B compact and 589 B expanded.
- Added minimal MQTT 5 CONNECT/CONNACK traffic for per-report TLS/TCP rebuilds and a zero-versus-one standalone TCP ACK-per-modeled-data-segment sensitivity.
- Result: 162/360 envelope rows exceed the nominal raw 500-MB allowance; at the 180-row source level, 81 robustly exceed under both E0/E1 and 99 remain within under both; zero rows flip solely due to E0/E1.
- All 54 MQTT/TLS 60-s tracking source rows remain above the nominal raw allowance under both session/control surrogates.
- No canonical security handshake, TCP ACK count, billed volume, TopUp count or report energy is claimed.
- Transport-detail expansion is frozen by default. Next: Stage 6A first decision-ready slice consolidation.

## 2026-08-12 — v0.1.46 / Stage 6A first decision-slice consolidation

- Froze the Stage-5 transport/accounting sequence after v0.1.45 and added no new protocol-detail assumptions.
- Consolidated the 21 feasible candidates against five canonical targets, producing 105 criterion-readiness rows.
- Retained energy/report and lifecycle cost as the two mandatory soft targets for the first decision slice; latency/coverage remain hard/contextual and delivery probability remains deferred.
- Found 0/42 mandatory soft-target rows ready, 10 context-only lifecycle-cost rows and 32 blocked mandatory rows; therefore 0/21 feasible candidates are ready for publication scoring.
- Collapsed Stage-5N tariff-volume robustness to the ten feasible IP-cellular candidates: 4 robust-within, 3 robust-exceed and 3 protocol-envelope-sensitive.
- Selected the four IP-cellular candidates in `asset_tracking_periodic_cross_cell` as a development-only 2×2 subset for closing the remaining inputs. This does not exclude the two feasible Non-IP candidates from the full scenario and does not authorise a scenario-wide optimum claim.
- Stage 6B priorities: matched whole-device cellular report energy first; explicit EUR lifecycle-cost robustness family second. No transport-detail reopening without a material methodological error.

## 2026-08-12 — v0.1.47 / Stage 6B matched cellular-energy audit

Reviewed the closest primary empirical/model sources for the 64-B/60-s periodic-tracking IP-cellular subset. No public source simultaneously supplies NB-IoT and LTE-M, both candidate upper-layer bindings, a 60-s report-cycle regime and the required whole-device boundary. Recorded the negative result and froze a minimal matched repeated-measures experiment instead of scaling Vomhoff or importing modem-only model values as whole-device energy.

## 2026-08-12 — Stage 6C lifecycle-cost robustness family (v0.1.48)

- Rechecked dated 1NCE and DigiKey evidence.
- Added official 1NCE Platform-2.0 evidence that usage rounding is per PDP session at session end.
- Replaced the previous generic billing-aggregation blocker with two explicit unweighted deployment anchors: persistent PDP and one PDP session per report.
- Retained all 144 Stage-5N rows for the four periodic-tracking IP-cellular development candidates.
- Crossed them with 2 billing anchors and 2 procurement anchors, creating 576 lifecycle-cost family members.
- Materialised four candidate cost summaries.
- Cost criterion is now `READY_ROBUSTNESS_FAMILY` for 4/4 preferred candidates; energy remains blocked.
- No MCDA rankings were run and no probability weights were attached to the robustness family.

## 2026-08-12 — Stage 6D synthetic nested decision-engine dry run (v0.1.49)

- Aligned the 576 Stage-6C family rows into 144 shared cost states across the four preferred periodic-tracking IP-cellular candidates.
- Added three synthetic paired energy fixtures with 64 common-block draws each and opposite RAT-ordering/tie stress cases.
- Added 21 deterministic energy-vs-cost preference anchors without probability semantics.
- Implemented fixed external value transformations, fractional tie rank mass and nested envelope reporting.
- Produced 9,072 conditional state×weight×fixture evaluations, 252 weight-sensitivity rows and 12 fixture-level rank envelopes.
- Passed 13 engine invariants, including mass conservation, alternative-permutation invariance, cost symmetry preservation, RAT-order reversal fixtures and preference-weight sensitivity.
- No real candidate ranking was run; Stage-6B matched whole-device energy remains the only publication-critical blocker for the preferred subset.


## 2026-08-12 — v0.1.50 benchmark release-candidate decision

Reframed the harmonised multi-source evidence resource as an explicit scientific output. The project does not require a new laboratory campaign to justify the benchmark: its contribution is the provenance-preserving transformation of four independent real measurement datasets into a common evidence model while retaining incompatible boundaries and non-identifiability. Added a compact layered release builder and kept raw upstream archives outside the release.

## 2026-08-12 — v0.1.50.post1 release-builder correction

- Found a stale-artifact mismatch during the first full local RC build: the pre-refinement Stage-4D scenario CSV contains 6 rows, while the frozen Stage-4E benchmark contains 7 scenarios after the asset-tracking mobility split.
- Corrected the release builder to materialise the canonical refined scenario table from the Stage-4 YAML and Stage-4E refinement logic.
- Scientific content is unchanged: 7 scenarios, 9 candidate stacks, 63 feasibility rows, 21 feasible / 39 infeasible / 3 unresolved.

## 2026-08-12 — v0.1.50.post2 benchmark release QA

- Reviewed the first successful full local `v1.0.0-rc1` build: 25 table/data artifacts, ~2.95 MB, 398 canonical evidence records, 4 core sources, 7 scenarios, 9 stacks and frozen 21/39/3 feasibility counts.
- Found a release-manifest presentation defect: Parquet row counts were reported as zero although the files contained data. Replaced empty-column Pandas counting with Parquet metadata counting.
- Added a release QA gate for canonical evidence equivalence across CSV/JSONL/Parquet, complete 7×9 feasibility coverage, licence status, checksum coverage and raw-archive exclusion.
- Added standalone self-description assets: benchmark dataset card, eight canonical schemas and four source dataset cards.
- Kept benchmark scientific content unchanged. The final licence for STACKWISE-authored benchmark material remains a manual release-owner decision; Zenodo upload is not yet authorised.

## 2026-08-12 — v0.1.51 final benchmark release decision

- Approved CC BY 4.0 for STACKWISE-authored benchmark material; repository software remains Apache-2.0.
- Completed the four-source scientific attribution audit using source/associated-publication metadata and froze creator/DOI/licence/derivation-role metadata in `datasets/benchmark_source_attribution.yml`.
- Promoted the benchmark from `1.0.0-rc1` to `1.0.0` without changing scientific table content or frozen counts.
- Added final release build/QA tooling. Publication MCDA remains explicitly out of scope for the dataset release.


## 2026-08-13 — v0.1.52 Experiment 1 closed

Ran the first publication-oriented benchmark experiment on frozen STACKWISE Benchmark v1.0.0. Four completely observed structural preferences were enumerated over a 35-anchor deterministic simplex and applied both before and after hard-feasibility filtering. Across 245 scenario-anchor evaluations, score-first top sets contained at least one hard-infeasible candidate in 193 and were entirely infeasible in 159. For the five scenarios with feasible alternatives, contamination remained 142/175 and entirely infeasible top sets 115/175. The two no-feasible scenarios generated 70/70 apparently ranked score-first outcomes, while feasibility-first correctly returned no decision. No missing empirical soft criterion was imputed.


## 2026-08-13 — v0.1.53 / Experiment 2 evidence admissibility

Experiment 2 tested whether source provenance grade can stand in for decision admissibility. It cannot in the frozen core-four benchmark: all four sources are Grade A and all 398 canonical records survive every A/B/C/D source-grade threshold. At the canonical target boundary, however, the 20 source×target relations contain 0 C0 direct, 5 C1 bridgeable, 1 C2 conditional and 14 missing relations.

The first-slice candidate audit overlays Stage-6C lifecycle-cost readiness onto Stage-6A. Of 42 required energy+cost cells, 4 are ready robustness-family cost cells, 6 are context-only cost cells, 10 carry structural energy-transfer support and 22 remain otherwise blocked. No feasible candidate is complete under authorised canonical/context evidence. A counterfactual rule that treats context+structural-transfer support as score-ready would make 10 candidates across 3 scenarios appear complete; explicit assumption priors make all 21 feasible candidates appear complete. These counts quantify assumption-driven decision-space inflation and are not candidate rankings.

## 2026-08-13 — Experiment 3 closed (v0.1.54)

Compared deterministic point collapse with three validated native uncertainty semantics. Vomhoff marginal bootstrap intervals preserve the source-level point ordering but show unequal precision; LoED temporal block choices leave point estimates fixed while changing uncertainty scale; paired Stage-6C cost states show no MQTT-cheaper reversal despite overlapping marginal ranges. No pooled epistemic probability or global ranking was introduced.


## 2026-08-13 — Experiment 4 accounting/cost simplification ablation

Aligned the periodic-tracking IP-cellular 2×2 subset onto 288 common traffic/billing states (576 rows after procurement expansion). The application-payload-only model reports 0/288 states above the nominal 500-MB allowance, while the frozen billing-aware reference reports 252/288. Intermediate counts are 144 transport-aware, 152 serialization-aware and 216 session/control-aware. Relative to billing-aware accounting, false-within counts are 252, 108, 100 and 36. Payload-only lifecycle-cost estimates understate the Stage-6C billing-aware result in 504/576 procurement-expanded rows, with median/max underestimation 50/100 EUR. No state-frequency probability is inferred.

## 2026-08-13 — v0.1.57 publication consolidation

Consolidated Experiments 1–4 into nine headline results and a claim-evidence matrix. The consolidation does not alter Benchmark v1.0.0 or any experiment output. It identifies five strong claims and three open claims, with fleet portfolio feasibility selected as the only recommended additional experiment for the broad article scope.

## 2026-08-13 — v0.1.57 Experiment 5

Implemented the final fleet portfolio experiment as hard-feasibility set cover. Strict serviceability is 5/7 scenario classes; the best single stack/technology/family covers 4/5, while complete strict coverage requires two elements. Minimum technology portfolios are LTE-M + LoRaWAN-LoRa or LTE-M + LoRaWAN-LR-FHSS; cellular + LoRaWAN is the unique minimum family portfolio. An unresolved-only sensitivity requires three elements for all seven scenarios and is not promoted to a feasibility claim.
