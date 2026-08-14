# STACKWISE Stage-3 uncertainty model contract

Version: v0.1.18  
Stage: 3 — Uncertainty specification and identifiability audit

## Purpose

Stage 3 defines how uncertainty may be calibrated and propagated from the validated Stage-2 evidence matrix. It does **not** fit MCDA score distributions, invent missing variance, or rank technologies.

The central rule is:

> Uncertainty belongs to a declared estimand and a defensible sampling/dependence unit. It does not arise mechanically from the number of rows or high-frequency samples in a dataset.

The Stage-3 contract separates six uncertainty layers:

1. measurement/calibration uncertainty;
2. within-unit temporal/sample variation;
3. between-unit empirical variability;
4. study/implementation effects;
5. shared-parameter uncertainty;
6. downstream bridge/model structural uncertainty.

These layers must not be collapsed into a single default standard deviation.

## Core-four identifiability regimes

### Vomhoff NB-IoT/LTE-M

Vomhoff is the only core source in which matched configurations contain replicated physical/source runs suitable for immediate empirical calibration.

The calibration unit is `physical_run_id`, not source segment and not source Figure. A future bootstrap or empirical-resampling model must preserve phase energy/duration dependence within the same physical run and must preserve the already identified Figure-4/Figure-5 dependent views.

Recommended initial approach:

- cluster/bootstrap physical runs within matched semantic configurations;
- resample all relevant phases from the same run jointly;
- do not bootstrap the 1,671 source segments independently;
- do not treat source Figure as a replication factor.

The retained Stage-2 materials do not contain structured primary-source device/implementation metadata for Vomhoff. Therefore a device-specific random effect is not estimable and no device model is invented. The replicated run variability remains usable.

### InSecTT

Each technology x reporting-period configuration has one approximately 60 s physical trace. Millions of electrical samples estimate the behaviour of that trace; they do not identify between-run or between-device repeatability.

Therefore:

- direct current/charge records have `n=1` independent unit per configuration;
- population repeatability requires external repeatability evidence, a justified prior, or new repeated traces;
- no standard error may be obtained by dividing a within-trace sample standard deviation by `sqrt(samples)`;
- derived power and capture energy additionally share the same uncertain voltage calibration parameter.

The 20 implied source-voltage values are validation scale checks against rounded publication values. They are not 20 independent voltage measurements and may not be converted into a calibration standard error.

### LR-FHSS

Each DR x confirmation-mode configuration has one physical trace.

Therefore:

- full-capture energy and incremental transaction energy share the same parent trace and cannot be sampled independently;
- population between-run variability is not identified from the dataset;
- each ACK/RX overhead value is one confirmed-minus-unconfirmed matched-DR contrast;
- the four DR contrasts are descriptive, not four replications from one common ACK-overhead population.

External repeatability evidence or a justified prior is required before population uncertainty is assigned to LR-FHSS energy.

### LoED

LoED is a large but hierarchical observational campaign. The large row count does not imply millions of independent observations.

Dependence exists across:

- source days/files;
- gateways;
- device addresses;
- repeated/retransmitted frame observations;
- logical frames;
- RSSI/SNR pairs recorded on the same receptions.

Stage-2 PHY-stratum summaries are adequate evidence inventory records but are insufficient by themselves for stochastic uncertainty sampling. Before a link-quality uncertainty model is calibrated, a bounded-memory grouped artifact must be constructed from the campaign hierarchy.

RSSI and SNR must be calibrated jointly or with their dependence preserved. Reception-row IID bootstrap and `sqrt(n)` uncertainty are prohibited.

CRC-valid fraction and logical-frame gateway diversity remain descriptive reception-side quantities and are not promoted to delivery-probability distributions.

## Why a generic study random effect is not yet valid

The four core datasets do not provide a crossed multi-study design. Study identity is heavily confounded with:

- nominal technology;
- hardware implementation;
- measurement boundary;
- workload;
- deployment environment.

Consequently, a mixed model with an automatically estimated `study_id` random intercept would not identify a general cross-study variance component from the current core-four matrix.

Cross-study variance must later come from one of:

- additional comparable studies with overlapping estimands/configurations;
- an explicitly justified external prior;
- a sensitivity analysis over a declared plausible range.

