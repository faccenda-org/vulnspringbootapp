# Copilot Instructions for vulnspringbootapp

## Project Purpose
This is an intentionally vulnerable Spring Boot application (baseline Spring Boot v3.1.5) designed for testing security tools like Dependabot, Renovate, CodeQL, and dependency review workflows. The codebase deliberately contains known vulnerabilities. Spring Boot 3.1.5 is chosen as the earliest release with official Java 21 support while still carrying known transitive CVEs.

## Architecture Overview
- **Minimal Spring Boot app**: Single REST controller with one endpoint
- **Package structure**: `com.example.vulnspringbootapp` (flat, no layers)
- **No persistence**: In-memory only, no database
- **No tests**: Testing infrastructure intentionally omitted

## Build System: Gradle with Kotlin DSL

### Version Management
All versions are in `gradle.properties`:
- `springBootVersion=3.1.5` (**DO NOT UPDATE FURTHER** - intentionally vulnerable baseline)
- `springDependencyManagementVersion=1.1.6`
- `javaVersion=21`

Build system uses:
- Gradle 8.5 (supports JDK 17-21)
- JDK 21 for CI/CD workflows

### Build Commands
```bash
./gradlew clean build    # Build the application
./gradlew bootRun        # Run locally (http://localhost:8080)
```

## Critical Rules

### Security Vulnerabilities Are Intentional
- **NEVER** update Spring Boot version beyond 3.1.5 or fix security vulnerabilities
- **NEVER** add security hardening (authentication, input validation, etc.)
- This app exists to trigger Dependabot alerts and test dependency review workflows
- Expect security scanners to report issues—this is the desired state

### Keep It Simple
- No service layer, repositories, or DTOs
- No test coverage
- Only direct dependencies: `spring-boot-starter-web` and one intentionally vulnerable library (e.g. `commons-text:1.9`)
- Single controller with minimal logic

## Dependency Management & CI/CD

### Dependabot Configuration
- Updates only **direct** dependencies (not transitive)
- Runs weekly, max 10 open PRs
- Will create PRs to fix vulnerable dependencies (intentionally ignored/closed)

### Dependency Review Workflow
**Purpose**: Block PRs with high/critical vulnerabilities and add explanatory comments

Configuration in `.github/workflows/dependency-review.yml`:
- Fails on `high` or `critical` severity vulnerabilities
- Always adds PR comment with vulnerability details
- Requires dependency graph enabled (and GHAS for private repos)

### CI Workflow
- Runs on push/PR to main/master/develop
- Uses JDK 21 with Amazon Corretto
- Command: `./gradlew clean build --no-daemon`

### Dependency Submission Workflow
- Uses Gradle 8.5 with JDK 21
- Submits dependency graph via `gradle/actions/setup-gradle@v4`

## Code Structure

### Application Entry Point
```java
@SpringBootApplication
public class VulnSpringBootAppApplication {
    public static void main(String[] args) {
        SpringApplication.run(VulnSpringBootAppApplication.class, args);
    }
}
```

### Controller Pattern
```java
@RestController
public class HelloController {
    @GetMapping("/")
    public String hello() {
        return "Hello, World!";
    }
}
```

## When Adding Features
- Add controllers directly in root package
- Keep endpoints simple (no business logic)
- Do not add security measures
- Avoid adding dependencies unless absolutely necessary
- Maintain the vulnerable state (intentionally outdated/vulnerable versions)
    - If a dependency is upgraded by automated tooling and reduces vulnerability coverage, prefer reverting unless demonstrating an upgrade scenario.
