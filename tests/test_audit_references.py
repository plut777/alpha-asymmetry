"""Every commit hash cited in the audit record must resolve to a real Git object.

An entry in REVIEW_NOTES.md cited commit 24f6e6a, which does not exist in this
repository. The commit had not yet been made when the line was written, so there
was no hash to know and a plausible-looking one was written instead. Nothing
would have caught it: a hash is not a number, no build step reads it, and it
looks exactly like a real one.

This is the deterministic check for that class. It is cheap, it is total over the
audit documents, and it fails on a reference that cannot be resolved rather than
on one that merely looks wrong.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DOCS = ("docs/REVIEW_NOTES.md", "docs/CORRECTION_CHANGELOG.md",
              "docs/PROPOSED_PR.md", "docs/REVIEWER_RESPONSE.md",
              "docs/PREREGISTRATION_ENTRY_SYMMETRY.md")

# Backtick-quoted 7-40 hex characters: how this record cites commits. Requiring
# the backticks keeps the check off hex-looking prose such as SHA-256 digests
# quoted in full sentences, which are checked by the data manifest instead.
HASH = re.compile(r"`([0-9a-f]{7,40})`")

# Hashes that are deliberately recorded although unreachable from this branch.
KNOWN_EXTERNAL: dict[str, str] = {}


def _docs_with_hashes():
    out = []
    for rel in AUDIT_DOCS:
        path = ROOT / rel
        if not path.exists():
            continue
        hashes = sorted(set(HASH.findall(path.read_text())))
        if hashes:
            out.append((rel, hashes))
    return out


def _resolves(sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=ROOT, capture_output=True)
    return result.returncode == 0


@pytest.mark.parametrize("rel,hashes", _docs_with_hashes(), ids=lambda v: v if isinstance(v, str) else "")
def test_cited_commit_hashes_resolve(rel, hashes):
    missing = [h for h in hashes if h not in KNOWN_EXTERNAL and not _resolves(h)]
    assert not missing, (
        f"{rel} cites commit hash(es) that do not resolve to a Git object: "
        f"{', '.join(missing)}. A hash that cannot be resolved is an unsupported "
        f"reference: it names evidence that may not exist. Either correct it against "
        f"git log, or record it in KNOWN_EXTERNAL with the reason it is unreachable.")


def test_the_guard_would_catch_an_unresolvable_hash():
    """Mutation: the check must reject a hash that does not exist."""

    assert not _resolves("24f6e6a"), (
        "24f6e6a resolves in this repository, so it can no longer serve as the "
        "negative control; pick another unreachable hash")
    assert _resolves("HEAD"), "the resolver rejects a hash that does exist"
