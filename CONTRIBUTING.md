# Contributing

Contributions should preserve evidence provenance and avoid unsupported numerical assumptions.

A new dataset adapter must include:

- a registry entry with DOI or stable landing page;
- a licence/access assessment;
- raw-file discovery rules;
- an explicit measurement boundary;
- unit conversions with tests;
- a fixture that contains no copyrighted raw data;
- a citation entry in `docs/DATASET_CATALOGUE.md`.

Do not commit third-party raw data. Do not infer missing voltage, payload, security mode or coverage condition unless the source documents it. Unknown values must remain null and be reported by the audit.
