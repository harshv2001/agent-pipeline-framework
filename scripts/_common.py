"""Shared helpers for the pipeline-framework scripts.

Not a public API — used by scaffold_pipeline.py, validate_stage_file.py,
and advance_stage.py. Kept dependency-light (PyYAML only) on purpose so
these scripts run in any environment this framework's Claude Code sessions
run in.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

STAGES = [
    "00-source-manifest",
    "01-raw-metadata",
    "02-triage-decisions",
    "03-draft",
    "04-agent-review",
    "05-pending-human-review",
    "06-approved",
    "07-rejected",
    "08-executed",
    "09-audit-log",
]

# Which forward transitions advance_stage.py will perform. Anything not
# listed here is refused — this is the mechanical half of docs/01-governance-
# rules.md Rule 2 ("nothing skips a stage").
ALLOWED_TRANSITIONS = {
    "01-raw-metadata": ["02-triage-decisions"],
    "02-triage-decisions": ["03-draft", "05-pending-human-review"],  # escalate skips drafting
    "03-draft": ["04-agent-review"],
    "04-agent-review": ["03-draft", "05-pending-human-review"],  # revise, or pass/escalate
    "05-pending-human-review": ["06-approved", "07-rejected"],
    # 06-approved -> 07-rejected: the human reviewer changes their mind
    # after approving but before publish (nothing external has happened
    # yet) -- e.g. "approved this, now I want it expanded first." Added
    # 2026-10-30. Still goes through revise()'s same reject-with-feedback
    # path (docs/06-review-and-notification.md), never a hand-edit of the
    # locked 06-approved record itself.
    "06-approved": ["07-rejected", "08-executed"],
}

# 05-pending-human-review is the one stage that is a *queue*, not a ledger of
# history: it must hold only items genuinely awaiting a human decision. When
# an item is approved or rejected its packet is moved (not copied) out of
# here -- 06/07 carry the identical body forward byte for byte, so nothing is
# lost. Every other stage keeps its record (01 for dedup, 02-04 as history,
# 06 for the hash lock and publish-run pickup, 08 as the receipt).
QUEUE_STAGE = "05-pending-human-review"
DECIDED_STAGES = ["06-approved", "07-rejected", "08-executed"]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a stage-store markdown file into (frontmatter dict, body)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("File has no valid --- delimited frontmatter block")
    fm_text, body = m.group(1), m.group(2)
    fm = yaml.safe_load(fm_text) or {}
    return fm, body


def render(frontmatter: dict, body: str) -> str:
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm_text}\n---\n{body}"


_FM_BYTES_RE = re.compile(rb"\A(---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|\Z))", re.DOTALL)


def rewrite_frontmatter(path: Path, frontmatter: dict) -> None:
    """Replace ONLY the frontmatter block of a stage-store file, leaving every
    byte after the closing '---' exactly as it was (including leading blank
    lines and the file's line-ending style). `render`/`write_item` can't
    promise that -- they round-trip the body through a regex that eats
    leading whitespace -- so anything that must not touch the body (a status
    flip on an immutable-body record) uses this."""
    raw = path.read_bytes()
    m = _FM_BYTES_RE.match(raw)
    if not m:
        raise ValueError(f"{path}: no valid --- delimited frontmatter block")
    eol = b"\r\n" if m.group(1).endswith(b"\r\n") else b"\n"
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    new_fm = fm_text.replace("\n", eol.decode()).encode("utf-8")
    path.write_bytes(m.group(1) + new_fm + m.group(3) + raw[m.end():])


def read_item(path: Path) -> tuple[dict, str]:
    return split_frontmatter(path.read_text(encoding="utf-8"))


def write_item(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(frontmatter, body), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def stage_file(pipeline_dir: Path, stage: str, item_id: str) -> Path:
    return pipeline_dir / "stage-store" / stage / f"{item_id}.md"


_VERSION_SUFFIX_RE = re.compile(r"^(?P<base>.+)-v(?P<n>\d+)$")


def base_item_id(item_id: str) -> str:
    """Strip a trailing '-vN' version suffix, if any. 'ab12-v2' -> 'ab12'."""
    m = _VERSION_SUFFIX_RE.match(item_id)
    return m.group("base") if m else item_id


def next_version_id(pipeline_dir: Path, item_id: str) -> str:
    """The next '-vN' id for a revision of `item_id`, unique across every
    stage. The unversioned record is implicitly v1, so the first revision
    is always '-v2' regardless of which stage holds the highest version
    seen so far -- a revision started from an already-versioned packet
    (e.g. reviewing '-v2' again) still lands on the next free number."""
    base = base_item_id(item_id)
    max_v = 1
    for stage in STAGES:
        stage_dir = pipeline_dir / "stage-store" / stage
        if not stage_dir.exists():
            continue
        for path in stage_dir.glob("*.md"):
            stem = path.stem
            if stem == base:
                max_v = max(max_v, 1)
                continue
            m = _VERSION_SUFFIX_RE.match(stem)
            if m and m.group("base") == base:
                max_v = max(max_v, int(m.group("n")))
    return f"{base}-v{max_v + 1}"


def decided_stage(pipeline_dir: Path, item_id: str) -> str | None:
    """The furthest post-decision stage (06/07/08) that already holds this
    item, or None if it hasn't been decided. Furthest-first."""
    for stage in reversed(DECIDED_STAGES):
        if stage_file(pipeline_dir, stage, item_id).exists():
            return stage
    return None


def queue_report(pipeline_dir: Path) -> dict:
    """Classify every file in 05-pending-human-review.

    - pending:   status 'pending' and no record at 06/07/08 -- genuinely
                 awaiting a human decision. This is the only list a review
                 digest or a backpressure check should count.
    - undecided_sync: status was hand-edited to approved/rejected but
                 `advance_stage.py --sync` hasn't picked it up yet.
    - stale:     the item already exists at 06/07/08, so this 05 file is a
                 leftover copy (see QUEUE_STAGE). Each entry is
                 (item_id, later_stage). Clear with `--cleanup-queue`.
    """
    report: dict = {"pending": [], "undecided_sync": [], "stale": []}
    queue_dir = pipeline_dir / "stage-store" / QUEUE_STAGE
    if not queue_dir.exists():
        return report
    for path in sorted(queue_dir.glob("*.md")):
        fm, _ = read_item(path)
        item_id = fm.get("item_id") or path.stem
        later = decided_stage(pipeline_dir, item_id)
        if later:
            report["stale"].append((item_id, later))
        elif fm.get("status") == "pending":
            report["pending"].append(item_id)
        else:
            report["undecided_sync"].append(item_id)
    return report


def manifest_hash(pipeline_dir: Path, body: str, manifest: list[str] | None) -> str:
    """Hash of the review packet body plus every manifest-listed file's
    current bytes, so the approval lock (docs/01-governance-rules.md Rule
    4) covers what actually ships -- not just the prose body -- for a
    pipeline whose Content Agent finalizes non-text artifacts (an image, a
    rendered page) at draft time alongside it (base-framework/agents/
    content-agent.md, Contract step 5).

    Deterministic and order-independent: manifest paths are sorted before
    hashing, so listing them in a different order locks the same hash.
    Paths are relative to `pipeline_dir` (`pipelines/<name>/`) -- a path
    like `../../../sibling-repo/src/...` can still be listed when the
    artifact lives in a sibling repo, same as this stage-store's own `ref`
    fields reach outside the pipeline folder when they need to.

    A missing listed file hashes as the literal string "MISSING" rather
    than raising, so verification reports a clear mismatch (Publisher
    Agent contract step 1) instead of crashing mid-publish."""
    lines = [f"body:{sha256_hex(body)}"]
    for rel in sorted(manifest or []):
        path = (pipeline_dir / rel).resolve()
        if path.is_file():
            lines.append(f"{rel}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        else:
            lines.append(f"{rel}:MISSING")
    return sha256_hex("\n".join(lines))


def check_completeness(pipeline_dir: Path) -> list[tuple[str, str, str]]:
    """Find items left behind mid-pipeline instead of reaching a final-or-
    waiting status, per base-framework/SKILL.md's discovery-run steps 4-7:
    every item that gets a 02-triage-decisions record is supposed to reach,
    within the same run, either `discard` (terminal at 02), a direct
    escalation to 05 (02's `escalate` verdict), or the 03 -> 04 -> 05 chain
    (looping 03 <-> 04 on `revise` until `pass` or max_review_cycles).

    Returns a list of (item_id, furthest_stage, reason) for every item whose
    furthest stage is 02 (status proceed/escalate, i.e. not yet discarded),
    03, or 04 -- stages that should never be where an item rests at the end
    of a run. 05/06/07/08 are all valid resting stages (waiting on a human,
    locked for publish, rejected, or executed) and are not reported; so is
    02 with status discard, the one terminal outcome at that stage.

    Scans every item_id appearing in 02, 03, or 04 -- that covers every item
    that has entered the decision pipeline, including a human --revise's
    versioned draft (which starts fresh at 03, bypassing 02, docs/03-stage-
    store-model.md "File identity and naming"). 05/06/07/08 need no separate
    scan: every path there requires a 02 record first (ALLOWED_TRANSITIONS),
    so its item_id is already covered."""
    stuck: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for stage in ("02-triage-decisions", "03-draft", "04-agent-review"):
        stage_dir = pipeline_dir / "stage-store" / stage
        if not stage_dir.exists():
            continue
        for path in sorted(stage_dir.glob("*.md")):
            item_id = path.stem
            if item_id in seen:
                continue
            seen.add(item_id)
            furthest = None
            for s in ("08-executed", "07-rejected", "06-approved", QUEUE_STAGE,
                      "04-agent-review", "03-draft", "02-triage-decisions"):
                if stage_file(pipeline_dir, s, item_id).exists():
                    furthest = s
                    break
            if furthest == "02-triage-decisions":
                fm, _ = read_item(stage_file(pipeline_dir, furthest, item_id))
                status = fm.get("status")
                if status != "discard":
                    stuck.append((item_id, furthest, f"triage verdict {status!r} but never moved onward"))
            elif furthest in ("03-draft", "04-agent-review"):
                stuck.append((item_id, furthest, "drafted/reviewed but never packaged for review or escalated"))
    return stuck


_AUDIT_ENTRY_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.*?)(?=^---[ \t]*\n|\Z)",
                              re.DOTALL | re.MULTILINE)


