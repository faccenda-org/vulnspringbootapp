# vulnspringbootapp

This repository is an intentionally vulnerable Spring Boot application used to exercise security tooling (Dependabot, dependency review, CodeQL, Renovate, etc.). Vulnerable and outdated dependencies are **kept on purpose**.

## Reproducible Dependency State

The project now uses two Gradle features to demonstrate supply chain controls while still retaining known vulnerable versions:

### 1. Dependency Locking (`gradle.lockfile`)
Locks the resolved versions (direct + transitive) so future builds use the exact same module versions even if newer releases are published. This preserves a stable vulnerable baseline for comparison across scanners.

### 2. Dependency Verification (`gradle/verification-metadata.xml`)
Stores cryptographic checksums (sha256 + sha512) for each downloaded artifact. This detects tampering or unexpected artifact changes. Verification does **not** fix vulnerabilities; it only ensures the binary content that was originally resolved has not silently changed.

Why both? Locking ensures deterministic version selection; verification ensures artifact integrity. Together they provide a reproducible, integrity‑checked vulnerable snapshot.

If you intentionally change or add dependencies, regenerate verification metadata:

```
./gradlew --write-verification-metadata sha256,sha512 build
```

If you want to update locked versions (e.g., to introduce or demonstrate new advisories) run:

```
./gradlew --refresh-dependencies --write-locks build
```

Note: We still avoid upgrading core vulnerable dependencies unless explicitly demonstrating an update workflow. Security PRs from Dependabot or Renovate may be closed intentionally to keep the vulnerable state.

### Forcing a Vulnerable Version
Occasionally Spring Boot's dependency management (BOM) or other plugin constraints may attempt to substitute a newer version of a library. To retain an intentionally vulnerable version (e.g. `commons-text:1.9`) we add a `resolutionStrategy.force` entry:

```
configurations.all {
	resolutionStrategy {
		force("org.apache.commons:commons-text:1.9")
	}
}
```

This guarantees the build keeps the vulnerable coordinate even when transitive constraints suggest an upgrade. Remove this block when you want normal upgrade behavior restored.

