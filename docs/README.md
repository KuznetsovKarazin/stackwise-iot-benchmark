# STACKWISE documentation index

This directory is the human-readable research record for STACKWISE. It complements the machine-readable dataset registry, manifests, schemas and generated results.

## Start here

- `PROJECT_STATUS.md` — current state of the research programme and the next controlled step.
- `RESEARCH_LOG.md` — chronological record of what was done, with dates and quantitative validation outcomes.
- `DECISION_LOG.md` — methodological decisions and the reason for each decision.
- `REPRODUCIBILITY_WORKFLOW.md` — the allowed transformations from raw source data to publishable analysis-ready evidence.
- `DATA_MODEL.md` — canonical observation schema and accounting boundaries.
- `EMPIRICAL_EVIDENCE_MODEL.md` — Stage-2 typed evidence records, structured boundaries, compatibility classes and core-four evidence plan.
- `UNCERTAINTY_MODEL.md` — Stage-3 uncertainty layers, identifiability regimes, dependence groups and calibration safeguards.
- `METHODOLOGY.md` — evidence hierarchy, harmonisation rules and modelling principles.
- `RESEARCH_PLAN.md` — staged research programme and research questions.
- `DATASET_CATALOGUE.md` — intended scientific role of all registered sources.
- `CELLULAR_IP_SESSION_PROFILE_CONTRACT.md` — Stage-5J common LwM2M Send/session profile contract shared by tariff-volume and report-energy analysis.
- `CELLULAR_IP_PROTOCOL_ENVELOPE_VARIANTS.md` — Stage-5K deterministic protocol/session sensitivity anchors.
- `CELLULAR_IP_WIRE_VOLUME_ACCOUNTING.md` — Stage-5L standards-based steady-state wire-component accounting.
- `LWM2M_SERIALIZATION_ENVELOPE.md` — Stage-5M exact serialization for explicit synthetic Opaque-Resource surrogates and resulting raw-volume sensitivity.

## Dataset cards

Each empirically used dataset must have one card under `DATASET_CARDS/`. A card is the authoritative narrative record for that source and must document:

1. source and citation;
2. licence and redistribution status;
3. raw structure and measurement boundary;
4. harmonisation unit and transformations;
5. validation evidence;
6. analysis-ready derivations;
7. statistical unit and pseudoreplication risks;
8. known limitations;
9. current status and next action.

Current cards:

- `DATASET_CARDS/vomhoff_nbiot_ltem_energy_2023.md`
- `DATASET_CARDS/insectt_wsn_power_2023.md`
- `DATASET_CARDS/lorawan_lrfhss_energy_2024.md`
- `DATASET_CARDS/loed_lorawan_edge_2020.md`

## Rule for future work

A new dataset is not considered integrated merely because it downloads or parses. It becomes `validated` only after its dataset card contains source-backed units, measurement boundary, statistical unit, harmonisation logic, validation checks and explicit limitations.

- `SECURITY_SESSION_CONTROL_ENVELOPE.md` — Stage-5N final planned transport/accounting refinement: PSK DTLS/TLS session surrogates and MQTT/TCP ACK/control sensitivity.

- `LIFECYCLE_COST_ROBUSTNESS_FAMILY.md` — Stage-6C unweighted EUR cost family for the periodic-tracking IP-cellular development subset.
