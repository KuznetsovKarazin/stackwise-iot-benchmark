from stackwise.download import _matches


def test_file_glob_override_matching():
    assert _matches("LoED_LoRaWAN_at_edge_dataset.zip", ["LoED_LoRaWAN_at_edge_dataset.zip"])
    assert not _matches("LoED_LoRaWAN_at_edge_dataset-SAMPLE.zip", ["LoED_LoRaWAN_at_edge_dataset.zip"])
