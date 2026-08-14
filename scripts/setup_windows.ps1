$ErrorActionPreference = "Stop"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
stackwise registry-validate
pytest
stackwise reproduce --smoke
