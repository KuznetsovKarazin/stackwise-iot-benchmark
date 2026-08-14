from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .adapters.specific import LoedGatewayAdapter
from .io import dump_json
from .loed import build_gateway_day_summary, build_packet_reception_clusters
from .constants import CANONICAL_COLUMNS
from .schema import canonicalise_columns


DEFAULT_CHUNKSIZE = 250_000


def _is_real_daily_member(name: str) -> bool:
    path = Path(name)
    return (
        path.suffix.casefold() == ".csv"
        and not path.name.startswith("._")
        and "__MACOSX" not in path.parts
    )


def _select_archive(raw_dir: Path) -> tuple[Path, str]:
    archives = sorted(raw_dir.rglob("*.zip"))
    full = [p for p in archives if "loed_lorawan_at_edge_dataset" in p.name.casefold() and "sample" not in p.name.casefold()]
    if full:
        return full[0], "full"
    sample = [p for p in archives if "sample" in p.name.casefold()]
    if sample:
        return sample[0], "sample"
    raise FileNotFoundError(f"No LoED dataset ZIP found under {raw_dir}")


def _source_label(archive: Path, member: str) -> str:
    # Match the previous extracted-directory provenance format on the executing
    # platform so v0.1.7 -> v0.1.8 source labels remain stable for existing runs.
    return str(Path(archive.stem) / member)


def _payload_fingerprint(value: Any) -> str | None:
    return LoedGatewayAdapter._payload_fingerprint(value)


def _payload_length(value: Any) -> int | None:
    return LoedGatewayAdapter._payload_length(value)


def _loed_arrow_schema() -> pa.Schema:
    string_columns = {
        "dataset_id", "study_id", "source_file", "observation_id", "technology",
        "access_network", "transport_protocol", "application_protocol", "security_mode",
        "device_model", "radio_module", "firmware_version", "direction", "session_policy",
        "confirmation_mode", "operator", "environment", "measurement_boundary",
        "evidence_grade", "source_license", "source_doi", "notes", "source_gateway_id",
        "source_code_rate", "source_device_address", "source_mtype_bits", "source_mtype_name",
        "source_packet_fingerprint", "source_profile", "source_gateway_model",
    }
    int_columns = {"sample_count", "retries", "source_row_index"}
    bool_columns = {"delivery_success", "source_crc_valid"}
    timestamp_columns = {"timestamp_utc"}
    extra_columns = [
        "source_snr_db_raw", "source_gateway_id", "source_crc_status", "source_crc_valid",
        "source_frequency_hz", "source_spreading_factor", "source_bandwidth_khz",
        "source_code_rate", "source_device_address", "source_frame_counter", "source_fport",
        "source_mtype_raw", "source_mtype_bits", "source_mtype_name", "source_size_field",
        "source_physical_payload_bytes", "source_packet_fingerprint", "source_profile",
        "source_row_index", "source_gateway_altitude_m", "source_gateway_model",
    ]
    names = list(CANONICAL_COLUMNS) + [c for c in extra_columns if c not in CANONICAL_COLUMNS]
    fields: list[pa.Field] = []
    for name in names:
        if name in string_columns:
            dtype = pa.string()
        elif name in int_columns:
            dtype = pa.int64()
        elif name in bool_columns:
            dtype = pa.bool_()
        elif name in timestamp_columns:
            dtype = pa.timestamp("ns", tz="UTC")
        else:
            dtype = pa.float64()
        fields.append(pa.field(name, dtype, nullable=True))
    return pa.schema(fields)


