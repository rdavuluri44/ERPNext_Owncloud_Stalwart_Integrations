// P82 trial: a throw-away test app, never shipped. Versions are pinned; advisories checked 26 November 2026
// (docs/decisions.md). Kotlin comes with the Android Gradle plugin (built-in Kotlin, AGP 9).
plugins {
    id("com.android.application") version "9.2.1"
}

android {
    namespace = "com.example.passkeytrial"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.example.passkeytrial"
        minSdk = 28 // Android 9, the app's minimum
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.biometric:biometric:1.1.0")
    // Own QR route (question 2): the relay connection and a QR reader that needs no camera permission.
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
    testImplementation("junit:junit:4.13.2")
}
