plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("java")
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    // Restore toolchain to ensure Gradle compiles with JDK 21 (class file major version 65)
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

dependencies {
    val springBootVersion = providers.gradleProperty("springBootVersion").get()
    implementation("org.springframework.boot:spring-boot-starter-web:$springBootVersion")
    implementation("org.apache.commons:commons-text:1.9")
}

dependencyLocking {
    lockAllConfigurations()
}
