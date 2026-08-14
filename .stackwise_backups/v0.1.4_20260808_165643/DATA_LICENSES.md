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

## Verified dataset licences

### `vomhoff_nbiot_ltem_energy_2023`

- **Title:** NB-IoT vs. LTE-M: Measurement Data of the Energy Consumption of LPWAN Technologies
- **DOI:** 10.5281/zenodo.7603641
- **Provider:** Zenodo
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Licence status:** verified from the downloaded Zenodo record metadata on 2026-08-06
- **Redistribution:** permitted with appropriate attribution
- **STACKWISE policy:** raw files remain in `data/raw/` and are not committed to Git
- **Adapter boundary:** 5 ms device power samples are aggregated by experimental run and phase; the source R-script normalisations are preserved and recorded in provenance columns