def _transform_chunk(
    adapter: LoedGatewayAdapter,
    chunk: pd.DataFrame,
    *,
    source_label: str,
    source_stem: str,
    row_start: int,
    profile: str,
) -> tuple[pd.DataFrame, int]:
    n = len(chunk)
    row_indices = np.arange(row_start, row_start + n, dtype=np.int64)
    timestamps = pd.to_datetime(chunk["time"], utc=True, errors="coerce")
    gateway = chunk["gateway"].astype("string")
    crc_status = pd.to_numeric(chunk["crc_status"], errors="coerce")
    mtype_bits = chunk["mtype"].map(adapter._mtype_bits)
    direction = mtype_bits.map(adapter._direction_from_mtype)
    mtype_name = mtype_bits.map(adapter.mtype_names)
    payload_hash = chunk["physical_payload"].map(_payload_fingerprint)
    payload_len = chunk["physical_payload"].map(_payload_length)

    out = pd.DataFrame(index=chunk.index)
    out["dataset_id"] = adapter.record["id"]
    out["study_id"] = adapter.record.get("doi") or adapter.record["id"]
    out["source_file"] = source_label
    out["observation_id"] = [
        f"{adapter.record['id']}:{source_stem}:{int(i)}" for i in row_indices
    ]
    out["technology"] = "LoRaWAN"
    out["access_network"] = "LoRaWAN"
    out["direction"] = direction
    out["measurement_boundary"] = "gateway_observation"
    out["evidence_grade"] = adapter.record.get("evidence_grade", "A")
    out["source_license"] = adapter.record.get("licence", {}).get("id", "unknown")
    out["source_doi"] = adapter.record.get("doi")
    out["timestamp_utc"] = timestamps
    out["rssi_dbm"] = pd.to_numeric(chunk["rssi"], errors="coerce")
    source_snr = pd.to_numeric(chunk["snr"], errors="coerce")
    snr_bad = (source_snr < -50.0) | (source_snr > 50.0)
    out["source_snr_db_raw"] = source_snr
    out["snr_db"] = source_snr.where(~snr_bad)
    out["delivery_success"] = pd.NA
    out["retries"] = pd.NA
    out["source_gateway_id"] = gateway
    out["source_crc_status"] = crc_status
    out["source_crc_valid"] = crc_status.map({1.0: True, -1.0: False})
    out["source_frequency_hz"] = pd.to_numeric(chunk["frequency"], errors="coerce")
    out["source_spreading_factor"] = pd.to_numeric(chunk["spreading_factor"], errors="coerce")
    out["source_bandwidth_khz"] = pd.to_numeric(chunk["bandwidth"], errors="coerce")
    out["source_code_rate"] = chunk["code_rate"].astype("string")
    out["source_device_address"] = chunk["device_address"].astype("string")
    out["source_frame_counter"] = pd.to_numeric(chunk["fcnt"], errors="coerce")
    out["source_fport"] = pd.to_numeric(chunk["fport"], errors="coerce")
    out["source_mtype_raw"] = pd.to_numeric(chunk["mtype"], errors="coerce")
    out["source_mtype_bits"] = mtype_bits
    out["source_mtype_name"] = mtype_name
    out["source_size_field"] = pd.to_numeric(chunk["size"], errors="coerce")
    out["source_physical_payload_bytes"] = pd.to_numeric(payload_len, errors="coerce")
    out["source_packet_fingerprint"] = payload_hash
    out["source_profile"] = profile
    out["source_row_index"] = row_indices
    out["latitude"] = gateway.map(
        lambda x: adapter.gateway_metadata.get(str(x), {}).get("latitude") if pd.notna(x) else None
    )
    out["longitude"] = gateway.map(
        lambda x: adapter.gateway_metadata.get(str(x), {}).get("longitude") if pd.notna(x) else None
    )
    out["source_gateway_altitude_m"] = gateway.map(
        lambda x: adapter.gateway_metadata.get(str(x), {}).get("altitude_m") if pd.notna(x) else None
    )
    out["source_gateway_model"] = gateway.map(
        lambda x: adapter.gateway_metadata.get(str(x), {}).get("model") if pd.notna(x) else None
    )
    out["environment"] = gateway.map(
        lambda x: adapter.gateway_metadata.get(str(x), {}).get("location") if pd.notna(x) else None
    )
    out["notes"] = (
        "LoED reception-side gateway observation. Presence of a row is not an absolute "
        "packet-delivery-success denominator; delivery_success intentionally remains null."
    )
    return canonicalise_columns(out), int(snr_bad.sum())


def _fast_validation_errors(frame: pd.DataFrame) -> list[str]:
    """Vectorised equivalent of the canonical checks relevant to LoED.

    JSON-schema row iteration is intentionally avoided for the multi-million-row
    full LoED corpus; all canonical constraints populated by this adapter are
    checked vectorially for every row.
    """
    errors: list[str] = []
    required = [
        "dataset_id", "observation_id", "technology", "measurement_boundary",
        "evidence_grade", "source_license",
    ]
    for column in required:
        if column not in frame.columns or frame[column].isna().any():
            errors.append(f"required field {column!r} contains missing values")
            continue
        if frame[column].astype(str).str.len().eq(0).any():
            errors.append(f"required field {column!r} contains empty strings")
    grades = set(frame["evidence_grade"].dropna().astype(str).unique())
    if not grades.issubset({"A", "B", "C", "D", "TEST_ONLY"}):
        errors.append(f"unexpected evidence_grade values: {sorted(grades)}")
    lat = pd.to_numeric(frame["latitude"], errors="coerce")
    lon = pd.to_numeric(frame["longitude"], errors="coerce")
    if ((lat < -90) | (lat > 90)).any():
        errors.append("latitude outside [-90, 90]")
    if ((lon < -180) | (lon > 180)).any():
        errors.append("longitude outside [-180, 180]")
    for column in ["payload_bytes", "duration_s", "sample_count", "voltage_v", "energy_j", "latency_ms", "retries", "upper_layer_bytes"]:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            if (values < 0).any():
                errors.append(f"{column} contains negative values")
    if frame["delivery_success"].notna().any():
        vals = frame.loc[frame["delivery_success"].notna(), "delivery_success"]
        if not vals.isin([True, False]).all():
            errors.append("delivery_success contains non-boolean values")
    return errors


