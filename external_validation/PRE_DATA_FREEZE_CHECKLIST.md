# PRE-DATA Freeze Checklist

Do **not** run outcome-producing external-validation analyses until every required item is complete.

- [ ] Exact HINTS Case A hard requirements extracted from the paper/repository.
- [ ] Exact HINTS Case B hard requirements extracted.
- [ ] Exact HINTS Case C hard requirements extracted; repository artifact identified.
- [ ] Exact Vannieuwenborg smart-container requirements extracted.
- [ ] Exact Vannieuwenborg smart-parking requirements extracted.
- [ ] Source locations (section/table/file) recorded for every mapped requirement.
- [ ] Mapping status assigned without looking at STACKWISE output.
- [ ] Kousias selected file downloaded and MD5 verified.
- [ ] Povalac selected file downloaded and MD5 verified.
- [ ] Leenders selected archive downloaded and MD5 verified.
- [ ] Measurement boundary and independence unit recorded for each external source.
- [ ] External adapters pass schema validation without changing frozen taxonomy.
- [ ] Primary metrics and stop rules reviewed and frozen.
- [ ] `python scripts/freeze_external_validation_protocol.py --freeze` passes.
- [ ] Freeze manifest committed/tagged before outcome inspection.

Suggested tag: `paper-b-external-validation-predata-v1`.
