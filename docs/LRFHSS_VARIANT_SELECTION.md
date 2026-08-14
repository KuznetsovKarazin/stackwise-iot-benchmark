# Stage-5D LR-FHSS variant-selection identifiability

Stage 5D asks a different question from Stage 5C: **can any one of the eight source-aligned LR-FHSS variants be selected for the benchmark without looking at the energy result?**

The answer is currently no. LoRaWAN provides mechanisms for data-rate, transmit-power and transmission-count control through ADR/LinkADRReq, and it defines distinct confirmed and unconfirmed data-message semantics. Those protocol mechanisms do not identify the configuration used by the synthetic agriculture benchmark. The repository contains no deployment-specific ADR/network-server policy, assigned/observed DR history, confirmation policy, TX-power policy, regional deployment declaration, or generic-hardware alignment.

## Unweighted robustness family

The Stage-5C family is retained exactly as enumerated inside its declared source-model domain:

- DR8–DR11;
- confirmed/unconfirmed;
- +14 dBm;
- 16-byte benchmark payload;
- LR1121 source-model hardware context.

No probability, frequency, preference, or deployment likelihood is attached to a variant. The family contains two conditionally infeasible variants (unconfirmed DR8/DR10) and six unresolved variants; it contains no conditionally feasible variant. Therefore it is neither universally infeasible nor universally feasible.

The family is exhaustive only within the declared source-model domain and is **not exhaustive for the generic LR-FHSS candidate**. The generic candidate remains unresolved.

## Selection dimensions

Data rate may be controlled by ADR or by an explicit device/network profile, but a control mechanism is not a deployment selection rule. Selecting a DR requires deployment evidence such as ADR enablement, network-server/device-profile policy and assigned/observed DR history, or an explicit fixed-DR declaration.

Confirmed/unconfirmed is a message-policy dimension. Stage 5D does not infer it from energy because confirmed and unconfirmed have different protocol semantics.

The +14 dBm TX power and LR1121 radio are source-model alignment constraints, not generic deployment facts. They therefore cannot make the eight variants exhaustive for all LR-FHSS deployments.

## Frozen conclusions

- Stage-4 remains 21 feasible / 39 infeasible / 3 unresolved.
- No LR-FHSS variant is selected.
- No variant probabilities are assigned.
- No whole-device energy bridge is activated.
- Variant outcomes are not projected to the generic candidate.
- Preference scoring and publication MCDA remain prohibited.

Further LR-FHSS work should resume only when real deployment/profile selection evidence or a new matched bridge is available. Otherwise Stage 5 should move to another unresolved hard bridge.
