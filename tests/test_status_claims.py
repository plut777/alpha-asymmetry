"""Documents may not assert their own status from memory.

Four claims in this project stopped being true without anything noticing: a PDF
described as compiled that was not, a toolchain described as absent that was
present, a branch described as unpushed that had been pushed, and a PR body that
drifted 29 commits behind the branch it described. Three of the four were
self-referential status assertions; the fourth was two copies of one document
diverging silently.

Guard A checks that docs/PROPOSED_PR.md is not older than the work it describes.
Guard C checks the status numbers the document states about itself.

Neither guard asks anyone to remember anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PR_DOC = ROOT / "docs" / "PROPOSED_PR.md"
PDF = ROOT / "paper" / "alpha-asymmetry.pdf"
BUILD_STATS = ROOT / "paper" / "build_stats.json"

# Paths whose changes make the PR description stale.
WATCHED = ("paper/", "analysis/")

REVIEWED_AT = re.compile(r"<!--\s*reviewed-at:\s*([0-9a-f]{7,40})\s*-->")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


# ---------------------------------------------------------------- Guard A

def test_pr_document_carries_a_reviewed_at_stamp():
    stamp = REVIEWED_AT.search(PR_DOC.read_text())
    assert stamp, (
        "docs/PROPOSED_PR.md has no <!-- reviewed-at: SHA --> stamp. The stamp is "
        "what makes staleness detectable: without it the document can drift behind "
        "the branch indefinitely, which is exactly how the PR body fell 29 commits "
        "behind.")
    sha = stamp.group(1)
    assert subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                          cwd=ROOT, capture_output=True).returncode == 0, (
        f"reviewed-at names {sha}, which is not a commit in this repository")


def test_pr_document_is_not_stale_against_the_work_it_describes():
    sha = REVIEWED_AT.search(PR_DOC.read_text()).group(1)
    newer = _git("log", "--oneline", f"{sha}..HEAD", "--", *WATCHED)
    assert not newer, (
        "docs/PROPOSED_PR.md is stale. These commits touched "
        f"{' or '.join(WATCHED)} after the reviewed-at commit {sha}:\n{newer}\n\n"
        "Either update the document to describe the current branch and re-stamp it, "
        "or re-stamp it deliberately if the changes do not affect the description. "
        "Re-stamping is a recorded act in git, which is the point: 'I meant to keep "
        "it current' becomes visible rather than assumed.")


# ---------------------------------------------------------------- Guard C

def _stats() -> dict:
    return json.loads(BUILD_STATS.read_text())


def test_build_stats_describe_the_committed_pdf():
    """Stats that no longer describe the current PDF must fail, not be believed."""

    actual = hashlib.sha256(PDF.read_bytes()).hexdigest()
    assert _stats()["pdf_sha256"] == actual, (
        "paper/build_stats.json describes a different PDF than the one committed. "
        "Rebuild and rerun analysis/record_build_stats.py; do not edit the figures "
        "by hand.")


def test_declared_page_count_matches_the_built_pdf():
    claimed = re.findall(r"clean:\s*(\d+)\s*pages", PR_DOC.read_text())
    assert claimed, "docs/PROPOSED_PR.md no longer states a page count in the expected form"
    for shown in claimed:
        assert int(shown) == _stats()["pages"], (
            f"docs/PROPOSED_PR.md claims {shown} pages; the built PDF has "
            f"{_stats()['pages']}. This is the '27 pages' defect.")


def test_declared_test_count_matches_collection():
    if os.environ.get("STATUS_CLAIMS_NESTED"):
        pytest.skip("nested collection; the outer run performs this check")
    claimed = re.findall(r"^- (\d+) deterministic tests", PR_DOC.read_text(), re.M)
    assert claimed, "docs/PROPOSED_PR.md no longer states a test count in the expected form"
    env = dict(os.environ, STATUS_CLAIMS_NESTED="1")
    # sys.executable, not "python": a different interpreter lacks the project
    # dependencies, silently fails to import several test modules, and reports a
    # smaller count that would read as a stale claim in the document.
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                          "-p", "no:cacheprovider"],
                         cwd=ROOT, capture_output=True, text=True, env=env).stdout
    # "67/68 tests collected (1 deselected)" -> the claim is about the default
    # offline suite, so the selected count is the one that matters; the network
    # divergence check is stated separately in the document.
    split = re.search(r"(\d+)/(\d+) tests? collected", out)
    plain = re.search(r"(\d+)\s+tests? collected", out)
    assert split or plain, f"could not read a collected-test count from pytest output:\n{out[-500:]}"
    collected = int(split.group(1)) if split else int(plain.group(1))
    for shown in claimed:
        assert int(shown) == collected, (
            f"docs/PROPOSED_PR.md claims {shown} tests; collection reports "
            f"{collected}. This is the '14 tests' defect.")


def test_declared_provenance_coverage_matches_the_inventory():
    from analysis.table_provenance import PROVENANCE

    tex = (ROOT / "paper" / "alpha-asymmetry.tex").read_text()
    total = len(set(re.findall(r"\\label\{(tab:[^}]+)\}", tex)))
    covered = len(set(PROVENANCE) | {"tab:spec"})

    text = PR_DOC.read_text()
    claimed = re.findall(r"\*\*(\d+) of the (\d+) manuscript tables\*\*", text)
    assert claimed, "docs/PROPOSED_PR.md no longer states provenance coverage in the expected form"
    for shown_cov, shown_total in claimed:
        assert (int(shown_cov), int(shown_total)) == (covered, total), (
            f"docs/PROPOSED_PR.md claims {shown_cov} of {shown_total} tables covered; "
            f"the inventory gives {covered} of {total}. This is the 'every figure was "
            f"machine-checked' defect.")
