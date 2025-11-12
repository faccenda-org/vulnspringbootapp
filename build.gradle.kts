plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("java")
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    // Use Java 17 toolchain (Spring Boot 3.0 baseline; avoids class file version 65 incompatibility here)
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
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