Until then, `generic_study_random_effect_authorised = false`.

## Correlated uncertainty that must be preserved

The following correlations are structural, not optional modelling refinements.

### Vomhoff

Phases from the same physical run share conditions. Future per-report energy or latency bridges must compose phases using joint run-level draws rather than independently sampled phase means.

### InSecTT

`derived_mean_power_w` and `derived_capture_energy_j` inherit the same calibration parameter `insectt_ppk2_source_voltage_v`. A voltage draw must be shared across all affected configurations in a simulation draw.

### LR-FHSS

Full-capture and incremental transaction energy derived from the same trace share parent-trace uncertainty. ACK/RX overhead is a function of its two matched parent transaction records.

### LoED

RSSI and SNR occur on the same reception events. A future LoRaWAN link model must not sample marginal RSSI and SNR distributions independently unless a validated transformation removes the dependence.

## Distribution-family policy

No global distribution family is fixed at this stage.

Allowed principles:

- prefer empirical/cluster resampling when replicated independent units exist;
- select parametric families only after diagnostics and estimand-specific justification;
- use bounded/probability-support models for probability estimands when they are eventually identified;
- represent single-unit population uncertainty only through justified external priors or explicit sensitivity ranges;
- preserve shared parameters and parent-child dependence.

Prohibited shortcuts:

- default CV or default SD;
- `std = 0.08` fallback for publication analysis;
- lognormal-by-default because a metric is positive;
- normal approximation solely because a row count is large;
- IID bootstrap of source segments or LoED receptions;
- CI from one trace or one ACK contrast.

## Machine-readable artifacts

The contract is encoded in:

- `datasets/schema/uncertainty_model.schema.json`;
- `datasets/uncertainty_taxonomy.yml`;
- `datasets/core_four_uncertainty_policy.yml`;
- `src/stackwise/uncertainty.py`.

The audit writes:

- `results/validation/core_four_uncertainty/summary.json`;
- `results/validation/core_four_uncertainty/uncertainty_plan.csv`;
- `results/validation/core_four_uncertainty/dependence_groups.csv`;
- `results/validation/core_four_uncertainty/calibration_gaps.csv`;
- `results/validation/core_four_uncertainty/run_manifest.json`.

The current policy contains one uncertainty specification for every one of the 14 dataset/metric groups in the 398-record core-four matrix.

## Calibration status expected at v0.1.16

The contract intentionally distinguishes what can be calibrated now from what cannot:

- 2 Vomhoff metric models: `calibrated_nonparametric` (v0.1.18);
- 6 InSecTT/LR-FHSS metric models: `external_prior_required`;
- 2 LoED RSSI/SNR models: `grouped_artifact_required`;
- 4 descriptive metrics/contrasts: `descriptive_only`.

This is not a weakness to hide. It is the scientifically correct consequence of the available replication structure.

## Stage boundary

v0.1.16 specifies uncertainty and identifies calibration requirements. It does not produce publication uncertainty samples.

The next controlled work should be split:

1. calibrate replicated Vomhoff run-level variability with dependence-preserving resampling;
2. build a bounded-memory LoED hierarchical calibration artifact for joint RSSI/SNR campaign variability;
3. perform a targeted evidence review for defensible repeatability/calibration priors for InSecTT and LR-FHSS;
4. only after explicit bridge models exist, propagate empirical + calibration + structural uncertainty to common decision estimands.

Stack definition, scenarios, feasibility filtering, stakeholder weights, SMAA and fleet optimisation remain downstream.


## Stage-3A Vomhoff empirical calibration — v0.1.17

The first calibration step is intentionally split into marginal calibration and joint-resampling review.

For every evidence-eligible logical phase, v0.1.17 emits one energy and one duration observation keyed by the canonical `physical_run_id` and the exact Stage-2 `evidence_id`. The builder requires:

- one value at most for each `evidence_id x physical_run_id`;
- exact reconciliation of run-level means with the Stage-2 evidence estimate;
- exact reconciliation of unique physical-run counts with `n_independent_units`;
- no use of source segments as replication.

