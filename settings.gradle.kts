rootProject.name = "vulnspringbootapp"

pluginManagement {
    val springBootVersion = providers.gradleProperty("springBootVersion").get()

    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id("org.springframework.boot") version springBootVersion
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        mavenCentral()
    }
}




