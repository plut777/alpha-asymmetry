"""Guard B: the live pull-request body must match docs/PROPOSED_PR.md.

The PR description drifted 29 commits behind the branch because the document and
the published body are two copies of one text with nothing tying them together.
Guard A catches the document falling behind the code. This catches the published
body falling behind the document.

It needs network access and an authenticated `gh`, so it is marked `network` and
deselected by default: the offline suite must stay deterministic and runnable
without credentials. Run it deliberately, and before pushing a description change:

    pytest -m network

Comparison is on normalised text -- trailing whitespace and line-ending style are
not differences worth failing on, and GitHub rewrites the trailing newline.
Anything else is.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PR_DOC = ROOT / "docs" / "PROPOSED_PR.md"
PR_NUMBER = "2"
PR_REPO = "dissensus-ai/alpha-asymmetry"

pytestmark = pytest.mark.network


def _normalise(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").strip().split("\n"))


def _gh() -> str:
    for candidate in ("gh", str(Path.home() / ".local" / "bin" / "gh")):
        if shutil.which(candidate) or Path(candidate).exists():
            return candidate
    pytest.skip("gh CLI not available")


def _live_body() -> str:
    result = subprocess.run(
        [_gh(), "pr", "view", PR_NUMBER, "--repo", PR_REPO, "--json", "body"],
        cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"could not read PR #{PR_NUMBER}: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout)["body"]


def test_live_pr_body_matches_the_reviewed_document():
    local, live = _normalise(PR_DOC.read_text()), _normalise(_live_body())
    if local == live:
        return

    import difflib
    diff = [d for d in difflib.unified_diff(
        local.split("\n"), live.split("\n"), "docs/PROPOSED_PR.md",
        f"live PR #{PR_NUMBER}", lineterm="", n=1)
        if d[:1] in "+-" and d[:3] not in ("---", "+++")]
    pytest.fail(
        f"the live PR #{PR_NUMBER} body and docs/PROPOSED_PR.md have diverged in "
        f"{len(diff)} line(s). The document is the reviewed copy; publish it with\n"
        f"    gh pr edit {PR_NUMBER} --repo {PR_REPO} --body-file docs/PROPOSED_PR.md\n"
        f"rather than editing the description in the browser, which is how the two "
        f"came apart before.\n\nFirst differences:\n" + "\n".join(diff[:12]))
