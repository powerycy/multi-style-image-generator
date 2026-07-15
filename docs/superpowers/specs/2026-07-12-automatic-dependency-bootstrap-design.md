# Automatic Dependency Bootstrap Design

## Goal

Make the installed `multi-style-image-generator` skill usable without asking users to manually install Pillow or NumPy, while keeping installations isolated from the system Python and making failures actionable.

## Scope

This change covers dependency declaration, automatic Python environment setup, documentation, tests, and CI. It does not change image prompts, rendering behavior, BigModel requests, or the generated HTML viewers.

## Chosen approach

Add a single dependency-aware launcher at `multi-style-image-generator/scripts/run_with_deps.py`. Commands in `SKILL.md` that need third-party Python packages will run through this launcher. The launcher will:

1. Resolve paths relative to its own skill directory rather than a developer-specific absolute path.
2. Accept only an explicit allowlist of bundled scripts that need managed Python dependencies.
3. Create `multi-style-image-generator/.venv` with the invoking Python when the environment does not exist.
4. Install packages from `multi-style-image-generator/requirements.txt` into that environment.
5. Store a hash of the dependency file after a successful installation and reinstall only when the file changes or required imports are unavailable.
6. Execute the requested bundled script with the virtual environment's Python and forward its arguments and exit code.

The launcher will not install system packages or use `sudo`. The frame-sequence workflow will detect a missing `ffmpeg` command and provide platform-neutral guidance plus a Homebrew example, because silently modifying the operating system is outside the safe scope of a Skill.

## Files and responsibilities

- `multi-style-image-generator/requirements.txt`: runtime Python packages needed by the managed scripts.
- `multi-style-image-generator/scripts/run_with_deps.py`: isolated environment creation, dependency synchronization, target validation, and process execution.
- `tests/test_run_with_deps.py`: standard-library unit tests for target validation, environment decisions, failure reporting, and command construction.
- `.github/workflows/ci.yml`: syntax, configuration, unit-test, and CLI smoke checks across supported Python versions.
- `README.md` and `README_en.md`: user-facing installation behavior, first-run network requirement, environment location, recovery, manual setup, removal, and `ffmpeg` guidance.
- `multi-style-image-generator/SKILL.md`: relative-path commands and mandatory use of the launcher for dependency-bearing workflows.
- `.gitignore`: ignore the generated Skill-local virtual environment and bootstrap state.

## Dependency behavior

The first dependency-bearing command may take longer because it creates a virtual environment and downloads packages. Later commands reuse the environment. A changed `requirements.txt` invalidates the stored hash and triggers dependency synchronization.

If environment creation or package installation fails, the launcher will stop before running the target and report:

- which phase failed;
- the virtual environment path;
- the exact recovery command the user can run;
- common network/proxy causes without exposing environment secrets.

The launcher will never write API keys, proxy credentials, or pip output containing secrets into tracked files.

## Security and portability

Only known scripts inside the bundled `scripts` directory may be launched. Absolute paths, parent traversal, arbitrary Python modules, and shell commands are rejected. Subprocesses will receive argument arrays without `shell=True`.

All project commands will derive paths from `__file__` or documented placeholders. Existing developer-specific absolute home paths will be removed.

## Testing strategy

Use Python's built-in `unittest` so the test suite itself needs no third-party package. Follow test-first development for the launcher. Tests will use temporary directories and injected/mocked process boundaries while exercising real path validation and state decisions.

Required cases:

- reject an unknown target;
- reject traversal and absolute target paths;
- create a virtual environment when missing;
- reuse an environment when imports and dependency hash are current;
- synchronize when `requirements.txt` changes;
- stop and return a useful message when venv creation or pip installation fails;
- construct the final target command without a shell and preserve target arguments.

CI will also compile every bundled Python script, validate `evals.json`, run all unit tests, check `--help` for standard-library scripts, and run dependency-bearing `--help` commands through the managed environment.

## Documentation contract

The Chinese and English READMEs must remain structurally equivalent. They will clearly distinguish:

- features that require no extra Python packages;
- features that trigger automatic Skill-local installation;
- external requirements such as WebGL, a BigModel API key, and optional `ffmpeg`;
- manual commands for users who prefer to prepare or remove the environment themselves.

`SKILL.md` will give future Codex instances an executable recipe: use the launcher, let it install automatically, report failures faithfully, and never fall back to global or privileged installation.

## Acceptance criteria

- A clean checkout can invoke a Pillow/NumPy-dependent `--help` command through the launcher without preinstalling those packages globally.
- A second invocation reuses the existing Skill-local environment without reinstalling unchanged dependencies.
- No developer-specific absolute path remains in tracked text files.
- Unit tests pass using the repository's supported base Python.
- CI configuration covers the documented Python version floor and at least one newer Python version.
- README, English README, Skill instructions, dependency file, tests, and CI agree on the installation workflow.
