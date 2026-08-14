# Stage 5H — Lifecycle-Cost Accounting and Evidence Contract

Stage 5H freezes the accounting semantics needed for the first STACKWISE decision slice without inventing publication prices.

## Canonical target

`lifecycle_cost_eur` is defined for the first decision slice as the **five-year cumulative differential lifecycle cost attributable to the communication stack/deployment path, in constant 2026 EUR**. Costs common to every candidate (sensor, application logic, common enclosure/cloud workload) are excluded unless a candidate creates a demonstrable differential cost.

The primary benchmark is undiscounted. Three- and ten-year horizons are reserved for later sensitivity analysis. This is an analysis convention, not a market claim.

## Boundary decomposition

Costs are not collapsed prematurely into a per-device scalar. The contract separates:

- incremental device/module CAPEX;
- operator connectivity/service cost per device-year;
- managed access-service cost per device-year where applicable;
- private access-infrastructure CAPEX per site;
- private access-infrastructure OPEX per site-year;
- optional differential backend, maintenance and installation components when source evidence shows that they differ between candidates.

Battery replacement and commodity-energy cost are deferred until a common whole-device energy/lifetime model exists, preventing energy-related double counting.

## Shared infrastructure

Private infrastructure remains a site-level shared term. It must not be divided by the number of devices until a reference deployment scale is explicitly materialised. This is currently a blocker for the private LoRaWAN benchmark.

## Price evidence

Stage 5H contains no publication price observations. Every future numerical cost record must be date-stamped and traceable to an admissible source such as an official operator tariff, official vendor/distributor price, public service price, peer-reviewed cost study or public procurement record. Non-EUR evidence requires a dated exchange-rate source.

`configs/fleet.yml` remains a smoke-test configuration and is explicitly prohibited as publication evidence.

## Current result

Across the 21 Stage-4 feasible candidate incidences:

- 17 use an operator-managed costing mode;
- 2 use a private-owned access mode;
- 2 urban LoRaWAN incidences retain unresolved service ownership rather than inferring it;
- 0 have complete required price evidence;
- 0 have a publication-ready lifecycle-cost scalar.

The next task is targeted cost evidence collection, not scoring.
