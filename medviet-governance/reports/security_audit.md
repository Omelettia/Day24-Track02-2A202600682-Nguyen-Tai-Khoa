# Security Audit Evidence — MedViet AI Platform

_Generated: 2026-06-30_

## 1. git-secrets pre-commit hook BLOCKS credentials ✅

**Setup:** `git secrets --register-aws` + custom pattern `CCCD[:space:]+[0-9]{12}`.
The hook (`.github/hooks/pre-commit`, copied to `.git/hooks/pre-commit`) runs
`git secrets --pre_commit_hook` first.

> **Note:** the README's example key `wJalrXUtnFEMI/...EXAMPLEKEY` is the canonical
> AWS documentation key, which `git secrets --register-aws` *whitelists* by design
> (it appears in `secrets.allowed`). We therefore demonstrate with **non-whitelisted**
> fake credentials so the block is genuine.

**Result — staging a file with fake secrets and committing is blocked (exit 1):**

```
🔍 Running security checks...
medviet-governance/leak_test.py:2:aws_access_key_id = "AKIAQYLPMN5HZ7Q9R2T4"
medviet-governance/leak_test.py:3:aws_secret_access_key = "0123456789abcdefABCDEFghij0123456789abcd"
medviet-governance/leak_test.py:4:cccd_record = "CCCD: 012345678901"

[ERROR] Matched one or more prohibited patterns
❌ git-secrets found potential secrets! Commit blocked.
```

Three pattern types caught: AWS access-key id, AWS secret-access-key, and a
Vietnamese CCCD. The commit never completes.

## 2. Bandit SAST ✅

`bandit -r src/ -ll` (medium severity and above): **No issues identified.** The
pre-commit hook's Bandit gate passes.

Full-severity scan (`reports/bandit_report.json`) reports **3 LOW** findings, all
`B311` — use of the `random` module in the anonymizer's fake-data generators
(`_fake_cccd`, `_fake_phone`). **Reviewed and accepted:** these produce
non-cryptographic *fake replacement* values for anonymization, not keys or
secrets, so a CSPRNG is not required.

## 3. pip-audit (dependency CVE scan)

`pip-audit` queries the PyPI advisory database over the network. In this sandboxed
environment outbound requests to `pypi.org` time out, so the scan cannot complete
here. Command to run where network egress is permitted:

```
pip-audit --desc on
```

## 4. TruffleHog (verified-secret history scan)

TruffleHog's official installer pipes a remote script into the shell, which this
environment's security policy blocks (correctly — it executes remote code).
Command to run where permitted:

```
trufflehog git file://. --only-verified > reports/trufflehog_report.txt
```

## Summary

| Control | Status | Evidence |
|---|---|---|
| git-secrets blocks credentials | ✅ Demonstrated | section 1, exit 1 |
| Bandit SAST clean (medium+) | ✅ Pass | `reports/bandit_report.json` |
| pip-audit | ⚠️ Network-limited here | section 3 |
| TruffleHog | ⚠️ Policy-limited here | section 4 |
