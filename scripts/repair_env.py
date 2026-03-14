"""Repair local Python environment for deterministic project execution.

This utility enforces ``investment_strategist`` as the canonical virtual
environment name and repairs broken package states (for example corrupted
pandas installations causing ``ArrowDtype`` import failures).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CANONICAL_ENV_NAME = "investment_strategist"
CONFLICTING_ENV_NAMES: tuple[str, ...] = (".venv", "venv")


def _run(command: list[str], cwd: Path) -> None:
    """Execute a command and fail fast on non-zero exit codes.

    Args:
        command: Command and arguments.
        cwd: Working directory.
    """

    printable = " ".join(command)
    print(f"[RUN] {printable}")
    subprocess.run(command, cwd=cwd, check=True)


def _venv_python_path(project_root: Path, env_name: str) -> Path:
    """Return platform-specific Python executable path inside a venv."""

    return project_root / env_name / "Scripts" / "python.exe"


def _remove_directory(path: Path) -> None:
    """Delete a directory recursively if it exists."""

    if path.exists():
        print(f"[CLEAN] Removing: {path}")
        shutil.rmtree(path)


def repair_environment(recreate: bool, remove_conflicts: bool) -> None:
    """Repair the project virtual environment and reinstall core dependencies.

    Args:
        recreate: Whether to fully recreate ``investment_strategist``.
        remove_conflicts: Whether to delete additional venv folders
            (``.venv`` and ``venv``) to avoid interpreter ambiguity.
    """

    project_root = Path(__file__).resolve().parent.parent
    canonical_env_path = project_root / CANONICAL_ENV_NAME
    requirements_path = project_root / "requirements.txt"

    if not requirements_path.exists():
        raise FileNotFoundError("requirements.txt is missing in project root")

    if remove_conflicts:
        for env_name in CONFLICTING_ENV_NAMES:
            _remove_directory(project_root / env_name)

    if recreate:
        _remove_directory(canonical_env_path)
        _run([sys.executable, "-m", "venv", CANONICAL_ENV_NAME], cwd=project_root)
    elif not canonical_env_path.exists():
        _run([sys.executable, "-m", "venv", CANONICAL_ENV_NAME], cwd=project_root)

    env_python = _venv_python_path(project_root, CANONICAL_ENV_NAME)

    _run([str(env_python), "-m", "ensurepip", "--upgrade"], cwd=project_root)
    _run(
        [
            str(env_python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        cwd=project_root,
    )
    _run(
        [str(env_python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=project_root,
    )
    _run(
        [
            str(env_python),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-cache-dir",
            "numpy",
            "pandas",
        ],
        cwd=project_root,
    )
    _run([str(env_python), "-m", "scripts.check_env"], cwd=project_root)

    print("[OK] Environment repair completed successfully.")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for environment repair workflow."""

    parser = argparse.ArgumentParser(
        description=(
            "Repair the canonical investment_strategist virtual environment and "
            "fix broken pandas installs."
        )
    )
    parser.add_argument(
        "--no-recreate",
        action="store_true",
        help="Do not remove/recreate investment_strategist; repair in place.",
    )
    parser.add_argument(
        "--keep-conflicting-envs",
        action="store_true",
        help="Do not remove .venv/venv folders.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for repairing local environment."""

    args = parse_args()
    repair_environment(
        recreate=not args.no_recreate,
        remove_conflicts=not args.keep_conflicting_envs,
    )


if __name__ == "__main__":
    main()
