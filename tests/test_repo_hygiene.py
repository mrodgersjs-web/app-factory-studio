"""Repository hygiene invariants (GHUP polish wave, 2026-10-19).

Asserts, from the files on disk, the repo-health items a stranger's tooling
checks first: CODEOWNERS ownership, the copilot instructions file, the README
badge/footer/clone target, and workflow timeouts with no `continue-on-error`.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
REPO = "app-factory-studio"


def _job_blocks(text: str) -> dict[str, str]:
    """Split a workflow file into {job_name: job_block} by 2-space job keys."""
    lines = text.splitlines()
    jobs_at = next((i for i, ln in enumerate(lines) if ln.rstrip() == "jobs:"), None)
    assert jobs_at is not None, "workflow has no jobs: section"
    blocks: dict[str, list[str]] = {}
    current = None
    for ln in lines[jobs_at + 1 :]:
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", ln)
        if m:
            current = m.group(1)
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(ln)
    return {name: "\n".join(block) for name, block in blocks.items()}


def test_codeowners_owns_everything():
    text = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "* @mrodgersjs-web" in text


def test_copilot_instructions_shape():
    p = REPO_ROOT / ".github" / "copilot-instructions.md"
    text = p.read_text(encoding="utf-8")
    assert 0 < p.stat().st_size <= 8000, f"copilot-instructions.md is {p.stat().st_size} bytes"
    assert any(word in text for word in ("pytest", "smoke", "npm test"))


def test_readme_badge_footer_and_clone_target():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "github/actions/workflow/status" in text
    assert "rodgersintelligence.com" in text
    assert any(word in text for word in ("pytest", "smoke", "npm test", "node --test"))
    for line in text.splitlines():
        if "git clone" in line:
            assert f"mrodgersjs-web/{REPO}" in line, f"clone must target this repo: {line}"


def test_workflows_have_timeouts_and_no_continue_on_error():
    paths = sorted(WORKFLOWS.glob("*.yml"))
    assert paths, "no workflows found"
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "continue-on-error" not in text, f"{path.name} uses continue-on-error"
        for job_name, block in _job_blocks(text).items():
            assert "timeout-minutes" in block, f"{path.name}:{job_name} has no timeout-minutes"


def test_test_job_runs_on_push_to_main():
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "push:" in text and "pull_request:" in text
    assert _job_blocks(text), "ci.yml must keep real jobs"
