# Experiment 4 — Accounting and cost simplification ablation

## Question

How much does progressively simplified IoT communication accounting distort five-year tariff-volume and lifecycle-cost conclusions?

## Frozen scope

The experiment uses `asset_tracking_periodic_cross_cell` and the four IP-cellular candidates (NB-IoT/LTE-M × CoAP/DTLS/LwM2M or MQTT/TLS/LwM2M). All Stage-5L–6C transport, serialization, session/control, billing and procurement artifacts are frozen. No new protocol assumptions are introduced.

## Accounting ladder

1. `L0_APPLICATION_PAYLOAD_ONLY`: 64 B/report only.
2. `L1_TRANSPORT_AWARE_1TO1_PAYLOAD`: Stage-5L known transport/control floor plus a deliberately simplified 1:1 64-B serialized payload.
3. `L2_SERIALIZATION_AWARE`: exact Stage-5M synthetic LwM2M serialization surrogate plus transport.
4. `L3_SESSION_CONTROL_AWARE`: Stage-5N security/session/TCP-control surrogate increments.
5. `L4_BILLING_AWARE`: Stage-6C PDP-session rounding and TopUp accounting.

The same 288 traffic/billing states are evaluated at all five levels. Procurement expansion yields 576 rows for EUR cost comparison. These states are unweighted sensitivity states; row fractions are not probabilities.

## Frozen results

Nominal 500-MB exceedance counts are `0 / 144 / 152 / 216 / 252` for L0–L4. False-within classifications relative to L4 are `252 / 108 / 100 / 36` for L0–L3. Stepwise newly exposed exceedances are `144 / 8 / 64 / 36` from transport, serialization, session/control and billing respectively.

Payload-only accounting understates the final five-year connectivity cost in 504/576 procurement-expanded rows, with median 50 EUR and maximum 100 EUR underestimation. Session/control-aware raw accounting still understates final billed cost in 288/576 rows, with median 5 EUR and maximum 50 EUR.

## Interpretation

The result quantifies the cost of modelling simplification. Application payload alone is not a reliable proxy for billed traffic. Transport binding captures the dominant MQTT/TLS effect, while serialization, session lifecycle and PDP-session billing each expose additional tariff exceedances. No real global candidate ranking is implied.
