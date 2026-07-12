import re
import subprocess
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_md = ROOT / "multi-style-image-generator" / "SKILL.md"
        cls.readme_zh_path = ROOT / "README.md"
        cls.readme_en_path = ROOT / "README_en.md"
        cls.readme_zh = cls.readme_zh_path.read_text(encoding="utf-8")
        cls.readme_en = cls.readme_en_path.read_text(encoding="utf-8")

        tracked = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        text_suffixes = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}
        cls.tracked_text_files = [
            ROOT / name
            for name in tracked
            if name and ((ROOT / name).suffix in text_suffixes or name == ".gitignore")
        ]

    def test_tracked_text_has_no_developer_absolute_paths(self):
        developer_home_prefix = "/" + "Users/"
        for path in self.tracked_text_files:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn(
                    developer_home_prefix, path.read_text(encoding="utf-8")
                )

    def test_skill_routes_dependency_scripts_through_launcher(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        self.assertIn("scripts/run_with_deps.py create_spatial_preview.py", skill)
        self.assertIn("scripts/run_with_deps.py normalize_equirectangular_aspect.py", skill)

    def test_readmes_document_automatic_local_environment(self):
        self.assertIn("multi-style-image-generator/.venv", self.readme_zh)
        self.assertIn("multi-style-image-generator/.venv", self.readme_en)

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
            "360 环景说明": "360 Panorama Notes",
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
