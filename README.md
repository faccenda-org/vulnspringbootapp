# vulnspringbootapp

This repository is an intentionally vulnerable Spring Boot application used to exercise security tooling (Dependabot, dependency review, CodeQL, Renovate, etc.). Vulnerable and outdated dependencies are **kept on purpose**.

## Dependency Locking

`gradle.lockfile` is kept to freeze a stable vulnerable baseline of direct and transitive versions. We intentionally do *not* enable dependency verification or other hardening features.

Security update PRs from Dependabot or Renovate may be closed deliberately to preserve vulnerable versions for testing.

### Forcing a Vulnerable Version
Occasionally Spring Boot's dependency management (BOM) or other plugin constraints may attempt to substitute a newer version of a library. To retain an intentionally vulnerable version (e.g. `commons-text:1.9`) we add a `resolutionStrategy.force` entry:

```
configurations.all { resolutionStrategy.force("org.apache.commons:commons-text:1.9") }
```

## Auto-merge Dependabot Workflow
- File: `.github/workflows/auto-merge-dependabot.yml`
- Runs on `pull_request_target` for Dependabot PRs and:
	- Detects semver change type from the PR title.
	- Extracts compatibility score from the PR body.
	- Merges automatically when:
		- Patch updates; or
		- Minor updates with compatibility score ≥ threshold.
	- Otherwise, comments that manual review is required.
	- If merge fails, comments with error details.

### Configuration
- `MERGE_METHOD`: Merge strategy (`squash`, `merge`, `rebase`). Default: `squash`.
- `DEFAULT_COMPAT_THRESHOLD`: Default compatibility threshold percentage. Default: `80`.
- `vars.DEPENDABOT_COMPAT_THRESHOLD`: Optional repository variable to override threshold.
- `NO_AUTO_MERGE_LABEL`: Label name to skip auto-merge. Default: `no-auto-merge`.
 - Manual test override via `workflow_dispatch` input `compat_threshold`.

### Notes
- Uses `pull_request_target` and the workflow's `GITHUB_TOKEN` with `contents: write` and `pull-requests: write`.
- Supports Dependabot PR title format: `Bump <pkg> from X.Y.Z to A.B.C`.

#### Setting the repository variable
- In GitHub: Settings → Secrets and variables → Actions → Variables → New variable
- Name: `DEPENDABOT_COMPAT_THRESHOLD`, Value: e.g., `85`

#### Manual test run
```bash
gh workflow run auto-merge-dependabot.yml -f compat_threshold=90
```

This guarantees the build keeps the vulnerable coordinate even when transitive constraints suggest an upgrade. Remove this block when you want normal upgrade behavior restored.

