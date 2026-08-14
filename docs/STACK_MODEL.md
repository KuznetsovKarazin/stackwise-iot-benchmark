# STACKWISE Stage 4: typed end-to-end stack model

## Purpose

Stage 4 defines what a communication *stack* is before any decision scenario, preference model, or ranking is introduced. The model must support both IP-native and gateway-mediated IoT systems without pretending that a technology label such as "LoRaWAN", "BLE", or "NB-IoT" is itself a complete end-to-end stack.

## 1. Stack = placed component graph

A candidate is a graph of **component instances**. Each component declares:

- one or more functional `roles`;
- permitted execution `placements`;
- interfaces/capabilities it `provides`;
- interfaces/capabilities it `requires`;
- capabilities it explicitly `forbids`;
- provenance/verification status.

Bindings connect a provided interface of one placed instance to a required interface of another.

This deliberately differs from a five-column "access + transport + security + application + management" table. That tabular view is useful for presentation, but it is not sufficiently expressive as the canonical scientific representation.

## 2. Roles are not mutually exclusive OSI slots

Canonical roles are:

- `access_link`;
- `network_adaptation`;
- `network_protocol`;
- `transport`;
- `end_to_end_security`;
- `application_messaging`;
- `device_management`;
- `gateway_function`;
- `backend_integration`.

A component may occupy more than one role.

### Security

Security is compositional. Native access/network security is represented as a capability of the relevant access component; an additional end-to-end security component may coexist with it. STACKWISE therefore does **not** force one and only one "security-layer technology" into a stack.

### Gateways and non-IP access

Gateway/border-router/network-service functions are explicit components. This prevents a common modelling error: attaching an IP application protocol directly to a non-IP end-device access technology when the actual deployment terminates or bridges the access protocol elsewhere.

## 3. Primary access anchor

Every candidate declares exactly one `primary_access_instance_id`: the access used by the target IoT endpoint. Additional access components may exist elsewhere in the graph, for example as a gateway backhaul. They are not automatically treated as alternatives to the primary device access.

## 4. Structural compatibility

A candidate is structurally compatible only when all hard graph conditions pass, including:

1. every referenced component exists;
2. every instance uses a supported placement;
3. the primary access anchor has the `access_link` role;
4. every binding uses an interface provided by the source and required by the target;
5. every component requirement is satisfied by an incoming binding or an explicitly declared environment capability;
6. forbidden capability conflicts are absent;
7. the data/security carrying graph is acyclic.

Structural incompatibility is not a low score and cannot be compensated by another criterion.

## 5. Hard scenario feasibility is tri-state

Hard feasibility is evaluated separately from structural compatibility:

- `feasible`: all hard predicates pass;
- `infeasible`: at least one hard predicate fails;
- `unresolved`: none fails, but at least one required fact is unknown.

`unresolved` must never be silently converted to `feasible`.

The hard-constraint schema already supports the intended future dimensions:

- coverage;
- payload;
- latency;
- regulatory constraints;
- infrastructure availability;
- power;
- ownership;
- security;
- protocol compatibility;
- placement/deployment.

Stage 4A defines the predicate contract only. Quantitative benchmark scenarios are a later stage.

## 6. What Stage 4A intentionally does not contain

The contract fixtures under `tests/fixtures_stage4_stack_contract.yml` are synthetic and are **not** publication candidate stacks. Stage 4A does not yet assert that any specific real protocol combination is standards-compatible.

Before a real component enters the scientific candidate catalog, its capabilities, requirements, placement constraints, and hard compatibility statements must be verified against primary standards/specification sources and recorded with provenance.

Stage 4A therefore does not contain:

- a publication protocol catalog;
- MCDA scores or ranks;
- stakeholder weights;
- default uncertainty priors;
- benchmark scenario thresholds;
- lifecycle-cost values.

## 7. Stage-3 handoff

The Stage-3 mixed uncertainty state remains authoritative. Future bridge models attached to stack components must preserve the parent evidence semantics:

- empirical nonparametric uncertainty for Vomhoff;
- unweighted robustness scenarios for LoED;
- explicit non-identifiability for InSecTT/LR-FHSS population repeatability;
- descriptive-only quantities remain non-probabilistic.

Stage 4 may define structure and hard compatibility without resolving those uncertainty gaps.

## 8. Next step

Stage 4B should populate a **primary-source-verified component catalog** and explicit compatibility edges for the protocol families needed by the planned benchmark stacks. Only after that catalog is validated should STACKWISE enumerate real candidate end-to-end stacks.
