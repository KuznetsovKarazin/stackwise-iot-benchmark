# External data licences and access policy

STACKWISE code is Apache-2.0. External data are independent research objects and retain their original licences.

## Rules

1. The live landing page and licence metadata must be reviewed before every first download.
2. A registry value marked `unverified` is not permission to redistribute.
3. Raw external data must not be committed to Git.
4. Download manifests must store the source URL, record version, access date and checksum.
5. Every publication must cite each dataset used, not only STACKWISE.
6. Non-commercial or otherwise restrictive data must not be mixed into a redistributable derived dataset without legal review.

## Registry interpretation

- `verified`: the licence was explicitly visible in the source metadata when the registry was prepared.
- `verify_at_download`: the downloader must retrieve current metadata and the user must inspect it.
- `unknown`: no licence statement was sufficiently clear; download may be possible, but redistribution is prohibited by default.
- `download_only`: the project may automate retrieval from the source, but must not mirror the raw files.

The command `stackwise download` always requires `--accept-license`. If the registry status is not verified, it additionally requires `--accept-unverified-license`.

## InSecTT WSN Power Consumption Dataset

- Registry ID: `insectt_wsn_power_2023`
- DOI: `10.5281/zenodo.7762712`
- Provider: Zenodo
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Licence evidence: the dataset README explicitly states CC BY 4.0
- Redistribution: permitted with attribution; STACKWISE still keeps external raw files out of Git
- Raw measurement: 100 kS/s current traces from PPK II, one ~60 s trace per technology/configuration
- Important limitation: source voltage is not stated in the dataset README, so STACKWISE does not infer watts or joules from the raw current trace
