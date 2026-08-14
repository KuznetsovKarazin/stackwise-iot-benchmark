from pathlib import Path

import pandas as pd
import pytest

from stackwise.schema import canonicalise_columns, validate_frame


SMOKE_FIXTURE = Path("data/examples/smoke_observations.csv")


@pytest.mark.skipif(not SMOKE_FIXTURE.exists(), reason="source-only archive excludes data/ examples")
def test_smoke_fixture_validates():
    frame = pd.read_csv(SMOKE_FIXTURE)
    frame = canonicalise_columns(frame)
    assert validate_frame(frame) == []
