from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

DATASET_ID = "loed_lorawan_edge_2020"
DATASET_DOI = "10.5281/zenodo.4121430"
PUBLICATION_DOI = "10.1145/3419016.3431491"
IMPLEMENTATION_CONTEXT_ID = "loed_london_urban_gateway_deployment_2020"
PHY_KEYS = ("source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz")
GATEWAY_PHY_KEYS = ("source_gateway_id",) + PHY_KEYS


class LoEDEvidenceError(ValueError):
    pass


def _stable_id(prefix: str, *values: Any) -> str:
    serialised = "|".join("<NA>" if pd.isna(v) else str(v) for v in values)
    return f"{prefix}-{hashlib.sha1(serialised.encode('utf-8')).hexdigest()[:16]}"


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _normalise_phy(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in PHY_KEYS:
        if column not in out.columns:
            raise LoEDEvidenceError(f"Missing LoED PHY field: {column}")
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _metric_stats(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {"count": 0, "mean": None, "std_population": None, "min": None, "max": None}
    return {
        "count": int(len(values)),
        "mean": float(values.mean()),
        "std_population": float(values.std(ddof=0)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def summarise_reception_frame(
    receptions: pd.DataFrame,
    *,
    group_keys: Iterable[str] = PHY_KEYS,
) -> pd.DataFrame:
    """Summarise reception-side LoED evidence without treating rows as independent trials.

    The returned standard deviations are descriptive population moments over recorded
    gateway receptions. They are *not* standard errors and must not be used to infer
    attempted-transmission reliability.
    """
    group_keys = tuple(group_keys)
    required = set(group_keys) | {"rssi_dbm", "snr_db", "source_crc_valid"}
    missing = sorted(required - set(receptions.columns))
    if missing:
        raise LoEDEvidenceError(f"Missing reception evidence fields: {missing}")

    work = _normalise_phy(receptions)
    for key in group_keys:
        if key == "source_gateway_id":
            work[key] = work[key].astype("string")
    work = work.dropna(subset=list(group_keys)).copy()
    if work.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    grouper = list(group_keys) if len(group_keys) > 1 else group_keys[0]
    for key, group in work.groupby(grouper, sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = {name: value for name, value in zip(group_keys, key_tuple)}
        rssi = _metric_stats(group["rssi_dbm"])
        snr = _metric_stats(group["snr_db"])
        crc = group["source_crc_valid"].dropna()
        crc_known = int(len(crc))
        crc_valid = int((crc == True).sum())  # noqa: E712
        row.update({
            "reception_rows": int(len(group)),
            "rssi_observations": rssi["count"],
            "rssi_mean_dbm": rssi["mean"],
            "rssi_std_population_db": rssi["std_population"],
            "rssi_min_dbm": rssi["min"],
            "rssi_max_dbm": rssi["max"],
            "snr_observations": snr["count"],
            "snr_mean_db": snr["mean"],
            "snr_std_population_db": snr["std_population"],
            "snr_min_db": snr["min"],
            "snr_max_db": snr["max"],
            "crc_known_receptions": crc_known,
            "crc_valid_receptions": crc_valid,
            "crc_invalid_receptions": int(crc_known - crc_valid),
            "crc_valid_fraction_of_recorded_receptions": (
                float(crc_valid / crc_known) if crc_known else None
            ),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def summarise_logical_frame_frame(
    logical_frames: pd.DataFrame,
    *,
    group_keys: Iterable[str] = PHY_KEYS,
) -> pd.DataFrame:
    """Summarise CRC-valid exact-PHY logical-frame observation diversity.

    A logical frame is not asserted to be one physical RF transmission. The summary
    therefore describes observation diversity only.
    """
    group_keys = tuple(group_keys)
    required = set(group_keys) | {"gateway_count", "repeat_reception_rows", "gateway_time_span_s"}
    missing = sorted(required - set(logical_frames.columns))
    if missing:
        raise LoEDEvidenceError(f"Missing logical-frame evidence fields: {missing}")

    work = _normalise_phy(logical_frames)
    work = work.dropna(subset=list(group_keys)).copy()
    if work.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    grouper = list(group_keys) if len(group_keys) > 1 else group_keys[0]
    for key, group in work.groupby(grouper, sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = {name: value for name, value in zip(group_keys, key_tuple)}
        gateway_count = pd.to_numeric(group["gateway_count"], errors="coerce").dropna().astype(float)
        repeat_rows = pd.to_numeric(group["repeat_reception_rows"], errors="coerce").fillna(0)
        spans = pd.to_numeric(group["gateway_time_span_s"], errors="coerce")
        frame_count = int(len(group))
        multi = int((gateway_count > 1).sum())
        repeat = int((repeat_rows > 0).sum())
        spans_over_1s = int((spans > 1.0).sum())
        row.update({
            "logical_frame_count": frame_count,
            "gateway_count_observations": int(len(gateway_count)),
            "mean_distinct_gateway_count": float(gateway_count.mean()) if len(gateway_count) else None,
            "max_distinct_gateway_count": int(gateway_count.max()) if len(gateway_count) else None,
            "multi_gateway_logical_frames": multi,
            "multi_gateway_fraction": float(multi / frame_count) if frame_count else None,
            "logical_frames_with_repeat_receptions": repeat,
            "repeat_reception_frame_fraction": float(repeat / frame_count) if frame_count else None,
            "logical_frame_spans_over_1s": spans_over_1s,
            "span_over_1s_fraction": float(spans_over_1s / frame_count) if frame_count else None,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def _merge_group_summaries(parts: list[pd.DataFrame], group_keys: tuple[str, ...], *, kind: str) -> pd.DataFrame:
    """Merge chunk summaries exactly for count/sum-of-moments based quantities."""
    if not parts:
        return pd.DataFrame()
    frame = pd.concat(parts, ignore_index=True)
    if frame.empty:
        return frame

    if kind == "reception":
        metric_specs = [
            ("rssi", "rssi_observations", "rssi_mean_dbm", "rssi_std_population_db", "rssi_min_dbm", "rssi_max_dbm"),
            ("snr", "snr_observations", "snr_mean_db", "snr_std_population_db", "snr_min_db", "snr_max_db"),
        ]
        rows: list[dict[str, Any]] = []
        grouper = list(group_keys) if len(group_keys) > 1 else group_keys[0]
        for key, group in frame.groupby(grouper, sort=True, dropna=False):
            key_tuple = key if isinstance(key, tuple) else (key,)
            row = {name: value for name, value in zip(group_keys, key_tuple)}
            row["reception_rows"] = int(group["reception_rows"].sum())
            for prefix, count_col, mean_col, std_col, min_col, max_col in metric_specs:
                counts = pd.to_numeric(group[count_col], errors="coerce").fillna(0).astype(float)
                means = pd.to_numeric(group[mean_col], errors="coerce")
                stds = pd.to_numeric(group[std_col], errors="coerce")
                valid = counts > 0
                n = float(counts[valid].sum())
                if n <= 0:
                    row[count_col] = 0
                    row[mean_col] = None
                    row[std_col] = None
                    row[min_col] = None
                    row[max_col] = None
                    continue
                means_v = means[valid].astype(float)
                stds_v = stds[valid].fillna(0).astype(float)
                counts_v = counts[valid]
                total_sum = float((counts_v * means_v).sum())
                total_sumsq = float((counts_v * (stds_v.pow(2) + means_v.pow(2))).sum())
                mean = total_sum / n
                var = max(0.0, total_sumsq / n - mean * mean)
                row[count_col] = int(n)
                row[mean_col] = mean
                row[std_col] = math.sqrt(var)
                row[min_col] = float(pd.to_numeric(group[min_col], errors="coerce").min())
                row[max_col] = float(pd.to_numeric(group[max_col], errors="coerce").max())
            row["crc_known_receptions"] = int(group["crc_known_receptions"].sum())
            row["crc_valid_receptions"] = int(group["crc_valid_receptions"].sum())
            row["crc_invalid_receptions"] = int(group["crc_invalid_receptions"].sum())
            known = row["crc_known_receptions"]
            row["crc_valid_fraction_of_recorded_receptions"] = (
                float(row["crc_valid_receptions"] / known) if known else None
            )
            rows.append(row)
        return pd.DataFrame(rows)

    if kind == "logical":
        rows = []
        grouper = list(group_keys) if len(group_keys) > 1 else group_keys[0]
        for key, group in frame.groupby(grouper, sort=True, dropna=False):
            key_tuple = key if isinstance(key, tuple) else (key,)
            row = {name: value for name, value in zip(group_keys, key_tuple)}
            frame_count = int(group["logical_frame_count"].sum())
            gateway_obs = pd.to_numeric(group["gateway_count_observations"], errors="coerce").fillna(0).astype(float)
            means = pd.to_numeric(group["mean_distinct_gateway_count"], errors="coerce")
            total_gateway_obs = float(gateway_obs.sum())
            weighted_mean = (
                float((gateway_obs * means.fillna(0)).sum() / total_gateway_obs) if total_gateway_obs else None
            )
            row.update({
                "logical_frame_count": frame_count,
                "gateway_count_observations": int(total_gateway_obs),
                "mean_distinct_gateway_count": weighted_mean,
                "max_distinct_gateway_count": int(pd.to_numeric(group["max_distinct_gateway_count"], errors="coerce").max()),
                "multi_gateway_logical_frames": int(group["multi_gateway_logical_frames"].sum()),
                "logical_frames_with_repeat_receptions": int(group["logical_frames_with_repeat_receptions"].sum()),
                "logical_frame_spans_over_1s": int(group["logical_frame_spans_over_1s"].sum()),
            })
            row["multi_gateway_fraction"] = float(row["multi_gateway_logical_frames"] / frame_count) if frame_count else None
            row["repeat_reception_frame_fraction"] = float(row["logical_frames_with_repeat_receptions"] / frame_count) if frame_count else None
            row["span_over_1s_fraction"] = float(row["logical_frame_spans_over_1s"] / frame_count) if frame_count else None
            rows.append(row)
        return pd.DataFrame(rows)

    raise ValueError(f"Unknown merge kind: {kind}")


def _iter_parquet_row_groups(path: str | Path, columns: list[str]):
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    available = set(pf.schema.names)
    missing = sorted(set(columns) - available)
    if missing:
        raise LoEDEvidenceError(f"Parquet file {path} missing columns: {missing}")
    for index in range(pf.num_row_groups):
        yield pf.read_row_group(index, columns=columns).to_pandas()


def build_streaming_summaries(
    receptions_path: str | Path,
    logical_frames_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    reception_parts: list[pd.DataFrame] = []
    gateway_parts: list[pd.DataFrame] = []
    raw_rows = 0
    raw_complete_phy_rows = 0
    raw_snr_observations = 0
    raw_crc_known = 0
    raw_crc_valid = 0

    reception_columns = [
        "source_gateway_id", "source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz",
        "rssi_dbm", "snr_db", "source_crc_valid",
    ]
    for frame in _iter_parquet_row_groups(receptions_path, reception_columns):
        raw_rows += int(len(frame))
        complete = frame.dropna(subset=list(PHY_KEYS))
        raw_complete_phy_rows += int(len(complete))
        raw_snr_observations += int(pd.to_numeric(frame["snr_db"], errors="coerce").notna().sum())
        crc = frame["source_crc_valid"].dropna()
        raw_crc_known += int(len(crc))
        raw_crc_valid += int((crc == True).sum())  # noqa: E712
        reception_parts.append(summarise_reception_frame(frame, group_keys=PHY_KEYS))
        gateway_parts.append(summarise_reception_frame(frame, group_keys=GATEWAY_PHY_KEYS))

    phy = _merge_group_summaries(reception_parts, PHY_KEYS, kind="reception")
    gateway_phy = _merge_group_summaries(gateway_parts, GATEWAY_PHY_KEYS, kind="reception")

    logical_parts: list[pd.DataFrame] = []
    logical_rows = 0
    logical_complete_phy_rows = 0
    logical_columns = [
        "source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz",
        "gateway_count", "repeat_reception_rows", "gateway_time_span_s",
    ]
    for frame in _iter_parquet_row_groups(logical_frames_path, logical_columns):
        logical_rows += int(len(frame))
        complete = frame.dropna(subset=list(PHY_KEYS))
        logical_complete_phy_rows += int(len(complete))
        logical_parts.append(summarise_logical_frame_frame(frame, group_keys=PHY_KEYS))

    logical_phy = _merge_group_summaries(logical_parts, PHY_KEYS, kind="logical")
    diagnostics = {
        "raw_reception_rows": raw_rows,
        "raw_reception_rows_with_complete_phy_key": raw_complete_phy_rows,
        "canonical_snr_observations": raw_snr_observations,
        "crc_known_receptions": raw_crc_known,
        "crc_valid_receptions": raw_crc_valid,
        "crc_invalid_receptions": int(raw_crc_known - raw_crc_valid),
        "logical_frame_rows": logical_rows,
        "logical_frame_rows_with_complete_phy_key": logical_complete_phy_rows,
        "phy_strata": int(len(phy)),
        "gateway_phy_strata": int(len(gateway_phy)),
        "logical_frame_phy_strata": int(len(logical_phy)),
    }
    return phy, gateway_phy, logical_phy, diagnostics


def _base_record(metric_id: str, row: pd.Series, *, source_artifact: str, estimate: float | None,
                 summary_statistic: str, metric_family: str, unit: str, value_semantics: str,
                 derivation_class: str, conditioning: str, empirical_unit: str,
                 intended_use: str, limitations: str, bridge_requirements: str | None,
                 n_source_observations: int | None) -> dict[str, Any]:
    sf = int(row["source_spreading_factor"]) if _finite(row.get("source_spreading_factor")) else None
    freq = int(row["source_frequency_hz"]) if _finite(row.get("source_frequency_hz")) else None
    bw_khz = float(row["source_bandwidth_khz"]) if _finite(row.get("source_bandwidth_khz")) else None
    bw_hz = float(bw_khz * 1000.0) if bw_khz is not None else None
    return {
        "evidence_id": _stable_id("loed-evidence", metric_id, sf, freq, bw_hz, summary_statistic),
        "dataset_id": DATASET_ID,
        "study_id": PUBLICATION_DOI,
        "source_doi": DATASET_DOI,
        "source_license": "unknown",
        "source_artifact": source_artifact,
        "technology": "LoRaWAN",
        "access_network": "LoRaWAN",
        "transport_protocol": None,
        "application_protocol": None,
        "security_mode": None,
        "management_protocol": None,
        "implementation_context_id": IMPLEMENTATION_CONTEXT_ID,
        "device_model": None,
        "radio_module": None,
        "firmware_version": None,
        "measurement_instrument": "Nine LoRaWAN gateways in the LoED London deployment (Cisco, Multitech and Kerlink models)",
        "implementation_notes": (
            "Heterogeneous real-world urban gateway deployment. Device hardware is not controlled as a common implementation factor."
        ),
        "metric_id": metric_id,
        "metric_family": metric_family,
        "unit": unit,
        "value_semantics": value_semantics,
        "estimate": None if estimate is None else float(estimate),
        "summary_statistic": summary_statistic,
        "system_scope": "gateway_receiver",
        "temporal_scope": "logical_frame" if metric_family == "observation_diversity" else "reception_event",
        "accounting_basis": "per_logical_frame" if metric_family == "observation_diversity" else "per_reception",
        "conditioning": conditioning,
        "payload_basis": "not_applicable",
        "baseline_accounting": "not_applicable",
        "ack_rx_accounting": "not_applicable",
        "retry_accounting": "unknown" if metric_family == "observation_diversity" else "not_applicable",
        "path_start": "radio_antenna",
        "path_end": "gateway_receiver",
        "payload_bytes": None,
        "reporting_interval_s": None,
        "direction": None,
        "confirmation_mode": None,
        "tx_power_dbm": None,
        "environment": "heterogeneous_dense_urban_deployment",
        "phase_name": None,
        "data_rate_mode": None,
        "frequency_hz": freq,
        "bandwidth_hz": bw_hz,
        "spreading_factor": sf,
        "coding_rate": None,
        "bit_rate_bps": None,
        "operator": None,
        "empirical_unit": empirical_unit,
        "independence_unit": (
            "not_identified_hierarchical_observations_nested_within_devices_gateways_days_and_repeated_frames"
        ),
        "n_source_observations": n_source_observations,
        "n_independent_units": None,
        "dependence_structure": (
            "Repeated gateway receptions, repeated logical payloads/retransmissions, shared devices, gateways and collection days; "
            "row/frame counts are not independent replication counts."
        ),
        "source_grade": "A",
        "validation_status": "validated_with_limitations",
        "derivation_class": derivation_class,
        "parent_evidence_ids": [],
        "shared_parameter_ids": [],
        "uncertainty_basis": "hierarchical_observational",
        "uncertainty_notes": (
            "Descriptive corpus moments only. Stage 3 must model gateway/day/device/frame dependence; no sqrt(n) confidence interval is authorised."
        ),
        "applicability_domain": (
            f"LoED London urban deployment; recorded gateway observations at SF{sf}, {freq} Hz, {bw_hz} Hz bandwidth."
        ),
        "intended_use": intended_use,
        "bridge_requirements": bridge_requirements,
        "limitations": limitations,
        "notes": (
            "LoED has no complete attempted-transmission denominator. CRC-valid fraction and gateway diversity are reception-side/descriptive only."
        ),
    }


def build_evidence_records(
    phy_summary: pd.DataFrame,
    logical_summary: pd.DataFrame,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in phy_summary.sort_values(list(PHY_KEYS)).iterrows():
        if int(row.get("rssi_observations", 0)) > 0 and _finite(row.get("rssi_mean_dbm")):
            records.append(_base_record(
                "gateway_rssi_dbm", row,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv",
                estimate=float(row["rssi_mean_dbm"]), summary_statistic="mean", metric_family="link_quality", unit="dBm",
                value_semantics="Mean RSSI over recorded gateway receptions in one exact SF/frequency/bandwidth stratum.",
                derivation_class="direct_empirical", conditioning="observed_reception",
                empirical_unit="recorded_gateway_reception", intended_use="bridge_input",
                n_source_observations=int(row["rssi_observations"]),
                bridge_requirements=(
                    "Technology- and deployment-specific calibrated link model required before conversion to feasible_link_probability; "
                    "raw RSSI is not a cross-RAT utility score."
                ),
                limitations=(
                    "Reception-conditioned field measurement aggregated over heterogeneous devices, gateways and time. "
                    "The descriptive standard deviation in the companion artifact is not an inferential standard error."
                ),
            ))
        if int(row.get("snr_observations", 0)) > 0 and _finite(row.get("snr_mean_db")):
            records.append(_base_record(
                "gateway_snr_db", row,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv",
                estimate=float(row["snr_mean_db"]), summary_statistic="mean", metric_family="link_quality", unit="dB",
                value_semantics="Mean canonical SNR over recorded gateway receptions in one exact SF/frequency/bandwidth stratum.",
                derivation_class="direct_empirical", conditioning="observed_reception",
                empirical_unit="recorded_gateway_reception", intended_use="bridge_input",
                n_source_observations=int(row["snr_observations"]),
                bridge_requirements=(
                    "Technology- and deployment-specific calibrated link model required before conversion to feasible_link_probability; "
                    "raw SNR is not a cross-RAT utility score."
                ),
                limitations=(
                    "Reception-conditioned field measurement. Source SNR values outside the documented STACKWISE canonical range are retained "
                    "in source_snr_db_raw but excluded from this canonical SNR summary."
                ),
            ))
        crc_known = int(row.get("crc_known_receptions", 0))
        if crc_known > 0 and _finite(row.get("crc_valid_fraction_of_recorded_receptions")):
            records.append(_base_record(
                "gateway_crc_valid_fraction_of_receptions", row,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv",
                estimate=float(row["crc_valid_fraction_of_recorded_receptions"]), summary_statistic="proportion",
                metric_family="reception_status", unit="proportion",
                value_semantics="CRC-valid fraction among recorded gateway reception rows in one exact SF/frequency/bandwidth stratum.",
                derivation_class="source_reproduced", conditioning="observed_reception",
                empirical_unit="recorded_gateway_reception", intended_use="descriptive",
                n_source_observations=crc_known,
                bridge_requirements="No bridge to delivery_probability is authorised without an external attempted-transmission denominator.",
                limitations=(
                    "Denominator is recorded gateway receptions, not attempted transmissions or unique physical packets; therefore this is not PDR."
                ),
            ))

    for _, row in logical_summary.sort_values(list(PHY_KEYS)).iterrows():
        frame_count = int(row.get("logical_frame_count", 0))
        if frame_count <= 0:
            continue
        if _finite(row.get("mean_distinct_gateway_count")):
            records.append(_base_record(
                "logical_frame_distinct_gateway_count", row,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/logical_frame_phy_summary.csv",
                estimate=float(row["mean_distinct_gateway_count"]), summary_statistic="mean",
                metric_family="observation_diversity", unit="count",
                value_semantics="Mean number of distinct gateways that observed a CRC-valid exact-PHY logical frame within one source day.",
                derivation_class="validated_derived", conditioning="crc_valid_reception",
                empirical_unit="crc_valid_exact_phy_logical_frame_within_source_day", intended_use="descriptive",
                n_source_observations=frame_count,
                bridge_requirements="No direct bridge to delivery_probability or simultaneous RF diversity is authorised.",
                limitations=(
                    "Logical frame identity can merge repeated identical payload observations/retransmissions within a source day and is not one physical RF emission."
                ),
            ))
        if _finite(row.get("multi_gateway_fraction")):
            records.append(_base_record(
                "logical_frame_multi_gateway_fraction", row,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/logical_frame_phy_summary.csv",
                estimate=float(row["multi_gateway_fraction"]), summary_statistic="proportion",
                metric_family="observation_diversity", unit="proportion",
                value_semantics="Fraction of CRC-valid exact-PHY logical frames observed by more than one distinct gateway within one source day.",
                derivation_class="validated_derived", conditioning="crc_valid_reception",
                empirical_unit="crc_valid_exact_phy_logical_frame_within_source_day", intended_use="descriptive",
                n_source_observations=frame_count,
                bridge_requirements="No direct bridge to delivery_probability or simultaneous RF diversity is authorised.",
                limitations=(
                    "This is distinct-gateway observation diversity, not simultaneous RF reception probability and not PDR."
                ),
            ))
    return records


def build_overall_descriptive_records(diagnostics: dict[str, Any], logical_summary: pd.DataFrame) -> list[dict[str, Any]]:
    dummy = pd.Series({"source_spreading_factor": None, "source_frequency_hz": None, "source_bandwidth_khz": None})
    records: list[dict[str, Any]] = []
    known = int(diagnostics.get("crc_known_receptions", 0))
    valid = int(diagnostics.get("crc_valid_receptions", 0))
    if known:
        rec = _base_record(
            "gateway_crc_valid_fraction_of_receptions", dummy,
            source_artifact="data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv",
            estimate=float(valid / known), summary_statistic="proportion", metric_family="reception_status", unit="proportion",
            value_semantics="Corpus-level CRC-valid fraction among all recorded gateway reception rows.",
            derivation_class="source_reproduced", conditioning="observed_reception",
            empirical_unit="recorded_gateway_reception", intended_use="descriptive", n_source_observations=known,
            bridge_requirements="No bridge to delivery_probability is authorised without an external attempted-transmission denominator.",
            limitations="Corpus-level reception-side descriptive quantity; not PDR.",
        )
        rec["evidence_id"] = _stable_id("loed-evidence", rec["metric_id"], "overall")
        rec["applicability_domain"] = "Complete validated LoED corpus across all observed SF/frequency/bandwidth strata."
        records.append(rec)

    if not logical_summary.empty:
        total_frames = int(logical_summary["logical_frame_count"].sum())
        total_multi = int(logical_summary["multi_gateway_logical_frames"].sum())
        total_gateway_obs = int(logical_summary["gateway_count_observations"].sum())
        weighted_gateway_sum = float((logical_summary["mean_distinct_gateway_count"] * logical_summary["gateway_count_observations"]).sum())
        mean_gateway = weighted_gateway_sum / total_gateway_obs if total_gateway_obs else None
        for metric_id, estimate, stat, unit, semantics in [
            ("logical_frame_distinct_gateway_count", mean_gateway, "mean", "count",
             "Corpus-level mean distinct-gateway observation count for CRC-valid exact-PHY logical frames within source day."),
            ("logical_frame_multi_gateway_fraction", (total_multi / total_frames if total_frames else None), "proportion", "proportion",
             "Corpus-level fraction of CRC-valid exact-PHY logical frames observed by more than one distinct gateway."),
        ]:
            if estimate is None:
                continue
            rec = _base_record(
                metric_id, dummy,
                source_artifact="data/analysis_ready/loed_lorawan_edge_2020/logical_frame_phy_summary.csv",
                estimate=float(estimate), summary_statistic=stat, metric_family="observation_diversity", unit=unit,
                value_semantics=semantics, derivation_class="validated_derived", conditioning="crc_valid_reception",
                empirical_unit="crc_valid_exact_phy_logical_frame_within_source_day", intended_use="descriptive",
                n_source_observations=total_frames,
                bridge_requirements="No direct bridge to delivery_probability or simultaneous RF diversity is authorised.",
                limitations="Logical frame is not asserted to equal one physical RF transmission.",
            )
            rec["evidence_id"] = _stable_id("loed-evidence", metric_id, "overall")
            rec["applicability_domain"] = "Complete validated LoED logical-frame artifact across all PHY strata."
            records.append(rec)
    return records


def build_summary(
    phy_summary: pd.DataFrame,
    gateway_phy_summary: pd.DataFrame,
    logical_summary: pd.DataFrame,
    diagnostics: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    total_frames = int(logical_summary["logical_frame_count"].sum()) if not logical_summary.empty else 0
    total_multi = int(logical_summary["multi_gateway_logical_frames"].sum()) if not logical_summary.empty else 0
    total_repeat = int(logical_summary["logical_frames_with_repeat_receptions"].sum()) if not logical_summary.empty else 0
    total_span = int(logical_summary["logical_frame_spans_over_1s"].sum()) if not logical_summary.empty else 0
    max_gateways = int(logical_summary["max_distinct_gateway_count"].max()) if not logical_summary.empty else 0
    by_metric: dict[str, int] = defaultdict(int)
    for record in records:
        by_metric[str(record["metric_id"])] += 1
    return {
        "dataset_id": DATASET_ID,
        "stage": "Stage-2 LoED evidence materialisation",
        **diagnostics,
        "logical_frame_clusters": total_frames,
        "multi_gateway_logical_frames": total_multi,
        "multi_gateway_logical_frame_fraction": float(total_multi / total_frames) if total_frames else None,
        "gateway_count_max_per_logical_frame": max_gateways,
        "logical_frames_with_repeat_receptions": total_repeat,
        "logical_frame_spans_over_1s": total_span,
        "evidence_records": int(len(records)),
        "evidence_records_by_metric": dict(sorted(by_metric.items())),
        "independent_unit_policy": (
            "No independent-unit count is assigned to LoED reception or logical-frame summaries. Observations are hierarchical/dependent across devices, gateways, days and repeated/retransmitted frames."
        ),
        "reliability_policy": (
            "CRC-valid fractions are conditional on recorded receptions. No absolute PDR/delivery probability is materialised because attempted transmissions are unavailable."
        ),
        "logical_frame_policy": (
            "CRC-valid exact-PHY logical frame within source day; no wall-clock gap. Distinct-gateway counts are observation diversity, not simultaneous RF multiplicity."
        ),
        "snr_policy": (
            "Canonical SNR summaries use cleaned snr_db; out-of-range raw source values remain in source_snr_db_raw and are excluded from canonical SNR moments."
        ),
        "phy_stratum_summary_rows": int(len(phy_summary)),
        "gateway_phy_summary_rows": int(len(gateway_phy_summary)),
        "logical_frame_phy_summary_rows": int(len(logical_summary)),
    }
