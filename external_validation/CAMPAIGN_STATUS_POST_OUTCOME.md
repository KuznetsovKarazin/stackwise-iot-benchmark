# STACKWISE Paper B — External Validation Campaign Status

Current state: **OUTCOME_ANALYSIS_COMPLETE / INDEPENDENT_AUDIT_PENDING**

The protocol was frozen at `PRE_DATA_FROZEN` before outcome-producing analysis. No frozen method rule or Benchmark v1.0.0 object was changed after outcome inspection.

Completed:
- exact HINTS and Vannieuwenborg source transcription under no-silent-imputation policy;
- held-out source checksum verification;
- external scenario portability analysis;
- external candidate readiness analysis;
- held-out source-target gap-closure analysis;
- preregistered LoRaWAN sniffer negative control;
- preference-operator and leave-one-feature-out robustness;
- formal uncertainty contracts;
- factorial accounting robustness over 388,800 deterministic states;
- exact reproduction of the original Experiment-4 accounting point (288/288 states, zero byte difference at L0-L4);
- internal family-level leave-one-scenario-out robustness;
- external portfolio analysis correctly withheld because 0 cases met Tier-C eligibility;
- full automated test suite passes without failures.

Pending high-value item:
- independent blind admissibility audit (35 items; preferably two external experts, minimum one).

Next manuscript action:
- rewrite Paper B to v2 around evidence-readiness + external stress validation; demote portfolio generalisation claim.
