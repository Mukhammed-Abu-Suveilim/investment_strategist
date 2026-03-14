"""Test runner entrypoint for ``uv run test``."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    """Execute pytest and propagate its exit code."""

    result = subprocess.run([sys.executable, "-m", "pytest"], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
