# STACKWISE Stage-4B component catalog

## Purpose

Stage 4B materialises a versioned, primary-source-backed component catalog for the communication-stack graph defined in Stage 4A. The catalog is a structural interoperability artifact, **not** a ranking table and not a claim that all empirical evidence is directly transferable to every protocol component.

Canonical file: `datasets/stack_component_catalog.yml`.

## Version/source policy

- Standards/profile versions are explicit and frozen in the catalog.
- Newer standards are not silently substituted for source-relevant selected versions.
- A component is `primary_source_verified` only when every material interface claim used by STACKWISE is linked to an official standards body/specification source.
- Absence of a provided interface means only that Stage 4B has not verified that interface for the selected component variant; it is not a universal impossibility proof.
- `EPhESOS` is retained as an empirical evidence family but is not promoted to a verified interoperable component.

## Key modelling decisions

### Cellular IP and Non-IP are separate variants

3GPP EPS/CIoT permits both IP and Non-IP operation. STACKWISE therefore models NB-IoT and LTE-M as separate IP-PDN and Non-IP component variants. UDP/TCP bind only to the IP variants. OMA LwM2M Non-IP binding may bind to the Non-IP variants.

### Bluetooth LE is not automatically IP

Bare Bluetooth LE supplies the link/L2CAP context. GATT and IPSP are separate higher functions. IPv6-over-BLE requires the IPSP/IPv6 adaptation path; InSecTT BLE energy is not silently re-labelled as IPSP energy.

### LoRaWAN LoRa and LR-FHSS are separate access modes

Classical LoRa SF7-SF12 link evidence (LoED) and LR-FHSS transaction-energy evidence are not pooled as one PHY mode. Both may feed the LoRaWAN network/application-server architecture, but their empirical applicability remains mode-specific.

### Alternative protocol bindings are explicit OR requirements

Real protocols such as CoAP and LwM2M have several valid underlying bindings. Stage 4B extends the component contract with `requires_any`: each inner group is an OR-set, while separate groups are cumulative requirements. This avoids false AND semantics and avoids proliferating fake protocol identities solely to express alternative transports.

### Security remains compositional

TLS/DTLS and OSCORE are separate components. Native access security does not substitute for end-to-end security, and end-to-end security does not erase access-layer security.

## Primary verified families

The initial verified core catalog includes:

- 3GPP NB-IoT IP and Non-IP variants;
- 3GPP LTE-M IP and Non-IP variants;
- LoRaWAN LoRa and LR-FHSS modes plus LoRaWAN network/application backend;
- Thread IPv6 mesh and Thread Border Router;
- Bluetooth LE, GATT and IPSP/IPv6;
- IEEE 802.15.4-family UWB data/ranging access;
- UDP, TCP, TLS 1.3, DTLS 1.3;
- CoAP and OSCORE;
- MQTT 5 over plain ordered stream and over TLS-secured stream;
- HTTP/1.1 over plain stream and TLS-secured stream;
- OMA LwM2M 1.2.x.

## Evidence alignment is separate from protocol compatibility

`evidence_alignment` records explicitly state whether a core-four dataset directly matches, partially covers, or does not identify a component boundary. Examples:

- LR-FHSS radio-only energy directly aligns with `lorawan_lrfhss_access` at its measured radio boundary.
- LoED aligns with classical `lorawan_lora_access`, not LR-FHSS link quality.
- Vomhoff NB-IoT/LTE-M phase energy is a partial whole-device/application context, not a radio-only component cost.
- InSecTT BLE does not establish IPSP energy.
- InSecTT UWB remains implementation/revision specific.

## Explicit Stage-4B gaps

The catalog deliberately retains unresolved gaps for EPhESOS interoperability, InSecTT BLE profile alignment, InSecTT UWB revision/profile alignment, Vomhoff HTTP/MQTT version/security bindings, LoED-to-LR-FHSS link transfer, and deployment-specific LoRaWAN backend integration to MQTT/HTTP.

These gaps block unsupported verified stacks but do not block later Stage-4C work on the verified subset.

## Guards

Stage 4B does not authorise MCDA, stakeholder weights, rankings, or default stochastic priors.
