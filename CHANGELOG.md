# Changelog

## 0.1.61 — Public-repository hygiene and CI correction

- Removed the hidden local checkpoint directory `.stackwise_backups/` from the intended public tree and added it to `.gitignore`.
- Strengthened the public-repository audit so both `backups/` and `.stackwise_backups/` are rejected if staged.
- Replaced the fresh-clone GitHub Actions `pytest -q` step with an explicit 32-test self-contained public CI suite that does not require generated `results/` artifacts.
- Clarified that the complete local regression suite is run in the full research workspace after validated inputs/results have been materialised.
- Updated software citation/version metadata and Code Availability to public release `v0.1.61`.
- Benchmark v1.0.0 and Experiments 1–5 scientific results are unchanged.


## 0.1.60 — Public GitHub research-code release

- Prepared the repository for its first public GitHub release linked to STACKWISE Empirical Evidence Benchmark v1.0.0 (DOI: 10.5281/zenodo.21937093).
- Replaced the development README with a publication-facing reproducibility guide and final scope/limitation statements.
- Strengthened `.gitignore` so raw/derived local data, generated results/releases, backups, patch payloads, root diagnostic archives and manuscript files cannot be staged accidentally in a new repository.
- Added a fail-closed public-repository audit for staged files, common credential patterns, local research artifacts and oversized files.
- Added GitHub Actions source-only CI on Python 3.10 and 3.12.
- Added manuscript-ready code-availability and public-release guidance.
- Updated `CITATION.cff`, CodeMeta and optional Zenodo software metadata for the public code release.
- Benchmark v1.0.0, Experiments 1–5 and all scientific results remain unchanged.

## 0.1.59.post1 — Deposit attribution-gate bugfix

- Fix the Zenodo deposit packager to read the canonical final-release attribution record (`status`, not the obsolete test-only `review_status` key).
- Require consistent passed attribution state in `release_summary.json`, final QA checks, and `ATTRIBUTION_REVIEW.json`.
- Require the final attribution review to cover exactly the four frozen core sources.
- Add regression tests reproducing the real v1.0.0 release metadata shape.
- No benchmark tables, Experiment 1–5 outputs, publication claims, or Zenodo metadata content are changed.

## 0.1.59 — Deposit packaging and two-manuscript handoff

- Added fail-closed deterministic packaging for STACKWISE Empirical Evidence Benchmark v1.0.0.
- Deposit archive is generated only after final release QA and Zenodo-finalisation gates pass.
- Added archive SHA-256 sidecar and machine-readable deposit-package summary.
- Added Zenodo deposit checklist with explicit creator/authorship manual review gate.
- Added separate detailed outlines for the benchmark/data paper and STACKWISE methodology/results paper.
- Experimental programme remains closed at Experiments 1–5; Benchmark v1.0.0 scientific content remains frozen.

## 0.1.56 — 2026-08-13

- Added publication-result consolidation across frozen Experiments 1–4.
- Added machine-readable headline-result, claim-evidence, figure-plan and table-plan artifacts.
- Froze five publication-authorised claims and explicitly blocked global stochastic ranking, matched candidate-boundary cellular report-energy ranking and fleet-level claims without additional evidence.
- Recommended one final fleet portfolio feasibility/simplification experiment if the original heterogeneous-fleet contribution is retained.
- Kept Benchmark v1.0.0 and all Experiment 1–4 scientific outputs unchanged.

## 0.1.52 — 2026-08-13

- Closed publication-oriented Experiment 1: feasibility-first vs score-first on frozen Benchmark v1.0.0.
- Added a four-feature structural preference envelope and 35 deterministic simplex anchors with no probability interpretation.
- Added complete 7×35 scenario-anchor comparison, top-set feasibility summaries and two result figures.
- Added grid-resolution sensitivity at simplex steps 0.5, 0.25, 0.2 and 0.1 to verify that the ordering effect is not an artefact of the primary 35-anchor grid.
- Quantified score-first hard-infeasible top-set contamination (193/245 overall; 142/175 where feasible candidates exist) and false decisiveness in no-feasible scenarios (70/70 score-first top sets versus 0 forced feasibility-first decisions).
- Explicitly prohibited missing empirical soft-metric imputation and real-candidate MCDA interpretation for this experiment.

## 0.1.51 — 2026-08-12

- Froze `STACKWISE Empirical Evidence Benchmark v1.0.0` from the validated `v1.0.0-rc1` scientific content; no empirical or synthetic table values changed.
- Declared CC BY 4.0 for STACKWISE-authored benchmark material while preserving Apache-2.0 for repository software.
- Added a verified four-source scientific attribution manifest covering creators, dataset DOIs, related-publication DOIs, upstream licences and STACKWISE derivation roles.
- Added final benchmark `CITATION.cff`, Zenodo metadata draft, final dataset card, final build/audit scripts and final-release QA gates.
- Final release QA can now close the licence and attribution blockers and mark the package archival-deposit ready while publication MCDA remains unauthorised.

# Changelog

## 0.1.50.post2 — 2026-08-12

- Fixed Parquet row counting in `RELEASE_TABLE_MANIFEST.csv` by reading Parquet metadata instead of the false-zero `columns=[]` path.
- Added release-candidate QA covering CSV/JSONL/Parquet evidence equivalence, complete scenario×stack feasibility coverage, checksum coverage, licence gates, raw-archive absence and package self-description.
- Added a dataset card, eight canonical JSON schemas and four upstream dataset cards to the standalone RC package; these metadata assets are checksum-covered but kept outside the data-table manifest.
- Kept benchmark scientific content and benchmark version unchanged at `1.0.0-rc1`. The licence for STACKWISE-authored benchmark material remains an explicit manual finalisation decision; Zenodo upload remains unauthorised.


## 0.1.50.post1 — 2026-08-12

- Fixed the benchmark release-candidate builder to materialise the canonical seven-scenario Stage-4E definition instead of copying the stale six-row Stage-4D scenario CSV.
- Preserved the frozen 7 scenarios / 9 candidate stacks / 63 feasibility rows / 21 feasible / 39 infeasible / 3 unresolved checkpoint; no scientific result changed.
- Added post-materialisation row-count validation for transformed release artifacts.

