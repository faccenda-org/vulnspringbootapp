plugins {
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("java")
    id("com.github.spotbugs") version "6.0.5"
    id("pmd")
    id("checkstyle")
    id("org.jlleitschuh.gradle.ktlint") version "11.6.1"
    id("org.owasp.dependencycheck") version "9.0.9"
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
    implementation("org.springframework.boot:spring-boot-starter-web")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

tasks.test {
    useJUnitPlatform()
}

// SpotBugs configuration
spotbugs {
    toolVersion.set("4.8.3")
}

tasks.spotbugsMain {
    reports {
        create("html") {
            required.set(true)
        }
    }
}

// PMD configuration
pmd {
    toolVersion = "6.55.0"
    ruleSetFiles = files("${rootDir}/config/pmd/ruleset.xml")
}

// Checkstyle configuration
checkstyle {
    toolVersion = "10.3.4"
    configFile = file("${rootDir}/config/checkstyle/checkstyle.xml")
}

// ktlint configuration
ktlint {
    version.set("0.50.0")
    android.set(false)
    ignoreFailures.set(false)
}

// OWASP Dependency Check configuration
dependencyCheck {
    format = "HTML"
    failBuildOnCVSS = 7.0f
    suppressionFile = "${rootDir}/config/dependency-check/suppressions.xml"
    analyzers.assemblyEnabled = false
}




