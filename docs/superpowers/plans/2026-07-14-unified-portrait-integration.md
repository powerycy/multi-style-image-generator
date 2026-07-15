# Unified Portrait Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace rigid portrait-panorama sizing and delivery tiers with one intent-led uploaded-person rule shared by generative image and video outputs.

**Architecture:** Keep routing and tool execution unchanged. Put the concise global decision rule in `SKILL.md`, keep detailed prompt and QA guidance in `references/portrait-panorama-qa.md`, and lock the behavior with repository-contract tests and eval 14.

**Tech Stack:** Markdown Skill instructions, JSON behavior evals, Python `unittest` repository contracts.

## Global Constraints

- Preserve normal images, prompt-only output, 360° HTML, dynamic panorama, spatial photo, standard video, panorama video, dependency bootstrap, and API-key flows.
- Do not add named portrait-layout modes, fixed default meter ranges, fixed default height percentages, identity tiers, or delivery-tier labels.
- Derived previews inherit their source asset and do not independently restyle people.
- Automatic redraw remains capped at one and applies only to clearly unusable results.

---

### Task 1: Lock the simplified behavior with failing contracts

**Files:**
- Modify: `tests/test_repository_contract.py`
- Modify: `multi-style-image-generator/evals/evals.json`

**Interfaces:**
- Consumes: existing `RepositoryContractTests` fixture and eval id 14.
- Produces: assertions for the unified generation rule, derived-output boundary, intent-led prominence, and removal of rigid/tiered wording.

- [ ] **Step 1: Replace the panorama-tier assertions**

Require these behavior phrases in the Skill/reference/eval contract:

```python
required_rules = (
    "同一个人自然进入目标世界",
    "衣着、鞋履、发饰、道具、动作、材质和光照",
    "根据用户意图和画面叙事自然决定",
    "不因远景人物无法进行人像级身份核验",
    "自动重绘最多一次",
)
```

Reject the obsolete defaults and delivery labels:

```python
for obsolete in ("8–12 米", "6–10%", "通过 / 可用但需说明 / 不通过"):
    self.assertNotIn(obsolete, portrait_contract)
```

- [ ] **Step 2: Add the derived-output boundary contract**

```python
for phrase in (
    "空间照片预览",
    "动态增强",
    "继承已有底图",
    "不得自行换脸、换装",
):
    self.assertIn(phrase, skill)
```

- [ ] **Step 3: Update eval 14**

Make the uploaded-person panorama expectation require a comfortably visible person near the main viewing direction, scene-appropriate styling, intent-led prominence, normal-view QA, direct delivery when usable, and no engineering-style delivery label.

- [ ] **Step 4: Run focused tests and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_repository_contract.RepositoryContractTests.test_portrait_panorama_qa_uses_intent_led_delivery \
  tests.test_repository_contract.RepositoryContractTests.test_uploaded_person_rule_covers_generation_and_preserves_derived_assets \
  tests.test_repository_contract.RepositoryContractTests.test_portrait_panorama_eval_and_existing_modes_are_preserved -v
```

Expected: FAIL because the current Skill still contains `8–12 米`, `6–10%`, tiered labels, and no global derived-output boundary.

### Task 2: Implement the unified rule and verify every route

**Files:**
- Modify: `multi-style-image-generator/SKILL.md`
- Modify: `multi-style-image-generator/references/portrait-panorama-qa.md`
- Modify: `multi-style-image-generator/references/game-visual-styles.md`
- Modify: `multi-style-image-generator/evals/evals.json`
- Test: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: the failing contracts from Task 1.
- Produces: concise intent-led generation guidance and inherited-source behavior for derived previews.

- [ ] **Step 1: Replace fixed panorama sizing in `SKILL.md`**

State that uploaded-person generation places the same person naturally into the target world, redesigns clothing/footwear/hairstyle accessories/props/action/materials/lighting unless explicitly preserved, and chooses prominence from user intent without fixed ranges.

- [ ] **Step 2: Simplify QA and delivery**

Evaluate at intended viewing size. Deliver directly when the explicit creative goal is met and no obvious identity, gaze, compositing, deformation, seam, or artifact failure exists. Mention limitations only when they materially affect an explicit requirement or artifact usability. Redraw a clearly unusable result at most once.

- [ ] **Step 3: Add the derived-output boundary**

State that spatial-depth previews, panorama HTML, dynamic enhancement, and animation of an existing image inherit the source asset and do not independently change identity, clothing, accessories, pose, or environment.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: 3 tests pass.

- [ ] **Step 5: Run complete local validation**

```bash
python3 -m unittest discover -s tests -v
python3 -m json.tool multi-style-image-generator/evals/evals.json >/dev/null
python3 -m compileall -q multi-style-image-generator/scripts
/tmp/multi-style-skill-validator-venv/bin/python \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  multi-style-image-generator
```

Expected: all repository tests pass, JSON and Python validation exit 0, and the official validator prints `Skill is valid!`.

- [ ] **Step 6: Synchronize and publish**

Synchronize the repository Skill into `~/.codex/skills/multi-style-image-generator` while preserving `.venv` and `.deps-state.json`; validate the installed copy; inspect Git remote, branch, status, and diff; commit only scoped files; push the existing feature branch; update draft PR #1; and wait for all CI checks to pass.
