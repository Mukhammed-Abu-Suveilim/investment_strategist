"""Environment diagnostics for local developer workflows.

This module verifies interpreter and package resolution to reduce mixed-venv
issues (for example pandas import errors caused by conflicting environments).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

EXPECTED_ENV_DIR = "investment_strategist"


def _resolve_venv_name() -> str:
    """Return active virtual-environment directory name.

    Returns:
        The directory name inferred from ``VIRTUAL_ENV`` if available,
        otherwise ``"<none>"``.
    """

    venv_path = os.environ.get("VIRTUAL_ENV", "").strip()
    if not venv_path:
        return "<none>"

    return Path(venv_path).name


def main() -> None:
    """Print environment diagnostics and fail on mismatched venv name."""

    active_venv_name = _resolve_venv_name()
    python_executable = sys.executable

    print(f"Python executable: {python_executable}")
    print(f"Active VIRTUAL_ENV name: {active_venv_name}")

    try:
        import pandas as pd  # type: ignore[import-not-found]

        print(f"pandas version: {pd.__version__}")
        print(f"pandas module path: {pd.__file__}")
    except Exception as exc:  # pragma: no cover - direct diagnostics path
        print(f"pandas import failed: {exc}")
        raise SystemExit(1) from exc

    if active_venv_name != EXPECTED_ENV_DIR:
        print(
            "ERROR: Expected active virtual environment "
            f"'{EXPECTED_ENV_DIR}', got '{active_venv_name}'."
        )
        print(
            "Activate the canonical environment and rerun:\n"
            ".\\investment_strategist\\Scripts\\Activate.ps1"
        )
        raise SystemExit(2)

    print("Environment check passed.")


if __name__ == "__main__":
    main()
