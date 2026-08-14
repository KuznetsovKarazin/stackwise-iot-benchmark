from pathlib import Path

import pandas as pd

from stackwise.adapters.specific import LoedGatewayAdapter
from stackwise.loed import build_gateway_day_summary, build_packet_reception_clusters


RECORD = {
    "id": "loed_lorawan_edge_2020",
    "doi": "10.5281/zenodo.4121430",
    "technologies": ["LoRaWAN"],
    "measurement_boundaries": ["gateway_observation"],
    "evidence_grade": "A",
    "licence": {"id": "unknown"},
}


def _write_fixture(path: Path) -> None:
    rows = [
        {
            "time": "2020-05-02T00:00:01.476092Z",
            "device_address": "2000000d",
            "physical_payload": "QA0AACCAyZsKnX86YjTa4IXE2dO3iJc32WU=",
            "gateway": "0000024b0b031c97",
            "crc_status": 1,
            "frequency": 868300000,
            "spreading_factor": 7,
            "bandwidth": 125,
            "code_rate": "4/5",
            "rssi": -106,
            "snr": -7.0,
            "size": -1,
            "mtype": 10,
            "fcnt": 39881,
            "fport": 10.0,
        },
        {
            "time": "2020-05-02T00:00:01.486092Z",
            "device_address": "2000000d",
            "physical_payload": "QA0AACCAyZsKnX86YjTa4IXE2dO3iJc32WU=",
            "gateway": "00800000a0001793",
            "crc_status": 1,
            "frequency": 868300000,
            "spreading_factor": 7,
            "bandwidth": 125,
            "code_rate": "4/5",
            "rssi": -112,
            "snr": -9.0,
            "size": -1,
            "mtype": 10,
            "fcnt": 39881,
            "fport": 10.0,
        },
        {
            "time": "2020-05-02T00:00:05.000000Z",
            "device_address": "-1",
            "physical_payload": "AAAA",
            "gateway": "0000024b0b031c97",
            "crc_status": -1,
            "frequency": 867100000,
            "spreading_factor": 12,
            "bandwidth": 125,
            "code_rate": "4/5",
            "rssi": -125,
            "snr": -24.0,
            "size": -1,
            "mtype": -1,
            "fcnt": -1,
            "fport": -1,
        },
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def test_loed_adapter_preserves_gateway_rows(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")

    result = LoedGatewayAdapter(RECORD, tmp_path).harmonize()
    df = result.observations

    assert result.warnings == []
    assert len(df) == 3
    assert result.metadata["source_profile"] == "sample"
    assert df["observation_id"].is_unique
    assert df["technology"].eq("LoRaWAN").all()
    assert df["measurement_boundary"].eq("gateway_observation").all()
    assert df["delivery_success"].isna().all()
    assert df["source_crc_valid"].tolist() == [True, True, False]
    assert df.loc[0, "source_mtype_bits"] == "010"
    assert df.loc[0, "source_mtype_name"] == "Unconfirmed Data Up"
    assert df.loc[0, "direction"] == "uplink"
    assert df.loc[0, "latitude"] == 51.52183
    assert int(df.loc[0, "source_spreading_factor"]) == 7
    assert int(df.loc[0, "source_physical_payload_bytes"]) > 0


def test_loed_packet_clustering_counts_gateways(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    df = LoedGatewayAdapter(RECORD, tmp_path).harmonize().observations

    clusters = build_packet_reception_clusters(df)
    assert len(clusters) == 1
    first = clusters.sort_values("timestamp_start_utc").iloc[0]
    assert int(first["gateway_count"]) == 2
    assert int(first["reception_rows"]) == 2
    assert first["gateway_time_span_s"] == 0.01
    assert bool(first["crc_valid_all"])


def test_loed_crc_valid_retransmission_remains_one_logical_frame(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    df = LoedGatewayAdapter(RECORD, tmp_path).harmonize().observations
    extra = df.iloc[[0]].copy()
    extra["timestamp_utc"] = pd.to_datetime("2020-05-02T00:00:10Z", utc=True)
    df = pd.concat([df, extra], ignore_index=True)

    clusters = build_packet_reception_clusters(df)
    fingerprint = df.iloc[0]["source_packet_fingerprint"]
    same = clusters[clusters["source_packet_fingerprint"] == fingerprint]
    assert len(same) == 1
    assert int(same.iloc[0]["reception_rows"]) == 3
    assert int(same.iloc[0]["gateway_count"]) == 2
    assert int(same.iloc[0]["repeat_reception_rows"]) == 1


def test_gateway_day_summary_is_reception_conditional(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    df = LoedGatewayAdapter(RECORD, tmp_path).harmonize().observations

    summary = build_gateway_day_summary(df)
    gateway = summary[summary["source_gateway_id"] == "0000024b0b031c97"].iloc[0]
    assert int(gateway["reception_rows"]) == 2
    assert gateway["crc_valid_fraction_of_receptions"] == 0.5
    assert "not end-to-end PDR" in gateway["interpretation"]

def test_loed_prefers_full_archive_when_both_are_extracted(tmp_path: Path):
    sample = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    full = tmp_path / "LoED_LoRaWAN_at_edge_dataset"
    sample.mkdir()
    full.mkdir()
    _write_fixture(sample / "02_05_2020.csv")
    _write_fixture(full / "03_05_2020.csv")

    result = LoedGatewayAdapter(RECORD, tmp_path).harmonize()
    assert result.metadata["source_profile"] == "full"
    assert len(result.observations) == 3
    assert result.observations["source_file"].str.contains("SAMPLE").sum() == 0

def test_loed_ignores_macos_appledouble_csv_artifacts(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    (source / "._02_05_2020.csv").write_bytes(b"\x00\x05\x16\x07\xa2binary-resource-fork")

    result = LoedGatewayAdapter(RECORD, tmp_path).harmonize()

    assert result.warnings == []
    assert len(result.observations) == 3
    assert result.metadata["source_files"] == 1



def test_loed_preserves_out_of_range_source_snr_but_cleans_canonical_field(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    raw = pd.read_csv(source / "02_05_2020.csv")
    raw.loc[0, "snr"] = -128.0
    raw.to_csv(source / "02_05_2020.csv", index=False)

    result = LoedGatewayAdapter(RECORD, tmp_path).harmonize()
    df = result.observations

    assert float(df.loc[0, "source_snr_db_raw"]) == -128.0
    assert pd.isna(df.loc[0, "snr_db"])
    assert result.metadata["source_snr_out_of_range_count"] == 1
    assert "outside [-50, 50]" in result.metadata["snr_cleaning_rule"]


def test_loed_streaming_zip_harmonization_and_full_preference(tmp_path: Path):
    import zipfile
    import pytest

    pytest.importorskip("pyarrow")
    from stackwise.loed_streaming import harmonize_loed_streaming

    raw = tmp_path / "raw"
    raw.mkdir()
    sample_csv = tmp_path / "sample.csv"
    full_csv = tmp_path / "full.csv"
    _write_fixture(sample_csv)
    _write_fixture(full_csv)

    with zipfile.ZipFile(raw / "LoED_LoRaWAN_at_edge_dataset-SAMPLE.zip", "w") as z:
        z.write(sample_csv, arcname="02_05_2020.csv")
        z.writestr("__MACOSX/._02_05_2020.csv", b"\x00\xa2garbage")
    with zipfile.ZipFile(raw / "LoED_LoRaWAN_at_edge_dataset.zip", "w") as z:
        z.write(full_csv, arcname="03_05_2020.csv")

    output = tmp_path / "observations.parquet"
    report = harmonize_loed_streaming(RECORD, raw_dir=raw, output=output, strict=True, chunksize=2)
    df = pd.read_parquet(output)

    assert report["rows"] == 3
    assert report["metadata"]["source_profile"] == "full"
    assert report["metadata"]["execution_mode"] == "streaming_zip_to_parquet"
    assert report["warnings"] == []
    assert report["validation_errors"] == []
    assert len(df) == 3
    assert df["source_file"].str.contains("SAMPLE").sum() == 0
    assert df["observation_id"].is_unique


def test_loed_streaming_validation_and_analysis_ready_match_in_memory(tmp_path: Path):
    import zipfile
    import pytest

    pytest.importorskip("pyarrow")
    from stackwise.loed_streaming import (
        build_loed_analysis_ready_streaming,
        harmonize_loed_streaming,
        validate_loed_streaming,
    )

    raw = tmp_path / "raw"
    raw.mkdir()
    day1 = tmp_path / "day1.csv"
    day2 = tmp_path / "day2.csv"
    _write_fixture(day1)
    _write_fixture(day2)
    with zipfile.ZipFile(raw / "LoED_LoRaWAN_at_edge_dataset.zip", "w") as z:
        z.write(day1, arcname="02_05_2020.csv")
        z.write(day2, arcname="03_05_2020.csv")

    output = tmp_path / "observations.parquet"
    harmonize_loed_streaming(RECORD, raw_dir=raw, output=output, strict=True, chunksize=2)

    summary = validate_loed_streaming(output, tmp_path / "validation")
    assert summary["rows"] == 6
    assert summary["source_files"] == 2
    assert summary["logical_frame_clusters"] == 2
    assert summary["multi_gateway_logical_frames"] == 2
    assert summary["crc_invalid_receptions_excluded_from_logical_frame_clustering"] == 2
    assert summary["structural_checks_passed"] is True
    assert summary["execution_mode"] == "single-pass parquet streaming validation"

    paths = build_loed_analysis_ready_streaming(output, tmp_path / "analysis")
    clusters = pd.read_parquet(paths["packet_clusters_parquet"])
    gateway_day = pd.read_csv(paths["gateway_day_summary"])
    assert len(clusters) == 2
    assert len(gateway_day) >= 2


def test_loed_logical_frame_clustering_excludes_crc_invalid_identity(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    df = LoedGatewayAdapter(RECORD, tmp_path).harmonize().observations

    clusters = build_packet_reception_clusters(df)
    assert len(clusters) == 1
    assert clusters["crc_valid_all"].all()
    assert int(clusters["invalid_crc_receptions"].sum()) == 0
    assert clusters["cluster_semantics"].eq("crc_valid_logical_frame_within_source_day").all()


def test_loed_logical_frame_clustering_is_robust_to_gateway_clock_offset(tmp_path: Path):
    source = tmp_path / "LoED_LoRaWAN_at_edge_dataset-SAMPLE"
    source.mkdir()
    _write_fixture(source / "02_05_2020.csv")
    df = LoedGatewayAdapter(RECORD, tmp_path).harmonize().observations
    valid = df[df["source_crc_valid"] == True].copy()  # noqa: E712
    # Mimic the full-corpus audit: the same CRC-valid PHY frame can be timestamped
    # about one second apart by different gateways. It must remain one logical frame.
    valid.loc[valid.index[1], "timestamp_utc"] = pd.to_datetime("2020-05-02T00:00:02.511092Z", utc=True)
    clusters = build_packet_reception_clusters(valid)
    assert len(clusters) == 1
    row = clusters.iloc[0]
    assert int(row["gateway_count"]) == 2
    assert float(row["gateway_time_span_s"]) > 1.0
    assert "gateway-clock" in row["interpretation"]


def test_loed_validation_reuses_analysis_ready_logical_frames(tmp_path: Path, monkeypatch):
    import zipfile
    import pytest

    pytest.importorskip("pyarrow")
    import stackwise.loed_streaming as ls
    from stackwise.loed_streaming import (
        build_loed_analysis_ready_streaming,
        harmonize_loed_streaming,
        validate_loed_streaming,
    )

    raw = tmp_path / "raw"
    raw.mkdir()
    day1 = tmp_path / "day1.csv"
    _write_fixture(day1)
    with zipfile.ZipFile(raw / "LoED_LoRaWAN_at_edge_dataset.zip", "w") as z:
        z.write(day1, arcname="02_05_2020.csv")

    observations = tmp_path / "observations.parquet"
    harmonize_loed_streaming(RECORD, raw_dir=raw, output=observations, strict=True, chunksize=2)
    analysis_paths = build_loed_analysis_ready_streaming(observations, tmp_path / "analysis")

    # First create a passed raw summary using the explicit cluster artifact.
    first = validate_loed_streaming(
        observations,
        tmp_path / "validation",
        analysis_ready_clusters=analysis_paths["logical_frame_clusters_parquet"],
        reuse_raw_summary=False,
    )
    assert first["logical_frame_artifact_reused"] is True
    assert first["logical_frame_clusters"] == 1

    # A second run must not rebuild logical frames.  If it tries, fail loudly.
    def _forbidden(*args, **kwargs):
        raise AssertionError("logical-frame reconstruction should have been reused")

    monkeypatch.setattr(ls, "build_packet_reception_clusters", _forbidden)
    second = validate_loed_streaming(
        observations,
        tmp_path / "validation",
        analysis_ready_clusters=analysis_paths["logical_frame_clusters_parquet"],
    )
    assert second["raw_validation_reused"] is True
    assert second["logical_frame_artifact_reused"] is True
    assert second["logical_frame_clusters"] == 1
    assert "cached raw structural validation" in second["execution_mode"]


def test_loed_validation_does_not_leak_repository_logical_frame_cache(tmp_path: Path, monkeypatch):
    """A noncanonical Parquet must never reuse the repository's LoED cache."""
    import zipfile
    import pytest

    pytest.importorskip("pyarrow")
    from stackwise.loed_streaming import harmonize_loed_streaming, validate_loed_streaming

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    fake_cache = work / "data/analysis_ready/loed_lorawan_edge_2020"
    fake_cache.mkdir(parents=True)
    pd.DataFrame({
        "gateway_count": [9] * 7,
        "repeat_reception_rows": [0] * 7,
        "gateway_time_span_s": [0.0] * 7,
    }).to_parquet(fake_cache / "logical_frame_reception_clusters.parquet", index=False)

    raw = tmp_path / "raw_cache_isolation"
    raw.mkdir()
    day = tmp_path / "cache_isolation_day.csv"
    _write_fixture(day)
    with zipfile.ZipFile(raw / "LoED_LoRaWAN_at_edge_dataset.zip", "w") as z:
        z.write(day, arcname="02_05_2020.csv")

    output = tmp_path / "noncanonical_observations.parquet"
    harmonize_loed_streaming(RECORD, raw_dir=raw, output=output, strict=True, chunksize=2)
    summary = validate_loed_streaming(output, tmp_path / "validation_cache_isolation")

    assert summary["logical_frame_clusters"] == 1
    assert summary["logical_frame_artifact_reused"] is False
    assert summary["logical_frame_cache_scope"] == "input-local reconstruction"
