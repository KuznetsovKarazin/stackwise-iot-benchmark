# STACKWISE Paper B — External Validation Campaign

Status: **DESIGN FREEZE v0.1 (pre-data)**  
Target manuscript: Paper B / Elsevier *Internet of Things*  
Benchmark frozen input: STACKWISE Empirical Evidence Benchmark v1.0.0

## 1. Purpose

The campaign tests whether the STACKWISE decision methodology generalises beyond the scenarios, evidence sources and stress-test spaces authored during construction of Benchmark v1.0.0. It does **not** add new physical measurements. External validity is established through independently published use cases, held-out empirical datasets and robustness analyses whose rules are fixed before outcome inspection.

The primary threat addressed is construct circularity: the original Paper B experiments use scenarios, candidates, feasibility rules and evidence relations defined inside STACKWISE. The external-validation campaign therefore separates **method definition** from **validation inputs**.

## 2. Non-negotiable pre-registration rules

1. Benchmark v1.0.0, the canonical evidence schema, evidence-boundary taxonomy and hard-feasibility semantics are frozen.
2. No externally observed result may be used to add a new admissibility class, relax a boundary rule or alter a hard constraint after the PRE-DATA freeze.
3. External use-case requirements are transcribed from the cited source. Missing requirements remain `unavailable`; conflicting source values remain explicit conflicts; neither is silently imputed or harmonised from general knowledge.
4. External evidence is ingested as held-out validation material. It does not retroactively change Benchmark v1.0.0.
5. A result that remains `unresolved` after adding external evidence is an admissible and potentially informative outcome.
6. Positive and negative evidence transitions are both publication-relevant. The campaign is not considered failed if a held-out source closes no evidence gap.
7. All exclusions, failed parsings and mapping ambiguities are retained in machine-readable audit tables.
8. Primary analyses are deterministic except where an uncertainty contract explicitly defines resampling.

## 3. Primary external use-case set

Five independently authored application cases are selected before running STACKWISE:

- HINTS Case A — smart building.
- HINTS Case B — event video-surveillance.
- HINTS Case C — precision agriculture.
- Vannieuwenborg et al. — smart shipping containers in the Port of Antwerp.
- Vannieuwenborg et al. — Shop'n Go smart parking.

HINTS is especially important because it is published in *Internet of Things* and already contains application modelling, pre-selection, simulation and multi-attribute decision making. STACKWISE is therefore not evaluated against a straw-man `score-first` method. Instead, the external cases test the earlier question: whether the evidence required to populate a candidate evaluation is admissible at the declared target boundary.

The exact requirement values must be extracted from the source paper and/or companion repository and entered into `datasets/external_validation_use_cases.yml` **before** PRE-DATA freeze. If a published requirement cannot be recovered, the corresponding field remains `unavailable`.

## 4. Held-out empirical evidence set

Three sources are preselected for complementary roles:

### EV-E1 — Kousias et al. operational NB-IoT/4G/5G measurements
- Zenodo DOI: 10.5281/zenodo.8224890
- Role: held-out operational-network coverage/link evidence, including NB-IoT passive measurements.
- Pre-registered expectation: may improve NB-IoT coverage/link support; must not be allowed to create whole-device energy, application latency or delivery-denominator evidence unless those estimands are explicitly present.

### EV-E2 — Povalac & Kral LoRaWAN Traffic Analysis Dataset v2
- Zenodo DOI: 10.5281/zenodo.8090619
- Role: held-out LoRaWAN packet/sniffer evidence collected in four cities.
- Pre-registered negative-control expectation: reception/sniffer observations must **not** be promoted to attempted-transmission delivery probability without an external denominator. The source may enrich LoRaWAN traffic/link context without closing that target.

### EV-E3 — Leenders & Callebaut NB-IoT Power Measurements v1.0
- Zenodo DOI: 10.5281/zenodo.3557239
- Associated measurement paper: 10.1109/WF-IoT48130.2020.9221010
- Role: held-out NB-IoT power/energy measurements from a different measurement campaign and device context.
- Pre-registered expectation: may improve NB-IoT energy-component support; direct per-application-report status is allowed only if system scope, temporal boundary, workload and reporting-cycle accounting actually match the target.

