import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "multi-style-image-generator" / "scripts" / "run_with_deps.py"
SPEC = importlib.util.spec_from_file_location("run_with_deps", LAUNCHER_PATH)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class RecordingRunner:
    def __init__(self, fail_on=None, error_factory=None):
        self.commands = []
        self.fail_on = fail_on
        self.error_factory = error_factory

    def __call__(self, command, **kwargs):
        command = list(command)
        self.commands.append((command, kwargs))
        if self.fail_on and self.fail_on(command):
            if self.error_factory:
                raise self.error_factory(command)
            raise subprocess.CalledProcessError(7, command)
        return subprocess.CompletedProcess(command, 0)


class RunWithDepsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.skill_dir = Path(self.temp_dir.name)
        self.scripts_dir = self.skill_dir / "scripts"
        self.scripts_dir.mkdir()
        self.requirements = self.skill_dir / "requirements.txt"
        self.requirements.write_text("Pillow\n", encoding="utf-8")

    def make_current_environment(self):
        venv_python = self.skill_dir / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()
        digest = launcher.requirements_digest(self.requirements)
        (self.skill_dir / ".deps-state.json").write_text(
            json.dumps({"requirements_digest": digest}), encoding="utf-8"
        )
        return venv_python

    def test_resolve_target_accepts_allowlisted_script(self):
        target = launcher.resolve_target("create_spatial_preview.py", self.scripts_dir)
        self.assertEqual(target, self.scripts_dir / "create_spatial_preview.py")

    def test_resolve_target_rejects_unknown_traversal_and_absolute_paths(self):
        for value in ("other.py", "../create_spatial_preview.py", "/tmp/script.py"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                launcher.resolve_target(value, self.scripts_dir)

    def test_requirements_digest_changes_with_content(self):
        first = launcher.requirements_digest(self.requirements)
        self.requirements.write_text("Pillow\nNumPy\n", encoding="utf-8")
        self.assertNotEqual(first, launcher.requirements_digest(self.requirements))

    def test_ensure_environment_creates_missing_environment(self):
        runner = RecordingRunner()

        venv_python = launcher.ensure_environment(self.skill_dir, runner=runner)

        self.assertEqual(venv_python, self.skill_dir / ".venv" / "bin" / "python")
        self.assertEqual(
            [command for command, _ in runner.commands],
            [
                [launcher.sys.executable, "-m", "venv", str(self.skill_dir / ".venv")],
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(self.requirements),
                ],
            ],
        )
        state = json.loads((self.skill_dir / ".deps-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["requirements_digest"], launcher.requirements_digest(self.requirements))

    def test_ensure_environment_reuses_current_environment(self):
        venv_python = self.make_current_environment()
        runner = RecordingRunner()

        result = launcher.ensure_environment(self.skill_dir, runner=runner)

        self.assertEqual(result, venv_python)
        self.assertEqual(
            [command for command, _ in runner.commands],
            [[str(venv_python), "-c", "import PIL, numpy"]],
        )

    def test_ensure_environment_synchronizes_changed_requirements(self):
        venv_python = self.make_current_environment()
        self.requirements.write_text("Pillow\nNumPy\n", encoding="utf-8")
        runner = RecordingRunner()

        launcher.ensure_environment(self.skill_dir, runner=runner)

        self.assertEqual(
            [command for command, _ in runner.commands],
            [
                [launcher.sys.executable, "-m", "venv", str(self.skill_dir / ".venv")],
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(self.requirements),
                ],
            ],
        )

    def test_ensure_environment_propagates_pip_failure_without_writing_state(self):
        runner = RecordingRunner(fail_on=lambda command: "pip" in command)

        with self.assertRaises(subprocess.CalledProcessError) as caught:
            launcher.ensure_environment(self.skill_dir, runner=runner)

        self.assertEqual(caught.exception.returncode, 7)
        self.assertFalse((self.skill_dir / ".deps-state.json").exists())

    def assert_main_reports_setup_oserror_phase(self, fail_on, expected_phase):
        runner = RecordingRunner(
            fail_on=fail_on, error_factory=lambda command: OSError("command unavailable")
        )
        ensure_environment = launcher.ensure_environment

        def ensure_in_temp_dir(_skill_dir):
            return ensure_environment(self.skill_dir, runner=runner)

        stderr = io.StringIO()
        with mock.patch.object(
            launcher, "ensure_environment", side_effect=ensure_in_temp_dir
        ), mock.patch.object(launcher.sys, "stderr", stderr):
            result = launcher.main(["create_spatial_preview.py"])

        self.assertEqual(result, 1)
        self.assertIn(f"failed during {expected_phase}", stderr.getvalue())

    def test_main_identifies_oserror_during_venv_creation(self):
        self.assert_main_reports_setup_oserror_phase(
            lambda command: "venv" in command, "virtual environment creation"
        )

    def test_main_identifies_oserror_during_dependency_installation(self):
        self.assert_main_reports_setup_oserror_phase(
            lambda command: "pip" in command, "dependency installation"
        )

    def test_main_preserves_target_arguments(self):
        target_args = ["input image.png", "--output", "result path.html"]
        venv_python = ROOT / "multi-style-image-generator" / ".venv" / "bin" / "python"
        target = ROOT / "multi-style-image-generator" / "scripts" / "create_spatial_preview.py"
        runner = RecordingRunner()

        with mock.patch.object(launcher, "ensure_environment", return_value=venv_python), mock.patch.object(
            launcher.subprocess, "run", runner
        ):
            result = launcher.main(["create_spatial_preview.py", *target_args])

        self.assertEqual(result, 0)
        self.assertEqual(runner.commands[0][0], [str(venv_python), str(target), *target_args])

    def test_main_target_failure_preserves_exit_code_without_setup_recovery(self):
        venv_python = self.skill_dir / ".venv" / "bin" / "python"
        stderr = io.StringIO()
        runner = RecordingRunner(fail_on=lambda _command: True)

        with mock.patch.object(
            launcher, "ensure_environment", return_value=venv_python
        ), mock.patch.object(launcher.subprocess, "run", runner), mock.patch.object(
            launcher.sys, "stderr", stderr
        ):
            result = launcher.main(["create_spatial_preview.py"])

        self.assertEqual(result, 7)
        self.assertIn("Target script failed with exit code 7", stderr.getvalue())
        self.assertNotIn("Environment:", stderr.getvalue())
        self.assertNotIn("Recovery command:", stderr.getvalue())
        self.assertNotIn("Dependency launcher failed", stderr.getvalue())

    def test_main_target_oserror_reports_only_execution_failure(self):
        venv_python = self.skill_dir / ".venv" / "bin" / "python"
        stderr = io.StringIO()
        runner = RecordingRunner(
            fail_on=lambda _command: True,
            error_factory=lambda _command: OSError("permission denied"),
        )

        with mock.patch.object(
            launcher, "ensure_environment", return_value=venv_python
        ), mock.patch.object(launcher.subprocess, "run", runner), mock.patch.object(
            launcher.sys, "stderr", stderr
        ):
            result = launcher.main(["create_spatial_preview.py"])

        self.assertEqual(result, 1)
        self.assertEqual(
            stderr.getvalue(), "Target script could not execute: permission denied\n"
        )

    def test_reset_deletes_only_launcher_owned_environment_and_is_idempotent(self):
        venv_dir = self.skill_dir / ".venv"
        venv_dir.mkdir()
        (venv_dir / "installed-package").write_text("data", encoding="utf-8")
        state_path = self.skill_dir / ".deps-state.json"
        state_path.write_text("{}\n", encoding="utf-8")
        preserved_file = self.skill_dir / "keep.txt"
        preserved_file.write_text("keep", encoding="utf-8")
        preserved_dir = self.skill_dir / "output"
        preserved_dir.mkdir()
        (preserved_dir / "result.txt").write_text("keep", encoding="utf-8")
        stdout = io.StringIO()

        with mock.patch.object(
            launcher, "__file__", str(self.scripts_dir / "run_with_deps.py")
        ), mock.patch.object(launcher.sys, "stdout", stdout):
            first = launcher.main(["--reset"])
            second = launcher.main(["--reset"])

        self.assertEqual((first, second), (0, 0))
        self.assertFalse(venv_dir.exists())
        self.assertFalse(state_path.exists())
        self.assertEqual(preserved_file.read_text(encoding="utf-8"), "keep")
        self.assertEqual(
            (preserved_dir / "result.txt").read_text(encoding="utf-8"), "keep"
        )
        self.assertEqual(stdout.getvalue().count("Reset complete:"), 2)

    def test_setup_failure_recommends_cross_platform_launcher_reset(self):
        launcher_path = self.scripts_dir / "launcher with spaces.py"
        interpreter = str(self.skill_dir / "Python Dir" / "python")

        for platform in ("linux", "win32"):
            with self.subTest(platform=platform):
                stderr = io.StringIO()
                with mock.patch.object(
                    launcher, "__file__", str(launcher_path)
                ), mock.patch.object(
                    launcher.sys, "executable", interpreter
                ), mock.patch.object(
                    launcher.sys, "platform", platform
                ), mock.patch.object(
                    launcher, "ensure_environment", side_effect=OSError("setup failed")
                ), mock.patch.object(launcher.sys, "stderr", stderr):
                    result = launcher.main(["create_spatial_preview.py"])

                self.assertEqual(result, 1)
                output = stderr.getvalue()
                self.assertIn("--reset", output)
                self.assertIn(interpreter, output)
                self.assertIn(str(launcher_path), output)
                self.assertNotIn("rm -rf", output)


if __name__ == "__main__":
    unittest.main()
