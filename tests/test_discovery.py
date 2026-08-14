from stackwise.discovery import empirical_candidate_score


def test_empirical_measurements_rank_high():
    score, label = empirical_candidate_score(
        "Experimental LoRaWAN current measurements",
        "Raw traces collected on a real testbed",
    )
    assert score >= 5
    assert label == "high_priority_review"


def test_simulation_is_not_core_evidence():
    score, label = empirical_candidate_score(
        "5G latency simulation dataset",
        "Synthetic packet traces from a simulator",
    )
    assert score < 1
    assert label == "likely_unsuitable"