## v0.1.49 — Stage 6D synthetic nested decision-engine dry run

- Added a new nested decision/robustness engine that keeps Stage-6C cost states and stakeholder-weight anchors unweighted instead of pooling them into unsupported probabilities.
- Aligned the 576 lifecycle-cost family rows into 144 shared cross-candidate cost states for the preferred 2×2 periodic-tracking subset.
- Added three paired synthetic energy fixtures (LTE-M advantage, exact RAT tie with binding trade-off, and NB-IoT advantage), 64 draws each, solely for regression validation.
- Added 21 deterministic energy-vs-cost preference anchors; Stage 6D reports min/max rank-acceptability envelopes across cost states and weights rather than a global rank probability.
- Added fixed external linear value functions, fractional rank-mass handling for exact ties, permutation-invariance checks, and an explicit Dirichlet helper that is not used by the Stage-6D audit.
- Passed 13 engine invariants; real energy, real candidate ranking and publication MCDA remain blocked pending the Stage-6B matched experiment.



## v0.1.48 — Stage 6C lifecycle-cost robustness family

- Materialised a 576-member unweighted five-year EUR lifecycle-cost family for the preferred periodic-tracking IP-cellular 2×2 subset.
- Added current 1NCE Platform-2.0 PDP-session billing-rounding evidence and explicit persistent-vs-per-report PDP-session anchors.
- Retained dated DigiKey BG95 quantity-1 and quantity-250 procurement observations without treating them as a market distribution.
- Marked `lifecycle_cost_eur` as `READY_ROBUSTNESS_FAMILY` for 4/4 preferred candidates while keeping whole-device report energy blocked.
- Added Stage-6C audit, artifacts, tests and documentation; publication MCDA remains disabled.

## v0.1.47 — Stage 6B matched cellular-IP energy evidence audit

- Audited four closest public cellular-energy sources against the 64-B/60-s whole-device candidate boundary.
- Found zero public sources matching both NB-IoT and LTE-M, both preferred IP bindings, the exact reporting regime and whole-device boundary.
- Froze a minimal matched experiment contract with four primary RAT×binding cells plus four context-reuse robustness cells on one dual-mode DUT.
- Defined one complete 60-s report cycle as the replication unit, a five-block randomized pilot, and preservation of failed cycles/retries.
- Kept candidate-boundary energy and publication MCDA blocked; handed the independent lifecycle-cost blocker to Stage 6C.

## v0.1.46 — Stage-6A first decision-slice consolidation

- Consolidates the frozen 21/39/3 Stage-4 feasibility matrix with the completed Stage-5 evidence, cost and transport/accounting artifacts without adding new protocol detail.
- Produces 105 feasible candidate×criterion readiness rows; the first slice retains energy/report and lifecycle cost as the only mandatory soft targets.
- Finds 0/42 mandatory soft-target rows ready, 10 context-only lifecycle-cost rows and 32 blocked rows; 0/21 feasible candidates are score-ready.
- Collapses Stage-5N tariff-volume robustness to ten feasible IP-cellular candidates: 4 robust-within, 3 robust-exceed and 3 protocol-envelope-sensitive.
- Selects the four periodic-tracking IP-cellular candidates as a development-only 2×2 subset; two feasible Non-IP candidates remain outside and no full-scenario optimum is claimed.
- Freezes further transport-detail expansion and hands Stage 6B two targeted gaps: matched cellular report energy and an explicit EUR lifecycle-cost robustness family. Publication MCDA/fleet optimisation remain blocked.

## v0.1.45 — Stage-5N security-session and MQTT/TCP control envelope

- Closes the planned transport/accounting refinement sequence with two deterministic standards-bounded PSK/session-control sensitivity surrogates over all 180 Stage-5M serialization rows, yielding 360 envelope rows.
- Sizes current TLS 1.3 PSK grammar surrogates at 311 B (`psk_ke`, 16-B identity) and 449 B (`psk_dhe_ke` + X25519, 64-B identity) before TCP/IP; treats these as benchmark anchors, not empirical traces.
- Sizes DTLS 1.3 PSK session surrogates including the mandatory final-flight ACK at 431 B and 589 B including modeled UDP datagram headers.
- Adds minimal MQTT 5 CONNECT/CONNACK traffic when TLS/TCP is rebuilt and a zero-versus-one standalone TCP ACK-per-data-segment sensitivity, preserving TCP ACK/segmentation non-identifiability.
- Finds 81/180 Stage-5M source rows above and 99/180 below the nominal raw 500-MB allowance under both session/control surrogates; no source row crosses the threshold solely because of the E0/E1 session-control choice.
- Keeps all 54 MQTT/TLS tracking source rows above the nominal raw allowance across both surrogates; security re-establishment each report strongly raises both CoAP and MQTT tracking traffic.
- Freezes further transport-detail expansion by default. Exact billed volume, canonical application serialization, report energy, publication MCDA and fleet optimisation remain blocked. Stage 6A now consolidates the first decision-ready slice.

## v0.1.44 — Stage-5M LwM2M Send serialization surrogate envelope

- Replaces Stage-5L's zero-payload serialization placeholder with exact lengths for two explicit synthetic Opaque-Resource surrogates under OMA test Object ID 42769.
- Evaluates one-resource and three-resource shapes carrying the same 64/200-B pre-LwM2M payload under LwM2M CBOR, SenML CBOR and SenML JSON, yielding 180 variant×surrogate rows.
- Keeps canonical real-application serialization unidentified: the benchmark surrogates do not claim to reconstruct an application object model.
- Finds all 54 MQTT/TLS 60-s tracking surrogate rows above the nominal raw 500-MB allowance at the strict primary-exchange layer.
- Demonstrates serialization-shape sensitivity for CoAP/DTLS tracking: the 64-B one-resource SenML-JSON surrogate is about 478.6 MB/5y, while the three-resource surrogate is about 594.3 MB/5y.
- Keeps security-session increments, MQTT pure TCP ACK/segmentation, billing rounding, exact TopUp count, report energy and publication MCDA unresolved; hands Stage 5N the final planned transport/control refinement.

