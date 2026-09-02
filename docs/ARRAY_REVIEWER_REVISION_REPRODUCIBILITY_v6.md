# Array reviewer-revision reproducibility (v0.1.63)

This release adds post-review, non-confirmatory sensitivity analyses requested during peer review of the STACKWISE methodology paper. The frozen Benchmark v1.0.0, pre-specified external portability/held-out-evidence campaign, and frozen C0/C1/C2/E0 classifier are unchanged.

Added analyses:

- class-specific agreement and four-class confusion matrix for the four independent expert groups;
- item-bootstrap 95% CI for Fleiss' kappa (20,000 resamples; seed 20260816);
- operational two-class boundary sensitivity (C0/C1 vs C2/E0);
- majority-consensus and conservative-consensus relabelling sensitivity without overwriting frozen labels;
- downstream readiness sensitivity at external-case, first-slice and full Stage-5E levels;
- uncertainty-label extreme sensitivity for the current readiness contract;
- illustrative readiness-engine computational-overhead benchmark;
- exact replay tests for the frozen v0.1.62 external-campaign outputs.

Primary reviewer-revision report: `docs/REVIEWER_REVISION_EXPERIMENT_REPORT_v6.md`.
Machine-readable outputs: `reviewer_revision/results_public/`.

Interpretive guardrail: these analyses test robustness of the frozen conclusions. They are not used to tune the frozen classifier or to convert the original external portability stress test into a new confirmatory campaign.
