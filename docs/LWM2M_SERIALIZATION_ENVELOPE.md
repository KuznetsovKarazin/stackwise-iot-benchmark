# Stage 5M — LwM2M Send Serialization Surrogate Envelope

## Purpose

Stage 5L deliberately left the serialized LwM2M payload unidentified because the benchmark `64/200 B` values are defined before the LwM2M resource/value representation. Stage 5M closes only the serialization arithmetic, not the missing application semantics.

## Scientific decision

The benchmark does **not** infer a real application Object, Resource count or Resource data model. Instead, two deterministic serialization surrogates are introduced under OMA test Object ID `42769`, which belongs to the test-only Object-ID range and is not authorised for production interpretation.

- `S0_single_opaque_test_resource`: all application octets are represented as one Opaque Resource at `/42769/0/0`.
- `S1_three_opaque_test_resources`: the same total octets are split deterministically across Resources `0`, `1` and `2` under Object Instance `0`. This is a structural stress surrogate, not an empirical claim about report composition.

Opaque is used because it preserves the frozen application byte count as binary octets. OMA maps Opaque to CBOR byte strings for LwM2M CBOR/SenML CBOR and to unpadded URL-safe Base64 for SenML JSON.

## Deterministic serialization sizes

| Pre-LwM2M bytes | Surrogate | LwM2M CBOR | SenML CBOR | SenML JSON |
|---:|---|---:|---:|---:|
| 64 | one Resource | 73 B | 81 B | 114 B |
| 64 | three Resources | 77 B | 94 B | 158 B |
| 200 | one Resource | 209 B | 217 B | 295 B |
| 200 | three Resources | 216 B | 233 B | 340 B |

These lengths are exact **for the declared surrogates only**. They are not estimates of an unknown real application serialization.

## Transport implications

The Stage-5M lengths are injected into the existing Stage-5L standards-based transport accounting. Across `90 variants × 2 surrogates = 180` rows:

- 180/180 have exact surrogate serialization lengths;
- 0/180 identify the canonical application serialization;
- 57/180 strict surrogate raw-volume rows exceed the nominal 500-MB allowance;
- 69/180 deterministic anchor-accounting rows exceed the nominal allowance.

All MQTT/TLS rows in the two 60-s tracking scenarios exceed the nominal raw allowance under both surrogates. For CoAP/DTLS tracking, serialization structure matters: the one-Resource SenML-JSON surrogate is about `478.624 MB/5y`, while the three-Resource SenML-JSON surrogate is about `594.335 MB/5y` at the strict primary-exchange layer. The one-retry and expanded-binding anchors can exceed the nominal allowance even when their strict primary exchange remains below it.

The 900-s smart-meter surrogate rows remain below the nominal allowance even under deterministic anchor accounting.

## What Stage 5M does not establish

Stage 5M does not establish exact billed traffic, TopUp count, real report structure, security-handshake traffic, MQTT pure TCP ACK/segmentation overhead, or device energy. The 1NCE billing aggregation interval remains unresolved. No surrogate is assigned a probability or interpreted as a typical deployment.

## Next gate

Stage 5N should quantify standards-bounded DTLS/TLS establishment/resumption increments and conservative MQTT TCP ACK/segmentation bounds. Those increments must remain separate from the steady-state application exchange. Exact lifecycle connectivity cost can be reconsidered only after those traffic components and billing aggregation semantics are bounded.