## v0.1.43 — Stage-5L standards-based cellular IP wire-volume accounting

- Adds standards-based byte accounting for all 90 Stage-5K cellular-IP variants without equating pre-LwM2M 64/200-B application payloads with serialized LwM2M data.
- Separates a strict primary-exchange known-component transport floor from a fuller deterministic Stage-5K anchor accounting.
- Encodes CoAP `/dp` Send structure, DTLS 1.3 record fields, OMA MQTT Send/Generic Response CBOR wrappers, MQTT 5 PUBLISH/QoS control structure, TLS 1.3 records, UDP/TCP and IPv4/IPv6 header anchors.
- Keeps exact wire volume at 0/90 because LwM2M serialization remains unresolved; keeps MQTT pure-TCP ACK/segmentation and security establishment/resumption as explicit positive gaps.
- Finds 27 MQTT/TLS tracking variants whose strict raw transport-component floor exceeds the nominal 500-MB five-year allowance; compact persistent MQTT is 205 B/report = 539.109 MB/5y before serialized LwM2M payload.
- Preserves billing-rounding non-identifiability: raw-volume exceedance is not promoted to exact billed volume or TopUp count.
- Keeps canonical report energy, lifecycle cost, publication MCDA and fleet optimisation blocked; hands Stage 5M the LwM2M serialization and security-session increment problem.

## v0.1.42 — Stage-5K parameterised cellular IP protocol-envelope variants

- Materialises nine deterministic sensitivity anchors across all ten feasible IP-cellular profiles, yielding 90 variants (45 CoAP/DTLS/UDP and 45 MQTT/TLS/TCP).
- Assigns every Stage-5J unresolved profile field in every variant without selecting a "typical" deployment and without enumerating the full Cartesian product.
- Covers LwM2M Send representation, IPv4/IPv6, CoAP acknowledgement/header choices, MQTT QoS/topic/TCP choices, security-context persistence/resumption/re-establishment and a one-retry stress case.
- Assigns no variant probabilities, frequencies or stakeholder weights; all values remain standards-bounded or explicitly synthetic sensitivity anchors.
- Adds a raw aggregate tariff-headroom diagnostic: approximately 2651.93 B/report beyond a 200-B / 900-s application payload and 126.13 B/report beyond a 64-B / 60-s payload under the 500-MB allowance, before unknown tariff-accounting rounding.
- Keeps exact wire volume, tariff TopUp count, canonical report energy, publication MCDA and fleet optimisation prohibited.
- Adds Stage-5K policy, protocol-envelope module, audit artifacts, documentation and regression tests; hands Stage 5L a standards-based wire-accounting task.

## v0.1.41 — Stage-5J cellular IP session/transport profile contract

- Freezes one cross-binding telemetry benchmark semantic: LwM2M `Send`, with scenario payload bytes defined before LwM2M/transport/security overhead.
- Materialises 10 feasible IP-cellular session profiles (5 CoAP/DTLS/UDP, 5 MQTT/TLS/TCP) and 200 typed profile fields: 70 known/frozen, 130 unresolved.
- Keeps exact tariff volume and canonical report energy at zero ready rows; no TopUp count, handshake amortisation, QoS, CoAP confirmability, IP family, retry rate or security-session lifetime is silently inferred.
- Adds primary-source standards ledger showing why protocol overhead is variable rather than one constant.
- Refreshes TLS 1.3 primary reference from obsolete RFC 8446 to RFC 9846 and LwM2M Transport Bindings from 1.2.1 to 1.2.2; Stage-4B structural validation remains unchanged.
- Adds Stage-5J audit, gap-priority artifacts, documentation and regression tests. Publication MCDA/fleet optimisation remain prohibited.

## v0.1.40 — Stage-5I dated cellular cost evidence and tariff-volume audit

- Materialises dated price evidence for the ten feasible IP-cellular incidences using a dual-mode Quectel BG95-M3 reference module, standard 1NCE SIM and official prepaid IP-connectivity tariff.
- Uses one hardware reference for NB-IoT and LTE-M and therefore does not invent a RAT-specific module-price difference.
- Preserves the full 10-year prepaid tariff cash payment inside the five-year benchmark rather than silently prorating it.
- Blocks transfer of the IP tariff to seven Non-IP/NIDD cellular incidences because reviewed official service evidence does not establish that path.
- Adds a finite-tariff-volume audit without interpreting the source's 1-kByte measurement/billing granularity as per-report rounding; the aggregation interval is not specified.
- Materialises five-year application-payload volumes (35.064 MB for 900-s smart metering; 168.3072 MB for 60-s tracking) while leaving full transport/session usage unresolved.
- Materialises a non-canonical EUR 46.41 hardware + standard-SIM + base-plan cash-cost floor for all 10 IP-cellular incidences; TopUp need is not inferred without a session/transport profile.
- Keeps canonical lifecycle cost, publication MCDA and fleet optimisation blocked pending a common IP session/transport profile contract.

## v0.1.39 — Stage-5H lifecycle-cost accounting/evidence contract

- Freezes the primary lifecycle-cost boundary as five-year cumulative differential cost in constant 2026 EUR.
- Separates per-device CAPEX/operator service from shared private-infrastructure CAPEX/OPEX and prohibits shared-cost allocation without a frozen deployment scale.
- Classifies the 21 feasible incidences as 17 operator-managed, 2 private-owned and 2 unresolved urban-LoRaWAN ownership cases.
- Keeps `configs/fleet.yml` prices smoke-only and materialises zero publication market-price rows.
- Defers battery-replacement and commodity-energy costs until a common whole-device energy/lifetime model exists.

## v0.1.38 — Stage-5G cellular transfer-evidence admissibility

- Reviews a targeted validated external NB-IoT/LTE-M state/procedure model as structural transfer evidence.
- Confirms structural support for payload and report-cycle/state dependence across all 10 feasible IP-cellular incidences.
- Prohibits absolute recalibration of Vomhoff whole-device evidence from modem-only, device/network-specific external coefficients.
- Leaves exact upper-layer support and all canonical report-energy targets unresolved; publication MCDA remains blocked.

## v0.1.37 — Stage-5F cellular-IP report-energy bridge audit

