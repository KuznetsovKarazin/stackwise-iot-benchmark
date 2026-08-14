from __future__ import annotations

__version__ = "0.1.61"

CANONICAL_COLUMNS = [
    "dataset_id", "study_id", "source_file", "observation_id", "technology",
    "access_network", "transport_protocol", "application_protocol", "security_mode",
    "device_model", "radio_module", "firmware_version", "payload_bytes", "direction",
    "reporting_interval_s", "session_policy", "confirmation_mode", "tx_power_dbm",
    "rssi_dbm", "snr_db", "rsrp_dbm", "rsrq_db", "sinr_db", "operator",
    "environment", "latitude", "longitude", "timestamp_utc", "duration_s",
    "sample_count", "voltage_v", "current_a", "peak_current_a", "power_w",
    "mean_power_w", "energy_j", "latency_ms", "delivery_success", "retries",
    "upper_layer_bytes", "measurement_boundary", "evidence_grade", "source_license",
    "source_doi", "notes",
]

MEASUREMENT_BOUNDARIES = {
    "end_device_radio_cycle",
    "full_device_cycle",
    "device_to_gateway",
    "gateway_observation",
    "receiver_observation",
    "ip_to_modem",
    "network_coverage",
    "end_to_end_network",
    "end_to_end_application",
    "authentication",
    "connection",
    "transfer",
    "idle",
    "standby",
}

EVIDENCE_GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "TEST_ONLY": 0}
