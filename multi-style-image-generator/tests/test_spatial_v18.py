import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import create_spatial_photo_depth_viewer as viewer
import create_pointcloud_viewer as pointcloud_viewer
import infer_depth_anything_v2
import stabilize_depth_map


class SpatialV18Tests(unittest.TestCase):
    def make_images(self, root: Path):
        rgb = root / "rgb.png"
        raw = root / "raw.png"
        Image.new("RGB", (64, 36), (130, 90, 50)).save(rgb)
        gradient = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (36, 1))
        Image.fromarray(gradient, mode="L").save(raw)
        return rgb, raw

    def test_stabilization_preserves_size_and_dynamic_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, raw = self.make_images(root)
            stable = stabilize_depth_map.stabilize_depth(raw, root / "stable.png", size=(64, 36))
            with Image.open(stable) as result:
                values = np.asarray(result) / 257
                self.assertEqual(result.size, (64, 36))
                self.assertLess(int(values.min()), 10)
                self.assertGreater(int(values.max()), 245)

    def test_generated_html_is_single_mesh_v18_with_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            document = viewer.build_document(rgb, depth)
        self.assertEqual(document.count("gl.drawElements(gl.TRIANGLES"), 1)
        for forbidden in (
            "uLayer",
            "uBackground",
            "foregroundMask",
        ):
            self.assertNotIn(forbidden, document)
        for expected in (
            'class="controls"',
            'id="depthScale" type="range"',
            'id="motion" type="range"',
            'id="perspective" type="range"',
            'id="autoToggle"',
            "function bindSlider(id, key, textId)",
            "depthScale: 0.62",
            "motion: 0.56",
            "perspective: 1.15",
            "Math.sin(t * 0.42) * 0.36",
            "Math.cos(t * 0.33) * 0.18",
            "float farMask = 0.0",
            "vec2 radius = uTexelSize * 2.25",
            "function handleOrientation(event)",
            "manualUntil = performance.now() + 2800",
        ):
            self.assertIn(expected, document)

    def test_custom_values_initialize_slider_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            document = viewer.build_document(
                rgb,
                depth,
                options=viewer.ViewerOptions(
                    depth_scale=0.62,
                    motion=0.56,
                    perspective=1.35,
                ),
            )
        self.assertIn("depthScale: 0.62", document)
        self.assertIn("motion: 0.56", document)
        self.assertIn("perspective: 1.35", document)
        self.assertIn("input.value = String(state[key])", document)

    def test_one_shot_cli_with_supplied_stable_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "create_spatial_preview.py"),
                    str(rgb),
                    "--depth",
                    str(depth),
                    "--out-dir",
                    str(root / "out"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["depth_provenance"], "supplied-stable-depth")
            self.assertEqual(result["spatial_mode"], "mesh")
            self.assertTrue(Path(result["stable_depth"]).is_file())
            document = Path(result["html"]).read_text(encoding="utf-8")
            self.assertIn('"depthProvenance": "supplied-stable-depth"', document)

    def test_pointcloud_document_matches_reference_controls_and_render_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            document = pointcloud_viewer.build_document(rgb, depth)
        self.assertEqual(document.count("gl.drawArrays(gl.POINTS"), 1)
        self.assertIn('id="depthScale" type="range"', document)
        self.assertIn('id="pointSize" type="range"', document)
        self.assertIn('id="focus" type="range"', document)
        self.assertIn('"cols": 64', document)
        self.assertIn('"depthScale": 1.25', document)
        self.assertIn('"pointSize": 2.1', document)
        self.assertIn('"focus": 0.46', document)

    def test_one_shot_pointcloud_cli_reuses_stable_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "create_spatial_preview.py"),
                    str(rgb),
                    "--depth",
                    str(depth),
                    "--spatial-mode",
                    "pointcloud",
                    "--out-dir",
                    str(root / "out"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["spatial_mode"], "pointcloud")
            self.assertEqual(result["preset"], "pointcloud-adaptive")
            self.assertTrue(result["html"].endswith("-pointcloud.html"))
            document = Path(result["html"]).read_text(encoding="utf-8")
            self.assertIn("gl.drawArrays(gl.POINTS", document)

    def test_default_cli_has_no_silent_heuristic_fallback(self):
        source = (SCRIPTS / "create_spatial_preview.py").read_text(encoding="utf-8")
        self.assertIn('default="depth-anything-v2-small"', source)
        self.assertNotIn("except ImportError", source)
        self.assertNotIn("except RuntimeError", source)
        self.assertIn('elif args.depth_backend == "heuristic"', source)

    def test_complete_huggingface_cache_is_resolved_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot"
            snapshot.mkdir()
            for name in infer_depth_anything_v2.REQUIRED_MODEL_FILES:
                (snapshot / name).write_bytes(b"cached")

            fake_hub = types.ModuleType("huggingface_hub")

            def snapshot_download(**kwargs):
                self.assertTrue(kwargs["local_files_only"])
                return str(snapshot)

            fake_hub.snapshot_download = snapshot_download
            with patch.dict(sys.modules, {"huggingface_hub": fake_hub}):
                cached = infer_depth_anything_v2.find_cached_snapshot(
                    infer_depth_anything_v2.DEFAULT_MODEL, Path(tmp) / "cache"
                )

            self.assertEqual(cached, snapshot)
            self.assertTrue((cached / "model.safetensors").is_file())
            self.assertTrue((cached / "preprocessor_config.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