- Audits all 10 feasible IP-cellular candidate incidences selected by Stage 5E.
- Materialises only a diagnostic 1 KB Vomhoff whole-device active transaction component (Connection Establishment + Data Request + Data Download + Postprocessing), preserving Stage-3B within-block bootstrap dependence.
- Records 10/10 payload mismatches (64/200 B benchmark versus 1024 B source) and 0/10 exact source application-context matches.
- Explicitly blocks HTTP→CoAP transfer, NB-IoT MQTT correction transfer to LTE-M, unvalidated payload scaling, and reporting-interval scaling of source Idle/Standby.
- Leaves canonical `expected_device_energy_per_application_report_j` at 0 ready rows; MCDA/fleet optimisation remain prohibited.
- Hands Stage 5G a targeted transfer-evidence problem: payload dependence, upper-layer context and reporting-cycle state accounting; lifecycle cost remains mandatory in parallel.

## v0.1.36 — Stage-5E decision-readiness and gap prioritisation

- Audits 24 non-infeasible scenario×stack pairs across five canonical decision targets (120 target cells) without scoring.
- Finds zero canonical target cells already ready and zero feasible candidates ready for the first energy/report + lifecycle-cost slice.
- Identifies the Vomhoff cellular-IP report-energy bridge as the highest-leverage existing-evidence gap (10 feasible incidences, three scenarios).
- Keeps lifecycle cost as a separate mandatory cross-cutting evidence contract and preserves all MCDA/fleet prohibitions.

## v0.1.35 — Stage-5D LR-FHSS variant-selection identifiability and robustness closure

- Audits whether the eight Stage-5C LR-FHSS variants can be selected from standards/deployment evidence rather than from their modeled energy outcome.
- Records primary/official LoRaWAN evidence for confirmed/unconfirmed message semantics, LinkADRReq/ADR control, regional-parameter context, and operator/device-profile coordination.
- Separates a standards control mechanism from deployment-specific selection evidence: ADR capability does not identify DR8–DR11 for the synthetic benchmark.
- Freezes the eight source-aligned variants as an unweighted robustness family with 2 conditional-infeasible and 6 unresolved variants; no variant is feasible.
- Preserves the generic LR-FHSS candidate as unresolved because the family is not exhaustive for generic hardware/TX-power/deployment conditions and no selection evidence or weights exist.
- Preserves the Stage-4 matrix (21/39/3) and keeps whole-device bridge, preference scoring, and MCDA prohibited.

## 0.1.33 - 2026-08-11

## v0.1.34 — Stage-5C versioned LR-FHSS operating-profile variants

- Materialises all eight source-aligned `DR8–DR11 × confirmed/unconfirmed` LR-FHSS operating-profile variants without selecting a preferred DR or confirmation mode.
- Separates whole-device profile completeness from decision sufficiency for a monotone one-sided component lower bound.
- Authorises conditional infeasibility only for explicitly matched unconfirmed DR8/DR10 variants whose validated radio-component lower bound exceeds the 0.2 J whole-device/report budget.
- Keeps unconfirmed DR9/DR11 unresolved for residual whole-device energy and all confirmed variants unresolved because the Stage-5B source-model reproduction gate failed.
- Preserves the generic LR-FHSS candidate as unresolved; no variant probabilities, deployment selection, whole-device numeric bridge, preference score or MCDA ranking are introduced.


- Added Stage-5B LR-FHSS source-model audit before any radio-to-whole-device bridge activation.
- Reproduces four published Table-6 LR-FHSS airtime rows under an explicit table-consistent payload-duration operationalisation while retaining the rendered Eq. (6) discrepancy as unresolved provenance.
- Validates the published radio-state model against all eight 4-byte source traces: all four unconfirmed configurations reproduce within the versioned 2% deterministic audit tolerance; all four confirmed configurations fail by >43% absolute relative energy error.
- Materialises the measured confirmed TX-plateau mismatch (~50 mA versus the published 25.7 mA state-model current) without assigning a causal explanation.
- Authorises 16-byte payload extrapolation only for unconfirmed radio-component variants; confirmed extrapolation remains blocked.
- Adds a one-sided 0.2 J component-bound diagnostic: unconfirmed DR8/DR10 exceed the whole-device budget on radio transaction energy alone, whereas DR9/DR11 remain whole-device unresolved.
- Preserves the generic LR-FHSS candidate as unresolved, the Stage-4 matrix at 21/39/3, the Stage-3 single-trace epistemic gap, and all preference/MCDA prohibitions.

## 0.1.32 - 2026-08-11

- Added Stage-5A typed operating-profile and evidence-to-decision bridge contracts for the three frozen Stage-4 hard-feasibility blockers.
- Materialised three scenario-specific partial operating profiles with 26 field records: 6 scenario-derived known context fields and 20 explicitly unresolved fields.
- Reconciled all 22 Stage-4F required profile fields: 2 payload fields are satisfied by benchmark scenario definitions and 20 remain unresolved.
- Added three bridge contracts: Thread stack latency, classical-LoRa whole-device energy, and LR-FHSS radio-to-whole-device energy. No numerical bridge is active.
- Preserved the LR-FHSS Stage-3 `explicit_epistemic_gap` uncertainty semantics and explicitly prohibited 4-byte-to-16-byte unvalidated scaling, radio-to-whole-device coercion, post-hoc best-mode selection, and population-distribution invention.
- Replaced ambiguous handoff booleans with explicit `required` / `prohibited` policy states for Stage-5B.
- Preserved the frozen Stage-4 feasibility matrix (21 feasible / 39 infeasible / 3 unresolved); preference scoring and publication MCDA remain blocked.
- Added schemas, fail-fast materialisation script, provenance manifest and regression tests.

## 0.1.25 - 2026-08-11

