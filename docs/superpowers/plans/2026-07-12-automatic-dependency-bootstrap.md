# Automatic Dependency Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Pillow/NumPy-dependent Skill commands install and reuse an isolated local Python environment automatically, with tested failure handling, CI coverage, and complete bilingual documentation.

**Architecture:** A standard-library launcher owns virtual-environment lifecycle, requirements hashing, target allowlisting, and child-process execution. Existing functional scripts stay focused on image/video work and are invoked unchanged through the launcher only when they need third-party packages. Contract tests keep `SKILL.md`, both READMEs, dependencies, and CI aligned.

**Tech Stack:** Python 3.9+, `venv`, `subprocess`, `hashlib`, `unittest`, Pillow, NumPy, GitHub Actions YAML.

## Global Constraints

- Create and reuse `multi-style-image-generator/.venv`; never install into the system interpreter.
- Never invoke `sudo`, Homebrew, or another system package manager automatically.
- Execute subprocesses with argument arrays and `shell=False`.
- Allow only bundled dependency-bearing scripts; reject absolute paths, traversal, and unknown targets.
- Keep Python 3.9 as the documented minimum.
- Keep Chinese and English README sections structurally equivalent.
- Do not change prompt routing, rendering behavior, BigModel request behavior, or generated viewer HTML.

---

### Task 1: Dependency launcher contract and implementation