The campaign deliberately contains one likely positive coverage source, one likely positive energy/component source and one semantic negative control.

## 4.1 Validation tiers and independence convention

The five use cases are not treated as five statistically independent replicates. The three HINTS cases share one publication/methodology family, and the two Vannieuwenborg cases share another. Results are therefore reported both per case and stratified by source family; no pooled hypothesis test treats case count as an IID sample from a population of IoT applications.

External validation is tiered:
- **Tier A — ontology portability:** all five cases are retained, including cases with unmapped requirements. Unmapped fields are evidence of portability limits, not a reason to edit the frozen ontology.
- **Tier B — decision-readiness validation:** cases with complete source transcription enter readiness analysis even if some hard requirements are outside the frozen ontology; those unmapped requirements conservatively block `DECISION_READY`.
- **Tier C — portfolio validation:** external set-cover analysis is reported only if at least three external scenarios from at least two independent publication families meet Tier B. Otherwise the external portfolio claim is withheld rather than repaired post hoc.

## 5. External-validation questions

### EV-RQ1 — Scenario portability
Can independently defined application requirements be represented without changing the STACKWISE scenario ontology?

Primary metrics:
- fraction of source requirements mapped `exact`;
- fraction mapped `interpretable`;
- fraction `unavailable`;
- number of new schema fields required (**target = 0; any non-zero value is reported as a limitation**).

### EV-RQ2 — Decision-readiness portability
For external scenarios, does the frozen method distinguish `INFEASIBLE`, `UNRESOLVED`, `FEASIBLE_BUT_EVIDENCE_INCOMPLETE` and `DECISION_READY` without forcing a winner?

Primary metrics:
- state counts by external scenario;
- number of feasible candidates per scenario;
- number of decision-ready candidates per scenario;
- proportion of feasible candidates blocked specifically by evidence admissibility.

### EV-RQ3 — Prospective evidence-gap closure
Do independently published held-out datasets close only the evidence gaps predicted by their measurement semantics?

Primary metrics:
- target-relation transition matrix before/after each external source;
- `E0 -> C2`, `E0 -> C1`, `E0 -> C0`, `C2 -> C1`, `C1 -> C0` counts;
- inappropriate-transition count (must be 0 under frozen rules);
- no-change count for targets outside the source boundary.

No transition is interpreted as improvement merely because the class becomes numerically lower; the scientific meaning of the class is retained.

### EV-RQ4 — Negative-control validity
Does the method correctly refuse unsupported inference when a new dataset looks relevant but lacks the required denominator/boundary?

Primary test: Povalac LoRaWAN traffic evidence must not become `C0_DIRECT` for `delivery_probability` unless an explicit attempted-transmission denominator is present in the ingested records and source documentation.

### EV-RQ5 — Portfolio portability
Does the need for a heterogeneous connectivity portfolio persist when the scenario universe is independently defined?

Universes:
- U_internal: frozen 7 STACKWISE scenarios;
- U_external: externally defined scenarios passing minimum transcription completeness;
- U_combined: U_internal + U_external.

For each universe report minimum set cover at stack, access-technology and technology-family levels, plus leave-one-scenario-out stability. No universal claim is allowed if the external universe produces a different minimum portfolio structure.

## 6. Method-robustness extensions required for Paper B v2

These are run after PRE-DATA freeze and are independent of external source outcomes.

### MR1 — Preference-operator robustness for Experiment 1
Use the same frozen structural feature matrix with:
- weighted additive score (existing);
- TOPSIS;
- weighted Chebyshev distance to the ideal point.

For each operator run:
- full 4-feature set;
- leave-one-feature-out subsets;
- equal weights;
- frozen simplex weight grid.

