import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from depth_geometry import read_depth, save_depth
from stabilize_depth_map import stabilize_depth
from infer_depth_anything_v2 import _normalize_depth
import create_spatial_preview as preview
import create_spatial_photo_depth_viewer as mesh
import create_pointcloud_viewer as points


class DepthPrecisionTests(unittest.TestCase):
    def test_model_output_retains_more_than_256_levels(self):
        raw = _normalize_depth(np.linspace(0, 1, 2048).reshape(32, 64))
        self.assertGreater(len(np.unique(np.asarray(raw))), 1000)

    def test_bilateral_smoothing_reduces_noise_without_bridging_step(self):
        rng = np.random.default_rng(7)
        data = np.zeros((64, 128), dtype=np.float32) + .2
        data[:, 64:] = .8
        data += rng.normal(0, .009, data.shape).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_depth(data, root / "raw.png")
            stabilize_depth(root / "raw.png", root / "stable.png", low_percentile=0, high_percentile=100)
            result = read_depth(root / "stable.png")
        normalized = (data-data.min())/(data.max()-data.min())
        self.assertLess(result[8:-8, 8:56].std(), normalized[8:-8, 8:56].std())
        self.assertGreater((result[:, 64]-result[:, 63]).mean(), .85)
        self.assertGreater(len(np.unique(result)), 256)

    def test_supplied_16bit_depth_survives_copy_and_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = np.linspace(.2, .8, 2048, dtype=np.float32).reshape(32, 64)
            save_depth(data, root / "depth.png")
            preview._copy_stable_depth(root / "depth.png", root / "stable.png", (64, 32))
            np.testing.assert_allclose(read_depth(root / "stable.png"), data, atol=1/65535)
            Image.new("RGB", (64, 32)).save(root / "rgb.png")
            for builder in (mesh, points):
                html = builder.build_document(root / "rgb.png", root / "stable.png")
                config = json.loads(re.search(r"const CONFIG = (.*);", html)[1])
                self.assertGreater(len(set(config["depthValues"])), 256)

    def test_removed_presets_and_unsupported_modes_fail_explicitly(self):
        for preset in ("legacy", "v18"):
            with self.assertRaises(SystemExit):
                preview.parser().parse_args(["image.png", "--preset", preset])
        with self.assertRaisesRegex(ValueError, "only supported"):
            preview.main(["image.png", "--demo", "on"])

    def test_constant_depth_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_depth(np.ones((8, 8), dtype=np.float32)*.4, root/"raw.png")
            with self.assertRaisesRegex(ValueError, "dynamic range"):
                stabilize_depth(root/"raw.png", root/"stable.png")

    def test_mesh_grid_cannot_overflow_uint16_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (64, 64)).save(root/"rgb.png")
            Image.new("L", (64, 64)).save(root/"depth.png")
            with self.assertRaisesRegex(ValueError, "index budget"):
                mesh.build_document(root/"rgb.png", root/"depth.png", grid=300)