**Files:**
- Create: `multi-style-image-generator/requirements.txt`
- Create: `multi-style-image-generator/scripts/run_with_deps.py`
- Create: `tests/test_run_with_deps.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: a target filename from the explicit set `create_spatial_preview.py`, `create_spatial_photo_viewer.py`, `create_spatial_photo_depth_viewer.py`, and `normalize_equirectangular_aspect.py`, followed by target arguments.
- Produces: `resolve_target(name: str, scripts_dir: Path) -> Path`, `requirements_digest(path: Path) -> str`, `environment_is_current(venv_dir: Path, digest: str, runner=...) -> bool`, `ensure_environment(skill_dir: Path, runner=...) -> Path`, and `main(argv: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write failing launcher tests**

Create `tests/test_run_with_deps.py` with standard-library `unittest` cases that import the launcher by file path and verify:

```python
def test_resolve_target_accepts_allowlisted_script(self):
    target = launcher.resolve_target("create_spatial_preview.py", self.scripts_dir)
    self.assertEqual(target, self.scripts_dir / "create_spatial_preview.py")

def test_resolve_target_rejects_unknown_traversal_and_absolute_paths(self):
    for value in ("other.py", "../create_spatial_preview.py", "/tmp/script.py"):
        with self.subTest(value=value), self.assertRaises(ValueError):
            launcher.resolve_target(value, self.scripts_dir)

def test_requirements_digest_changes_with_content(self):
    first = launcher.requirements_digest(self.requirements)
    self.requirements.write_text("Pillow\nNumPy\n", encoding="utf-8")
    self.assertNotEqual(first, launcher.requirements_digest(self.requirements))
```

Add focused tests with a recording runner for missing environment creation, current-environment reuse, changed-requirements synchronization, pip failure propagation, and final argument preservation.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest discover -s tests -v`

Expected: failure because `multi-style-image-generator/scripts/run_with_deps.py` does not exist.

- [ ] **Step 3: Add the minimal dependency declaration and ignore rules**

Create `multi-style-image-generator/requirements.txt` containing compatible Pillow and NumPy constraints for Python 3.9. Add these patterns to `.gitignore`:

```gitignore
multi-style-image-generator/.venv/
multi-style-image-generator/.deps-state.json
```

- [ ] **Step 4: Implement target validation and state decisions**

Implement `run_with_deps.py` using `Path(__file__).resolve()` to find the Skill directory. Hash the raw requirements bytes with SHA-256. Store state as JSON only after successful installation. Check the virtual environment by running:

```python
[str(venv_python), "-c", "import PIL, numpy"]
```

Return `False` for a missing interpreter, missing/invalid state, digest mismatch, or failed import probe.

- [ ] **Step 5: Implement isolated setup and execution**

When synchronization is required, run these argument-array commands in order:

```python
[sys.executable, "-m", "venv", str(venv_dir)]
[str(venv_python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements_path)]
```

Then write the successful digest and execute:

```python
[str(venv_python), str(target), *target_args]
```

Catch `subprocess.CalledProcessError` and `OSError`, identify the failed phase, print the environment path and recovery command to stderr, and return the child exit code or `1`.

- [ ] **Step 6: Run launcher tests and verify GREEN**

Run: `python3 -m unittest discover -s tests -v`

Expected: all launcher tests pass with no network access and no real virtual environment creation.

- [ ] **Step 7: Commit the launcher slice**

```bash
git add .gitignore multi-style-image-generator/requirements.txt multi-style-image-generator/scripts/run_with_deps.py tests/test_run_with_deps.py
git commit -m "feat: bootstrap skill dependencies automatically"
```

### Task 2: Skill behavior and documentation contracts

**Files:**
- Create: `tests/test_repository_contract.py`
- Modify: `multi-style-image-generator/SKILL.md`
- Modify: `README.md`
- Modify: `README_en.md`

**Interfaces:**
- Consumes: the launcher command from Task 1.
- Produces: copy-pasteable relative commands and an explicit automatic-installation contract for users and future Codex instances.

- [ ] **Step 1: Add failing repository contract tests**

Create tests asserting:

```python
def test_tracked_docs_have_no_developer_absolute_paths(self):
    developer_home_prefix = "/" + "Users/"
    for path in self.tracked_text_files:
        self.assertNotIn(developer_home_prefix, path.read_text(encoding="utf-8"))

def test_skill_routes_dependency_scripts_through_launcher(self):
    skill = self.skill_md.read_text(encoding="utf-8")
    self.assertIn("scripts/run_with_deps.py create_spatial_preview.py", skill)
    self.assertIn("scripts/run_with_deps.py normalize_equirectangular_aspect.py", skill)

def test_readmes_document_automatic_local_environment(self):
    self.assertIn("multi-style-image-generator/.venv", self.readme_zh)
    self.assertIn("multi-style-image-generator/.venv", self.readme_en)
```

Also compare the ordered level-two headings of both READMEs after applying a Chinese-to-English heading map.

- [ ] **Step 2: Run contract tests and verify RED**

Run: `python3 -m unittest tests.test_repository_contract -v`

Expected: failures for hard-coded paths, missing launcher commands, and missing automatic-installation documentation.

- [ ] **Step 3: Baseline-test the existing Skill instructions**

With explicit user authorization for subagent validation, give a fresh agent the unmodified Skill plus a spatial-preview request in an environment without Pillow/NumPy. Record whether it attempts a global install, fails without recovery, or discovers an isolated setup. Do not disclose the intended fix.

- [ ] **Step 4: Update `SKILL.md` minimally**

Add a concise dependency bootstrap rule near the bundled-dependency section:

```text
需要 Pillow 或 NumPy 的脚本必须通过 scripts/run_with_deps.py 调用。首次运行允许启动器在 Skill 目录创建 .venv 并自动安装 requirements.txt；不要改用全局 pip、sudo 或系统包管理器。
```

Replace the two developer-specific absolute commands and every direct invocation of a dependency-bearing script with launcher-based, Skill-relative commands. Add missing-`ffmpeg` detection guidance without automatic system installation.

- [ ] **Step 5: Update both READMEs**

In matching sections, document:

- which commands need only the Python standard library;
- the automatic `.venv` creation and first-run download;
- launcher examples for spatial preview and 2:1 normalization;
- manual preparation using `python3 scripts/run_with_deps.py create_spatial_preview.py --help`;
- reset/removal by deleting only `multi-style-image-generator/.venv` and `.deps-state.json`;
- network/proxy recovery and optional `ffmpeg` installation guidance;
- API keys remain environment-only and are unrelated to Python package installation.

- [ ] **Step 6: Run contract and unit tests and verify GREEN**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 7: Forward-test the updated Skill**

With explicit user authorization for subagent validation, repeat the same fresh-agent scenario with the updated Skill. Verify that it chooses the launcher, keeps installation local, and reports installation failure rather than silently using global pip.

- [ ] **Step 8: Commit the Skill and documentation slice**

```bash
git add README.md README_en.md multi-style-image-generator/SKILL.md tests/test_repository_contract.py
git commit -m "docs: explain automatic skill setup"
```

### Task 3: Continuous integration and executable consistency

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: executable modes for `multi-style-image-generator/scripts/*.py`
- Modify: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: repository tests and launcher from Tasks 1-2.
- Produces: a GitHub Actions `test` job that validates the repository on Python 3.9 and Python 3.13.

- [ ] **Step 1: Extend the contract test for CI and script modes**

Add tests that require `.github/workflows/ci.yml`, assert it invokes `python -m unittest discover -s tests -v`, and verify every Python script starts with the Python shebang. Add a shell verification step for executable Git modes because `unittest` cannot portably inspect index modes.

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m unittest tests.test_repository_contract -v`

Expected: failure because `.github/workflows/ci.yml` does not exist.

- [ ] **Step 3: Add the CI workflow**

Create one workflow triggered by pushes and pull requests. Use `actions/checkout` and `actions/setup-python`, a matrix containing `3.9` and `3.13`, pip caching keyed by the bundled requirements file, and these commands:

```bash
python -m compileall -q multi-style-image-generator/scripts
python -m unittest discover -s tests -v
python -c "import json, pathlib; data=json.loads(pathlib.Path('multi-style-image-generator/evals/evals.json').read_text()); assert len(data['evals']) == 11"
python multi-style-image-generator/scripts/create_bigmodel_video.py --help
python multi-style-image-generator/scripts/create_panorama_viewer.py --help
python multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py --help
```

- [ ] **Step 4: Normalize executable modes**

Set executable mode on every tracked `multi-style-image-generator/scripts/*.py` file and verify:

```bash
git ls-files -s 'multi-style-image-generator/scripts/*.py'
```

Expected: every script reports mode `100755`.

- [ ] **Step 5: Run local CI-equivalent checks**

Run the compile, unittest, JSON, standard-library `--help`, and launcher `--help` commands from Step 3. The launcher command may download dependencies into the ignored Skill-local `.venv`.

- [ ] **Step 6: Commit the CI slice**

```bash
git add .github/workflows/ci.yml tests/test_repository_contract.py multi-style-image-generator/scripts
git commit -m "ci: validate skill scripts and documentation"
```

### Task 4: Skill validation and release-readiness verification

**Files:**
- Modify only files required to correct issues discovered by validation.

**Interfaces:**
- Consumes: the completed repository.
- Produces: evidence that the Skill package is structurally valid, portable, tested, and clean.

- [ ] **Step 1: Run the official Skill validator**

Run:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" multi-style-image-generator
```

Expected: validation succeeds. If it fails, add a failing repository test for the discovered regression when practical, then make the minimal correction.

- [ ] **Step 2: Run the full verification suite fresh**

Run:

```bash
python3 -m compileall -q multi-style-image-generator/scripts
python3 -m unittest discover -s tests -v
python3 -c "import json, pathlib; data=json.loads(pathlib.Path('multi-style-image-generator/evals/evals.json').read_text()); assert len(data['evals']) == 11"
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --help >/dev/null
python3 multi-style-image-generator/scripts/create_panorama_viewer.py --help >/dev/null
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py --help >/dev/null
git diff --check
git status --short --branch
```

Expected: all commands exit `0`; no untracked generated environment or state file appears because both are ignored.

- [ ] **Step 3: Confirm acceptance criteria explicitly**

Verify `git grep "$(printf '/%s/' Users)"` finds no developer path in tracked project text, the second launcher invocation does not run pip, all scripts have mode `100755`, and both README heading structures match.

- [ ] **Step 4: Commit any validation-only corrections**

If Step 1-3 required changes, commit only those corrections:

```bash
git add -u
git commit -m "fix: address skill validation findings"
```

- [ ] **Step 5: Review local commit range**

Run:

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git status --short --branch
```

Expected: the design plus implementation commits are present, the change set stays within dependency bootstrap/testing/documentation scope, and the worktree is clean.
