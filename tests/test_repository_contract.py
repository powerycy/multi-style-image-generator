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

    def test_readmes_describe_the_real_spatial_photo_default(self):
        combined = self.readme_zh + self.readme_en

        self.assertIn("Depth Anything V2", self.readme_zh)
        self.assertIn("Depth Anything V2", self.readme_en)
        self.assertIn("真实深度", self.readme_zh)
        self.assertIn("real model depth", self.readme_en)
        self.assertIn("PyTorch / Transformers", self.readme_zh)
        self.assertIn("PyTorch / Transformers", self.readme_en)
        self.assertIn("空间景深图", self.readme_zh)
        self.assertIn("spatial depth image", self.readme_en)
        self.assertNotIn("displacement`：推荐默认值", self.readme_zh)
        self.assertNotIn("`displacement`: recommended default", self.readme_en)
        self.assertNotIn("--spatial-mode displacement", combined)

        evals = json.loads(
            (ROOT / "multi-style-image-generator" / "evals" / "evals.json").read_text(
                encoding="utf-8"
            )
        )["evals"]
        spatial = [item for item in evals if item["id"] == 15]
        self.assertEqual(len(spatial), 1)
        expected = spatial[0]["expected_output"]
        self.assertIn("Depth Anything V2 Small", expected)
        self.assertIn("immersive-v18 单 mesh HTML", expected)
        self.assertIn("不得静默改用启发式深度", expected)

    def test_readme_showcase_gifs_are_directly_embedded(self):
        gif_paths = (
            "assets/examples/spatial-depth-preview.gif",
            "assets/examples/dynamic-360-panorama-preview.gif",
            "assets/examples/dunhuang-colored-pointcloud-preview.gif",
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

    def test_pointcloud_showcase_gif_is_orbit_animated_and_bounded(self):
        path = ROOT / "assets" / "examples" / "dunhuang-colored-pointcloud-preview.gif"
        self.assertTrue(path.is_file())
        self.assertLessEqual(path.stat().st_size, 5 * 1024 * 1024)
        payload = path.read_bytes()
        self.assertIn(payload[:6], (b"GIF87a", b"GIF89a"))
        self.assertEqual(struct.unpack("<HH", payload[6:10]), (520, 292))
        delays = gif_frame_delays_ms(payload)
        self.assertGreaterEqual(len(delays), 20)
        duration_ms = sum(delays)
        self.assertGreaterEqual(duration_ms, 5000)
        self.assertLessEqual(duration_ms, 5500)
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
        self.assertIn("保留身份锚点", intro)
        self.assertIn("重新设计到目标世界观", intro)
        self.assertIn("只有用户明确要求保留原服装", intro)

    def test_photo_reference_guidance_is_generic_and_bilingual(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        reference = (
            ROOT
            / "multi-style-image-generator"
            / "references"
            / "game-visual-styles.md"
        ).read_text(encoding="utf-8")
        eval_path = ROOT / "multi-style-image-generator" / "evals" / "evals.json"
        evals = json.loads(eval_path.read_text(encoding="utf-8"))["evals"]
        photo_evals = [item for item in evals if item["id"] in (10, 11)]

        scoped_text = "\n".join(
            (
                self.readme_zh,
                self.readme_en,
                skill.split("再判断是否有上传图片或照片参考：", 1)[1].split(
                    "再判断界面模式：", 1
                )[0],
                reference.split("## 2. 上传图片 / 人像参考规则", 1)[1].split(
                    "\n## 3.", 1
                )[0],
                json.dumps(photo_evals, ensure_ascii=False),
            )
        )
        personal_fragments = (
            "第一张参考场景和穿着",
            "第二张参考我的脸",
            "墨镜戴上",
            "米色帽子",
            "黑外套",
            "红围巾",
            "红瓶",
            "参考第一张衣服",
        )
        for fragment in personal_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, scoped_text)

        self.assertIn("默认保留身份锚点并重设计服装、动作和光照", self.readme_zh)
        self.assertIn("只有用户明确要求时才保留原服装、原姿势或原道具", self.readme_zh)
        self.assertIn(
            "preserves identity anchors while redesigning clothing, action, and lighting",
            self.readme_en,
        )
        self.assertIn(
            "Original clothing, poses, or props are preserved only when explicitly requested",
            self.readme_en,
        )
        self.assertTrue(
            all("不得自行添加未指定" in item["expected_output"] for item in photo_evals)
        )

    def test_portrait_generation_defaults_to_world_integration(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        photo_rules = skill.split("再判断是否有上传图片或照片参考：", 1)[1].split(
            "再判断界面模式：", 1
        )[0]

        self.assertIn("references/portrait-panorama-qa.md", skill)
        self.assertIn("让同一个人自然进入目标世界", photo_rules)
        self.assertIn("默认重设计衣着、鞋履、发饰、道具、动作、材质和光照", photo_rules)
        self.assertIn("只有用户明确要求保留", photo_rules)
        self.assertIn("人物身份一致", photo_rules)
        self.assertNotIn(
            "只把用户明确指定或参考图中实际存在的服装、配饰、道具和姿势作为约束",
            photo_rules,
        )

    def test_portrait_panorama_qa_uses_intent_led_delivery(self):
        qa_path = (
            ROOT
            / "multi-style-image-generator"
            / "references"
            / "portrait-panorama-qa.md"
        )
        self.assertTrue(qa_path.is_file())
        qa = qa_path.read_text(encoding="utf-8")

        required_rules = (
            "身份相似度高于场景细节、特效和服装精致度",
            "双眼视线同向",
            "斗鸡眼",
            "同一个人自然进入目标世界",
            "衣着、鞋履、发饰、道具、动作、材质和光照",
            "根据用户意图和画面叙事自然决定",
            "不因远景人物无法进行人像级身份核验",
            "顶部和底部极点",
            "左右拼接缝",
            "多个朝向",
            "正常观看尺寸",
            "不要为了检查而过度放大",
            "自动重绘最多一次",
            "第二次重绘",
            "只是已规格化为 2:1",
            "不得声称“已保留本人脸”",
        )
        for rule in required_rules:
            with self.subTest(rule=rule):
                self.assertIn(rule, qa)

        skill = self.skill_md.read_text(encoding="utf-8")
        portrait_contract = skill + qa + json.dumps(
            [item for item in json.loads(
                (ROOT / "multi-style-image-generator" / "evals" / "evals.json").read_text(
                    encoding="utf-8"
                )
            )["evals"] if item["id"] == 14],
            ensure_ascii=False,
        )
        for obsolete in (
            "4–6 米",
            "8–12 米",
            "6–10%",
            "10–15%",
            "通过 / 可用但需说明 / 不通过",
            "可用但需说明",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, portrait_contract)

        panorama_flow = skill.split("再判断是否需要 360° 全景预览：", 1)[1].split(
            "直接出图时，", 1
        )[0]
        self.assertIn("质检候选", panorama_flow)
        self.assertIn("根据用户意图和画面叙事自然决定", panorama_flow)
        self.assertIn("自动重绘最多一次", panorama_flow)
        self.assertIn("create_panorama_viewer.py", panorama_flow)

    def test_uploaded_person_rule_covers_generation_and_preserves_derived_assets(self):
        skill = self.skill_md.read_text(encoding="utf-8")
        photo_rules = skill.split("再判断是否有上传图片或照片参考：", 1)[1].split(
            "再判断界面模式：", 1
        )[0]

        generation_rules = (
            "图片、360° 全景图或视频内容",
            "同一个人自然进入目标世界",
            "衣着、鞋履、发饰、道具、动作、材质和光照",
            "只有用户明确要求保留",
        )
        for rule in generation_rules:
            with self.subTest(rule=rule):
                self.assertIn(rule, photo_rules)

        derived_rules = (
            "空间照片预览",
            "360° 全景 HTML",
            "动态增强全景",
            "继承已有底图",
            "不得自行换脸、换装",
            "先生成并质检融合后的底图",
        )
        for rule in derived_rules:
            with self.subTest(rule=rule):
                self.assertIn(rule, photo_rules)

    def test_portrait_panorama_eval_and_existing_modes_are_preserved(self):
        eval_path = ROOT / "multi-style-image-generator" / "evals" / "evals.json"
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        portrait_panorama = [item for item in payload["evals"] if item["id"] == 14]

        self.assertEqual(len(payload["evals"]), 15)
        self.assertEqual(len(portrait_panorama), 1)
        expected = portrait_panorama[0]["expected_output"]
        self.assertIn("默认重设计世界观服装和叙事动作", expected)
        self.assertIn("身份和眼神质检", expected)
        self.assertIn("同一个人自然进入目标世界", expected)
        self.assertIn("主要观看方向", expected)
        self.assertIn("根据用户意图", expected)
        self.assertIn("不因远景人物无法进行人像级身份核验", expected)
        self.assertIn("自动重绘最多一次", expected)
        self.assertNotIn("可用但需说明", expected)
        self.assertNotIn("8–12 米", expected)
        self.assertNotIn("6–10%", expected)

        skill = self.skill_md.read_text(encoding="utf-8")
        preserved_routes = (
            "scripts/create_dynamic_panorama_viewer.py",
            "scripts/run_with_deps.py create_spatial_preview.py",
            "scripts/create_bigmodel_video.py",
            "scripts/create_panorama_frame_sequence_viewer.py",
            "360° 全景图生视频模式",
            "只写提示词",
        )
        for route in preserved_routes:
            with self.subTest(route=route):
                self.assertIn(route, skill)

    def test_onboarding_eval_locks_terminology_and_video_durations(self):
        eval_path = ROOT / "multi-style-image-generator" / "evals" / "evals.json"
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        onboarding = [item for item in payload["evals"] if item["id"] == 12]

        self.assertEqual(len(payload["evals"]), 15)
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
        self.assertEqual(len(payload["evals"]), 15)
        self.assertEqual(len(key_onboarding), 1)
        self.assertIn("不得要求用户把 SK 粘贴到对话中", key_onboarding[0]["expected_output"])

        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("assert len(data['evals']) == 15", workflow)

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
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "python -m unittest discover -s multi-style-image-generator/tests -v",
            workflow,
        )
        self.assertIn('python -m pip install "Pillow>=10,<13" "numpy>=1.26,<3"', workflow)

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
