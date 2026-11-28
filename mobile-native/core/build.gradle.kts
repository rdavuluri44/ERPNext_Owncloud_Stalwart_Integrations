// The app's rules, free of Android: runs and is tested on any computer, and can later be shared with an iPhone app.
plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin {
    jvmToolchain(17)
    compilerOptions { allWarningsAsErrors.set(true) }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