- Closed Stage 3 for the validated core-four using mixed uncertainty semantics rather than forcing all 14 metric families into one probability model.
- Added machine-readable Stage-3 closure policy and derived uncertainty-state artifact covering 2 empirical-probability, 2 scenario-robustness, 6 explicit-epistemic-gap and 4 descriptive-nonprobability metric families.
- Classified all six residual gaps as explicit/deferred rather than silently resolved; no Stage-3 closure-blocking gap remains under the current evidence base.
- Preserved zero numerical population priors for InSecTT/LR-FHSS single-trace evidence and prohibited conversion of instrument metrology into population variability.
- Preserved LoED campaign/block-length scenarios as unweighted model/deployment robustness and Vomhoff as dependence-preserving within-study nonparametric uncertainty.
- Authorised Stage 4 stack-definition/compatibility work only; publication-wide uncertainty sampling, ranking and MCDA remain blocked.
- Added fail-fast Stage-3 closure audit, Stage-4 handoff rules and regression tests.

## 0.1.24 - 2026-08-11

- Accepted Stage-3G LoED RSSI/SNR uncertainty as a scenario-indexed robustness family; no campaign or block-length probabilities are assigned.
- Added Stage-3H targeted primary-source review for the six InSecTT/LR-FHSS single-trace metric families.
- Review identifies zero defensible numerical population/repeatability priors; default CV/SD and conversion of instrument accuracy into population SD remain forbidden.
- Retained LR-FHSS publication statement of negligible differences across several transmission processes as qualitative evidence only; no numerical CV is inferred.
- Corrected LR-FHSS structured instrumentation metadata: N6705A DC Power Analyzer is measurement hardware; 14585A is Control and Analysis Software. The original Zenodo wording is retained in provenance notes.
- Extended the evidence schema with optional `acquisition_software` and re-materialise LR-FHSS/core-four evidence without changing empirical values.
- Added fail-fast single-trace evidence-review audit and regression tests. Publication uncertainty sampling and MCDA remain unauthorised.

## 0.1.18 - 2026-08-11

- Added Stage-3B Vomhoff joint nonparametric physical-run bootstrap.
- Reviewed production run-set overlap: four blocks are rectangular; NB-IoT/MQTT differs only because `Data Download` has 44 of 45 runs (97.78% overlap).
- Partial overlap is handled by union-run cluster resampling with structural missingness preserved; no imputation and no listwise deletion are used.
- Bootstrap replicate indices are meaningful only within an experimental block; no cross-block joint dependence is asserted.
- Added reproducible 10,000-replicate policy, percentile summaries, complete-case sensitivity diagnostics and within-block bootstrap-mean dependence.
- Vomhoff uncertainty status is now `calibrated_nonparametric`; publication-wide uncertainty sampling and MCDA remain blocked.

# Changelog

## 0.1.17 - 2026-08-11

- Began Stage-3A empirical uncertainty calibration with replicated Vomhoff physical/source runs; no other core dataset receives artificial population variance.
- Added a run-level calibration builder that maps every evidence-eligible logical phase back to its Stage-2 evidence ID and fails if run counts or means do not reconcile exactly.
- Materialises empirical run-level samples and marginal conditional run-to-run dispersion for all 52 Vomhoff energy/duration evidence records.
- Added candidate experimental resampling blocks based on source Figure family, technology, source application protocol and data object.
- Added run-set overlap and paired dependence diagnostics so cross-phase/energy-duration dependence can be reviewed before a joint cluster bootstrap is authorised.
- No parametric family, device/study random effect, default SD/CV or publication uncertainty sample is introduced.
- Final joint physical-run bootstrap remains intentionally pending until production run-set overlap is reviewed.
- Publication MCDA remains unauthorised.

## 0.1.16 - 2026-08-11

- Closed Stage 2 for the validated core-four after review of the 398-record unified evidence matrix, 14 empirical metric IDs, 20 measurement-boundary signatures and one shared parameter.
- Added a Stage-3 uncertainty-model schema, uncertainty taxonomy and complete 14-group core-four uncertainty policy.
- Separated measurement/calibration, within-unit, between-unit, study/implementation, shared-parameter and bridge-structural uncertainty.
- Added fail-fast uncertainty identifiability audit covering all 398 evidence records, eight dependence groups and seven explicit calibration gaps.
- Authorised empirical uncertainty calibration only for replicated Vomhoff physical-run energy/duration at this checkpoint.
- Explicitly blocked population CIs from single-trace InSecTT/LR-FHSS configurations and from single ACK/RX contrasts.
- Required bounded-memory hierarchical calibration before stochastic use of LoED RSSI/SNR and prohibited reception-row IID bootstrap.
- Blocked generic `study_id` random effects because study identity is confounded with technology, implementation and measurement boundary in the core-four.
- Preserved Vomhoff implementation context as unknown rather than filling it from secondary descriptions.
- Publication uncertainty sampling, default SD/CV fallbacks and publication MCDA remain unauthorised.

## 0.1.15 - 2026-08-11

- Added canonical unified core-four Stage-2 evidence matrix assembly over 398 validated evidence records and 14 empirical metric IDs.
- Added global parent-evidence/shared-parameter lineage validation and unified shared-parameter export.
- Added metric coverage and 20-signature measurement-boundary audit tables; heterogeneous accounting boundaries are preserved rather than normalised.
- Added a machine-readable 5-target x 4-dataset decision-target gap policy plus non-metric standards/stack/scenario evidence gaps.
- Added an explicit bridge relation from Vomhoff phase duration to future end-to-end application latency; this is component evidence, not direct latency.
- Documented the LoED reception-only SF7 / 868.3 MHz / 250 kHz stratum with 65,498 CRC-invalid receptions and no CRC-valid logical frames, without causal interpretation.
- Missing evidence imputation and publication MCDA remain unauthorised; Stage 3 uncertainty specification is next after production review.

## 0.1.12 - 2026-08-11

- Materialised InSecTT Stage-2 evidence at the technology x reporting-period trace level: 20 configurations and 80 typed evidence records.
- Preserved one independent approximately 60 s trace per configuration; millions of within-trace samples are recorded as source observations but never counted as replicate runs.
- Added explicit implementation contexts for BLE, Thread, EPhESOS and UWB, including the nRF52832 + DW1000 hardware change for UWB.
- Added a typed shared-parameter artifact for the validated inferred PPK II source voltage; all 40 derived power/energy records reference the same parameter ID.
- Derived mean power and capture energy are Stage-2 fields only; raw/harmonised voltage, power and energy provenance remain unchanged.
- Added fail-fast checkpoints against the validated 20-configuration design and publication Table-1 scale check.
- Added regression tests for pseudo-replication prevention, parent/shared-parameter lineage, implementation-aware compatibility and complete-design validation.
- Publication MCDA remains unauthorised.

