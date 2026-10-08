# PHASE R5.2 — VERSION DRIFT AUDIT & 1.1.0 RESTORATION DESIGN

## 1. Objective

Execute a **READ-ONLY audit only**.

PHASE R5.1 is complete:

> PASS — RELEASE ARTIFACT SYNCHRONIZED

The Gitea v1.1.0 release is now authoritative and must NOT be modified.

Current known state:

```text
Released artifact = 1.1.0
Online manifest = 1.1.0
Gitea Release = v1.1.0
Local authoritative EXE = DesktopCleaner-1.1.0.exe
Local EXE SHA256 = dacdb0e9…
```

However, the repository worktree now contains pre-existing uncommitted user-side changes, including:

```text
src/version.py = 1.1.1
build.spec
src/ui/about.py
assets/
```

This creates a version drift:

```text
source = 1.1.1
release = 1.1.0
artifact = 1.1.0
manifest = 1.1.0
```

The intended release remains **V1.1.0** unless explicitly changed later.

---

## 2. HARD RULE

This phase is:

> **READ-ONLY VERSION DRIFT AUDIT + RESTORATION DESIGN**

Do NOT:

- modify any file
- revert any file
- delete any file
- modify `assets/`
- rebuild the EXE
- modify Gitea
- replace release assets
- modify online manifest
- create a new release
- change release version
- create a commit
- amend a commit
- push
- force-push
- run destructive Git cleanup

Do NOT use:

```text
git reset --hard
git restore .
git checkout -- .
git clean -fd
```

The purpose is to determine the safest minimal restoration plan before any implementation authorization.

---

## 3. Baseline

Re-establish and report:

```text
Branch:
HEAD:
git status --short:
```

Confirm that PHASE R5.2 itself starts from the current state and has made:

```text
0 file modifications
0 staged changes
0 commits
0 pushes
0 remote changes
```

---

## 4. Version Drift Audit

Inspect:

```text
src/version.py
build.spec
src/ui/about.py
update_manifest.json
RELEASE_MANIFEST.md
SHA256SUMS.txt
```

Also inspect:

```text
assets/
```

but do not modify it.

Determine exactly where `1.1.1` is introduced.

Determine exactly where `1.1.0` remains authoritative.

---

## 5. Diff Attribution

For every modified/untracked item, classify it as:

### A. Required for restoring V1.1.0

or

### B. Unrelated user work that MUST be preserved

or

### C. Mixed file requiring surgical restoration

Pay particular attention to:

```text
build.spec
src/ui/about.py
```

Do NOT assume the entire file can safely be reverted.

For each file, inspect the actual diff against:

```text
HEAD = 35def82
```

and identify the exact lines/fields responsible for the 1.1.1 version state.

---

## 6. Assets Protection

Treat:

```text
assets/
```

as protected user-side work.

Do not delete, restore, rename, or otherwise modify it.

Determine only whether it is related to the 1.1.1 version bump or independent work.

---

## 7. Release Documentation

Determine the current state of:

```text
RELEASE_MANIFEST.md
SHA256SUMS.txt
update_manifest.json
```

Distinguish carefully between:

### Local Git-tracked source documentation

and

### Gitea release asset

The Gitea V1.1.0 `RELEASE_MANIFEST.md` was intentionally corrected during R5.1 as an upload-only copy.

Do NOT modify the local tracked `RELEASE_MANIFEST.md`.

Do NOT modify Gitea.

---

## 8. Validator Analysis

Run/read-only analysis of:

```text
tools/release_validate.py
```

and explain precisely why Scenario B currently returns exit 1.

Expected failures:

```text
filename consistency
version consistency
```

Confirm that:

```text
SHA256 consistency
remote artifact SHA
download HTTP
release metadata
```

remain PASS.

Do not alter anything to make the validator pass.

---

## 9. Minimum Restoration Plan

Assuming the intended official release remains V1.1.0, design the smallest possible restoration needed to make the source release state consistent with:

```text
1.1.0
```

The plan must preserve all unrelated user work.

For every proposed change provide:

```text
file
current value
target value
reason
whether unrelated changes in same file must be preserved
```

Do not execute the plan.

---

## 10. Gitea Integrity

Verify that the already synchronized Gitea v1.1.0 release remains:

```text
EXE SHA = dacdb0e9…
EXE size = 39,377,599 B
Manifest SHA = dacdb0e9…
Online manifest SHA = dacdb0e9…
```

This is a read-only verification only.

Do not upload or delete anything.

---

## 11. Final Report

Return exactly:

# PHASE R5.2 — VERSION DRIFT AUDIT REPORT

## 1. Verdict

One of:

```text
PASS — RESTORATION PLAN READY
BLOCKED — VERSION STATE AMBIGUOUS
```

## 2. Current Version Matrix

| Source               | Current Version | Expected V1.1.0 | Action |
| -------------------- | --------------- | --------------- | ------ |
| src/version.py       |                 |                 |        |
| build.spec           |                 |                 |        |
| src/ui/about.py      |                 |                 |        |
| update_manifest.json |                 |                 |        |
| RELEASE_MANIFEST.md  |                 |                 |        |
| Gitea Release        |                 |                 |        |

## 3. User Change Attribution

For each of:

```text
src/version.py
build.spec
src/ui/about.py
assets/
```

state exactly which changes are version-related and which must be preserved.

## 4. Minimum Restoration Plan

Provide exact file/field/line-level restoration requirements.

## 5. Preservation Requirements

Explicitly list everything that must survive the restoration.

## 6. Validator State

Explain the two current failures and all passing checks.

## 7. Gitea Release Integrity

Confirm the remote V1.1.0 artifact remains synchronized.

## 8. Git Safety

Provide actual evidence showing:

```text
0 modifications created by R5.2
0 staged changes
0 commits
0 pushes
0 remote mutations
```

## 9. Final Decision Boundary

Do NOT perform restoration.

End exactly with:

```text

STOP.
Await explicit authorization for PHASE R5.3 implementation.
```
