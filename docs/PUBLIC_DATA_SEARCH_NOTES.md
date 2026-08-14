# Public-data search notes

The initial search deliberately excluded papers whose raw data were not publicly available. No author-contact dependency is part of the core plan.

## Kaggle assessment

Kaggle contains useful BLE RSSI records, but no verified dataset was found that directly replaces the Zenodo power-trace sources for cross-protocol energy calibration. The two BLE records in the active registry are supplementary environment/mobility evidence.

Examples intentionally excluded:

- an IoT energy dataset that measures smart-light electrical consumption rather than communication energy;
- an integrated network-security/energy table whose fields include simulation parameters and mixed source datasets;
- generic intrusion-detection records with protocol labels but no physical energy measurement boundary.

## Continuing discovery

Use:

```bash
stackwise discover "LoRaWAN current energy measurement" --provider zenodo
stackwise discover "BLE power consumption" --provider kaggle
```

The discovery score is only a triage heuristic. Every candidate still requires manual review of provenance, raw-file availability, measurement equipment, licence and accounting boundary before entering `datasets/registry.yml`.