## 0.1.11.post1 - 2026-08-11

- Extended Stage-2 evidence records with optional implementation context: device model, radio module, firmware, measurement instrument and stable implementation ID.
- Added implementation-aware compatibility: mismatched device/radio/firmware context is C2 conditional unless explicitly declared as a comparison factor.
- Clarified that C0_DIRECT means estimand comparability, not automatic statistical pooling across studies or dependent evidence.
- Accepted Vomhoff v0.1.11 materialisation after review; no validated empirical values changed.



## 0.1.11 — 2026-08-10

### Stage 2: Vomhoff materialisation
- Materialised a run/phase analysis-ready layer that sums contiguous repeated `Data Request` source segments within one experimental run.
- Introduced canonical physical/source-run identity across verified Figure-4/Figure-5 NB-IoT/HTTP reuse; exact non-Idle duplicate phase views are counted once.
- Retained Figure-specific HTTP `Idle` derivations as dependent views rather than pooling them.
- Excluded Figure-5 MQTT `Idle` from decision evidence, following the source README statement that it is discarded because the device disconnects; source reproduction remains unchanged.
- Preserved the Figure-5 MQTT `Standby` README/script discrepancy without inventing a 10 s transformation.
- Added validated Stage-2 Vomhoff evidence records for device phase energy and duration, plus a source-segment-vs-logical-run estimand audit.
- Publication MCDA remains unauthorised.

## 0.1.10.post2 - 2026-08-10 — Vomhoff independence and cross-Figure reuse audit

- Reviewed the production `v0.1.10.post1` logical-unit audit: 1,671 source-segment rows, 1,449 candidate run/phase groups, and 222 two-segment groups, all confined to `Data Request`.
- Verified from the exported segment table that every repeated pair is temporally contiguous within a 6 ms tolerance (5 ms source sampling interval plus timestamp quantisation allowance); maximum observed absolute continuity residual is approximately 5.22 ms.
- Authorised additive aggregation of contiguous repeated `Data Request` segments for the Stage-2 estimand **total phase energy/duration within one experimental run**. Source segments remain preserved as parent observations and are not independent replicates.
- Identified exact reuse of NB-IoT/HTTP source segments between Figures 4 and 5; source Figure is therefore not an independence boundary.
- Added a production audit for exact cross-Figure segment reuse and run-level overlap before any final Vomhoff evidence materialisation or deduplication.
- No MCDA, uncertainty model, or cross-dataset ranking is executed by this patch.

## 0.1.10.post1 - 2026-08-10 — Vomhoff logical-unit audit checkpoint

- Added a non-destructive Stage-2 audit for the validated 1,671-row Vomhoff source-reproduction table.
- Encoded source Figure 3--5 target phases separately from auxiliary instrumentation/log events.
- Added candidate logical run/phase grouping diagnostics that deliberately do not select sum versus mean aggregation.
- Added complete export of multi-segment target groups so the aggregation rule can be decided from real data rather than assumed.
- Added metadata-consistency checks within candidate groups and a Figure 5 Standby audit.
- Recorded the source discrepancy that the README describes a 10 s Standby calculation while `fig5.R` explicitly normalises only Idle. No validated source-reproduction values are changed.
- Added regression tests for target-phase filtering, segment multiplicity, condition separation, metadata inconsistency, Standby reporting and dataset identity.
- No MCDA or Stage-2 evidence matrix is materialised in this audit-only patch.

## 0.1.10 — 2026-08-10 — Stage-2 empirical evidence contract

- Added a separate typed evidence-record schema for cross-dataset scientific claims; the canonical observation schema remains unchanged.
- Added canonical metric catalogue and structured measurement-boundary taxonomy.
- Added conservative C0 direct / C1 bridgeable / C2 conditional / C3 incompatible compatibility semantics and regression tests.
- Separated source/provenance grade from derivation class and uncertainty basis.
- Clarified in code that the legacy `evidence_score()` is a source/provenance quality score, not an inferential-strength metric.
- Added parent-evidence/shared-parameter lineage fields to support correlated uncertainty in Stage 3.
- Formalised the core-four evidence plan and documented the evidence gaps that must remain missing before MCDA.
- Corrected InSecTT Thread metadata so UDP is stored as a transport protocol rather than an application protocol; no numerical transformation changed.
- Marked existing energy-model, MCDA and fleet-optimizer modules explicitly as prototype/smoke infrastructure rather than publication models.
- Updated project status to the validated full-LoED checkpoint and Stage-2 workflow.

## 0.1.9.post2 — 2026-08-10

- Fixed LoED validation cache isolation: repository-level logical-frame artifacts are reused only for the canonical repository LoED observations Parquet.
- Noncanonical inputs (pytest fixtures, temporary experiments, externally supplied Parquet files) now reconstruct logical frames from their own input unless an analysis-ready artifact is supplied explicitly.
- Added regression coverage preventing cross-input cache leakage.
- Patch installer now treats non-zero `pip`, registry-validation, or `pytest` exit codes as fatal and cannot report success after failed tests.

## 0.1.9.post1 — 2026-08-10

- Split LoED validation into gateway-level structural validation and logical-frame validation.
- Default validation now reuses a previously passed raw structural summary when the local Parquet signature is unchanged.
- Default logical-frame validation reuses the existing analysis-ready `logical_frame_reception_clusters.parquet` instead of rebuilding ~5.38 million pandas groups.
- Added cheap local Parquet signatures (`size_bytes`, `mtime_ns`, row count, row groups) for cache invalidation.
- Added `--rebuild-clusters` for the intentionally expensive semantic audit path and `--no-reuse-raw-summary` for a forced fresh gateway-level scan.
- Existing harmonised and analysis-ready LoED artifacts remain valid; no regeneration is required.

## 0.1.9 — LoED logical-frame semantics correction

