from pathlib import Path

import pytest

from stackwise.reproduce import reproduce_smoke


SMOKE_FIXTURE = Path("data/examples/smoke_observations.csv")


@pytest.mark.skipif(not SMOKE_FIXTURE.exists(), reason="source-only archive excludes data/ examples")
def test_smoke_pipeline(tmp_path: Path):
    outputs = reproduce_smoke(tmp_path / "smoke")
    assert outputs
    assert all(path.exists() for path in outputs.values())