The marginal artifact reports observed sample SD and empirical quantiles. These describe **conditional run-to-run variability under the original Vomhoff laboratory configuration**. They are not estimates of generic device-to-device, implementation-to-implementation or cross-study dispersion. No parametric distribution is selected.

Candidate joint-resampling blocks are defined from source Figure family, technology, source application protocol and data object. Within each block, the production audit compares the physical-run sets attached to all energy/duration/phase evidence records. If run sets differ, the final block-bootstrap policy is reviewed before stochastic draws are generated.

Pairwise Pearson/Spearman coefficients are diagnostic summaries over shared physical runs; they do not replace the future dependence-preserving empirical resampler.

Artifacts:

- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/run_level_samples.parquet`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/marginal_calibration.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/resampling_blocks.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/run_set_overlap.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/paired_dependence.csv`;
- `results/validation/vomhoff_uncertainty_calibration/summary.json`.

Publication uncertainty sampling remains blocked until the joint block structure is reviewed and the other Stage-3 calibration gaps remain explicit.


## Stage-3B Vomhoff joint nonparametric bootstrap — v0.1.18

The production Stage-3A overlap audit contains five experimental blocks. Four are complete rectangular repeated-measures blocks. The only partial block is NB-IoT/MQTT: `Data Download` has 44 runs whereas the other phase/metric records have 45, giving 97.78% run-set overlap.

The final within-block resampling policy is:

1. resample `physical_run_id` clusters, never source segments;
2. use one shared sampled-run index vector for all evidence records within the same experimental block;
3. for a partial block, sample from the union run set and preserve the original phase-level missingness;
4. do not impute the missing `Data Download` value and do not delete that run from the other phases;
5. treat bootstrap replicate IDs as local to one block because cross-block dependence is not identified;
6. retain the full empirical bootstrap distribution rather than fitting a normal/lognormal family by default.

The materialised draws quantify **epistemic uncertainty of the conditional phase mean**. They are distinct from the Stage-3A empirical run-to-run distribution, which describes conditional aleatory variation across observed source runs.

Artifacts:

- `datasets/vomhoff_bootstrap_policy.yml`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/block_bootstrap_means.parquet`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/bootstrap_mean_summary.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/bootstrap_block_policy.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/complete_case_sensitivity.csv`;
- `data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/bootstrap_mean_dependence.csv`;
- `results/validation/vomhoff_joint_bootstrap/summary.json`.

This closes the identifiable Vomhoff within-study uncertainty layer. It does not authorise publication-wide uncertainty sampling because LoED hierarchical calibration and justified uncertainty for the single-trace sources remain unresolved.

## Stage 3C — LoED hierarchical grouped calibration

LoED RSSI/SNR uncertainty is not calibrated from reception-row counts. Stage 3C materialises a bounded-memory grouped artifact at `source day × gateway × spreading factor × frequency × bandwidth`. Each cell stores reception counts, RSSI and SNR sums/sums-of-squares, paired RSSI/SNR cross-products, CRC counts and descriptive device/fingerprint counts. This permits exact reconstruction of Stage-2 moments while retaining within-cell and between-cell variation.

For each PHY stratum the artifact reports descriptive variance decomposition and joint RSSI/SNR covariance. These are calibration diagnostics, not IID sampling variances. Gateway-day-PHY cells are not declared independent population replicates. Daily-PHY summaries and lag-1 correlations over consecutive source days are generated only to select a later temporal resampling policy. IID reception bootstrap, IID cell bootstrap, IID day bootstrap and any publication stochastic sampler remain blocked until the production diagnostics are reviewed.

## Stage 3D — LoED temporal campaigns and nonstationarity audit

Stage-3C production data contain 188 source days separated into two acquisition windows by one 386-day gap. Consequently, the time axis is not treated as a single exchangeable sequence. Stage 3D introduces an explicit campaign map and audits temporal dependence separately inside each window.

The audit uses the already materialised `gateway_day_phy_cells.parquet` and `daily_phy_summary.csv`; the 11.26M reception table is not rescanned. For each campaign × PHY × RSSI/SNR series it reports raw and linearly detrended autocorrelation through 14 calendar-day lags, a linear-trend diagnostic and first-difference lag-1 correlation. These are diagnostics, not proofs of stationarity.