def harmonize_loed_streaming(
    record: dict[str, Any],
    *,
    raw_dir: str | Path,
    output: str | Path,
    strict: bool = False,
    chunksize: int = DEFAULT_CHUNKSIZE,
) -> dict[str, Any]:
    raw_dir = Path(raw_dir)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    archive, profile = _select_archive(raw_dir)
    adapter = LoedGatewayAdapter(record, raw_dir)
    warnings: list[str] = []
    validation_errors: list[str] = []
    files_meta: list[dict[str, Any]] = []
    all_gateways: set[str] = set()
    all_crc: set[int] = set()
    all_sf: set[int] = set()
    all_freq: set[int] = set()
    all_bw: set[float] = set()
    snr_bad_total = 0
    global_rows = 0
    writer: pq.ParquetWriter | None = None
    arrow_schema: pa.Schema | None = None
    output_tmp = output.with_suffix(output.suffix + ".tmp")
    if output_tmp.exists():
        output_tmp.unlink()

    try:
        with zipfile.ZipFile(archive) as z:
            members = [n for n in z.namelist() if _is_real_daily_member(n)]
            if not members:
                raise ValueError(f"No LoED daily CSV members found in {archive}")
            for member in sorted(members):
                source_label = _source_label(archive, member)
                source_stem = Path(member).stem
                file_rows = 0
                file_gateways: set[str] = set()
                crc_values: set[int] = set()
                file_start: pd.Timestamp | None = None
                file_end: pd.Timestamp | None = None
                try:
                    with z.open(member) as handle:
                        reader = pd.read_csv(handle, chunksize=chunksize, low_memory=False)
                        for raw_chunk in reader:
                            missing = sorted(adapter.required_columns - set(raw_chunk.columns))
                            if missing:
                                raise ValueError(f"missing required columns {missing}")
                            out, snr_bad = _transform_chunk(
                                adapter,
                                raw_chunk,
                                source_label=source_label,
                                source_stem=source_stem,
                                row_start=file_rows,
                                profile=profile,
                            )
                            n = len(out)
                            if n == 0:
                                continue
                            file_rows += n
                            global_rows += n
                            snr_bad_total += snr_bad
                            chunk_errors = _fast_validation_errors(out)
                            for error in chunk_errors:
                                if error not in validation_errors:
                                    validation_errors.append(error)
                            if strict and chunk_errors:
                                raise ValueError("; ".join(chunk_errors[:20]))

                            ts = pd.to_datetime(out["timestamp_utc"], utc=True, errors="coerce")
                            if ts.notna().any():
                                lo, hi = ts.min(), ts.max()
                                file_start = lo if file_start is None else min(file_start, lo)
                                file_end = hi if file_end is None else max(file_end, hi)
                            gateways = set(out["source_gateway_id"].dropna().astype(str).unique())
                            file_gateways.update(gateways)
                            all_gateways.update(gateways)
                            crc = pd.to_numeric(out["source_crc_status"], errors="coerce").dropna()
                            crc_values.update(int(v) for v in crc.unique())
                            all_crc.update(int(v) for v in crc.unique())
                            sf = pd.to_numeric(out["source_spreading_factor"], errors="coerce").dropna()
                            all_sf.update(int(v) for v in sf.unique())
                            freq = pd.to_numeric(out["source_frequency_hz"], errors="coerce").dropna()
                            all_freq.update(int(v) for v in freq.unique())
                            bw = pd.to_numeric(out["source_bandwidth_khz"], errors="coerce").dropna()
                            all_bw.update(float(v) for v in bw.unique())

                            if arrow_schema is None:
                                arrow_schema = _loed_arrow_schema()
                            table = pa.Table.from_pandas(
                                out[list(arrow_schema.names)],
                                schema=arrow_schema,
                                preserve_index=False,
                                safe=False,
                            )
                            if writer is None:
                                writer = pq.ParquetWriter(output_tmp, arrow_schema, compression="zstd")
                            writer.write_table(table)
                except Exception as exc:
                    warnings.append(f"{Path(member).name}: failed during streaming import: {exc}")
                    if strict:
                        raise
                    continue

                files_meta.append({
                    "source_file": source_label,
                    "rows": file_rows,
                    "gateways": sorted(file_gateways),
                    "crc_status_values": sorted(crc_values),
                    "time_start_utc": file_start.isoformat() if file_start is not None else None,
                    "time_end_utc": file_end.isoformat() if file_end is not None else None,
                })
    finally:
        if writer is not None:
            writer.close()

    if writer is None or not output_tmp.exists():
        raise RuntimeError("LoED streaming harmonisation produced no output rows")
    output_tmp.replace(output)

    unknown_gateways = sorted(all_gateways - set(adapter.gateway_metadata))
    if unknown_gateways:
        warnings.append(f"Gateway metadata missing for IDs: {unknown_gateways}")

    metadata = {
        "adapter": adapter.__class__.__name__,
        "execution_mode": "streaming_zip_to_parquet",
        "aggregation_level": "one source row = one gateway reception observation",
        "source_profile": profile,
        "source_archive": archive.name,
        "source_files": len(files_meta),
        "source_rows": global_rows,
        "files": files_meta,
        "gateway_count": len(all_gateways),
        "source_snr_out_of_range_count": int(snr_bad_total),
        "snr_cleaning_rule": "source_snr_db_raw outside [-50, 50] dB mapped to canonical snr_db = null",
        "crc_status_values": sorted(all_crc),
        "spreading_factors": sorted(all_sf),
        "frequency_hz_values": sorted(all_freq),
        "bandwidth_khz_values": sorted(all_bw),
    }
    return {
        "dataset_id": record["id"],
        "rows": global_rows,
        "columns": list(arrow_schema.names) if arrow_schema is not None else list(CANONICAL_COLUMNS),
        "warnings": warnings,
        "validation_errors": validation_errors,
        "metadata": metadata,
    }