Report:
- Any-Infeasible@Top;
- All-Infeasible@Top;
- Unique-Infeasible-Winner;
- fraction of cases in which a feasible candidate exists but every top candidate is infeasible.

The publication claim is an ordering-risk robustness result, **not** novelty of hard-constraint filtering.

### MR2 — Deterministic admissibility audit
The C0/C1/C2/E0 mapping must be produced by frozen boundary rules wherever possible. Human annotation is used only for source-to-schema transcription and ambiguous source semantics. A 20-relation audit table must record rule inputs, output class and reasons.

Optional high-value audit: one independent IoT/network researcher labels the 20 internal source-target relations and a stratified sample of external relations before seeing algorithm output; agreement and adjudication are reported.

### MR3 — Uncertainty-contract decomposition
Experiment 3 is reported as three diagnostics rather than one homogeneous stochastic experiment:
- U1 empirical physical-run bootstrap (Vomhoff);
- U2 temporal aggregation/model-form sensitivity (LoED);
- U3 bounded aligned state sensitivity (lifecycle cost).

For each diagnostic record resampling unit, replication count, seed, interval/statistic and prohibited interpretation.

### MR4 — Accounting-boundary factorial sensitivity
Pre-register a broad grid:
- payload bytes: 32, 64, 128, 256, 512, 1024;
- reporting intervals: 300, 900, 3600, 21600, 86400 s;
- included monthly allowances: 50, 100, 250, 500, 1000 MB;
- billing increments: 50, 100, 500 MB;
- horizons: 1, 3, 5 years.

Primary outputs:
- continuous relative billed-volume error;
- tariff classification error;
- error quantiles across the entire grid;
- proportion of regimes in which payload-only accounting changes the tariff class.

Existing EUR-specific headline results remain a frozen worked example, not the sole robustness claim.

### MR5 — External and leave-one-out fleet robustness
Run minimum set cover on U_internal, U_external and U_combined, with leave-one-scenario-out analysis. Report the full distribution of minimum portfolio cardinality, not only the modal/minimum combination.

## 7. Unified STACKWISE decision-readiness algorithm

Paper B v2 will present one operational algorithm with the following state machine:

1. **HARD SCREEN** — evaluate scenario hard constraints for each candidate.
2. **TARGET MAP** — enumerate decision targets required by the scenario/objective.
3. **ADMISSIBILITY** — classify each evidence-target relation under frozen boundary rules.
4. **UNCERTAINTY CONTRACT** — attach the source-appropriate uncertainty/dependence treatment.
5. **ACCOUNTING CHECK** — verify protocol/session/billing/system boundaries for derived targets.
6. **READINESS** — assign each candidate one of:
   - `INFEASIBLE`
   - `UNRESOLVED`
   - `FEASIBLE_BUT_EVIDENCE_INCOMPLETE`
   - `DECISION_READY`
7. **PREFERENCE** — rank only feasible decision-ready candidates when the objective supports ranking.
8. **PORTFOLIO** — if multiple scenarios are jointly served, solve set-cover/portfolio selection only over candidates whose feasibility state is defensible.

A numerical winner is therefore an optional terminal state, not an obligatory output.

## 8. External use-case transcription policy

Each extracted requirement must carry:
- `source_case_id`;
- bibliographic source/DOI;
- source artefact path or table/section reference;
- source wording or concise source-faithful paraphrase;
- STACKWISE field;
- value and unit;
- mapping status: `exact`, `interpretable`, `unavailable`;
- interpretation note;
- whether the requirement is hard or preference-only.

An externally stated hard requirement with mapping status `unavailable` is **not silently discarded**. The mapped subset may be screened, but the scenario/candidate state cannot become `DECISION_READY` while an unmapped hard requirement remains unresolved. Such cases are reported as ontology-portability failures or `UNRESOLVED_EXTERNAL_REQUIREMENT`, rather than being repaired by extending the frozen schema.

### 8.1 Source precedence and discrepancy policy

