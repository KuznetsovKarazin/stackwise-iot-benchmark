from stackwise.registry import DatasetRegistry


def test_registry_validates():
    registry = DatasetRegistry()
    registry.validate()
    assert len(registry.records) >= 10
    assert all(record.data["empirical"] for record in registry.records)


def test_core_records_exist():
    registry = DatasetRegistry()
    for dataset_id in [
        "insectt_wsn_power_2023",
        "vomhoff_nbiot_ltem_energy_2023",
        "loed_lorawan_edge_2020",
        "lorawan_lrfhss_energy_2024",
    ]:
        assert registry.get(dataset_id).data["status"] == "core"
