from __future__ import annotations

import math
from dataclasses import dataclass


SOURCE_VOLTAGE_V = 3.3
SLEEP_CURRENT_A = 0.5e-6
TX_CURRENT_A = 25.7e-3
HOP_CURRENT_A = 12.3e-3
HOP_DURATION_S = 0.225e-3
HEADER_DURATION_PER_COPY_S = 233.472e-3
PAYLOAD_FRAGMENT_DURATION_S = 102.4e-3
LORAWAN_PHY_OVERHEAD_BYTES = 13


@dataclass(frozen=True)
class AirtimeBreakdown:
    dr: int
    frm_payload_bytes: int
    phy_payload_bytes: int
    header_repetitions: int
    fragment_bytes: int
    header_duration_s: float
    payload_duration_s: float
    rendered_eq6_payload_duration_s: float
    hop_count: int
    hop_duration_s: float
    tx_total_duration_s: float


def _family(dr: int) -> str:
    if dr in (8, 10):
        return "cr_1_3"
    if dr in (9, 11):
        return "cr_2_3"
    raise ValueError(f"Unsupported LR-FHSS DR: {dr}")


def airtime_breakdown(frm_payload_bytes: int, dr: int) -> AirtimeBreakdown:
    if frm_payload_bytes < 0:
        raise ValueError("frm_payload_bytes must be non-negative")
    family = _family(dr)
    n = 3 if family == "cr_1_3" else 2
    m = 2 if family == "cr_1_3" else 4
    l_phy = int(frm_payload_bytes) + LORAWAN_PHY_OVERHEAD_BYTES

    header = n * HEADER_DURATION_PER_COPY_S

    # The published Eq. (6) is rendered with +2+6/8 bytes, but the numeric
    # payload-duration entries in Table 6 are reproduced by an effective +3 B.
    # We keep both values and use the Table-6-reproducing convention only as an
    # explicit operationalisation; this does not claim a causal correction.
    rendered_eq6_payload = ((l_phy + 2 + 6 / 8) / m) * PAYLOAD_FRAGMENT_DURATION_S
    payload = ((l_phy + 3) / m) * PAYLOAD_FRAGMENT_DURATION_S

    # Eq. (7) hop count is kept as rendered, including the floor operation.
    hops = n + math.floor((l_phy + 2 + 6 / 8) / m)
    hop_duration = hops * HOP_DURATION_S
    total = header + payload + hop_duration
    return AirtimeBreakdown(
        dr=int(dr),
        frm_payload_bytes=int(frm_payload_bytes),
        phy_payload_bytes=l_phy,
        header_repetitions=n,
        fragment_bytes=m,
        header_duration_s=header,
        payload_duration_s=payload,
        rendered_eq6_payload_duration_s=rendered_eq6_payload,
        hop_count=hops,
        hop_duration_s=hop_duration,
        tx_total_duration_s=total,
    )


def _incremental_energy(states: list[tuple[float, float]], voltage_v: float = SOURCE_VOLTAGE_V) -> float:
    """Energy above the source-model sleep-current baseline."""
    return float(voltage_v) * sum((current_a - SLEEP_CURRENT_A) * duration_s for duration_s, current_a in states)


def _tx_states(frm_payload_bytes: int, dr: int) -> list[tuple[float, float]]:
    family = _family(dr)
    air = airtime_breakdown(frm_payload_bytes, dr)
    post_tx_s = 10.4e-3 if family == "cr_1_3" else 12.4e-3
    return [
        (2.370e-3, 3.8e-3),
        # Header+payload signal time is TX-current time. Frequency-hop time is
        # accounted separately at the hop-state current, avoiding double count.
        (air.header_duration_s + air.payload_duration_s, TX_CURRENT_A),
        (air.hop_duration_s, HOP_CURRENT_A),
        (post_tx_s, 3.7e-3),
    ]


def unconfirmed_incremental_radio_energy_j(frm_payload_bytes: int, dr: int) -> float:
    family = _family(dr)
    rx1_s = 99.2e-3 if family == "cr_1_3" else 49.5e-3
    states = _tx_states(frm_payload_bytes, dr) + [
        (1.0, SLEEP_CURRENT_A),
        (1.3e-3, 2.3e-3),
        (rx1_s, 5.8e-3),
        (0.7e-3, 1.2e-3),
        (911.2e-3, SLEEP_CURRENT_A),
        (1.5e-3, 1.8e-3),
        (198.4e-3, 5.8e-3),
        (0.7e-3, 1.2e-3),
    ]
    return _incremental_energy(states)


def confirmed_expected_incremental_radio_energy_j(
    frm_payload_bytes: int,
    dr: int,
    *,
    p_ack_rx1: float = 0.5,
    p_ack_rx2: float = 0.5,
) -> float:
    if p_ack_rx1 < 0 or p_ack_rx2 < 0 or not math.isclose(p_ack_rx1 + p_ack_rx2, 1.0, abs_tol=1e-12):
        raise ValueError("ACK probabilities must be non-negative and sum to 1")
    family = _family(dr)
    rx1_no_ack_s = 99.2e-3 if family == "cr_1_3" else 49.5e-3
    rx1_ack_s = 576.4e-3 if family == "cr_1_3" else 286.6e-3
    tx = _tx_states(frm_payload_bytes, dr)

    ack_rx1 = tx + [
        (1.0, SLEEP_CURRENT_A),
        (1.3e-3, 2.3e-3),
        (rx1_ack_s, 5.8e-3),
        (0.7e-3, 1.2e-3),
    ]
    ack_rx2 = tx + [
        (1.0, SLEEP_CURRENT_A),
        (1.3e-3, 2.3e-3),
        (rx1_no_ack_s, 5.8e-3),
        (0.7e-3, 1.2e-3),
        (911.2e-3, SLEEP_CURRENT_A),
        (1.5e-3, 1.8e-3),
        (1.141, 5.8e-3),
        (0.7e-3, 1.2e-3),
    ]
    return p_ack_rx1 * _incremental_energy(ack_rx1) + p_ack_rx2 * _incremental_energy(ack_rx2)


def model_incremental_radio_energy_j(frm_payload_bytes: int, dr: int, confirmation_mode: str) -> float:
    mode = str(confirmation_mode).lower()
    if mode == "unconfirmed":
        return unconfirmed_incremental_radio_energy_j(frm_payload_bytes, dr)
    if mode == "confirmed":
        return confirmed_expected_incremental_radio_energy_j(frm_payload_bytes, dr)
    raise ValueError(f"Unsupported confirmation mode: {confirmation_mode}")
