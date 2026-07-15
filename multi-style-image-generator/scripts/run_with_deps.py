#!/usr/bin/env python3
"""Run dependency-bearing bundled scripts in a Skill-local environment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Optional, Sequence


ALLOWED_TARGETS = {
    "create_spatial_preview.py",
    "create_spatial_photo_viewer.py",
    "create_spatial_photo_depth_viewer.py",
    "infer_depth_anything_v2.py",
    "normalize_equirectangular_aspect.py",
    "stabilize_depth_map.py",
}


class _SetupOSError(OSError):
    def __init__(self, phase: str, error: OSError):
        super().__init__(str(error))
        self.phase = phase


def resolve_target(name: str, scripts_dir: Path) -> Path:
    """Resolve an allowlisted script name without accepting arbitrary paths."""
    if name not in ALLOWED_TARGETS or Path(name).name != name:
        raise ValueError(f"unsupported target script: {name}")
    return scripts_dir / name


def requirements_digest(path: Path) -> str:
    """Return the SHA-256 digest of the dependency declaration's raw bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def environment_is_current(
    venv_dir: Path, digest: str, runner=subprocess.run
) -> bool:
    """Check the interpreter, saved requirements digest, and required imports."""
    venv_python = _venv_python(venv_dir)
    if not venv_python.is_file():
        return False

    state_path = venv_dir.parent / ".deps-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(state, dict) or state.get("requirements_digest") != digest:
        return False

    try:
        runner(
            [
                str(venv_python),
                "-c",
                "import PIL, numpy, torch, transformers, safetensors, huggingface_hub",
            ],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return False
    return True


def ensure_environment(skill_dir: Path, runner=subprocess.run) -> Path:
    """Create or synchronize the Skill-local virtual environment as needed."""
    requirements_path = skill_dir / "requirements.txt"
    digest = requirements_digest(requirements_path)
    venv_dir = skill_dir / ".venv"
    venv_python = _venv_python(venv_dir)

    if environment_is_current(venv_dir, digest, runner=runner):
        return venv_python

    try:
        runner([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    except OSError as error:
        raise _SetupOSError("virtual environment creation", error) from error

    try:
        runner(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements_path),
            ],
            check=True,
        )
    except OSError as error:
        raise _SetupOSError("dependency installation", error) from error
    (skill_dir / ".deps-state.json").write_text(
        json.dumps({"requirements_digest": digest}) + "\n", encoding="utf-8"
    )
    return venv_python


def _setup_phase(error: BaseException) -> str:
    phase = getattr(error, "phase", None)
    if isinstance(phase, str):
        return phase
    command = getattr(error, "cmd", ())
    if isinstance(command, (list, tuple)):
        if "venv" in command:
            return "virtual environment creation"
        if "pip" in command:
            return "dependency installation"
    return "environment setup"


def reset_environment(skill_dir: Path) -> None:
    """Delete only the environment artifacts owned by this launcher."""
    venv_path = skill_dir / ".venv"
    try:
        if venv_path.is_symlink() or not venv_path.is_dir():
            venv_path.unlink()
        else:
            shutil.rmtree(venv_path)
    except FileNotFoundError:
        pass
    except OSError as error:
        raise OSError(f"{venv_path}: {error}") from error

    state_path = skill_dir / ".deps-state.json"
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise OSError(f"{state_path}: {error}") from error


def _format_command(command: Sequence[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _report_setup_failure(phase: str, error: BaseException, skill_dir: Path) -> None:
    venv_dir = skill_dir / ".venv"
    recovery = _format_command(
        [sys.executable, str(Path(__file__).resolve()), "--reset"]
    )
    print(f"Dependency launcher failed during {phase}: {error}", file=sys.stderr)
    print(f"Environment: {venv_dir}", file=sys.stderr)
    print(f"Recovery command: {recovery}", file=sys.stderr)


def _report_target_failure(error: BaseException) -> None:
    if isinstance(error, subprocess.CalledProcessError):
        print(
            f"Target script failed with exit code {error.returncode}: {error}",
            file=sys.stderr,
        )
    else:
        print(f"Target script could not execute: {error}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            f"Usage: {Path(__file__).name} TARGET [ARG ...] | --reset",
            file=sys.stderr,
        )
        return 2

    scripts_dir = Path(__file__).resolve().parent
    skill_dir = scripts_dir.parent
    if args == ["--reset"]:
        try:
            reset_environment(skill_dir)
        except OSError as error:
            print(f"Reset failed: {error}", file=sys.stderr)
            return 1
        print(f"Reset complete: removed launcher environment state from {skill_dir}")
        return 0
    try:
        target = resolve_target(args[0], scripts_dir)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    try:
        venv_python = ensure_environment(skill_dir)
    except (subprocess.CalledProcessError, OSError) as error:
        _report_setup_failure(_setup_phase(error), error, skill_dir)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) else 1

    try:
        completed = subprocess.run(
            [str(venv_python), str(target), *args[1:]], check=True
        )
    except (subprocess.CalledProcessError, OSError) as error:
        _report_target_failure(error)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) else 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
