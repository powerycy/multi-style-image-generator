import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import create_panorama_pointcloud as scene

class PanoramaSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.image=self.root/'pano.png';self.depth=self.root/'depth.png'
        yy,xx=np.mgrid[:64,:128]
        Image.fromarray(np.stack([xx*2,yy*4,np.full_like(xx,100)],axis=-1).astype('uint8')).save(self.image)
        Image.fromarray((yy/63*65000).astype('uint16')).save(self.depth)

    def test_reuse_and_ply_without_completion(self):
        original=self.image.read_bytes()
        with patch.object(scene,'infer_depth',side_effect=AssertionError('unexpected inference')):
            scene.main([str(self.image),'--depth',str(self.depth),'--rows','128','--out-dir',str(self.root/'result')])
        report=json.loads((self.root/'result/pano-360-pointcloud.json').read_text())
        self.assertEqual(report['depth_provenance'],'supplied-stable-depth')
        self.assertEqual(report['point_sources']['1'],0);self.assertEqual(report['point_sources']['2'],0)
        data=Path(report['ply']).read_bytes().split(b'end_header\n',1)[1]
        self.assertEqual(len(data),report['points']*16)
        xyz=np.ndarray((report['points'],3),dtype='<f4',buffer=data,strides=(16,4))
        self.assertTrue(np.isfinite(xyz).all())
        self.assertTrue((xyz.min(axis=0)<0).all() and (xyz.max(axis=0)>0).all())
        self.assertEqual(original,self.image.read_bytes())

    def test_completion_has_explicit_sources(self):
        im=np.asarray(Image.open(self.image));dep=scene.read_depth(self.depth)
        xyz,rgb,spacing,kind=scene.build_geometry(im,dep,128,'terrain')
        self.assertEqual(set(np.unique(kind)),{0,1,2})
        self.assertTrue(np.isfinite(xyz).all());self.assertTrue((spacing>0).all())
        self.assertGreater(np.max(np.hypot(xyz[kind==2,0],xyz[kind==2,2])),100)

    def test_inference_failure_propagates(self):
        with patch.object(scene,'infer_depth',side_effect=RuntimeError('backend unavailable')):
            with self.assertRaisesRegex(RuntimeError,'backend unavailable'):
                scene.main([str(self.image),'--out-dir',str(self.root/'failure')])
        self.assertFalse((self.root/'failure/pano-360-pointcloud.html').exists())

    def test_rejects_non_panorama_and_mismatched_depth(self):
        bad=self.root/'ordinary.png';Image.new('RGB',(128,100)).save(bad)
        with self.assertRaises(SystemExit):scene.main([str(bad),'--depth',str(self.depth)])
        wrong=self.root/'wrong.png';Image.new('I',(32,32),4).save(wrong)
        with self.assertRaisesRegex(ValueError,'dimensions'):
            scene.write_scene(self.image,wrong,self.root/'bad.html')

if __name__=='__main__':unittest.main()
