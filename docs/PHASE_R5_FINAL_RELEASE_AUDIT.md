# PHASE R5.1 — GITEA RELEASE ARTIFACT SYNCHRONIZATION

## MODE

**CONTROLLED RELEASE DEPLOYMENT — ARTIFACT ONLY**

PHASE R5 has concluded:

```text
CONDITIONAL RELEASE READY
```

The only current release-blocking deployment inconsistency is:

```text
Gitea v1.1.0 Release attachment = OLD EXE
Online manifest SHA256 = NEW EXE
```

Known values:

```text
OLD RELEASE ATTACHMENT SHA256:
0fd68615...

NEW AUTHORITATIVE EXE:
dist/DesktopCleaner-1.1.0.exe

NEW SHA256:
dacdb0e9...
```

The objective of this phase is ONLY to synchronize the Gitea v1.1.0 release assets with the already validated local release package.

---

# 1. HARD SCOPE

AUTHORIZED:

- inspect current Gitea v1.1.0 release
- verify existing release assets
- upload/replace the authoritative `DesktopCleaner-1.1.0.exe`
- upload/replace the matching `SHA256SUMS.txt`
- upload/replace the matching `RELEASE_MANIFEST.md`
- verify resulting remote assets
- verify remote SHA256

NOT AUTHORIZED:

- source code changes
- test changes
- manifest redesign
- version changes
- new release version
- new Git commit
- force push
- tag rewriting
- signing
- SmartScreen remediation
- Windows installer redesign
- database changes
- update-system redesign
- unrelated release asset changes

---

# 2. PRE-DEPLOYMENT BASELINE

Record:

```text
Current branch:
Current HEAD:
Local artifact path:
Local artifact SHA256:
Local artifact size:
Local manifest SHA256:
Current Gitea release:
Current remote artifact SHA256:
Current remote artifact size:
```

Do not assume the values.

Recalculate local SHA256:

```powershell
Get-FileHash dist/DesktopCleaner-1.1.0.exe -Algorithm SHA256
```

Confirm it equals:

```text
dacdb0e9...
```

If it does not:

**STOP.**

---

# 3. LOCAL RELEASE PACKAGE CONSISTENCY

Verify:

```text
DesktopCleaner-1.1.0.exe
SHA256SUMS.txt
RELEASE_MANIFEST.md
update_manifest.json
```

Confirm all local release metadata refers to the same artifact.

Required invariant:

```text
artifact SHA256
==
SHA256SUMS
==
manifest SHA256
==
validator expected SHA256
```

If mismatch:

**STOP.**

---

# 4. GITEA RELEASE IDENTIFICATION

Locate the existing:

```text
v1.1.0
```

release.

Do NOT create a new version.

Do NOT delete the release.

Do NOT modify unrelated releases.

Record:

```text
Release ID:
Tag:
Release status:
Existing assets:
```

---

# 5. OLD ASSET VERIFICATION

Before replacement, verify that the existing Gitea attachment is indeed the known old artifact:

```text
SHA256:
0fd68615...
Size:
39,368,407 B
```

If the remote asset differs unexpectedly:

**STOP.**

Do not overwrite an unexpected artifact.

---

# 6. CONTROLLED ASSET REPLACEMENT

Replace/upload ONLY:

```text
DesktopCleaner-1.1.0.exe
SHA256SUMS.txt
RELEASE_MANIFEST.md
```

The authoritative EXE MUST be:

```text
dist/DesktopCleaner-1.1.0.exe
```

Do not rename it to a different release version.

Do not upload `dist/DesktopCleaner.exe`.

Do not upload build caches.

Do not upload temporary files.

Do not upload debug artifacts.

---

# 7. POST-UPLOAD REMOTE VERIFICATION

After upload, independently retrieve/list the Gitea v1.1.0 release assets.

Verify:

```text
DesktopCleaner-1.1.0.exe
SHA256SUMS.txt
RELEASE_MANIFEST.md
```

Then verify the remote EXE SHA256.

Required:

```text
remote EXE SHA256
==
dacdb0e9...
```

Required:

```text
remote EXE size
==
local EXE size
```

---

# 8. ONLINE MANIFEST → RELEASE ARTIFACT CHAIN

Re-query the actual online manifest endpoint.

Verify:

```text
latest_version = 1.1.0
download_url = intended Gitea v1.1.0 artifact
sha256 = dacdb0e9...
```

