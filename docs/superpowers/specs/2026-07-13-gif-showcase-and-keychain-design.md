# GIF Showcase and macOS Keychain Design

## Objective

Improve first-time and repeated use in two places:

1. Show the spatial-depth and dynamic 360° panorama results directly in the GitHub README as animated GIFs, without requiring readers to open HTML files.
2. Let macOS users enter their BigModel/CogVideoX API key once in a secure system dialog and reuse it from macOS Keychain on later video requests.

## Scope

### README showcase

- Replace the two interactive HTML demo files with two looping GIF files.
- Embed both GIFs directly in the Chinese and English README result sections.
- Do not retain links to the removed HTML demos.
- Match the existing panorama GIF presentation: 520×292 pixels, approximately 3–4 seconds per loop, and continuous looping.
- Keep each new GIF small enough for a practical GitHub README target of no more than 3 MB where image content permits. If the dynamic panorama cannot meet 3 MB without obvious damage, the hard ceiling is 5 MB.
- The spatial-depth GIF must visibly demonstrate foreground/background parallax.
- The dynamic panorama GIF must visibly demonstrate both scene motion and a changing 360° viewing direction.

Planned asset names:

- `assets/examples/spatial-depth-preview.gif`
- `assets/examples/dynamic-360-panorama-preview.gif`

The existing source HTML files will be removed from the repository after the GIFs have been generated and verified.

### API key onboarding

- Continue supporting `BIGMODEL_API_KEY` and `ZHIPU_API_KEY` environment variables.
- Resolve credentials in this order:
  1. the environment variable selected by `--api-key-env`;
  2. `ZHIPU_API_KEY` as the existing compatibility fallback;
  3. the saved macOS Keychain item;
  4. a first-run macOS secure input dialog.
- On macOS, if no environment variable or saved credential exists, display a native password dialog with hidden input.
- After confirmation, save the key as a generic-password item in macOS Keychain and use it for the current request.
- On later requests, retrieve the key automatically without asking the user to re-enter it.
- Never print the key, add it to command examples as a literal value, write it to repository files, or include it in generated JSON metadata.
- Keep environment variables as a non-persistent override so users can temporarily use another account.

The Keychain identifiers will be stable and specific to this Skill:

- service: `multi-style-image-generator.bigmodel`
- account: `api-key`

## User Controls

Extend `create_bigmodel_video.py` with:

- `--replace-api-key`: show the secure macOS dialog and replace the saved Keychain item without generating a video;
- `--forget-api-key`: delete the saved Keychain item without generating a video.

The two management options are mutually exclusive. They must not require `--prompt` because no generation request is made.

The Skill instructions will tell users they can say:

- “更换视频生成 SK” to run the replace flow;
- “删除已保存的视频生成 SK” to run the forget flow.

## Platform Behavior

### macOS

- Use the system `osascript` executable for the hidden-input dialog.
- Use the system `security` executable to read, update, and delete the generic-password item.
- When saving, invoke `security -i` and provide an `add-generic-password ... -X <hex>` command only through the child process standard input. This keeps the key and its encoded form out of the process argument list; captured output is never echoed.
- Capture subprocess output internally and never echo credential-bearing output.
- Treat user cancellation as a normal, clearly explained stop rather than an application crash.

### Other operating systems

- Preserve environment-variable support.
- If no environment key exists, stop before the API request and explain that automatic secure storage is currently available only through macOS Keychain.
- Do not add plaintext `.env` storage or silently introduce another persistence mechanism.

## Failure Handling

- Empty dialog submission: explain that no key was saved and stop.
- Dialog cancellation: explain that video generation was cancelled and stop.
- Missing `osascript` or `security`: fall back to the existing environment-variable guidance.
- Keychain read failure other than “item not found”: stop with a concise Keychain error that does not contain the key.
- Invalid API credential response: explain that the saved key may need replacement and point to `--replace-api-key`; do not delete it automatically.
- Keychain deletion when no item exists: report that no saved key was found and exit successfully.
- `--dry-run`: continue to work without resolving or prompting for an API key.

## Implementation Boundaries

- Keep credential resolution functions separate from API request and polling functions.
- Use dependency injection for platform name and subprocess execution in unit tests so tests never access the real Keychain or show a dialog.
- Do not add a third-party keyring dependency; macOS already supplies the required system tools.
- GIF generation may use the Skill-local Pillow/NumPy environment, but the resulting GIFs are committed assets and do not require dependencies when viewed on GitHub.

## Tests and Verification

### Credential behavior

- Environment key takes precedence over Keychain.
- A saved Keychain key is returned without opening a dialog.
- A missing Keychain item opens the secure dialog once, stores the result, and returns it.
- Cancellation and empty input stop safely without storing anything.
- Replace and forget flows call only their intended Keychain operations.
- Dry-run does not read Keychain or open a dialog.
- Non-macOS behavior remains environment-only and gives actionable guidance when missing.
- No test invokes the real `security` or `osascript` executable.

### GIF and documentation behavior

- Both GIF files exist, are 520×292, contain multiple frames, and loop continuously.
- GIF file sizes respect the 5 MB hard ceiling.
- Both Chinese and English READMEs embed both GIF paths with `<img>` tags.
- Neither README links to the removed interactive HTML demos.
- The two superseded HTML demo files are absent.

### Release verification

- Run the full unit and repository-contract suite.
- Run the official Skill validator.
- Inspect both GIFs visually for smooth looping, recognizable motion, and acceptable compression.
- Confirm the worktree is clean after commit.
- Push the existing feature branch and verify all GitHub Actions checks pass.

## Acceptance Criteria

- A GitHub visitor sees the spatial-depth and dynamic 360° panorama animations directly on the repository page.
- No click is required to understand either demo.
- A macOS user requesting video for the first time gets a hidden native key-entry dialog.
- After the first successful save, later video requests reuse the Keychain credential automatically.
- The credential never appears in chat, terminal commands, logs, committed files, or generated output metadata.
- Users can explicitly replace or forget the stored credential.
