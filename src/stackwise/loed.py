from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


def _stable_cluster_id(source_file: str, fingerprint: str, cluster_index: int) -> str:
    material = f"{source_file}|{fingerprint}|{cluster_index}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def build_packet_reception_clusters(
    receptions: pd.DataFrame,
    *,
    cluster_gap_s: float | None = None,
) -> pd.DataFrame:
    """Aggregate LoED gateway rows into CRC-valid logical-frame clusters.

    LoED gateway UTC clocks are not sufficiently synchronized to reconstruct a
    physical RF emission by a fixed wall-clock window.  The full-corpus audit
    found CRC-valid copies of the same exact PHY payload at three gateways with
    timestamp spans around one second, while confirmed retransmissions can reuse
    the same PHY payload / frame counter over several seconds.

    Therefore the analysis-ready unit is deliberately a *logical LoRaWAN frame*:
    all CRC-valid receptions of the exact physical-payload fingerprint within one
    source day are grouped together.  CRC-invalid receptions remain in the
    harmonised gateway-level table but are excluded here because their decoded
    payload bytes cannot be trusted as an identity key.

    ``gateway_count`` is the number of distinct gateways that observed the
    logical frame at least once.  It is neither simultaneous RF-reception
    multiplicity nor absolute packet-delivery probability.  ``cluster_gap_s`` is
    retained only for API compatibility and is ignored.
    """

    required = {
        "source_file",
        "source_packet_fingerprint",
        "timestamp_utc",
        "source_gateway_id",
        "rssi_dbm",
        "snr_db",
        "source_crc_valid",
    }
    missing = sorted(required - set(receptions.columns))
    if missing:
        raise ValueError(f"LoED logical-frame clustering missing columns: {missing}")

    work = receptions.copy()
    work = work[
        work["source_packet_fingerprint"].notna()
        & (work["source_crc_valid"] == True)  # noqa: E712
    ].copy()
    if work.empty:
        return pd.DataFrame()

    work["timestamp_utc"] = pd.to_datetime(work["timestamp_utc"], utc=True, errors="coerce")
    work = work[work["timestamp_utc"].notna()].copy()
    work.sort_values(
        ["source_file", "source_packet_fingerprint", "timestamp_utc", "source_gateway_id"],
        inplace=True,
        kind="mergesort",
    )

    base_keys = ["source_file", "source_packet_fingerprint"]
    work["source_packet_cluster_index"] = 0
    cluster_keys = base_keys + ["source_packet_cluster_index"]

    def first_nonmissing(series: pd.Series):
        values = series.dropna()
        if values.empty:
            return pd.NA
        if values.dtype == "string" or values.dtype == object:
            values = values[values.astype(str) != "-1"]
            if values.empty:
                return pd.NA
        return values.iloc[0]

    grouped = work.groupby(cluster_keys, sort=False, dropna=False)
    out = grouped.agg(
        timestamp_start_utc=("timestamp_utc", "min"),
        timestamp_end_utc=("timestamp_utc", "max"),
        reception_rows=("source_gateway_id", "size"),
        gateway_count=("source_gateway_id", "nunique"),
        mean_rssi_dbm=("rssi_dbm", "mean"),
        median_rssi_dbm=("rssi_dbm", "median"),
        best_rssi_dbm=("rssi_dbm", "max"),
        worst_rssi_dbm=("rssi_dbm", "min"),
        mean_snr_db=("snr_db", "mean"),
        median_snr_db=("snr_db", "median"),
        best_snr_db=("snr_db", "max"),
        worst_snr_db=("snr_db", "min"),
        valid_crc_receptions=("source_crc_valid", "size"),
    ).reset_index()
    out["invalid_crc_receptions"] = 0

    for column in [
        "source_device_address",
        "source_frame_counter",
        "source_fport",
        "source_mtype_bits",
        "source_mtype_name",
        "source_physical_payload_bytes",
        "source_spreading_factor",
        "source_frequency_hz",
        "source_bandwidth_khz",
        "source_code_rate",
    ]:
        if column in work.columns:
            values = grouped[column].agg(first_nonmissing).reset_index(name=column)
            out = out.merge(values, on=cluster_keys, how="left")

    gateway_lists = grouped["source_gateway_id"].agg(
        lambda s: ";".join(sorted(set(str(v) for v in s.dropna())))
    ).reset_index(name="gateway_ids")
    out = out.merge(gateway_lists, on=cluster_keys, how="left")

    out["gateway_time_span_s"] = (
        out["timestamp_end_utc"] - out["timestamp_start_utc"]
    ).dt.total_seconds()
    out["repeat_reception_rows"] = out["reception_rows"] - out["gateway_count"]
    out["crc_valid_any"] = True
    out["crc_valid_all"] = True
    out["packet_cluster_id"] = [
        _stable_cluster_id(str(sf), str(fp), 0)
        for sf, fp in zip(out["source_file"], out["source_packet_fingerprint"])
    ]
    out["cluster_gap_s"] = pd.NA
    out["cluster_semantics"] = "crc_valid_logical_frame_within_source_day"
    out["interpretation"] = (
        "CRC-valid logical-frame reception cluster. gateway_count is the number of distinct gateways "
        "that observed the exact PHY frame at least once; timestamp span may include gateway-clock "
        "offsets and retransmissions. It is not simultaneous reception multiplicity or absolute PDR."
    )
    return out