Gateway composition is retained at the source-day level. Consecutive-day gateway-set Jaccard overlap and campaign-specific gateway participation are reported, but gateway IDs are not treated as IID bootstrap units. The observed deployment is the conditioning context.

The two campaigns are compared descriptively using campaign-specific RSSI/SNR means and shifts expressed relative to the overall Stage-3C reception-level standard deviation. With only two campaigns, this is a domain-shift/sensitivity diagnostic and not an estimate of a campaign random-effect distribution.

A future LoED sampler, if supported by the production diagnostics, must satisfy all of the following:

1. never construct temporal blocks across the inter-campaign gap;
2. resample source-day clusters rather than reception rows or gateway-day-PHY cells independently;
3. carry all gateway×PHY cells observed on a sampled day together;
4. preserve RSSI/SNR joint moments and cross-PHY/day dependence available in the grouped artifact;
5. choose block length only after campaign-local ACF/nonstationarity review;
6. if stationarity is not defensible, retain the observed campaigns/trajectories as explicit sensitivity scenarios instead of forcing a block bootstrap.

Stage 3D therefore remains a resampling-policy audit. Publication uncertainty sampling and MCDA remain blocked.

## LoED gateway-support confounding before temporal resampling (Stage-3E)

Stage-3D shows strong within-campaign temporal dependence and a large separation between the 2019 and 2020 acquisition windows. It also reveals that gateway support is not common across campaigns: only 2 of the 9 observed gateway IDs appear in both campaigns. Therefore the campaign-level RSSI/SNR shift is a mixture of temporal/environmental change and changing deployment/observation support.

Stage-3E keeps campaign identity fixed and audits common infrastructure support. It reports same-gateway shifts for the two shared gateways, an equal-gateway sensitivity estimate, an observed-reception-weighted shared-gateway estimate, and within-campaign dispersion of gateway-level PHY means. None of these is treated as a causal decomposition. In particular, a shared gateway is not an exchangeable replicate and the two campaigns are not an exchangeable sample of campaigns.

A temporal block bootstrap may only be considered after this audit. If common-gateway shifts remain material, the two campaigns should remain explicit deployment sensitivity scenarios and any within-campaign bootstrap should estimate conditional mean uncertainty separately inside each campaign. If the full-campaign shift largely disappears on common infrastructure, gateway composition is a dominant confounder; cross-campaign pooling still remains prohibited.


## LoED Stage-3E/3F: fixed deployment scenarios and block-length sensitivity

Stage-3E shows that the two LoED acquisition campaigns have substantially different gateway support. The observed cross-campaign difference is therefore not an identified temporal effect and cannot be represented by a campaign random effect. STACKWISE retains the campaigns as fixed deployment scenarios.

Stage-3F evaluates within-campaign conditional mean uncertainty using a non-circular overlapping moving-block bootstrap of **source days**. Candidate block lengths are 3, 7 and 14 days. A sampled day carries its observed gateway composition, all available PHY strata and both RSSI/SNR metrics jointly; gateway IDs are never bootstrapped independently. Missing PHY/day cells remain missing.

The Stage-3F outputs are sensitivity diagnostics only. No candidate block length is selected a priori, no cross-campaign replicate alignment has joint probabilistic meaning, and publication uncertainty sampling remains disabled until the production width sensitivity is reviewed.


## Stage-3G — LoED scenario-indexed robustness family (v0.1.23)

Stage-3F does not support selecting one block length. The 3-day resampler is systematically narrower than the 7-day reference, while 14-day uncertainty remains materially wider for most campaign/metric combinations. Individual PHY strata can be more sensitive than the aggregate medians. Therefore block length is retained as **model uncertainty**, not collapsed to one tuned value.

The two LoED acquisition campaigns remain fixed observed deployment scenarios; no probability is assigned to either campaign. Likewise no probability weights are assigned to 3-, 7- or 14-day block lengths. A joint draw is indexed by `(campaign_id, block_length_days, replicate_id)` and has probabilistic joint meaning only within that scope. The same source-day block indices generate all PHY strata and both RSSI/SNR metrics, preserving the dependence available from the grouped artifact.

