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
                values = np.asarray(result)
                self.assertEqual(result.size, (64, 36))
                self.assertLess(int(values.min()), 10)
                self.assertGreater(int(values.max()), 245)

    def test_generated_html_is_single_mesh_v18_without_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb, depth = self.make_images(root)
            document = viewer.build_document(rgb, depth)
        self.assertEqual(document.count("gl.drawElements(gl.TRIANGLES"), 1)
        for forbidden in (
            "uLayer",
            "uBackground",
            "foregroundMask",
            'class="controls"',
            "<input",
            "<button",
        ):
            self.assertNotIn(forbidden, document)
        for expected in (
            "depthScale: 1.80",
            "motion: 1.40",
            "perspective: 1.15",
            "Math.sin(t * 0.42) * 0.42",
            "Math.cos(t * 0.33) * 0.22",
            "float farMask = 1.0 - smoothstep(0.14, 0.30, depthValue)",
            "vec2 radius = uTexelSize * 2.25",
            "farMask * 0.52",
            "function handleOrientation(event)",
            "manualUntil = performance.now() + 2800",
        ):
            self.assertIn(expected, document)

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
