# M6 Recovery Drill

Status: passed

Run date: 2026-07-30

Commit: 3dd266204baf57620fce7d16a223c2a84b670e6c

Environment: independent `git clone --no-local`, new Python virtual environment,
and Source assets restored only from a separately created encrypted archive

## Recovery procedure

1. Streamed `01_Inbox/_assets/` through `tar` directly into an
   AES-256-CBC/PBKDF2/salted archive outside the clean clone. No plaintext archive
   file was written.
2. Created an independent clone at commit `3dd2662`.
3. Decrypted the archive as a stream and restored it into the clean clone.
4. Installed `.[dev,ui]` into a new virtual environment.
5. Ran asset verification, validation, index checks and the full engineering suite
   inside the clone.
6. Unset the ephemeral secret. The temporary archive and clone were moved to macOS
   Trash after the drill; they are recoverable until the owner empties Trash.

## Results

| Check | Result |
|---|---|
| Encrypted archive | PASS — 28,364,832 bytes |
| Encrypted archive SHA-256 | `a12665dcbc481dd9772593f2a5c32bd2a8f3616da236c62f59c605e2d07a6e5d` |
| Processed Sources restored | PASS — 36/36 |
| Restored asset files | PASS — 144 |
| Raw Source SHA-256 | PASS — 36/36 exact match |
| Capture exceptions | PASS — 3 remain visibly `registered`, not fabricated |
| Install `.[dev,ui]` | PASS |
| Ruff format and lint | PASS |
| mypy strict | PASS — 51 source files |
| Tests | PASS — 98/98 |
| Coverage | PASS — 84.03% |
| `research-os doctor` | PASS |
| Formal objects | PASS — 166/166 |
| Repository validation | PASS — 0 errors, 0 warnings |
| Global and project indexes | PASS — drift 0 |

## Boundary

This drill proves that Git state plus an encrypted Source-asset archive can restore
the current product and all currently processed PRJ-001/PRJ-002 evidence assets on a
clean clone. It does not create an ongoing backup service. Source assets remain
excluded from Git, and the owner must still configure a durable off-device encrypted
destination and key-recovery policy.

## Decision

M6-07 recovery acceptance passed for commit `3dd2662`: the clean clone restored all
36 processed Sources and 144 asset files with zero hash, validation or index
failure. The three registered capture exceptions remained explicit. Human research
review and release gates remain independent blockers.
