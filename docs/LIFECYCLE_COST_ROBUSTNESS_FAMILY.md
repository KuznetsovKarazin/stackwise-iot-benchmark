# Stage 6C — Lifecycle-Cost Robustness Family

Version: `v0.1.48`

## Scope

Stage 6C closes the cost-side blocker for the Stage-6A development subset only:

- scenario: `asset_tracking_periodic_cross_cell`;
- payload: 64 B pre-LwM2M application data;
- reporting interval: 60 s;
- candidates: NB-IoT/LTE-M × CoAP/DTLS/LwM2M or MQTT/TLS/LwM2M.

This is still a development subset, not the full six-candidate scenario optimum.

## New operator-billing evidence

Current 1NCE Platform 2.0 documentation resolves the former Stage-5I billing-aggregation ambiguity: data usage is rounded per PDP session at session end to the nearest kB. The same documentation explicitly distinguishes many short PDP sessions from many transmissions inside one persistent PDP session.

STACKWISE therefore uses two deterministic, unweighted deployment anchors:

1. `B0_persistent_pdp`: one long-running PDP session over the benchmark horizon;
2. `B1_pdp_per_report`: one PDP session per scheduled report.

These are sensitivity anchors, not occurrence probabilities. Security-session re-establishment and PDP-session re-establishment are not equated.

## Procurement anchors

The dated Quectel BG95-M3 observations are retained as two explicit procurement anchors:

- `P0_volume_250`: EUR 26.06644/module at published quantity 250;
- `P1_retail_qty1`: EUR 33.41/module at quantity 1.

The standard SIM is EUR 1, the prepaid 1NCE base plan is EUR 12, and each additional 500 MB TopUp is EUR 10. No probability is assigned to either procurement quantity.

## Family construction

All 144 Stage-5N rows belonging to the four preferred candidates are retained. They already span protocol-envelope anchors, two synthetic LwM2M resource shapes and two session/control surrogates.

The cost family is the cross-product:

`144 Stage-5N rows × 2 PDP-session billing anchors × 2 procurement anchors = 576 rows`.

For each family member:

`lifecycle cost = module + SIM + prepaid base plan + TopUp count × TopUp price`.

Only differential connectivity hardware/service cash costs within the frozen five-year contract are included. Shipping, taxes/VAT without a common tax basis, energy cost, battery replacement and common application hardware/cloud costs remain excluded according to Stage 5H.

## Result

All four preferred candidates now have `lifecycle_cost_eur = READY_ROBUSTNESS_FAMILY`.

| Binding | Five-year cost family | TopUp count family | Billed-volume family |
|---|---:|---:|---:|
| CoAP/DTLS/LwM2M | EUR 39.06644–96.41 | 0–5 | 373.432–2629.8 MB |
| MQTT/TLS/LwM2M | EUR 49.06644–146.41 | 1–10 | 738.974–5259.6 MB |

Within each binding, the NB-IoT and LTE-M cost families are identical under the shared dual-mode BG95 hardware and the same operator tariff. Stage 6C therefore does not manufacture a RAT-specific cost difference where the source evidence provides none.

## Interpretation

The family is a finite epistemic/deployment robustness family, not a statistical sample and not a market-price distribution. Members must not be assigned frequencies unless future evidence supports them.

This closes the cost criterion for decision-engine development, but not the first full decision slice:

- lifecycle cost: `READY_ROBUSTNESS_FAMILY` for 4/4 preferred candidates;
- whole-device report energy: `BLOCKED` for 4/4;
- first-slice-ready candidates: 0/4;
- publication MCDA: not authorised.

The remaining primary scientific blocker is the Stage-6B matched whole-device energy experiment.