- Audited 865 full-corpus clusters whose prior 1 s adjacency rule produced spans above 1 s.
- Found 91 CRC-invalid long clusters, all sharing one Join Request fingerprint; CRC-invalid receptions are now excluded from packet-identity reconstruction.
- Found CRC-valid same-frame observations with multi-gateway timestamp spans around 1 s, showing that LoED gateway UTC clocks are not sufficiently synchronized for robust physical-emission clustering.
- Reframed the analysis-ready unit as a CRC-valid logical LoRaWAN frame: exact PHY-payload fingerprint within one source day.
- `gateway_count` now explicitly means distinct gateways that observed the logical frame at least once, not simultaneous RF-reception multiplicity and not PDR.
- Added `repeat_reception_rows`, `cluster_semantics`, logical-frame validation counters, and clearer output filenames.
- Preserved the old `build_packet_reception_clusters` API name and legacy summary aliases for compatibility, but wall-clock `cluster_gap_s` is ignored.
- Added regression tests for CRC-invalid exclusion, retransmission grouping, and >1 s gateway-clock offsets.

## 0.1.8 - 2026-08-09 — full-scale LoED streaming pipeline

- Added direct ZIP-to-Parquet streaming harmonisation for LoED; the full archive no longer needs extraction and the adapter no longer accumulates the complete reception table in RAM.
- Added vectorised full-row canonical checks for LoED strict mode, avoiding per-row JSON-schema iteration on multi-million-row data.
- Full archive is preferred automatically when both sample and full ZIPs are present.
- Reworked LoED validation and analysis-ready construction to process one source day at a time and write packet clusters incrementally to compressed Parquet.
- Added a sample-state checkpoint utility that preserves small reports and SHA-256 hashes of large reproducible artifacts before full-corpus processing.
- Added streaming regression tests for ZIP selection, AppleDouble exclusion, packet clustering, and analysis-ready output.
- Sample validation is frozen at 326,870 gateway receptions with structural checks passed; full archive has been downloaded and is the next production run.

## 0.1.7.post2

- Preserve LoED source SNR in `source_snr_db_raw`.
- Map out-of-range source SNR outside [-50, 50] dB to null in canonical `snr_db` while retaining provenance.
- Validation now reports raw out-of-range SNR counts/fractions separately from cleaned physical SNR ranges.
- Added regression coverage for the observed `-128 dB` source value.

## 0.1.7.post1 - 2026-08-09 — LoED archive-hygiene hotfix

- Ignore macOS AppleDouble ``._*.csv`` resource-fork files and ``__MACOSX`` entries before LoED CSV discovery.
- Add regression coverage ensuring binary AppleDouble artefacts do not produce warnings or observations.
- Record the first production sample checkpoint: 326,870 gateway receptions, six daily source files, six observed gateways, zero schema errors.
- Clarify that nine gateways describe the complete LoED campaign; the official six-day sample may expose fewer observed gateways.

## 0.1.7 - 2026-08-08 — LoED gateway-reception integration

- Replaced the generic LoED reader with a dataset-specific chunked gateway-observation adapter.
- Preserved one canonical row per gateway reception with UTC timestamp, RSSI, SNR, SF, frequency, bandwidth, code rate, CRC status and gateway deployment metadata.
- Added SHA-256 physical-payload fingerprints without copying raw payloads into processed evidence.
- Deliberately left `delivery_success` empty because reception logs do not provide the denominator of attempted transmissions.
- Added cautious packet-reception clustering for gateway-diversity analysis with a configurable temporal gap, separating repeated identical frames from simultaneous multi-gateway receptions.
- Added gateway/day summaries whose CRC-valid fraction is explicitly conditional on recorded receptions and is not PDR.
- Added `--file-glob` download override so the same registry record can request the complete LoED archive; the adapter prefers the full archive when both sample and full data are present.
- Added LoED structural-validation and analysis-ready scripts plus regression tests.
- Extended project documentation and dataset card with packet-identity, privacy/provenance and sample/full decisions.

## 0.1.6 - 2026-08-08 — documentation checkpoint

- Added a structured research documentation system: project status, chronological research log, methodological decision log and reproducibility workflow.
- Added dataset cards for Vomhoff NB-IoT/LTE-M, InSecTT, LoRaWAN LR-FHSS and LoED.
- Recorded production validation results and statistical-unit limitations for the first three validated datasets.
- Recorded LoED as sample-diagnosed / adapter-pending and explicitly prohibited deriving absolute PDR from reception-only counts without a transmission denominator.
- Added reusable templates for future dataset cards and decision records.
- Bumped package version to 0.1.6. No scientific transformation code was changed in this documentation checkpoint.

## 0.1.5 - 2026-08-08

- Replaced the generic LR-FHSS reader with a dataset-specific streaming adapter.
- Added explicit parsing of ACK/noACK, DR8--DR11 and 20.48 us source metadata.
- Added published 3.3 V radio-supply provenance and full-trace charge/energy integration.
- Added 4-byte FRM payload, +14 dBm TX power, DR coding-rate and bit-rate metadata.
- Added low-current and TX-plateau diagnostics without silently claiming per-message energy.
- Verified the dataset licence as CC BY 4.0 from the live Zenodo metadata.
- Added LR-FHSS validation script and regression tests.

## 0.1.4

- Replaced the placeholder InSecTT generic adapter with a dataset-specific streaming nested-ZIP adapter.
- Added correct 10 us timestamp interpretation and microampere current handling.
- Added communication-period to payload mapping: 100/200/400/800/1600 ms -> 2/4/8/16/32 bytes.
- Added exact trace-level current statistics and integrated charge while intentionally leaving power/energy unset because source voltage is not present in the dataset README.
- Verified the InSecTT dataset licence as CC BY 4.0 from the source README.
- Added the related publication Table 1 reference values and an independent scale-validation script that infers the implied source voltage rather than guessing it.
- Added InSecTT adapter methodology notes and regression tests.

## 0.1.3 — 2026-08-06

- Canonicalise missing values in Vomhoff aggregation keys before cross-chunk accumulation.
- Fix one duplicate observation identifier caused by `NaN != NaN` when a logical Figure 3 group crossed a CSV chunk boundary.
- Add a regression test that forces the affected group across chunks.
- Expected regenerated dataset: 1,671 unique run-phase observations and no duplicate-ID warning.

