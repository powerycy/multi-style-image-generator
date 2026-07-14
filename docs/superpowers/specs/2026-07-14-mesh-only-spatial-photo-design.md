# Mesh-Only Spatial Photo Design

## Goal

Make “空间景深图”, “空间图”, “空间照片”, “spatial photo”, and similar requests consistently produce a depth-driven interactive spatial-photo preview instead of a shallow-depth-of-field still image or the weak shader-displacement effect.

## Product behavior

Treat the current uploaded image or most recent usable generated image as the source image. Generate a depth map, then create an interactive local HTML preview with a subdivided depth mesh and camera parallax. If no usable source image exists, first generate a base image with clear foreground, subject, midground, and background separation; that generated base image is also part of the delivery.

Only interpret a request as an ordinary static image when the user explicitly asks for “静态景深”, “浅景深”, “背景虚化”, “depth-of-field still”, or says not to create an interactive preview.

The output is an Apple-spatial-photo-like interactive HTML experience, not an Apple-native spatial-photo file. User-facing text must not claim that an HEIC or other native Apple spatial-media container was created.

## Single implementation path

Remove the `displacement` implementation and its routing, CLI option, documentation, and tests. `create_spatial_preview.py` becomes the single public entry point and always uses the existing depth-mesh renderer. The public command no longer requires `--spatial-mode`.

Keep automatic heuristic depth-map generation when the caller does not supply `--depth`; keep support for an external depth map when one is supplied. Rename generated artifacts and visible labels generically as spatial-photo preview artifacts rather than exposing a mode choice to ordinary users.

The obsolete displacement-only helper is removed from the dependency launcher allowlist and repository. Existing 360° panorama, dynamic panorama, panorama video, ordinary image generation, video generation, and uploaded-person integration behavior remain unchanged.

## Documentation and discovery

Add “空间景深图” and “空间图” to the skill triggers. Update Chinese and English README examples so ambiguous spatial-photo requests use the one mesh-based workflow and do not show `--spatial-mode displacement` or `--spatial-mode mesh` choices.

Explain that:

- an existing image is reused automatically and is not requested again;
- a base image is generated only when no usable image exists;
- the standard deliverables are the depth map and interactive HTML, plus the base image when the workflow had to generate one;
- a static blurred image is not a spatial-photo preview.

## Verification

Repository contract tests must fail while any `displacement` implementation, documentation, routing, or `--spatial-mode` option remains. Script tests must verify that the single entry point creates a depth map automatically, accepts a supplied depth map, invokes the mesh renderer, and uses generic output naming. Existing repository, dependency-bootstrap, video, panorama, and portrait-integration tests must remain green.
