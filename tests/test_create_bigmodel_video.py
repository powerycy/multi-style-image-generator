import importlib.util
import contextlib
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock
from unittest.mock import patch
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "multi-style-image-generator" / "scripts" / "create_bigmodel_video.py"
SPEC = importlib.util.spec_from_file_location("create_bigmodel_video", SCRIPT)
video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video)


def completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


class VideoCredentialTests(unittest.TestCase):
    def test_resolve_api_key_prefers_selected_environment_variable(self):
        run = Mock()

        key = video.resolve_api_key(
            {"CUSTOM_VIDEO_KEY": "env-key", "ZHIPU_API_KEY": "fallback-key"},
            "CUSTOM_VIDEO_KEY",
            "darwin",
            run,
        )

        self.assertEqual(key, "env-key")
        run.assert_not_called()

    def test_resolve_api_key_uses_compatibility_environment_variable(self):
        run = Mock()

        key = video.resolve_api_key(
            {"ZHIPU_API_KEY": "fallback-key"},
            "BIGMODEL_API_KEY",
            "darwin",
            run,
        )

        self.assertEqual(key, "fallback-key")
        run.assert_not_called()

    def test_resolve_api_key_reuses_saved_key_without_dialog(self):
        run = Mock(return_value=completed(["security"], stdout="saved-key\n"))

        key = video.resolve_api_key({}, "BIGMODEL_API_KEY", "darwin", run)

        self.assertEqual(key, "saved-key")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][1], "find-generic-password")

    def test_resolve_api_key_prompts_once_and_saves_missing_key(self):
        run = Mock(
            side_effect=[
                completed(["security"], returncode=44, stderr="item not found"),
                completed(["osascript"], stdout="dialog-key\n"),
                completed(["security"]),
                completed(["security"], stdout="dialog-key\n"),
            ]
        )

        key = video.resolve_api_key({}, "BIGMODEL_API_KEY", "darwin", run)

        self.assertEqual(key, "dialog-key")
        self.assertEqual(run.call_count, 4)
        save_call = run.call_args_list[2]
        self.assertNotIn("dialog-key", save_call.args[0])
        self.assertEqual(save_call.args[0], [video.SECURITY, "-i"])
        self.assertNotIn("dialog-key", save_call.kwargs["input"])
        self.assertIn("dialog-key".encode("utf-8").hex(), save_call.kwargs["input"])

    def test_resolve_api_key_treats_dialog_cancellation_as_safe_stop(self):
        run = Mock(
            side_effect=[
                completed(["security"], returncode=44, stderr="item not found"),
                completed(["osascript"], returncode=1, stderr="User canceled."),
            ]
        )

        with self.assertRaisesRegex(SystemExit, "取消"):
            video.resolve_api_key({}, "BIGMODEL_API_KEY", "darwin", run)

    def test_resolve_api_key_rejects_empty_dialog_value(self):
        run = Mock(
            side_effect=[
                completed(["security"], returncode=44, stderr="item not found"),
                completed(["osascript"], stdout="  \n"),
            ]
        )

        with self.assertRaisesRegex(SystemExit, "未保存"):
            video.resolve_api_key({}, "BIGMODEL_API_KEY", "darwin", run)

    def test_resolve_api_key_is_environment_only_off_macos(self):
        run = Mock()

        with self.assertRaisesRegex(SystemExit, "BIGMODEL_API_KEY"):
            video.resolve_api_key({}, "BIGMODEL_API_KEY", "linux", run)

        run.assert_not_called()

    def test_keychain_delete_is_idempotent_when_item_is_missing(self):
        run = Mock(
            return_value=completed(["security"], returncode=44, stderr="item not found")
        )

        self.assertFalse(video.keychain_delete(run))

    def test_keychain_write_rejects_a_write_that_cannot_be_read_back(self):
        run = Mock(
            side_effect=[
                completed(["security"]),
                completed(["security"], returncode=44, stderr="item not found"),
            ]
        )

        with self.assertRaisesRegex(SystemExit, "验证"):
            video.keychain_write("dialog-key", run)


class VideoCliTests(unittest.TestCase):
    def test_replace_api_key_does_not_require_generation_prompt(self):
        run = Mock(
            side_effect=[
                completed(["osascript"], stdout="replacement-key\n"),
                completed(["security"]),
                completed(["security"], stdout="replacement-key\n"),
            ]
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = video.main(["--replace-api-key"], {}, "darwin", run)

        self.assertEqual(result, 0)
        self.assertNotIn("replacement-key", output.getvalue())
        self.assertIn("已保存", output.getvalue())

    def test_forget_api_key_does_not_require_generation_prompt(self):
        run = Mock(return_value=completed(["security"]))
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = video.main(["--forget-api-key"], {}, "darwin", run)

        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0][1], "delete-generic-password")

    def test_key_management_options_are_mutually_exclusive(self):
        parser = video.build_parser()

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--replace-api-key", "--forget-api-key"])

    def test_normal_generation_requires_prompt(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                video.main([], {}, "darwin", Mock())

    def test_dry_run_does_not_read_keychain_or_open_dialog(self):
        run = Mock()
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = video.main(["--prompt", "mist moving", "--dry-run"], {}, "darwin", run)

        self.assertEqual(result, 0)
        run.assert_not_called()
        self.assertIn('"prompt": "mist moving"', output.getvalue())


class VideoApiErrorTests(unittest.TestCase):
    def test_authentication_error_is_redacted_and_points_to_key_replacement(self):
        error = urllib.error.HTTPError(
            "https://example.invalid",
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"debug":"dialog-key"}'),
        )

        with patch.object(video.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                video.request_json("POST", "https://example.invalid", "dialog-key", {})

        message = str(raised.exception)
        self.assertIn("--replace-api-key", message)
        self.assertNotIn("dialog-key", message)


if __name__ == "__main__":
    unittest.main()
