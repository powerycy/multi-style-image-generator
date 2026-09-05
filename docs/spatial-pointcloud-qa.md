# Spatial and single-image point-cloud QA

The default spatial motion is unchanged: depth 0.62, motion 0.56, perspective 1.15,
auto X/Y 0.36/0.18. Controls are visible unless explicitly hidden. Only the
`immersive` preset remains; removed aliases now fail at argument parsing.

## Repeatable validation

Run both unittest suites in an environment containing the repository requirements:

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s multi-style-image-generator/tests -v
python multi-style-image-generator/tests/make_browser_fixtures.py work/browser-fixtures
node multi-style-image-generator/tests/qa_pointcloud.js work/browser-fixtures work/pointcloud-qa
node multi-style-image-generator/tests/qa_spatial_v18.js work/browser-fixtures/mesh-visible.html work/spatial-qa
```

Fixture construction invokes each dependency-bearing viewer through `run_with_deps.py`.
Install Playwright 1.61.1 and its Chromium for browser tests, or set `CHROME_PATH`
to an existing browser. CI runs both Python suites and both browser suites, and
uploads screenshots. Point-cloud regression compares six deterministic downsampled
RGB views with a mean channel tolerance of 4/255; this tolerates rasterizer differences
without accepting a blank canvas. Behavior checks include visual changes from all
sliders, reset, drag/touch, angular limits, zoom, demo/pause, desktop/mobile layout,
hidden controls, no external requests and discontinuity triangle rejection.

Inspect all six screenshots before intentionally updating `pointcloud-baselines.json`
with `--update-baselines`. Never update baselines just to make a failed run pass.
The fixture has an abrupt foreground oval and smooth background; side views must
show their separation, without invented backside geometry.

## Routing evaluation

`evals/evals.json` contains 23 prompts, including crochet generation, direct existing
image point clouds, generation followed by point-cloud/depth derivation, default
visible controls, explicit hidden controls, and file-based panorama video delivery.
Review the expected tool sequence and preservation constraints for each request.
These are agent behavior scenarios, not claims that paid generation was executed
in unit tests. Pure existing-image derivations load only the spatial workflow;
style creation loads the style reference and generation workflow first.

## Visual acceptance and limits

Dunhuang checks reuse the existing RGB and model depth assets. In local verification,
an additional cached Depth Anything V2 inference checks the 16-bit output pipeline;
it does not generate a new RGB image or call a paid image API. Existing 8-bit depth
cannot regain lost precision. Optional Apple Depth Pro needs its own installed model.

The initial mesh edge threshold of 0.10 left excessive silhouette gaps on the real
Dunhuang image, so it was revised to 0.28 after screenshot inspection. Single-mesh
occlusion gaps can remain at large jumps; they are preferable to fabricating hidden
surfaces. Point clouds are explicitly single-image depth visualizations, not full 3D.
