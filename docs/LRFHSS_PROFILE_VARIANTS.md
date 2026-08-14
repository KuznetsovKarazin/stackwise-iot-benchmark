# Stage-5C LR-FHSS operating-profile variants

Stage 5C converts the generic LR-FHSS agriculture profile into a versioned, source-aligned **variant family** without choosing a deployment mode. The family enumerates DR8–DR11 crossed with confirmed/unconfirmed operation at the Stage-5B source-model domain (+14 dBm, 16-byte benchmark payload, LR1121 radio context).

The enumeration is exhaustive only inside that declared source-model domain. It is **not** exhaustive for the generic LR-FHSS candidate, and no probability or frequency is attached to any variant. DR or confirmation mode must not be selected post hoc from the energy result.

## Two different completeness notions

A variant remains incomplete for a whole-device numeric bridge while retry policy, whole-device hardware and reporting-cycle accounting remain unresolved. This does not prevent a narrower one-sided decision when a validated radio component is already above the whole-device budget.

For unconfirmed DR8 and DR10, the Stage-5B 16-byte radio-component lower bound is about 0.2044 J, already above the 0.2 J whole-device/report budget. Under an exactly source-aligned variant this is decision-sufficient for **conditional infeasibility**, because additional device energy or retries cannot reduce the total. No whole-device energy value is inferred.

For unconfirmed DR9/DR11, radio energy remains below the budget and therefore cannot establish feasibility; residual whole-device/report energy is unresolved. Confirmed variants remain unresolved because the source model failed the Stage-5B 4-byte reproduction gate.

## Generic candidate

The frozen generic `lorawan_lrfhss_lwm2m_nonip` candidate remains unresolved. Variant-level outcomes are not projected upward without deployment/profile selection evidence or an explicit benchmark refinement. Stage-4 remains 21 feasible / 39 infeasible / 3 unresolved.

## Prohibited inferences

- selecting the lowest-energy DR or unconfirmed mode after seeing the result;
- assigning probabilities to the enumerated variants;
- interpreting radio energy below 0.2 J as whole-device feasibility;
- using confirmed-model numbers after the source-model gate failed;
- converting deterministic single-trace/model outputs into a population distribution;
- preference scoring or publication MCDA.
