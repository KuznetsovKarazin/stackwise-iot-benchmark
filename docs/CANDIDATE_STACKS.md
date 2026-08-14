# Stage 4C — verified reference candidate stacks

Stage 4C freezes a **small reference set**, not an exhaustive combinatorial enumeration. Every component in a `verified_candidate` is primary-source verified and every explicit binding must match a frozen Stage-4B compatibility edge exactly. Interface-name coincidence is not sufficient.

Nine reference candidates are materialised: three NB-IoT profiles, three LTE-M profiles, classical LoRaWAN/LwM2M, LR-FHSS/LwM2M, and Thread/DTLS/CoAP/LwM2M with an explicit Border Router. The cellular set intentionally spans secure datagram, secure stream/MQTT and CIoT Non-IP LwM2M bindings. HTTP/TLS and OSCORE are valid catalog components but are not enumerated here because the reference set is intentionally bounded.

No candidate has complete end-to-end empirical support from the core-four datasets. Seven have some access/component-context alignment; two CIoT Non-IP candidates have no direct core-four alignment. Component alignment must not be converted into a whole-stack cost.

BLE remote-service, native-GATT gateway-service, UWB remote-service and EPhESOS remote-service families are deferred rather than fabricated. The reasons are explicit mediation/profile/standardisation gaps, not negative preference scores.

Stage 4C does not evaluate coverage, payload, latency, operator availability, infrastructure ownership, regulatory conditions or power budgets. Those are Stage-4D hard scenario facts. Unknown facts remain unresolved and cannot be compensated by preference scoring.
