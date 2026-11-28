// Native Android app (Phase 0: foundation). Versions are pinned here; every library is checked for licence and
// advisories before it is added (docs/decisions.md) and its checksum is pinned in gradle/verification-metadata.xml.
plugins {
    id("com.android.application") version "9.2.1" apply false
    // The Android plugin brings Kotlin 2.2.10; the two Kotlin plugins below must name the same version.
    id("org.jetbrains.kotlin.jvm") version "2.2.10" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false
}

// One command for everything a change must pass: `gradle checkAll`.
tasks.register("checkAll") {
    group = "verification"
    description = "Logic tests, Android lint, app unit tests and a debug build."
    dependsOn(":core:test", ":app:lintDebug", ":app:testDebugUnitTest", ":app:assembleDebug")
}