Because non-circular moving-block sampling underweights campaign edges at finite sample sizes, its raw bootstrap distribution can be displaced from the observed campaign mean. Stage-3G reports that raw bias and additionally materialises a centered perturbation family:

`centered draw = observed campaign mean + raw draw - mean(raw draws)`

This operation subtracts a constant for each campaign x block-length x PHY x metric and therefore preserves covariance and distributional shape inside the scenario. It removes only the finite-sample **location** bias of the diagnostic resampler. It does not establish stationarity, remove trends, resolve gateway composition confounding or turn the two campaigns into exchangeable population draws.

For each campaign x PHY x metric, Stage-3G also reports the number and fraction of observed source days. This is necessary because some rare strata have weak temporal support despite having a non-zero reception count.

The 3/7/14-day q2.5--q97.5 ranges are combined into an outer **robustness envelope** for reporting and bridge-model sensitivity. The envelope is not a confidence/credible interval and carries no probability interpretation. Publication-wide stochastic sampling remains blocked until the single-trace InSecTT/LR-FHSS uncertainty gaps are addressed.


## Stage-3H — single-trace external evidence review (v0.1.24)

A targeted primary-source review is used for the six InSecTT/LR-FHSS metric families that remain `external_prior_required`. The purpose is to determine whether the source studies or instrument documentation identify a defensible numerical population/repeatability model.

### InSecTT

The publication describes one approximately 60 s power measurement per protocol x reporting-period configuration, sampled at 100 kS/s with Nordic PPK II. It does not report independent replicate runs or configuration-level SD/CV/CI. The PPK II vendor accuracy statement is an instrument metrology bound/statement for average-current measurement; it is **not** between-run or between-device variance and is not converted to a Gaussian SD or other probability distribution.

### LR-FHSS

The associated publication states that state duration/current were measured for several individual transmission processes and that observed differences were negligible. The publication does not report the number of repeats or a numerical dispersion statistic, and the released energy dataset contains one trace per confirmation-mode x DR configuration. Therefore `negligible` is retained as qualitative low-variability evidence and is not translated into a CV. Instrument specifications are likewise not treated as process repeatability.

The source instrumentation is reconciled as N6705A DC Power Analyzer hardware plus 14585A Control and Analysis Software. The Zenodo `Power Analyzer: Keysight 14585A` label remains recorded as provenance rather than silently rewritten as source metadata.

### Consequence

The review identifies zero source-backed numerical population priors. STACKWISE therefore retains mixed uncertainty semantics:

- Vomhoff: empirical nonparametric within-study probability distributions where replicated runs identify them;
- LoED: fixed deployment/model robustness scenarios without scenario probabilities;
- InSecTT/LR-FHSS: explicit single-trace epistemic gaps for population repeatability.

No default CV/SD is introduced. Any later multiplicative envelope used to test decision robustness must be declared a researcher-selected **model-sensitivity scenario**, not an empirical or literature-derived prior.

## Stage-3 closure semantics (v0.1.25)

Stage 3 closes with heterogeneous uncertainty semantics. Closure does **not** mean that every metric has a fitted or inferred probability distribution.

Four resolution classes are retained:

1. `empirical_probability` — replicated within-study evidence supports dependence-preserving nonparametric uncertainty (Vomhoff).
2. `scenario_robustness` — uncertainty is represented by an unweighted deployment/model family rather than one probability law (LoED RSSI/SNR).
3. `explicit_epistemic_gap` — point evidence exists, but population repeatability is not identified from one independent trace and no defensible numerical prior was found (InSecTT/LR-FHSS).
4. `descriptive_nonprobability` — the quantity is intentionally descriptive and is not promoted to a population distribution.

This distinction is binding for downstream bridges. A bridge may propagate an empirical distribution where one exists, evaluate all unweighted robustness scenarios where appropriate, or carry an explicit epistemic/sensitivity flag for single-trace evidence. It may not silently replace an unresolved population variance with a default CV, instrument accuracy, or a qualitative source phrase.

The six residual gaps are retained as provenance-bearing unresolved items. Stage 3 can close because each gap has an explicit semantic treatment and none can be identified further from the current validated evidence without new information. This is different from declaring those uncertainties numerically solved.