## 0.1.2 — 2026-08-06

- Corrected the Vomhoff adapter to preserve separate run-phase segments when the authors' R scripts distinguish them by `diff_time`.
- Added `source_diff_time_s` provenance and stable collision-resistant observation identifiers.
- Removed misleading multiple-duration warnings caused by the previous segment collapse.
- Added regression tests for repeated event labels with distinct source durations and normalised-label collisions.

## 0.1.1 — 2026-08-06

- Added the missing runtime dependency `tabulate`.
- Replaced the placeholder Vomhoff NB-IoT/LTE-M adapter with a chunked run-by-phase importer for the real public CSV structure.
- Preserved the source Figure 3-5 normalisation rules and raw provenance values.
- Marked the downloaded dataset licence as verified CC BY 4.0.
- Added adapter-specific tests and documentation.

## 0.1.8.post1

- Fixed full-LoED validation/analysis performance regression: v0.1.8 rescanned the monolithic Parquet once per source day.
- Validation and analysis-ready builders now perform one sequential Parquet scan and buffer only the current source day.
- Added per-day progress output for long full-corpus runs.
- Existing full harmonised Parquet remains valid; no re-harmonisation is required.

## 0.1.14 — 2026-08-11

- Materialised full-corpus LoED Stage-2 evidence using bounded-memory reception-PHY and logical-frame-PHY summaries.
- Added explicit `gateway_crc_valid_fraction_of_receptions` and `logical_frame_multi_gateway_fraction` evidence metrics.
- Preserved hierarchical dependence by leaving LoED `n_independent_units` unset; no row-count-based confidence intervals are allowed.
- Kept CRC/reception diversity hard-incompatible with delivery probability/PDR.
- Corrected stale LoED documentation that still described temporal-gap clustering and full-corpus validation as pending.

## 0.1.19 — Stage-3C LoED hierarchical grouped calibration

- Added bounded-memory LoED `source day × gateway × exact PHY stratum` calibration cells for RSSI/SNR.
- Preserved paired RSSI/SNR sums, squares and cross-products so future joint calibration does not assume independence.
- Added weighted within-cell/between-cell variance decomposition, daily-PHY summaries, day/gateway coverage and consecutive-day lag-1 diagnostics.
- Reconciles grouped artifacts exactly against the validated Stage-2 PHY and gateway-PHY summaries.
- Marks LoED RSSI/SNR grouped artifacts as materialised while keeping IID reception/cell/day bootstrap, hierarchical sampling and publication MCDA unauthorised pending review.


## 0.1.28 — 2026-08-11

- Added Stage-4C bounded verified reference candidate stacks (9 candidates).
- Added exact primary-source compatibility-edge gating for `verified_candidate` graphs; interface-name matching alone is no longer sufficient.
- Added candidate-level empirical-support records that preserve boundary/application limitations; no candidate is promoted to complete end-to-end empirical support.
- Deferred BLE remote/GATT gateway, UWB remote and EPhESOS remote families instead of closing unresolved mediation/profile/standardisation gaps by assumption.
- Hard scenario feasibility, MCDA, rankings and stakeholder weights remain blocked.

## 0.1.29 — 2026-08-11

- Added Stage-4D six-scenario quantitative benchmark catalog and tri-state hard-feasibility screening across the frozen nine Stage-4C candidates.
- Separated quantitative scenario context from explicit hard predicates; payload/interval/latency values do not become hard automatically.
- Added conservative candidate hard-capability derivation from the verified component graph; unsupported numeric latency/payload/energy and mobility facts remain NULL/unresolved.
- Materialised 54 scenario×candidate screening rows: 12 feasible under declared hard constraints, 33 infeasible and 9 unresolved.
- Distinguished 27 unknown hard-result occurrences from the 9 decision-blocking unknowns; unknowns on already-infeasible candidates do not drive capability-review priority.
- Kept feasibility separate from empirical completeness: zero Stage-4C candidates have full end-to-end core-four empirical support.
- MCDA, ranking and stakeholder weights remain blocked.

## 0.1.31
- Close Stage 4 hard feasibility with three explicit unresolved profile/boundary blockers.
- Add Stage-4F blocker-freeze policy and reproducible closure script.
- Add LR-FHSS radio-energy/budget diagnostic without promoting radio-only 4-byte evidence to 16-byte whole-device feasibility.
- Add operating-profile handoff requirements for Stage 5A.
- Keep publication MCDA/ranking unauthorised.

## 0.1.38 — 2026-08-12

- Added Stage-5G targeted cellular transfer-evidence admissibility audit.
- Registered Sørensen et al. 2022 (DOI `10.1109/JIOT.2022.3152173`) as structural supporting evidence for NB-IoT/LTE-M payload and report-cycle/state dependence.
- Explicitly prohibited direct absolute recalibration of Vomhoff whole-device Stage-5F energy from the modem-only external model.
- Kept all 10 feasible cellular-IP candidate incidences blocked for canonical report-energy because device/boundary and exact upper-layer transfer remain unresolved.
- Added machine-readable source review, candidate transfer admissibility, next-step options and regression tests.

## 0.1.39 — 2026-08-12

- Added Stage 5H lifecycle-cost accounting/evidence contract.
- Added machine-readable separation of per-device recurring costs and shared site infrastructure costs.
- Added candidate-level cost-readiness and evidence-gap audit.
- Kept all numerical publication prices unmaterialised; smoke `configs/fleet.yml` values remain prohibited.
- Preserved unresolved urban LoRaWAN ownership rather than inferring a costing mode.

## 0.1.58 — Final publication consolidation

- closed the five-experiment publication programme without adding new empirical or synthetic evidence;
- added a fail-closed final consolidation over Experiments 1–5;
- promoted the fleet portfolio/simplification claim to publication-authorised after Experiment 5;
- retained explicit blocks on global stochastic ranking and matched whole-device cellular energy claims;
- added a machine-readable two-paper split, final figure/table plan and manuscript-scope guardrails;
- recommended separate benchmark/data and STACKWISE methodology/results manuscripts while keeping Benchmark v1.0.0 frozen.