Then resolve the download URL and calculate the downloaded artifact SHA256.

Required final invariant:

```text
online manifest SHA256
==
downloaded EXE SHA256
==
local EXE SHA256
```

This is the most important acceptance gate.

---

# 9. RELEASE VALIDATOR

Run the existing release validator using the established R2/R4 command.

Expected:

```text
Scenario B
PASS / exit 0
```

All remote SHA comparison checks must pass.

Do not alter the validator.

---

# 10. DOCUMENTATION ASSET VERIFICATION

Verify the Gitea `SHA256SUMS.txt` and `RELEASE_MANIFEST.md`.

They must contain:

```text
DesktopCleaner-1.1.0.exe
dacdb0e9...
```

and the current artifact size.

Do not modify source documentation in this phase.

If the uploaded documentation is still stale:

**BLOCK.**

---

# 11. NO CODE / GIT CHANGES

After deployment:

```powershell
git status --short
git diff --check
git log -1 --oneline
```

Confirm:

```text
No source modification
No new commit
No amend
No force push
```

Any deployment-generated local temporary file must be removed or remain outside tracked scope according to the existing release process.

Do not alter unrelated worktree content.

---

# 12. FINAL ACCEPTANCE GATES

All must PASS:

```text
Local EXE SHA256 = dacdb0e9...                 PASS
Local manifest SHA256 matches EXE              PASS
Gitea release identified as v1.1.0             PASS
Remote EXE replaced                            PASS
Remote EXE SHA256 = dacdb0e9...                PASS
Remote EXE size matches local                  PASS
Online manifest points to Gitea                PASS
Online manifest SHA256 = dacdb0e9...           PASS
Download URL resolves                          PASS
Downloaded EXE SHA256 matches manifest        PASS
SHA256SUMS.txt synchronized                    PASS
RELEASE_MANIFEST.md synchronized               PASS
Release validator Scenario B                   PASS
No source changes                              PASS
No new commit                                  PASS
No force push                                  PASS
```

If any gate fails:

```text
BLOCKED
```

Do not improvise.

---

# 13. SIGNING / SMARTSCREEN BOUNDARY

Do NOT attempt to solve:

```text
Signing = UNSIGNED
SmartScreen = NOT ESTABLISHED
```

These remain separate external release items.

Record them as:

```text
EXTERNAL RELEASE RISK — NOT MODIFIED IN R5.1
```

Do not allow them to contaminate the artifact synchronization scope.

---

# REQUIRED FINAL REPORT

# PHASE R5.1 — GITEA RELEASE ARTIFACT SYNCHRONIZATION REPORT

## 1. Verdict

Exactly one:

```text
PASS — RELEASE ARTIFACT SYNCHRONIZED
```

or

```text
BLOCKED — ARTIFACT SYNCHRONIZATION FAILED
```

---

## 2. Local Artifact

```text
Filename:
Size:
SHA256:
```

---

## 3. Gitea Release

```text
Release:
Tag:
Release ID:
Old EXE SHA256:
New EXE SHA256:
New EXE size:
```

---

## 4. Assets

```text
DesktopCleaner-1.1.0.exe:
SHA256SUMS.txt:
RELEASE_MANIFEST.md:
```

---

## 5. Online Manifest

```text
HTTP:
latest_version:
download_url:
sha256:
```

---

## 6. End-to-End Download Verification

```text
Download:
Downloaded SHA256:
Manifest SHA256:
Match:
```

---

## 7. Release Validator

```text
Scenario B:
Exit code:
Remote SHA comparison:
```

---

## 8. Git Safety

```text
Source modified:
New commit:
Amend:
Force push:
```

---

## 9. External Risks

```text
Signing:
SmartScreen:
Win32 version resource:
```

These must remain unchanged from R5 unless independently resolved.

---

## 10. FINAL STATE

If all artifact synchronization gates pass:

```text
PHASE R5.1 PASS

Gitea v1.1.0 release assets are synchronized with the authoritative local artifact.

Online manifest SHA256 == downloaded EXE SHA256.

The update distribution chain is technically consistent.

STOP.
Do not make further release changes without explicit authorization.
```

If any gate fails:

```text
PHASE R5.1 BLOCKED

Release artifact synchronization is incomplete.

STOP.
Do not modify unrelated components.
```

# END OF PHASE R5.1

