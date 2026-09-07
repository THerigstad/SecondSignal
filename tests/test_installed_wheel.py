"""Installed-distribution checks for data needed at runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

from secondsignal.profiles import DEFAULT_PROFILE_DIR


def _subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "PIP_PREFIX",
        "PIP_TARGET",
        "PIP_USER",
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    ):
        environment.pop(name, None)
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PIP_NO_INDEX"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _pip_is_available(python: Path, environment: dict[str, str]) -> bool:
    result = subprocess.run(
        [str(python), "-I", "-m", "pip", "--version"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )
    return result.returncode == 0


def _host_can_build_without_isolation(tmp_path: Path, environment: dict[str, str]) -> bool:
    """Can this host build any wheel with ``--no-build-isolation``?

    The check is deliberately independent of this project: a minimal package
    with no content of ours. If the host's own build backend cannot produce a
    wheel from it, the failure belongs to the machine and not to our
    packaging, and the caller skips instead of reporting a defect we did not
    have. A host that passes this probe and then fails on our package is
    reporting a real defect.
    """
    probe_root = tmp_path / "backend-probe"
    (probe_root / "src" / "ssprobe").mkdir(parents=True)
    (probe_root / "src" / "ssprobe" / "__init__.py").write_text("", encoding="utf-8")
    (probe_root / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["setuptools>=61"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        'name = "ssprobe"\n'
        'version = "0.0.0"\n\n'
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable, "-I", "-m", "pip", "wheel",
            "--no-build-isolation", "--no-deps", "--no-index",
            "--wheel-dir", str(probe_root / "out"), str(probe_root),
        ],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=environment,
        text=True,
    )
    return result.returncode == 0


def _venv_python(environment_dir: Path) -> Path:
    relative_path = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    python = environment_dir / relative_path
    assert python.is_file(), f"virtual-environment interpreter not found at {python}"
    return python


@pytest.mark.slow
def test_installed_wheel_loads_bundled_roster_from_unrelated_cwd(tmp_path: Path) -> None:
    environment = _subprocess_environment()
    if not _pip_is_available(Path(sys.executable), environment):
        pytest.skip("pip is unavailable")

    if not _host_can_build_without_isolation(tmp_path, environment):
        pytest.skip(
            "the host's build backend cannot build any wheel without isolation; "
            "this is a machine fault, not a packaging fault"
        )

    project_root = Path(__file__).resolve().parents[1]
    build_root = tmp_path / "build-source"
    build_root.mkdir()
    for filename in ("LICENSE", "README.md", "pyproject.toml"):
        shutil.copy2(project_root / filename, build_root / filename)
    shutil.copytree(
        project_root / "src" / "secondsignal",
        build_root / "src" / "secondsignal",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    wheel_dir = tmp_path / "wheelhouse"
    wheel_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "--no-index",
            "--wheel-dir",
            str(wheel_dir),
            str(build_root),
        ],
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env=environment,
        text=True,
    )
    wheels = list(wheel_dir.glob("secondsignal-*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]

    expected_profiles = {
        path.name: path.read_bytes() for path in sorted(DEFAULT_PROFILE_DIR.glob("*.json"))
    }
    assert len(expected_profiles) == 7
    with zipfile.ZipFile(wheel) as archive:
        profile_members = {
            name.removeprefix("secondsignal/profiles/")
            for name in archive.namelist()
            if name.startswith("secondsignal/profiles/") and name.endswith(".json")
        }
        assert profile_members == set(expected_profiles)
        for name, contents in expected_profiles.items():
            assert archive.read(f"secondsignal/profiles/{name}") == contents

    environment_dir = tmp_path / "fresh-environment"
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment_dir)
    except subprocess.CalledProcessError:
        pytest.skip("pip is unavailable in the fresh virtual environment")
    python = _venv_python(environment_dir)
    if not _pip_is_available(python, environment):
        pytest.skip("pip is unavailable in the fresh virtual environment")

    unrelated_cwd = tmp_path / "unrelated-cwd"
    unrelated_cwd.mkdir()
    subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            str(wheel),
        ],
        capture_output=True,
        check=True,
        cwd=unrelated_cwd,
        env=environment,
        text=True,
    )

    locations = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            (
                "import secondsignal; "
                "from secondsignal.profiles import DEFAULT_PROFILE_DIR; "
                "print(secondsignal.__file__); print(DEFAULT_PROFILE_DIR)"
            ),
        ],
        capture_output=True,
        check=True,
        cwd=unrelated_cwd,
        env=environment,
        text=True,
    ).stdout.splitlines()
    assert len(locations) == 2
    environment_root = environment_dir.resolve()
    assert Path(locations[0]).resolve().is_relative_to(environment_root)
    installed_profile_dir = Path(locations[1]).resolve()
    assert installed_profile_dir.is_relative_to(environment_root)

    roster = subprocess.run(
        [str(python), "-I", "-m", "secondsignal", "--roster"],
        capture_output=True,
        check=True,
        cwd=unrelated_cwd,
        env=environment,
        text=True,
    )
    assert f"7 agents loaded from {installed_profile_dir}" in roster.stdout
