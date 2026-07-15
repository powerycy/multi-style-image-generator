# Unified Portrait Integration Design

## Goal

Make uploaded-person behavior consistent across generative outputs without rigid panorama distances, subject-size tiers, identity tiers, or engineering-style delivery labels.

## Core behavior

When an uploaded person participates in image or video content generation, interpret the request as “place this same person naturally into the target world.” Prioritize recognizable identity while redesigning clothing, footwear, hairstyle accessories, props, action, materials, and lighting for the requested scene. Preserve source styling or pose only when the user explicitly asks.

Choose subject prominence from the user's words and the composition instead of fixed percentages or meter ranges. “Put me in this scene” requires a comfortably visible, integrated person; “make me the protagonist” increases prominence; an explicitly environment-led request may reduce it.

## Derived-output boundary

Spatial-depth previews, dynamic panorama enhancement, panorama HTML viewers, and animation of an existing image inherit their source image. They must not independently redesign the face, clothing, hairstyle accessories, pose, or environment. If the user asks for a styled result plus a derived preview, create and approve the integrated base image first, then derive the preview.

## Quality and delivery

Evaluate at the intended viewing size. Deliver when the result satisfies the stated creative goal and has no obvious wrong identity, abnormal gaze, cutout effect, lighting mismatch, severe deformation, panorama discontinuity, or unusable output. Do not downgrade a successful panorama merely because a distant face cannot support portrait-level verification.

Remove the “pass / usable with caveat / fail” label system. Mention a limitation only when it materially affects an explicit user requirement or the usability of the delivered artifact. Keep the existing cap of at most one automatic redraw for a genuinely unusable result.

## Compatibility

Preserve all existing style routing, normal image generation, prompt-only output, 360° panorama and HTML creation, dynamic panorama enhancement, spatial-photo preview, standard video, panorama video, dependency bootstrap, and API-key handling.

## Verification

Repository contract tests must require the unified rule across image, panorama, and video generation; require the derived-output boundary; reject rigid default distance/size wording and tiered delivery labels; and preserve every existing output route.
