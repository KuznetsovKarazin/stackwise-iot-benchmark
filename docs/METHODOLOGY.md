# Methodology

## Evidence hierarchy

The historical A-D evidence grade is retained as a **source/provenance grade**:

- **A:** raw observations or traces, sufficient metadata, stable source, and analysis code or clear processing description.
- **B:** raw observations with incomplete metadata or code.
- **C:** aggregate numerical results only.
- **D:** datasheet, expert estimate or qualitative report.

This grade does not describe replication or inferential strength. Stage-2 evidence records therefore carry separate `derivation_class` and `uncertainty_basis` fields. A Grade-A source may still provide only one independent trace for a configuration.

The default research pipeline uses A/B empirical evidence where available. C/D evidence may define standards-backed feasibility, priors or sensitivity bounds but must not be presented as direct measurement.

## Harmonisation rules

1. Preserve original variables before mapping.
2. Convert units only when the source unit is known.
3. Never infer supply voltage from a typical datasheet value without labelling it as an external assumption.
4. Keep energy and coverage evidence separate until a model explicitly connects them.
5. Do not compare RSSI numerically across different radio technologies without technology-specific calibration.
6. Keep public and private deployment costs as scenario inputs, not physical properties of a protocol.
7. Preserve source reproduction separately from STACKWISE-specific analysis-ready transformations.
8. Never promote a reception-conditional quantity to a transmission-attempt probability without a valid denominator.

## Stage-2 empirical evidence model

Cross-dataset evidence is represented by typed evidence records rather than by directly pooling canonical observation rows. The evidence model is defined in `docs/EMPIRICAL_EVIDENCE_MODEL.md`.

Direct comparison requires matching metric semantics and structured measurement boundaries. Values that are only bridgeable remain separate until an explicit transformation model is defined. Incompatible evidence is retained descriptively but cannot populate the corresponding decision criterion.

## Energy integration

For a sampled trace with time `t`, current `I` and voltage `V`:

`E = integral V(t) I(t) dt`.

If voltage is absent, STACKWISE reports charge `integral I(t) dt` and leaves energy missing. A voltage assumption or validated derived voltage may be supplied only through an explicit transformation with recorded provenance.

Whole-device, radio-rail, phase, transaction and full-capture energy are distinct estimands even when all are expressed in joules.

## Statistical units

Within-trace samples, gateway receptions and source-generated segments are not automatically independent experimental units. Every publishable uncertainty estimate must state its empirical unit, independence unit and dependence structure.

Bootstrap or other resampling methods may be used only at a defensible independence level or within an explicitly hierarchical resampling design.

## Cross-study modelling

The current `models.py` implementation is a software smoke/prototype model and is not a publication model. In particular, publication analysis must not pool all positive `energy_j` observations across incompatible boundaries.

Stage 3 will define uncertainty distributions only after the evidence matrix identifies compatible estimands, shared uncertain parameters, study/device effects and non-identifiable variance components.

## MCDA interpretation

The current `mcda.py` implementation is a software smoke/prototype implementation. Its fallback uncertainty and simple common-factor correlation are not empirical Stage-3 uncertainty models.

When publication MCDA is implemented, hard feasibility filtering must precede preference scoring. Rank-1 acceptability will mean the frequency with which an alternative attains rank 1 under the declared uncertainty and stakeholder-weight models. It is not a posterior probability that the alternative is objectively best.

## Validation

Future publication-level validation should include, where applicable:

- leave-one-study/device-out prediction only where replication supports it;
- source-specific residuals;
- calibration coverage;
- source-grade and derivation-class sensitivity;
- accounting-boundary sensitivity;
- correlated versus independent uncertainty ablation;
- alternative normalisation and utility functions;
- feasibility-first versus score-first ablation;
- deterministic versus stochastic decision analysis;
- heterogeneous versus restricted fleet optimisation.