def _source_files_from_parquet(path: Path) -> list[str]:
    report_path = path.parent / "harmonization_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            files = report.get("metadata", {}).get("files", [])
            values = [item.get("source_file") for item in files if item.get("source_file")]
            if values:
                return sorted(str(v) for v in values)
        except Exception:
            pass
    dataset = ds.dataset(path, format="parquet")
    table = dataset.to_table(columns=["source_file"])
    values = pc.unique(table["source_file"]).to_pylist()
    return sorted(str(v) for v in values if v is not None)


def _iter_source_frames_single_pass(
    path: Path,
    columns: list[str],
    *,
    batch_size: int = DEFAULT_CHUNKSIZE,
):
    """Yield one complete source-day DataFrame at a time in a single Parquet scan.

    LoED harmonisation writes source days contiguously, but an individual day may
    span several Parquet row groups.  The previous v0.1.8 implementation issued
    one filtered dataset scan per source day; on the full corpus that repeatedly
    rescanned the same monolithic Parquet file and caused multi-hour runtimes.
    This iterator reads the file once, buffers only the current source day, and
    yields it when the source label changes.
    """
    parquet = pq.ParquetFile(path)
    available = set(parquet.schema_arrow.names)
    cols = [c for c in columns if c in available]
    if "source_file" not in cols:
        cols = ["source_file", *cols]

    current_source: str | None = None
    pending: list[pd.DataFrame] = []
    completed: set[str] = set()

    for batch in parquet.iter_batches(batch_size=batch_size, columns=cols):
        frame = batch.to_pandas()
        if frame.empty:
            continue
        source_values = frame["source_file"].astype("string")
        # Batches can cross a row-group/source boundary, so preserve row order
        # and split only at contiguous source_file changes.
        change = source_values.ne(source_values.shift()).fillna(True)
        starts = list(frame.index[change])
        starts.append(frame.index[-1] + 1)
        for left, right in zip(starts[:-1], starts[1:]):
            part = frame.loc[left:right - 1].copy()
            if part.empty:
                continue
            source = str(part["source_file"].iloc[0])
            if current_source is None:
                current_source = source
            if source != current_source:
                if source in completed:
                    raise ValueError(
                        f"source_file {source!r} is not contiguous in Parquet; "
                        "single-pass day reconstruction would be ambiguous"
                    )
                yield current_source, pd.concat(pending, ignore_index=True)
                completed.add(current_source)
                pending = []
                current_source = source
            pending.append(part)

    if current_source is not None and pending:
        yield current_source, pd.concat(pending, ignore_index=True)


def _parquet_input_signature(path: Path) -> dict[str, Any]:
    """Cheap local cache signature for a processed Parquet artifact.

    This is intentionally not a cryptographic content hash.  It is used only to
    decide whether an expensive validation result can be reused locally.  Final
    publication freezes should still record a SHA-256 checksum separately.
    """
    parquet = pq.ParquetFile(path)
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "rows": int(parquet.metadata.num_rows),
        "row_groups": int(parquet.metadata.num_row_groups),
    }


def _logical_frame_summary_from_parquet(path: Path) -> dict[str, Any]:
    """Summarise an already-built logical-frame Parquet using Arrow kernels.

    Only three numeric columns are read.  This avoids rebuilding millions of
    pandas groups during every validation run.
    """
    parquet = pq.ParquetFile(path)
    total = int(parquet.metadata.num_rows)
    if total == 0:
        return {
            "logical_frame_clusters": 0,
            "multi_gateway_logical_frames": 0,
            "multi_gateway_logical_frame_fraction": None,
            "gateway_count_max_per_logical_frame": None,
            "logical_frames_with_repeat_receptions": 0,
            "repeat_reception_rows_total": 0,
            "logical_frame_observation_span_s_p95": None,
            "logical_frame_observation_span_s_max": None,
            "logical_frame_spans_over_1s": 0,
        }

    frame = pd.read_parquet(
        path,
        columns=["gateway_count", "repeat_reception_rows", "gateway_time_span_s"],
    )
    gateway_count = pd.to_numeric(frame["gateway_count"], errors="coerce")
    repeats = pd.to_numeric(frame["repeat_reception_rows"], errors="coerce").fillna(0)
    spans = pd.to_numeric(frame["gateway_time_span_s"], errors="coerce")

    multi_gateway = int((gateway_count > 1).sum())
    max_gateways = int(gateway_count.max())
    frames_with_repeats = int((repeats > 0).sum())
    repeat_rows_total = int(repeats.sum())
    spans_over_1s = int((spans > 1.0).sum())
    finite_spans = spans.dropna().to_numpy(dtype=float)
    span_max = float(np.max(finite_spans)) if finite_spans.size else None
    span_p95 = float(np.percentile(finite_spans, 95)) if finite_spans.size else None

    return {
        "logical_frame_clusters": total,
        "multi_gateway_logical_frames": multi_gateway,
        "multi_gateway_logical_frame_fraction": float(multi_gateway / total) if total else None,
        "gateway_count_max_per_logical_frame": max_gateways,
        "logical_frames_with_repeat_receptions": frames_with_repeats,
        "repeat_reception_rows_total": repeat_rows_total,
        "logical_frame_observation_span_s_p95": None if span_p95 is None else float(span_p95),
        "logical_frame_observation_span_s_max": None if span_max is None else float(span_max),
        "logical_frame_spans_over_1s": spans_over_1s,
    }


