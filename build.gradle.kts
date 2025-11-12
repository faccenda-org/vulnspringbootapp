plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("java")
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

// Use Gradle's default JVM; explicit toolchain removed for simplicity.

dependencies {
    // Intentionally vulnerable dependency retained (commons-text:1.9)
    val springBootVersion = providers.gradleProperty("springBootVersion").get()
    implementation("org.springframework.boot:spring-boot-starter-web:$springBootVersion")
    implementation("org.apache.commons:commons-text:1.9")
}

// Test configuration removed (no tests maintained intentionally).

configurations.all {
    resolutionStrategy.force("org.apache.commons:commons-text:1.9")
}
// Dependency locking removed for simplicity; vulnerable versions may drift unless forced.
dependencyLocking {
    // Keep locked versions to maintain a stable vulnerable baseline.
    lockAllConfigurations()
}
