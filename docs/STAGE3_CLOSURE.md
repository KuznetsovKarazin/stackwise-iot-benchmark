# Stage-3 uncertainty closure

STACKWISE Stage 3 is closed for the current validated core-four evidence with **mixed uncertainty semantics**.

Closure is a statement about methodological representation, not a claim that all uncertainties are numerically identified.

| Resolution class | Metric families | Meaning |
|---|---:|---|
| empirical probability | 2 | Vomhoff within-study physical-run uncertainty is materialised nonparametrically with dependence preserved. |
| scenario robustness | 2 | LoED RSSI/SNR retain two fixed campaigns × three unweighted block-length assumptions. |
| explicit epistemic gap | 6 | InSecTT/LR-FHSS point evidence is retained, but population repeatability is not identified from one independent trace. |
| descriptive nonprobability | 4 | CRC/diversity and single matched ACK contrast quantities remain descriptive. |

## Downstream rule

Stage 4 may define candidate communication stacks and hard feasibility/compatibility rules. It must not coerce the four resolution classes into a common probability distribution.

A future bridge must preserve parent uncertainty semantics:

- sample the materialised Vomhoff empirical distribution only within its identified dependence scope;
- evaluate LoED across explicitly indexed campaign/block-length scenarios without probability weights;
- retain InSecTT/LR-FHSS single-trace uncertainty as an epistemic gap or separately labelled sensitivity assumption;
- keep descriptive metrics nonprobabilistic unless a new estimand/evidence source justifies otherwise.

Publication-wide stochastic sampling and MCDA remain disabled at this checkpoint.
