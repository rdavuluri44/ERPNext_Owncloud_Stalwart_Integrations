plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.example.erp.app"
    compileSdk = 37
    defaultConfig {
        // Neutral default; a deployment sets its own ID in its private gradle.properties (erpAppId=...).
        applicationId = providers.gradleProperty("erpAppId").getOrElse("com.example.erp.next")
        minSdk = 28 // Android 9
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        // The one server this build talks to. Set privately (erpServer=... in the user's own gradle.properties),
        // never in this repository. Empty: the build reaches no server.
        val server = providers.gradleProperty("erpServer").getOrElse("")
        require(server.isEmpty() || Regex("https://[A-Za-z0-9.-]+(:\\d{1,5})?").matches(server)) { "erpServer must be https, a host and nothing else" }
        buildConfigField("String", "SERVER", "\"$server\"")
        // Alerts: the four values Google's messaging needs to know this app. Set privately like the server address
        // (erpAlertsApp, erpAlertsKey, erpAlertsProject, erpAlertsSender), never in this repository; there is no
        // settings file in the project and no build plug-in for it. Empty: the build receives no alerts.
        for ((field, property) in listOf("ALERTS_APP" to "erpAlertsApp", "ALERTS_KEY" to "erpAlertsKey", "ALERTS_PROJECT" to "erpAlertsProject", "ALERTS_SENDER" to "erpAlertsSender")) {
            val value = providers.gradleProperty(property).getOrElse("")
            require(Regex("[A-Za-z0-9:_.-]*").matches(value)) { "$property holds a character that does not belong in it" }
            buildConfigField("String", field, "\"$value\"")
        }
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions {
        // Screen tests run on the computer (Robolectric), with the app's real resources.
        unitTests { isIncludeAndroidResources = true }
    }
    lint {
        abortOnError = true
        warningsAsErrors = true
        // Version nags are handled by the dependency review, not by lint.
        disable += setOf("GradleDependency", "NewerVersionAvailable", "AndroidGradlePluginVersion", "OldTargetApi")
    }
}

dependencies {
    implementation(project(":core"))
    implementation(platform("androidx.compose:compose-bom:2026.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
    implementation("androidx.activity:activity-compose:1.12.4")
    implementation("androidx.biometric:biometric:1.1.0")
    // Alerts when the app is closed. The messaging part only: no analytics, no crash reports, no advertising ID.
    implementation("com.google.firebase:firebase-messaging:26.0.2")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.18")
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