def _raw_summary_can_be_reused(
    previous: dict[str, Any] | None,
    *,
    input_signature: dict[str, Any],
    source_files: list[str],
) -> tuple[bool, str | None]:
    if not previous or not previous.get("structural_checks_passed", False):
        return False, None

    previous_signature = previous.get("input_signature")
    if isinstance(previous_signature, dict):
        keys = ("size_bytes", "mtime_ns", "rows", "row_groups")
        if all(previous_signature.get(k) == input_signature.get(k) for k in keys):
            return True, "exact local Parquet signature match"
        return False, None

    # Compatibility path for v0.1.8/v0.1.9 summaries created before signatures
    # were recorded.  It is deliberately transparent in the output metadata.
    if (
        int(previous.get("rows", -1)) == int(input_signature["rows"])
        and int(previous.get("source_files", -1)) == len(source_files)
        and previous.get("source_profile") in {"sample", "full"}
    ):
        return True, "legacy compatibility: row count + source-file count + prior structural pass"
    return False, None


def _scan_raw_loed_summary(
    input_path: Path,
    source_files: list[str],
) -> dict[str, Any]:
    """Scan gateway-level observations once without rebuilding logical frames."""
    needed = [
        "source_file", "observation_id", "source_row_index", "source_profile",
        "source_gateway_id", "rssi_dbm", "snr_db", "source_snr_db_raw",
        "delivery_success", "source_crc_status", "source_crc_valid",
        "source_device_address", "source_spreading_factor", "source_frequency_hz",
        "source_bandwidth_khz",
    ]
    errors: list[str] = []
    source_stems = [Path(value).stem for value in source_files]
    if len(source_stems) != len(set(source_stems)):
        errors.append("duplicate daily CSV stems could collide in observation_id construction")

    rows = 0
    gateways: set[str] = set()
    devices: set[str] = set()
    crc_values: set[int] = set()
    sf_values: set[int] = set()
    freq_values: set[int] = set()
    bw_values: set[float] = set()
    crc_valid = crc_invalid = 0
    delivery_non_null = 0
    snr_bad_count = 0
    rssi_min = np.inf
    rssi_max = -np.inf
    snr_min = np.inf
    snr_max = -np.inf
    raw_snr_min = np.inf
    raw_snr_max = -np.inf
    profile: str | None = None

    for day_index, (source_file, df) in enumerate(
        _iter_source_frames_single_pass(input_path, needed), start=1
    ):
        if df.empty:
            continue
        print(
            f"[LoED validation/raw] day {day_index}/{len(source_files)}: "
            f"{Path(source_file).name} ({len(df):,} reception rows)",
            flush=True,
        )
        rows += len(df)
        if profile is None and df["source_profile"].notna().any():
            profile = str(df["source_profile"].dropna().iloc[0])
        if int(df["observation_id"].duplicated().sum()):
            errors.append(f"duplicate observation IDs within {source_file}")
        idx = pd.to_numeric(df["source_row_index"], errors="coerce")
        if idx.isna().any() or idx.duplicated().any():
            errors.append(f"invalid source_row_index in {source_file}")
        delivery_non_null += int(df["delivery_success"].notna().sum())
        crc = pd.to_numeric(df["source_crc_status"], errors="coerce")
        crc_values.update(int(v) for v in crc.dropna().unique())
        crc_valid += int((df["source_crc_valid"] == True).sum())  # noqa: E712
        crc_invalid += int((df["source_crc_valid"] == False).sum())  # noqa: E712
        sf = pd.to_numeric(df["source_spreading_factor"], errors="coerce")
        sf_values.update(int(v) for v in sf.dropna().unique())
        freq = pd.to_numeric(df["source_frequency_hz"], errors="coerce")
        freq_values.update(int(v) for v in freq.dropna().unique())
        bw = pd.to_numeric(df["source_bandwidth_khz"], errors="coerce")
        bw_values.update(float(v) for v in bw.dropna().unique())
        gateways.update(df["source_gateway_id"].dropna().astype(str).unique())
        device_values = df["source_device_address"].dropna().astype(str)
        devices.update(device_values[device_values != "-1"].unique())
        rssi = pd.to_numeric(df["rssi_dbm"], errors="coerce")
        snr = pd.to_numeric(df["snr_db"], errors="coerce")
        raw_snr = pd.to_numeric(df["source_snr_db_raw"], errors="coerce")
        snr_bad = (raw_snr < -50) | (raw_snr > 50)
        snr_bad_count += int(snr_bad.sum())
        if rssi.notna().any():
            rssi_min = min(rssi_min, float(rssi.min())); rssi_max = max(rssi_max, float(rssi.max()))
        if snr.notna().any():
            snr_min = min(snr_min, float(snr.min())); snr_max = max(snr_max, float(snr.max()))
        if raw_snr.notna().any():
            raw_snr_min = min(raw_snr_min, float(raw_snr.min())); raw_snr_max = max(raw_snr_max, float(raw_snr.max()))
        if ((rssi < -200) | (rssi > 0)).any():
            errors.append(f"RSSI outside [-200, 0] dBm in {source_file}")
        if ((snr < -50) | (snr > 50)).any():
            errors.append(f"canonical SNR outside [-50, 50] dB in {source_file}")

    if delivery_non_null:
        errors.append("delivery_success is populated even though LoED lacks an attempted-transmission denominator")
    if not crc_values.issubset({-1, 1}):
        errors.append(f"unexpected CRC status values: {sorted(crc_values)}")
    if sf_values and not sf_values.issubset(set(range(7, 13))):
        errors.append(f"unexpected spreading factors: {sorted(sf_values)}")

    return {
        "rows": int(rows),
        "source_profile": profile,
        "source_files": len(source_files),
        "gateway_count": len(gateways),
        "device_address_count_non_sentinel": len(devices),
        "duplicate_observation_ids": 0 if not any("duplicate observation IDs" in e for e in errors) else None,
        "delivery_success_non_null": int(delivery_non_null),
        "crc_status_values": sorted(crc_values),
        "crc_valid_receptions": int(crc_valid),
        "crc_invalid_receptions": int(crc_invalid),
        "spreading_factors": sorted(sf_values),
        "frequency_hz_values": sorted(freq_values),
        "bandwidth_khz_values": sorted(bw_values),
        "rssi_dbm_min": None if not np.isfinite(rssi_min) else float(rssi_min),
        "rssi_dbm_max": None if not np.isfinite(rssi_max) else float(rssi_max),
        "snr_db_min": None if not np.isfinite(snr_min) else float(snr_min),
        "snr_db_max": None if not np.isfinite(snr_max) else float(snr_max),
        "source_snr_db_raw_min": None if not np.isfinite(raw_snr_min) else float(raw_snr_min),
        "source_snr_db_raw_max": None if not np.isfinite(raw_snr_max) else float(raw_snr_max),
        "source_snr_out_of_range_count": int(snr_bad_count),
        "source_snr_out_of_range_fraction": float(snr_bad_count / rows) if rows else None,
        "structural_checks_passed": not errors,
        "structural_errors": errors,
    }


