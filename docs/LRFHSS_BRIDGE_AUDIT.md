# Stage-5B LR-FHSS source-model bridge audit

Stage 5B does not convert the LR-FHSS radio evidence into a whole-device/report estimate. It asks a narrower question first: can the published LR-FHSS radio-state model reproduce the existing 4-byte source traces closely enough to justify payload extrapolation inside the same radio-module boundary?

The primary analytical model is Sanchez-Vital et al., *Energy Performance of LR-FHSS: Analysis and Evaluation* (Sensors 2024, DOI 10.3390/s24175770). The source measurement dataset is DOI 10.5281/zenodo.13838241. An independent LR-FHSS airtime/current paper (arXiv:2408.09954) is retained only as qualitative corroboration that payload-dependent radio modelling is meaningful; its different hardware/configuration is not imported into the bridge.

## Source-model operationalisation

The source publication contains a small internal equation/table inconsistency. The payload-duration equation is rendered with an extra `2 + 6/8 = 2.75` bytes, while the numerical payload-duration values in Table 6 are reproduced by an effective `+3` bytes. STACKWISE preserves both quantities. For payload duration it uses the explicit Table-6-reproduction convention; for frequency-hop count it keeps the rendered expression and floor operation. This is an operational convention for reproducibility, not a claim about the causal origin of the discrepancy.

State-energy accounting separates TX signal time (`header + payload`) from the frequency-hop state. Hop time is therefore not double counted at both TX current and hop current. Incremental transaction energy is calculated above the source-model sleep-current baseline, matching the Stage-2 baseline-subtracted transaction estimand as closely as the available model permits.

## Validation gate

The model is first evaluated at the measured source point: 4-byte FRM payload, +14 dBm, DR8-DR11, confirmed and unconfirmed modes. A versioned deterministic audit tolerance of 2% absolute relative energy error is used to identify close source-trace reproduction. This threshold is not a confidence bound or statistical test.

The unconfirmed traces reproduce closely. The confirmed traces do not: the source traces also show a roughly 50 mA TX plateau, while the source-state model uses 25.7 mA. The audit records this mismatch but does not infer its cause. Therefore confirmed payload extrapolation is prohibited.

## 16-byte benchmark refinement

Only the unconfirmed radio-component model is allowed to extrapolate from 4 to 16 bytes under the source-aligned +14 dBm radio configuration. The diagnostic uses one mandatory Class-A transaction and does not add the 600 s sleep baseline because `reporting_cycle_definition` is still unresolved. This makes the component lower bound conservative: retransmissions, radio sleep, CPU, sensing and other device activity can only add non-negative energy. These values remain radio-module component quantities, not whole-device/report estimates.

If the validated radio component alone exceeds the 0.2 J whole-device budget, an exactly matched operating-profile variant is infeasible by a one-sided lower bound, because additional whole-device contributions cannot make total energy smaller. If the radio component is below the budget, whole-device feasibility remains unresolved.

The frozen Stage-4 matrix is not modified because the generic LR-FHSS candidate still lacks an explicit DR, confirmation mode, hardware/report-cycle definition, and other required operating-profile fields. No DR is selected post hoc by minimum energy.

## Uncertainty

The Stage-3 single-trace epistemic gap remains in force. Deterministic source-model reproduction does not create a population variability distribution, confidence interval, or MCDA sampling distribution.

## Stage 5C — profile variants, not post-hoc DR selection

The Stage-5B source-model result is consumed by Stage 5C as a versioned eight-cell variant family (DR8–DR11 × confirmed/unconfirmed) inside the declared LR1121/+14 dBm source-aligned domain. The family is not a probability distribution and is not exhaustive for all LR-FHSS deployments.

Only unconfirmed DR8/DR10 are decision-sufficient for a one-sided conditional infeasibility statement because their validated radio-component lower bound exceeds the whole-device/report budget. DR9/DR11 remain unresolved for residual device energy; confirmed variants remain blocked by the failed source-model reproduction gate. The generic candidate is not updated.

