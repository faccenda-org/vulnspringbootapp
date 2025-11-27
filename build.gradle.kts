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
    val springBootVersion = providers.gradleProperty("springBootVersion").get()
    implementation("org.springframework.boot:spring-boot-starter-web:$springBootVersion")
    implementation("org.apache.commons:commons-text:1.9")
    // Intentionally vulnerable: jackson-databind 2.13.1 has multiple CVEs
    implementation("com.fasterxml.jackson.core:jackson-databind:2.13.1")
    // Intentionally vulnerable: log4j-core 2.14.1 has Log4Shell (CVE-2021-44228)
    implementation("org.apache.logging.log4j:log4j-core:2.14.1")
    implementation("org.apache.logging.log4j:log4j-api:2.14.1")
    // Intentionally vulnerable: dom4j 2.1.3 has XXE (CVE-2020-10683), patch available in 2.1.4
    implementation("org.dom4j:dom4j:2.1.3")
}

configurations {
    compileClasspath {
        resolutionStrategy.activateDependencyLocking()
    }
}