# macOS Keychain Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prompt for the BigModel/CogVideoX API key once in a hidden macOS dialog, store it in Keychain, and reuse it automatically.

**Architecture:** Add isolated credential helpers to `create_bigmodel_video.py`, retaining environment-variable precedence and using injected subprocess/platform values for tests. Add explicit replace/forget management flows and document the behavior in Skill onboarding and both READMEs.

**Tech Stack:** Python 3.9+ standard library, macOS `osascript`, macOS `security`, `unittest`.

## Global Constraints

- Keychain service is `multi-style-image-generator.bigmodel`; account is `api-key`.
- Credential order is selected environment variable, `ZHIPU_API_KEY`, Keychain, then secure dialog.
- The key must never be printed, committed, placed in a process argument, or written to generated JSON.
- `--dry-run` never reads Keychain or opens a dialog.
- Non-macOS behavior remains environment-only.

---

### Task 1: Credential resolution helpers

**Files:**
- Modify: `multi-style-image-generator/scripts/create_bigmodel_video.py`
- Create: `tests/test_create_bigmodel_video.py`

**Interfaces:**
- Produces: `keychain_read(run) -> Optional[str]`, `prompt_api_key(run) -> str`, `keychain_write(api_key, run) -> None`, `keychain_delete(run) -> bool`, and `resolve_api_key(environ, platform_name, run) -> str`, using Python 3.9-compatible type syntax.

- [ ] **Step 1: Write failing tests**

Test environment precedence, saved-key reuse without dialog, missing-item prompt/write, cancellation, empty input, and non-macOS failure with a fake `run` callable returning `subprocess.CompletedProcess` objects.

```python
def test_resolve_api_key_prefers_environment(self):
    run = Mock()
    key = video.resolve_api_key({"BIGMODEL_API_KEY": "env-key"}, "darwin", run)
    self.assertEqual(key, "env-key")
    run.assert_not_called()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_create_bigmodel_video -v`

Expected: FAIL because the credential helper functions do not exist.

- [ ] **Step 3: Implement constants and Keychain helpers**

Add `KEYCHAIN_SERVICE`, `KEYCHAIN_ACCOUNT`, and helpers using argument-list subprocess calls. `keychain_write` must invoke `security -i` and send an `add-generic-password -U -a api-key -s multi-style-image-generator.bigmodel -X <hex>` command only through subprocess input; neither the key nor its encoded form may occur in the process argument list or captured output.

- [ ] **Step 4: Implement the secure dialog and resolution order**

Use AppleScript `text returned of (display dialog ... default answer "" with hidden answer ...)`, treat exit code 1 as cancellation, strip the captured value, and reject empty input. On non-darwin platforms raise the existing actionable environment-variable error.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_create_bigmodel_video -v`

Expected: all credential helper tests pass without invoking real system tools.

### Task 2: CLI management and dry-run behavior

**Files:**
- Modify: `multi-style-image-generator/scripts/create_bigmodel_video.py`
- Modify: `tests/test_create_bigmodel_video.py`

**Interfaces:**
- Produces: `build_parser() -> argparse.ArgumentParser` and `main(argv=None, environ=None, platform_name=None, run=subprocess.run) -> int`.

- [ ] **Step 1: Write failing CLI tests**

Cover `--replace-api-key` without prompt, `--forget-api-key` without prompt, mutual exclusion, normal generation requiring prompt, and dry-run avoiding `resolve_api_key`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests.test_create_bigmodel_video.VideoCliTests -v`

Expected: FAIL because the current parser requires `--prompt` before management actions.

- [ ] **Step 3: Refactor parser and main**

Make `--prompt` optional at parse time; place `--replace-api-key` and `--forget-api-key` in a mutually exclusive group. Process management actions first, then require prompt for generation. Build the payload before credential resolution and return immediately for dry-run.

- [ ] **Step 4: Improve authentication failure guidance**

For HTTP 401/403, raise a redacted message that tells macOS users to run `--replace-api-key`; preserve the response status without echoing Authorization headers.

- [ ] **Step 5: Run all video tests and verify GREEN**

Run: `python3 -m unittest tests.test_create_bigmodel_video -v`

Expected: all video tests pass.

### Task 3: Skill and README onboarding

**Files:**
- Modify: `multi-style-image-generator/SKILL.md`
- Modify: `README.md`
- Modify: `README_en.md`
- Modify: `multi-style-image-generator/evals/evals.json`
- Modify: `tests/test_repository_contract.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: CLI flags from Task 2.
- Produces: onboarding text and evaluation contract for first-run prompt, reuse, replace, and forget behavior.

- [ ] **Step 1: Write a failing repository-contract test**

Assert that SKILL.md contains `macOS 钥匙串`, `--replace-api-key`, and `--forget-api-key`, that both READMEs describe first-run secure input and later automatic reuse, and that the eval count is 13.

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL because current documentation only describes environment variables.

- [ ] **Step 3: Update Skill behavior**

State that a video request must resolve credentials before API use, macOS prompts once and saves to Keychain, later calls auto-read, secrets must never be requested in chat, and natural-language replace/forget requests map to the new flags.

- [ ] **Step 4: Update both READMEs and onboarding eval**

Document the same secure flow in Chinese and English. Preserve environment variables as an override, add eval 13 with an expectation that the assistant never asks the user to paste the key into chat, update the repository-contract count to 13, and update the CI eval assertion from 12 to 13.

- [ ] **Step 5: Run focused and full tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass.

### Task 4: Platform-safe verification and commit

**Files:**
- Modify only if validation exposes a defect.

**Interfaces:**
- Consumes: final script, docs, and tests.
- Produces: verified credential onboarding implementation.

- [ ] **Step 1: Compile AppleScript without displaying it**

Use `osacompile` against the exact hidden-input AppleScript and expect exit code 0.

- [ ] **Step 2: Verify Keychain command shape without a real secret**

Use unit-test fakes to assert the key is in subprocess stdin and absent from argv and captured diagnostic text. Do not create or modify the user's real Keychain item during automated verification.

- [ ] **Step 3: Run the full test suite and Skill validator**

Run `python3 -m unittest discover -s tests -v` and the official `quick_validate.py` through the prepared validator environment.

Expected: all tests pass and `Skill is valid!`.

- [ ] **Step 4: Commit**

```bash
git add multi-style-image-generator/scripts/create_bigmodel_video.py tests/test_create_bigmodel_video.py multi-style-image-generator/SKILL.md README.md README_en.md multi-style-image-generator/evals/evals.json tests/test_repository_contract.py
git commit -m "feat: reuse video API key from macOS Keychain"
```
