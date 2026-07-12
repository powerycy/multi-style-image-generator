import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def gif_frame_delays_ms(payload):
    """Return frame delays while walking GIF blocks without image libraries."""
    if payload[:6] not in (b"GIF87a", b"GIF89a"):
        raise ValueError("not a GIF")
    position = 13
    packed = payload[10]
    if packed & 0x80:
        position += 3 * (2 ** ((packed & 0x07) + 1))
    delays = []
    while position < len(payload):
        marker = payload[position]
        position += 1
        if marker == 0x3B:
            break
        if marker == 0x21:
            label = payload[position]
            position += 1
            if label == 0xF9:
                block_size = payload[position]
                if block_size != 4:
                    raise ValueError("invalid graphic control extension")
                delays.append(
                    int.from_bytes(payload[position + 2 : position + 4], "little")
                    * 10
                )
                position += block_size + 2
                continue
            while True:
                block_size = payload[position]
                position += 1
                if block_size == 0:
                    break
                position += block_size
            continue
        if marker == 0x2C:
            descriptor_packed = payload[position + 8]
            position += 9
            if descriptor_packed & 0x80:
                position += 3 * (2 ** ((descriptor_packed & 0x07) + 1))
            position += 1  # LZW minimum code size
            while True:
                block_size = payload[position]
                position += 1
                if block_size == 0:
                    break
                position += block_size
            continue
        raise ValueError(f"unexpected GIF block marker: {marker:#x}")
    return delays


