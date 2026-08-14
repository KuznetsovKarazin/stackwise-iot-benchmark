.PHONY: install test lint smoke audit clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests scripts

smoke:
	stackwise reproduce --smoke

audit:
	stackwise audit --output results/audit

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info results/smoke results/audit