For HINTS, the published case-study narrative and final case tables are the primary external source. Companion-repository artefacts are retained as implementation evidence, not as silent overrides. If the publication, summary table and repository disagree, every conflicting value is recorded in `external_validation/annotations/hints_source_discrepancies_predata.csv`. A conflicting field is not admitted as an exact hard-screen input unless the conflict is resolved by an explicit source statement that predates this campaign.

This policy is particularly important because source inspection identified several pre-outcome discrepancies (for example deployment-scope values and selected battery-lifetime thresholds). The discrepancies are part of the external-validation record and are not corrected from general IoT knowledge.

Minimum external-scenario inclusion threshold for Tier-B decision-readiness analysis:
- the source case has a complete transcription of the hard requirements that can be recovered from the publication; and
- no missing source value is silently imputed.

Tier-B inclusion does **not** imply that the frozen STACKWISE ontology can represent all hard requirements. Unmapped hard requirements remain explicit blockers to `DECISION_READY`.

Minimum external-scenario inclusion threshold for Tier-C portfolio analysis:
- at least 70% of hard requirements map as `exact` or `interpretable`; and
- no unresolved source ambiguity exists in a requirement that could flip a hard-feasibility decision for two or more candidate families.

Scenarios below the Tier-C threshold remain in ontology-portability and decision-readiness reporting but are excluded from external set-cover claims.

## 9. Held-out source ingestion policy

External evidence adapters may map new source columns into existing canonical fields. They may **not**:
- add a new comparison class;
- reinterpret receive-side observations as attempted transmissions;
- collapse module/radio/whole-device boundaries;
- treat repeated samples within one run as independent replications;
- use a publication conclusion as if it were a raw measurement row.

If a genuinely necessary canonical field is missing, the adapter records `schema_extension_required=true` and the source is excluded from primary validation rather than changing the frozen schema mid-campaign.

## 10. Success criteria

The campaign is considered strong enough for Paper B v2 if all of the following hold:

1. All five primary external scenarios are included in Tier-A ontology-portability reporting and, once source transcription is complete, in Tier-B decision-readiness reporting. Unmapped hard requirements may force an unresolved state. Tier-C portfolio claims require at least three scenarios from at least two independent publication families to meet the stricter mapping/ambiguity threshold. If this condition fails, the portfolio claim is withheld rather than changing the ontology.
2. External scenario ingestion requires no change to the core decision-state semantics.
3. At least two held-out datasets ingest without schema/taxonomy changes.
4. The negative-control source does not create prohibited direct delivery evidence.
5. At least one held-out source produces a scientifically justified evidence-class transition or new decision-readiness information; if none does, this is reported and the external-evidence claim is weakened.
6. Experiment-1 ordering risk remains qualitatively present under at least two of the three preference operators and under leave-one-feature-out analyses; otherwise the claim is narrowed.
7. Accounting-boundary error remains material over a broad parameter grid; otherwise the 500-MB worked example is explicitly labelled scenario-specific.
8. Portfolio conclusions are reported separately for internal, external and combined universes, with no universal heterogeneity claim unless supported externally.

## 11. Stop/decision rules

- Do not add a sixth experiment solely to obtain a positive result.
- Do not replace an external source after observing an unfavourable result unless the source is technically unusable (corrupt, inaccessible, licence-prohibited); such replacement must be documented and the original retained in the audit log.
- Do not tune scenario mappings using the final decision outcome.
- Do not publish a global ranking unless evidence readiness is independently satisfied.

## 12. Planned Paper B v2 structure

1. Introduction and problem statement
2. Related decision frameworks and positioning versus HINTS
3. Unified STACKWISE evidence-ready decision algorithm
4. Frozen benchmark and internal stress tests (condensed Experiments 1–5)
5. External validation protocol
6. External scenario portability
7. Held-out evidence and prospective gap-closure validation
8. Robustness analyses (preference, accounting, portfolio)
9. Threats to validity
10. Discussion and conclusions

The external-validation section becomes the principal answer to the v1 external-validity weakness; the original five experiments become controlled stress tests supporting the framework rather than five co-equal claims.
