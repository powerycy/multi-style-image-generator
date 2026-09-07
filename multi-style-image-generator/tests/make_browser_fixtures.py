"""Build deterministic offline visual/behavior fixtures; no model or paid API."""
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
x, y = np.meshgrid(np.linspace(0, 1, 320), np.linspace(0, 1, 180))
near = ((x-.55)**2/.12**2+(y-.5)**2/.32**2) < 1
rgb = np.stack((50+x*110+near*70, 45+y*80+near*50, 80+x*60), axis=-1).astype(np.uint8)
depth = np.where(near, .82+y*.04, .15+x*.22+y*.12)
Image.fromarray(rgb).save(root/'source.png')
Image.fromarray((depth*65535).astype(np.uint16)).save(root/'depth.png')
runner = Path(__file__).resolve().parents[1]/'scripts/run_with_deps.py'
for mode in ('mesh', 'pointcloud'):
    for controls in ('visible', 'hidden'):
        subprocess.run([sys.executable, str(runner), 'create_spatial_preview.py', str(root/'source.png'),
            '--depth', str(root/'depth.png'), '--spatial-mode', mode, '--controls', controls,
            '--output', str(root/f'{mode}-{controls}.html'), '--out-dir', str(root)], check=True)

# A 2:1 fixture exercises the separate panorama-to-point-cloud entry point.
x, y = np.meshgrid(np.linspace(0, 1, 256), np.linspace(0, 1, 128))
rgb = np.stack((60+x*120, 50+y*100, 80+x*50), axis=-1).astype(np.uint8)
Image.fromarray(rgb).save(root/'panorama.png')
Image.fromarray(((.15+x*.4+y*.25)*65535).astype(np.uint16)).save(root/'panorama-depth.png')
subprocess.run([sys.executable, str(runner), 'create_panorama_pointcloud.py', str(root/'panorama.png'),
    '--depth', str(root/'panorama-depth.png'), '--rows', '128', '--out-dir', str(root)], check=True)
