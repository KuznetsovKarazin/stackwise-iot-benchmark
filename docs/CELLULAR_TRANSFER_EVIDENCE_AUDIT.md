# Stage 5G — Targeted cellular transfer-evidence admissibility audit

Stage 5F established three valid Vomhoff 1 KB source-active whole-device transaction components but blocked all 10 feasible cellular-IP candidate incidences from the canonical `expected_device_energy_per_application_report_j` target.

Stage 5G reviews a targeted external state/procedure model rather than adding a broad new empirical corpus. Sørensen et al. (IEEE Internet of Things Journal, 2022, DOI `10.1109/JIOT.2022.3152173`) provides an experimentally validated NB-IoT/LTE-M modem-energy model with explicit traffic-profile, payload, coverage and transmit-cycle structure.

The source is useful for **structural support**: payload size, reporting periodicity, state transitions, PSM/eDRX and network timers can materially affect cycle energy, so Stage 5F was correct not to scale one 1 KB active transaction blindly.

It is **not** an absolute calibration bridge for STACKWISE. The paper models modem energy for specific devices and explicitly requires state-power characterization when applying the model to a new device. The retained Vomhoff Stage-5F quantity is a whole-device source-active component. The measurement boundaries and device/network implementations therefore differ. The reviewed model also does not supply exact CoAP/DTLS/LwM2M or MQTT5/TLS1.3/LwM2M application-stack energy.

Consequently:

- payload transfer: structurally supported, numeric candidate transfer robustness-only;
- report-cycle/state accounting: structurally supported, numeric candidate transfer robustness-only;
- exact upper-layer bridge: unresolved;
- external absolute recalibration: prohibited;
- canonical candidate report-energy: remains blocked for all 10 incidences;
- publication MCDA: remains blocked.

The preferred next scientific step is targeted matched bridge evidence: same-device or otherwise boundary-compatible NB-IoT/LTE-M measurements spanning the benchmark payloads and application/report-cycle contexts. If this is not obtainable, the external model may be used only as an explicitly labelled robustness family. Lifecycle-cost evidence should be developed in parallel because it is missing across all feasible candidates and is independent of this energy-transfer gap.