def validate_loed_streaming(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    cluster_gap_s: float | None = None,
    analysis_ready_clusters: str | Path | None = None,
    rebuild_clusters: bool = False,
    reuse_raw_summary: bool = True,
) -> dict[str, Any]:
    """Validate LoED with cache-aware separation of raw and logical-frame audits.

    Fast path:
      * reuse a previously passed gateway-level structural summary when the local
        Parquet signature is unchanged (legacy summaries use a transparent
        compatibility check), and
      * summarise the already-built analysis-ready logical-frame Parquet with
        Arrow kernels instead of rebuilding ~5.4 million pandas groups.

    ``rebuild_clusters=True`` intentionally restores the expensive audit path and
    should normally be used only after changing logical-frame semantics.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_files = _source_files_from_parquet(input_path)
    input_signature = _parquet_input_signature(input_path)
    summary_path = output_dir / "loed_validation_summary.json"
    previous: dict[str, Any] | None = None
    if summary_path.exists():
        try:
            previous = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            previous = None

    raw_reused = False
    raw_reuse_basis: str | None = None
    if reuse_raw_summary:
        raw_reused, raw_reuse_basis = _raw_summary_can_be_reused(
            previous, input_signature=input_signature, source_files=source_files
        )

    raw_keys = [
        "rows", "source_profile", "source_files", "gateway_count",
        "device_address_count_non_sentinel", "duplicate_observation_ids",
        "delivery_success_non_null", "crc_status_values", "crc_valid_receptions",
        "crc_invalid_receptions", "spreading_factors", "frequency_hz_values",
        "bandwidth_khz_values", "rssi_dbm_min", "rssi_dbm_max", "snr_db_min",
        "snr_db_max", "source_snr_db_raw_min", "source_snr_db_raw_max",
        "source_snr_out_of_range_count", "source_snr_out_of_range_fraction",
        "structural_checks_passed", "structural_errors",
    ]
    if raw_reused and previous is not None:
        raw_summary = {k: previous.get(k) for k in raw_keys}
        print(f"[LoED validation] reusing passed raw structural summary ({raw_reuse_basis})", flush=True)
    else:
        raw_summary = _scan_raw_loed_summary(input_path, source_files)

    errors = list(raw_summary.get("structural_errors") or [])

    # Cache isolation is part of validation correctness. The repository-level
    # analysis-ready artifact belongs only to the canonical repository LoED
    # observations.parquet. Temporary fixtures, alternative experiments and
    # externally supplied Parquet files must never silently borrow that cache.
    canonical_input = Path(
        "data/processed/loed_lorawan_edge_2020/observations.parquet"
    ).resolve()
    implicit_repository_cache = False
    if analysis_ready_clusters is None:
        try:
            is_canonical_input = input_path.resolve() == canonical_input
        except OSError:
            is_canonical_input = False
        if is_canonical_input:
            analysis_ready_clusters = Path(
                "data/analysis_ready/loed_lorawan_edge_2020/"
                "logical_frame_reception_clusters.parquet"
            )
            implicit_repository_cache = True

    cluster_path = Path(analysis_ready_clusters) if analysis_ready_clusters is not None else None

    cluster_reused = False
    if cluster_path is not None and cluster_path.exists() and not rebuild_clusters:
        print(f"[LoED validation] reusing analysis-ready logical frames: {cluster_path}", flush=True)
        cluster_summary = _logical_frame_summary_from_parquet(cluster_path)
        cluster_reused = True
        manifest_path = cluster_path.parent / "analysis_ready_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                declared = manifest.get("logical_frame_clusters")
                if declared is not None and int(declared) != int(cluster_summary["logical_frame_clusters"]):
                    errors.append(
                        f"analysis-ready manifest logical_frame_clusters={declared} does not match Parquet rows={cluster_summary['logical_frame_clusters']}"
                    )
            except Exception as exc:
                errors.append(f"could not verify analysis-ready manifest: {exc}")
    else:
        # Explicit expensive reconstruction path retained for semantic audits.
        needed = [
            "source_file", "source_packet_fingerprint", "timestamp_utc", "source_gateway_id",
            "rssi_dbm", "snr_db", "source_crc_valid", "source_device_address",
            "source_frame_counter", "source_fport", "source_mtype_bits", "source_mtype_name",
            "source_physical_payload_bytes", "source_spreading_factor", "source_frequency_hz",
            "source_bandwidth_khz", "source_code_rate",
        ]
        validation_cluster_path = output_dir / "logical_frame_validation.parquet"
        if validation_cluster_path.exists():
            validation_cluster_path.unlink()
        writer: pq.ParquetWriter | None = None
        schema: pa.Schema | None = None
        try:
            for day_index, (source_file, df) in enumerate(
                _iter_source_frames_single_pass(input_path, needed), start=1
            ):
                if df.empty:
                    continue
                print(
                    f"[LoED validation/rebuild] day {day_index}/{len(source_files)}: "
                    f"{Path(source_file).name} ({len(df):,} reception rows)",
                    flush=True,
                )
                clusters = build_packet_reception_clusters(df, cluster_gap_s=cluster_gap_s)
                if not clusters.empty:
                    table = pa.Table.from_pandas(clusters, preserve_index=False)
                    if writer is None:
                        schema = table.schema
                        writer = pq.ParquetWriter(validation_cluster_path, schema, compression="zstd")
                    elif schema is not None and table.schema != schema:
                        table = table.cast(schema, safe=False)
                    writer.write_table(table)
        finally:
            if writer is not None:
                writer.close()
        cluster_path = validation_cluster_path
        cluster_summary = _logical_frame_summary_from_parquet(cluster_path) if cluster_path.exists() else {
            "logical_frame_clusters": 0,
            "multi_gateway_logical_frames": 0,
            "multi_gateway_logical_frame_fraction": None,
            "gateway_count_max_per_logical_frame": None,
            "logical_frames_with_repeat_receptions": 0,
            "repeat_reception_rows_total": 0,
            "logical_frame_observation_span_s_p95": None,
            "logical_frame_observation_span_s_max": None,
            "logical_frame_spans_over_1s": 0,
        }

    packet_clusters = int(cluster_summary["logical_frame_clusters"])
    multi_gateway = int(cluster_summary["multi_gateway_logical_frames"])
    span_p95 = cluster_summary["logical_frame_observation_span_s_p95"]
    span_max = cluster_summary["logical_frame_observation_span_s_max"]

    summary = dict(raw_summary)
    summary.update({
        "logical_frame_clusters": packet_clusters,
        "packet_clusters": packet_clusters,
        "multi_gateway_logical_frames": multi_gateway,
        "multi_gateway_packet_clusters": multi_gateway,
        "multi_gateway_logical_frame_fraction": cluster_summary["multi_gateway_logical_frame_fraction"],
        "multi_gateway_cluster_fraction": cluster_summary["multi_gateway_logical_frame_fraction"],
        "gateway_count_max_per_logical_frame": cluster_summary["gateway_count_max_per_logical_frame"],
        "gateway_count_max_per_cluster": cluster_summary["gateway_count_max_per_logical_frame"],
        "logical_frame_observation_span_s_p95": span_p95,
        "logical_frame_observation_span_s_max": span_max,
        "gateway_time_span_s_p95": span_p95,
        "gateway_time_span_s_max": span_max,
        "logical_frames_with_repeat_receptions": int(cluster_summary["logical_frames_with_repeat_receptions"]),
        "repeat_reception_rows_total": int(cluster_summary["repeat_reception_rows_total"]),
        "logical_frame_spans_over_1s": int(cluster_summary["logical_frame_spans_over_1s"]),
        "cluster_gap_s": None,
        "clustering_rule": "CRC-valid exact-PHY logical frame within one source day; wall-clock gap is not used",
        "crc_invalid_receptions_excluded_from_logical_frame_clustering": int(raw_summary.get("crc_invalid_receptions") or 0),
        "structural_checks_passed": not errors,
        "structural_errors": errors,
        "execution_mode": (
            "cached raw structural validation + Arrow summary of analysis-ready logical frames"
            if raw_reused and cluster_reused
            else "single-pass raw structural validation + Arrow summary of analysis-ready logical frames"
            if cluster_reused
            else "explicit logical-frame rebuild validation"
            if rebuild_clusters
            else "single-pass parquet streaming validation"
        ),
        "raw_validation_reused": bool(raw_reused),
        "raw_validation_reuse_basis": raw_reuse_basis,
        "logical_frame_artifact_reused": bool(cluster_reused),
        "logical_frame_cache_scope": (
            "canonical repository input" if cluster_reused and implicit_repository_cache
            else "explicitly supplied artifact" if cluster_reused
            else "input-local reconstruction"
        ),
        "logical_frame_validation_path": str(cluster_path) if cluster_path.exists() else None,
        "cluster_validation_path": str(cluster_path) if cluster_path.exists() else None,
        "input_signature": input_signature,
        "interpretation": (
            "LoED rows are gateway receptions. Analysis-ready clusters are CRC-valid logical LoRaWAN frames "
            "defined by exact PHY-payload fingerprint within one source day. gateway_count is the number of "
            "distinct gateways that observed that logical frame at least once; it is not simultaneous RF "
            "reception multiplicity or absolute packet-delivery probability. Out-of-range source SNR values "
            "are retained in source_snr_db_raw and excluded from canonical SNR statistics."
        ),
        "reference_source": "Bhatia et al., DATA 2020, DOI 10.1145/3419016.3431491; dataset DOI 10.5281/zenodo.4121430",
    })
    dump_json(summary, summary_path)
    return summary

def build_loed_analysis_ready_streaming(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    cluster_gap_s: float | None = None,
) -> dict[str, Path]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_files = _source_files_from_parquet(input_path)
    needed = [
        "source_file", "source_packet_fingerprint", "timestamp_utc", "source_gateway_id",
        "rssi_dbm", "snr_db", "source_crc_valid", "source_device_address",
        "source_frame_counter", "source_fport", "source_mtype_bits", "source_mtype_name",
        "source_physical_payload_bytes", "source_spreading_factor", "source_frequency_hz",
        "source_bandwidth_khz", "source_code_rate",
    ]
    clusters_path = output_dir / "logical_frame_reception_clusters.parquet"
    if clusters_path.exists():
        clusters_path.unlink()
    writer: pq.ParquetWriter | None = None
    schema: pa.Schema | None = None
    gateway_day_parts: list[pd.DataFrame] = []
    total_clusters = 0
    try:
        for day_index, (source_file, df) in enumerate(
            _iter_source_frames_single_pass(input_path, needed), start=1
        ):
            if df.empty:
                continue
            print(
                f"[LoED analysis-ready] day {day_index}/{len(source_files)}: "
                f"{Path(source_file).name} ({len(df):,} reception rows)",
                flush=True,
            )
            clusters = build_packet_reception_clusters(df, cluster_gap_s=cluster_gap_s)
            gateway_day_parts.append(build_gateway_day_summary(df))
            total_clusters += len(clusters)
            if not clusters.empty:
                table = pa.Table.from_pandas(clusters, preserve_index=False)
                if writer is None:
                    schema = table.schema
                    writer = pq.ParquetWriter(clusters_path, schema, compression="zstd")
                elif schema is not None and table.schema != schema:
                    table = table.cast(schema, safe=False)
                writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()

    gateway_day = pd.concat(gateway_day_parts, ignore_index=True) if gateway_day_parts else pd.DataFrame()
    gateway_day_path = output_dir / "gateway_day_summary.csv"
    gateway_day.to_csv(gateway_day_path, index=False)
    manifest_path = output_dir / "analysis_ready_manifest.json"
    dump_json({
        "source_files": len(source_files),
        "logical_frame_clusters": int(total_clusters),
        "packet_clusters": int(total_clusters),
        "cluster_gap_s": None,
        "clustering_rule": "CRC-valid exact-PHY logical frame within one source day; wall-clock gap is not used",
        "logical_frame_clusters_parquet": str(clusters_path),
        "packet_clusters_parquet": str(clusters_path),
        "gateway_day_summary": str(gateway_day_path),
        "interpretation": "gateway_count is distinct-gateway observation diversity for a CRC-valid logical frame; not simultaneous RF multiplicity or absolute PDR",
    }, manifest_path)
    return {
        "logical_frame_clusters_parquet": clusters_path,
        "packet_clusters_parquet": clusters_path,
        "gateway_day_summary": gateway_day_path,
        "manifest": manifest_path,
    }