def iter_audit_entries(pipeline_dir: Path) -> list[dict]:
    """Every entry (frontmatter dict) across every 09-audit-log day-file,
    oldest file first, in file order within each -- append_audit_log's
    entries have no separator of their own between one note and the next
    entry's `---`, so this can't reuse split_frontmatter (built for a
    single-block stage-store file); it matches each block directly."""
    log_dir = pipeline_dir / "stage-store" / "09-audit-log"
    if not log_dir.exists():
        return []
    entries = []
    for path in sorted(log_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for m in _AUDIT_ENTRY_RE.finditer(text):
            fm = yaml.safe_load(m.group(1)) or {}
            entries.append(fm)
    return entries


def find_audit_entries_by_ref(pipeline_dir: Path, ref: str) -> list[dict]:
    """Every 09-audit-log entry (any day) whose `ref` field names this
    exact path (relative to pipeline_dir, forward or back slashes either
    way). Used to check whether a file already has a logged history under
    a different item_id before claiming it doesn't -- advance_stage.py's
    own --move requires an entry's item_id to match its destination
    filename, but a hand-written append_audit_log call doesn't, and this
    framework's real history has examples of exactly that (a review-cycle
    event logged under the base item_id, `ref` pointing at the versioned
    file read at that cycle)."""
    target = ref.replace("\\", "/")
    return [fm for fm in iter_audit_entries(pipeline_dir)
            if str(fm.get("ref", "")).replace("\\", "/") == target]


def orphaned_review_cycles(pipeline_dir: Path) -> list[tuple[str, str]]:
    """Find 04-agent-review files that are scratch records of an extra,
    same-run automated review cycle (SKILL.md's 03<->04 "revise" loop) that
    was never routed through advance_stage.py's own --move -- which would
    require an audit entry's item_id to match this exact filename -- but
    may or may not have a hand-written audit entry under a different
    item_id (find_audit_entries_by_ref checks that) and may or may not have
    a 03-draft counterpart under this exact filename -- rather than a
    genuine item needing its own resolution.

    Two mechanical tells, seen in practice, either one sufficient:
    - The record's own `item_id` frontmatter field doesn't match its
      filename stem (filed under a cycle-numbered name but never
      internally renamed to match).
    - `supersedes` points at a path under 04-agent-review or 03-draft
      instead of 07-rejected -- which a genuine `revise()`-created record
      never does (revise() always rejects the prior packet to 07-rejected
      first, before writing the new draft).

    Returns (filename_item_id, true_item_id) pairs -- true_item_id is the
    frontmatter's declared item_id, what actually needed to resolve, for
    the caller to verify (via its base_item_id) reached a terminal stage
    before removing anything. Only looks at items check_completeness()
    already finds stuck at 04-agent-review -- a narrower, mechanical
    explanation for a subset of those, not a separate scan."""
    candidates: list[tuple[str, str]] = []
    for item_id, stage, _ in check_completeness(pipeline_dir):
        if stage != "04-agent-review":
            continue
        fm, _ = read_item(stage_file(pipeline_dir, "04-agent-review", item_id))
        true_id = fm.get("item_id") or item_id
        supersedes = fm.get("supersedes")
        mismatched_id = true_id != item_id
        supersedes_not_rejected = bool(supersedes) and "07-rejected" not in str(supersedes)
        if mismatched_id or supersedes_not_rejected:
            candidates.append((item_id, true_id))
    return candidates


def cleanup_orphaned_reviews(pipeline_dir: Path, actor: str, dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Remove 04-agent-review scratch records identified by
    orphaned_review_cycles(), but only those verified safe: the true
    (frontmatter) item_id's base -- stripped of any -vN suffix -- has
    reached a terminal stage (06-approved, 07-rejected, or 08-executed).
    That's the real item resolving successfully, or being legitimately
    rejected, through its own unversioned id or its own genuine revision
    chain; this scratch file was never part of that chain, just an
    uncommitted intermediate review-cycle note describing work that's
    already captured (and superseded) elsewhere.

    Anything whose true base hasn't reached a terminal stage is left alone
    and reported, never removed -- that would risk destroying the only
    record of work still genuinely in progress. Each removal is audited
    (event 'correction'), same pattern as cleanup_queue()."""
    removed: list[str] = []
    skipped: list[str] = []
    for filename_id, true_id in orphaned_review_cycles(pipeline_dir):
        base = base_item_id(true_id)
        resolved_stage = decided_stage(pipeline_dir, base)
        if not resolved_stage:
            skipped.append(f"{filename_id}: base item {base!r} hasn't reached a terminal stage -- not removed")
            continue
        if dry_run:
            removed.append(filename_id)
            continue
        ref = f"stage-store/04-agent-review/{filename_id}.md"
        prior = [e for e in find_audit_entries_by_ref(pipeline_dir, ref) if e.get("event") != "correction"]
        if prior:
            p = prior[0]
            history_note = (f"a prior audit-log entry already covers this file (timestamp "
                             f"{p.get('timestamp')!r}, event {p.get('event')!r}, actor "
                             f"{p.get('actor')!r}, logged under item_id {p.get('item_id')!r} "
                             f"rather than this file's own name) -- this removal only retires "
                             f"the now-redundant file, it does not remove the only record of "
                             f"what happened")
        else:
            history_note = "no audit-log entry ever referenced this file"
        path = stage_file(pipeline_dir, "04-agent-review", filename_id)
        path.unlink()
        append_audit_log(pipeline_dir, {
            "timestamp": now_iso(),
            "item_id": filename_id,
            "pipeline": pipeline_dir.name,
            "event": "correction",
            "actor": actor,
            "detail": (f"Housekeeping: removed orphaned 04-agent-review scratch record "
                       f"(filed as {filename_id!r}, frontmatter item_id {true_id!r}) -- an "
                       f"extra same-run review-cycle note never routed through "
                       f"advance_stage.py's own --move ({history_note}; no 03-draft "
                       f"counterpart exists under this filename either way). The real item "
                       f"({base!r}) already resolved at {resolved_stage}."),
            "ref": ref,
        })
        removed.append(filename_id)
    return removed, skipped


def append_audit_log(pipeline_dir: Path, entry: dict, note: str = "") -> Path:
    """Append one audit-log entry, one file per UTC day, per docs/03-stage-store-model.md."""
    log_dir = pipeline_dir / "stage-store" / "09-audit-log"
    log_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = log_dir / f"{day}.md"
    entry_text = render(entry, f"\n{note}\n" if note else "\n")
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(existing + entry_text + "\n", encoding="utf-8")
    return log_path
