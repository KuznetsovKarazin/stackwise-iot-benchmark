# Stage 5I — dated cellular cost evidence

Version: **v0.1.40**  
Source capture date: **2026-08-12**

## Purpose

Stage 5H froze the lifecycle-cost accounting boundary but intentionally contained no market prices. Stage 5I adds the first targeted, dated monetary evidence tranche for the ten feasible **IP-cellular** candidate incidences. It does not infer prices for Non-IP/NIDD cellular service and does not touch the private-LoRaWAN cost boundary.

## Reference hardware

The reference communication module is the Quectel `BG95M3LA-64-SGNS`. The Quectel BG95 series manufacturer page identifies the family as supporting LTE Cat M1 and Cat NB2. DigiKey Italy is used as the dated retail reference observation for the specific SKU:

- quantity-1 price: **EUR 33.41**, VAT excluded;
- a published quantity-250 value of **EUR 26.07/unit** is retained only as a procurement sensitivity and is not used as statistical uncertainty or silently selected as the benchmark price.

The same dual-mode hardware reference is used for NB-IoT and LTE-M. STACKWISE therefore does **not** create an artificial RAT-dependent module-price difference.

## Reference connectivity tariff

The reference IP-connectivity evidence is the 1NCE IoT Lifetime Flat captured on 2026-08-12:

- base connectivity: **EUR 12** upfront for a 10-year term;
- standard physical SIM: **EUR 1**;
- included data: **500 MB**;
- published TopUp: **EUR 10 per additional 500 MB**;
- published service support includes LTE-M and NB-IoT;
- the reviewed support material describes IP transport using TCP/UDP and a private IP/APN path.

The 10-year prepaid fee is not prorated to the five-year STACKWISE horizon because the complete plan is purchased upfront.

No reviewed official 1NCE source is used as evidence for NIDD/Non-IP service. The seven feasible cellular Non-IP incidences therefore remain blocked rather than inheriting the IP tariff.

## Tariff-volume boundary

The price of a finite-volume tariff is not the same as a five-year lifecycle connectivity cost. 1NCE states that transferred data are measured/billed to the nearest 1 kByte and that protocol overhead is included. The reviewed source does **not** specify whether that rounding applies per packet, session, accounting interval or aggregate usage. STACKWISE therefore does not multiply the application-report count by 1 kByte.

What can be computed without inventing a transport profile is the five-year application-payload volume:

| Scenario | interval | reports in 5 y | application payload volume | conclusion about base 500 MB |
|---|---:|---:|---:|---|
| smart meter | 900 s | 175,320 | 35.064 MB | base allowance not disproven; exact fit unresolved |
| periodic asset tracking | 60 s | 2,629,800 | 168.3072 MB | base allowance not disproven; exact fit unresolved |
| connected-handover tracking | 60 s | 2,629,800 | 168.3072 MB | base allowance not disproven; exact fit unresolved |

These values omit transport, security, application-management, acknowledgements/downlink, connection establishment, keep-alives and retransmissions. They therefore cannot prove that the 500-MB allowance is sufficient. Conversely, because they are below 500 MB, they cannot prove that a TopUp is required either.

The published TopUp schedule is retained in the evidence ledger for later calculation once a reproducible session/transport profile is frozen. Stage 5I does **not** infer a TopUp count.

The source-backed reference cash-cost floor is therefore **EUR 46.41** for each IP-cellular incidence: EUR 33.41 module + EUR 1 standard SIM + EUR 12 base prepaid plan. This is the minimum selected reference purchase bundle, not the canonical five-year lifecycle cost.

## Scientific status

- feasible candidate rows: 21;
- operator-managed rows: 17;
- feasible IP-cellular rows with dated module/SIM/tariff evidence: **10**;
- feasible Non-IP cellular rows: **7**, still blocked for service-mode evidence;
- private/unresolved LoRaWAN rows: **4**, outside this tranche;
- canonical lifecycle-cost targets ready: **0**.

The useful result is the separation of **dated price evidence** from **tariff-volume identifiability**. A price floor is not promoted to a canonical cost.

## Next closure

Stage 5J should freeze candidate-specific IP session/transport profiles sufficient to compute defensible traffic-volume envelopes for CoAP/DTLS/LwM2M and MQTT/TLS/LwM2M. The same profile definitions should be reused by the open cellular energy bridge rather than creating separate incompatible assumptions for cost and energy.

Primary source URLs and exact captured price atoms are stored in `datasets/stage5i_dated_cellular_cost_evidence.yml` and materialised in `results/validation/stage5i_dated_cellular_cost_evidence/price_evidence_ledger.csv`.