def tracked_developer_path_matches(root):
    developer_home_prefix = "/" + "Users/"
    completed = subprocess.run(
        ["git", "grep", "--no-color", "-n", "-I", "-e", developer_home_prefix, "--"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 1:
        return ""
    if completed.returncode != 0:
        completed.check_returncode()
    return completed.stdout


class RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_md = ROOT / "multi-style-image-generator" / "SKILL.md"
        cls.readme_zh_path = ROOT / "README.md"
        cls.readme_en_path = ROOT / "README_en.md"
        cls.readme_zh = cls.readme_zh_path.read_text(encoding="utf-8")
        cls.readme_en = cls.readme_en_path.read_text(encoding="utf-8")

    def test_tracked_text_has_no_developer_absolute_paths(self):
        matches = tracked_developer_path_matches(ROOT)
        self.assertEqual(matches, "", f"tracked developer paths found:\n{matches}")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            developer_home_prefix = "/" + "Users/"
            (repo / "NOTICE").write_text(
                f"developer path: {developer_home_prefix}reviewer/private-tool\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "NOTICE"], cwd=repo, check=True)

            matches = tracked_developer_path_matches(repo)
            self.assertEqual(
                matches,
                f"NOTICE:1:developer path: {developer_home_prefix}reviewer/private-tool\n",
                "extensionless tracked text output was not deterministic",
            )

        with tempfile.TemporaryDirectory() as non_repository:
            with self.assertRaises(subprocess.CalledProcessError):
                tracked_developer_path_matches(Path(non_repository))

    def test_skill_routes_dependency_scripts_through_launcher(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        self.assertIn("scripts/run_with_deps.py create_spatial_preview.py", skill)
        self.assertIn("scripts/run_with_deps.py normalize_equirectangular_aspect.py", skill)

    def test_readmes_document_automatic_local_environment(self):
        self.assertIn("multi-style-image-generator/.venv", self.readme_zh)
        self.assertIn("multi-style-image-generator/.venv", self.readme_en)

    def test_readmes_document_launcher_reset_equivalently(self):
        command = "python3 scripts/run_with_deps.py --reset"
        self.assertIn(command, self.readme_zh)
        self.assertIn(command, self.readme_en)
        self.assertNotIn("rm -rf", self.readme_zh)
        self.assertNotIn("rm -rf", self.readme_en)

    def test_readme_showcase_gifs_are_directly_embedded(self):
        gif_paths = (
            "assets/examples/spatial-depth-preview.gif",
            "assets/examples/dynamic-360-panorama-preview.gif",
        )
        for path in gif_paths:
            with self.subTest(path=path):
                self.assertIn(f'<img src="{path}"', self.readme_zh)
                self.assertIn(f'<img src="{path}"', self.readme_en)
        readmes = self.readme_zh + self.readme_en
        self.assertNotIn("spatial-depth-preview.html", readmes)
        self.assertNotIn("dynamic-360-panorama-preview.html", readmes)

    def test_showcase_gifs_are_animated_and_bounded(self):
        examples = ROOT / "assets" / "examples"
        for name in (
            "spatial-depth-preview.gif",
            "dynamic-360-panorama-preview.gif",
        ):
            with self.subTest(name=name):
                path = examples / name
                self.assertTrue(path.is_file())
                self.assertLessEqual(path.stat().st_size, 5 * 1024 * 1024)
                payload = path.read_bytes()
                self.assertIn(payload[:6], (b"GIF87a", b"GIF89a"))
                self.assertEqual(struct.unpack("<HH", payload[6:10]), (520, 292))
                delays = gif_frame_delays_ms(payload)
                self.assertGreaterEqual(len(delays), 20)
                duration_ms = sum(delays)
                self.assertGreaterEqual(duration_ms, 3000)
                self.assertLessEqual(duration_ms, 4000)
                self.assertIn(b"NETSCAPE2.0", payload)

    def test_feature_introduction_uses_precise_generic_contract(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        intro = skill.split("## 功能介绍模式", 1)[1].split("\n## ", 1)[0]

        self.assertIn("360° 全景图", intro)
        self.assertIn("默认 5 秒", intro)
        self.assertIn("只支持 5 秒或 10 秒", intro)
        self.assertNotIn("5-10 秒", skill)
        self.assertEqual(skill.count("5–10 秒"), 1, "range wording may appear only as a prohibition")
        self.assertNotIn("黑外套", intro)
        self.assertNotIn("帽子", intro)
        self.assertIn("用户指定的服装或道具特征", intro)

    def test_onboarding_eval_locks_terminology_and_video_durations(self):
        eval_path = ROOT / "multi-style-image-generator" / "evals" / "evals.json"
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        onboarding = [item for item in payload["evals"] if item["id"] == 12]

        self.assertEqual(len(payload["evals"]), 13)
        self.assertEqual(len(onboarding), 1)
        expected = onboarding[0]["expected_output"]
        self.assertIn("360° 全景图", expected)
        self.assertIn("默认 5 秒", expected)
        self.assertIn("5 秒或 10 秒", expected)
        self.assertIn("不得虚构具体服装", expected)

    def test_video_key_onboarding_uses_macos_keychain_without_chat_secrets(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        self.assertIn("macOS 钥匙串", skill)
        self.assertIn("--replace-api-key", skill)
        self.assertIn("--forget-api-key", skill)
        self.assertIn("不要要求用户在对话中粘贴", skill)

        self.assertIn("首次生成视频", self.readme_zh)
        self.assertIn("后续自动读取", self.readme_zh)
        self.assertIn("first video generation", self.readme_en)
        self.assertIn("automatically reuse", self.readme_en)

        eval_path = ROOT / "multi-style-image-generator" / "evals" / "evals.json"
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        key_onboarding = [item for item in payload["evals"] if item["id"] == 13]
        self.assertEqual(len(payload["evals"]), 13)
        self.assertEqual(len(key_onboarding), 1)
        self.assertIn("不得要求用户把 SK 粘贴到对话中", key_onboarding[0]["expected_output"])

        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("assert len(data['evals']) == 13", workflow)

    def test_user_facing_panorama_labels_use_standard_term(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        agent = (ROOT / "multi-style-image-generator" / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        frame_viewer = (
            ROOT
            / "multi-style-image-generator"
            / "scripts"
            / "create_panorama_frame_sequence_viewer.py"
        ).read_text(encoding="utf-8")

        self.assertIn("360°×180° 等距柱状投影全景图", self.readme_zh)
        self.assertIn("360° 全景图", skill)
        self.assertIn("360° 全景预览", agent)
        self.assertIn("360° 全景动画预览", frame_viewer)
        self.assertNotIn("## 360 环景说明", self.readme_zh)

    def test_ci_workflow_runs_repository_tests(self):
        workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow_path.is_file())
        self.assertIn(
            "python -m unittest discover -s tests -v",
            workflow_path.read_text(encoding="utf-8"),
        )

    def test_ci_workflow_verifies_executable_script_modes(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "git ls-files -s 'multi-style-image-generator/scripts/*.py'", workflow
        )
        self.assertIn('$1 != "100755"', workflow)
        self.assertIn("exit 1", workflow)

    def test_python_scripts_have_python_shebangs(self):
        scripts_dir = ROOT / "multi-style-image-generator" / "scripts"
        for path in sorted(scripts_dir.glob("*.py")):
            with self.subTest(path=path.relative_to(ROOT)):
                first_line = path.read_text(encoding="utf-8").splitlines()[0]
                self.assertEqual(first_line, "#!/usr/bin/env python3")

    def test_readme_level_two_headings_are_structurally_equivalent(self):
        heading_map = {
            "生成效果": "Generated Results",
            "核心能力": "Core Capabilities",
            "支持风格": "Supported Style Directions",
            "安装": "Installation",
            "怎么用": "How To Use",
            "示例请求": "Example Requests",
            "360° 全景图说明": "360° Panorama Notes",
            "空间照片预览说明": "Spatial Photo Preview Notes",
            "视频模式说明": "Video Mode Notes",
            "辅助脚本": "Helper Scripts",
            "项目结构": "Repository Layout",
            "依赖": "Requirements",
            "许可": "License",
            "作者与交流": "Author & Community",
        }
        zh_headings = re.findall(r"^## (.+)$", self.readme_zh, flags=re.MULTILINE)
        en_headings = re.findall(r"^## (.+)$", self.readme_en, flags=re.MULTILINE)

        self.assertEqual([heading_map[heading] for heading in zh_headings], en_headings)


if __name__ == "__main__":
    unittest.main()
