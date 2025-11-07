plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("java")
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    val javaVersion = providers.gradleProperty("javaVersion").get().toInt()
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(javaVersion))
    }
}

dependencies {
    // Explicit version pin so Dependabot can propose security upgrade PRs
    val springBootVersion = providers.gradleProperty("springBootVersion").get()
    implementation("org.springframework.boot:spring-boot-starter-web:$springBootVersion")
    // Intentionally vulnerable version (CVE-2022-42889 - variable interpolation RCE)
    implementation("org.apache.commons:commons-text:1.9")
    testImplementation("org.springframework.boot:spring-boot-starter-test:$springBootVersion")
}

tasks.test {
    useJUnitPlatform()
}