def build_gateway_day_summary(receptions: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp_utc", "source_gateway_id", "rssi_dbm", "snr_db", "source_crc_valid"}
    missing = sorted(required - set(receptions.columns))
    if missing:
        raise ValueError(f"LoED gateway-day summary missing columns: {missing}")

    work = receptions.copy()
    work["timestamp_utc"] = pd.to_datetime(work["timestamp_utc"], utc=True, errors="coerce")
    work = work[work["timestamp_utc"].notna()].copy()
    work["date_utc"] = work["timestamp_utc"].dt.date.astype(str)
    if "source_device_address" in work.columns:
        valid_device = work["source_device_address"].astype("string")
        work["device_for_count"] = valid_device.where(valid_device != "-1")
    else:
        work["device_for_count"] = pd.NA

    keys = ["date_utc", "source_gateway_id"]
    out = work.groupby(keys, dropna=False).agg(
        reception_rows=("source_gateway_id", "size"),
        valid_crc_receptions=("source_crc_valid", lambda s: int((s == True).sum())),  # noqa: E712
        invalid_crc_receptions=("source_crc_valid", lambda s: int((s == False).sum())),  # noqa: E712
        unique_device_addresses=("device_for_count", "nunique"),
        median_rssi_dbm=("rssi_dbm", "median"),
        p10_rssi_dbm=("rssi_dbm", lambda s: float(np.nanpercentile(pd.to_numeric(s, errors="coerce"), 10))),
        p90_rssi_dbm=("rssi_dbm", lambda s: float(np.nanpercentile(pd.to_numeric(s, errors="coerce"), 90))),
        median_snr_db=("snr_db", "median"),
    ).reset_index()
    out["crc_valid_fraction_of_receptions"] = (
        out["valid_crc_receptions"] / out["reception_rows"]
    )
    out["interpretation"] = (
        "CRC-valid fraction is conditional on recorded gateway receptions and is not end-to-end PDR."
    )
    return out


def write_analysis_ready(
    processed_path: str | Path,
    output_dir: str | Path,
    *,
    cluster_gap_s: float = 1.0,
) -> dict[str, Path]:
    processed_path = Path(processed_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    needed = [
        "source_file",
        "source_packet_fingerprint",
        "timestamp_utc",
        "source_gateway_id",
        "rssi_dbm",
        "snr_db",
        "source_crc_valid",
        "source_device_address",
        "source_frame_counter",
        "source_fport",
        "source_mtype_bits",
        "source_mtype_name",
        "source_physical_payload_bytes",
        "source_spreading_factor",
        "source_frequency_hz",
        "source_bandwidth_khz",
        "source_code_rate",
    ]
    import pyarrow.parquet as pq

    available = set(pq.ParquetFile(processed_path).schema.names)
    columns = [c for c in needed if c in available]
    receptions = pd.read_parquet(processed_path, columns=columns)

    clusters = build_packet_reception_clusters(receptions, cluster_gap_s=cluster_gap_s)
    gateway_day = build_gateway_day_summary(receptions)

    clusters_path = output_dir / "packet_reception_clusters.parquet"
    clusters_csv = output_dir / "packet_reception_clusters.csv"
    gateway_day_path = output_dir / "gateway_day_summary.csv"
    clusters.to_parquet(clusters_path, index=False)
    clusters.to_csv(clusters_csv, index=False)
    gateway_day.to_csv(gateway_day_path, index=False)
    return {
        "packet_clusters_parquet": clusters_path,
        "packet_clusters_csv": clusters_csv,
        "gateway_day_summary": gateway_day_path,
    }
