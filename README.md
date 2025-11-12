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

This guarantees the build keeps the vulnerable coordinate even when transitive constraints suggest an upgrade. Remove this block when you want normal upgrade behavior restored.

