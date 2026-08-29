import org.gradle.api.tasks.testing.Test

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val githubOauthClientId = providers.gradleProperty("GITHUB_OAUTH_CLIENT_ID").orElse("").get().trim().also {
    require(it.isEmpty() || it.matches(Regex("[A-Za-z0-9_-]+"))) {
        "GITHUB_OAUTH_CLIENT_ID must be a public GitHub OAuth client identifier."
    }
}

android {
    namespace = "com.hangten.training"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.hangten.training"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "GITHUB_OAUTH_CLIENT_ID", "\"$githubOauthClientId\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        disable += "GradleDependency"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

val stageCanonicalAssets by tasks.registering(Copy::class) {
    from(rootProject.projectDir.parentFile.resolve("Hangboards")) { into("Hangboards") }
    from(rootProject.projectDir.parentFile.resolve("HangTen/Resources/PlanLibrary.json"))
    from(rootProject.projectDir.parentFile.resolve("HangTen/Resources/CountdownAudio")) { into("CountdownAudio") }
    into(layout.buildDirectory.dir("generated/assets/canonical"))
}

android.sourceSets.getByName("main").assets.srcDir(stageCanonicalAssets)
tasks.named("preBuild").configure { dependsOn(stageCanonicalAssets) }
tasks.withType<Test>().configureEach { dependsOn(stageCanonicalAssets) }
// Debug may leave sign-in disabled, but no Release AAB may be produced without
// the registered public Device Flow client ID. This is a public identifier,
// never a client secret or personal access token.
tasks.configureEach {
    if (name == "bundleRelease" || name == "assembleRelease" || name == "packageRelease") {
        doFirst {
            check(githubOauthClientId.isNotBlank()) {
                "Release requires -PGITHUB_OAUTH_CLIENT_ID=<public GitHub OAuth Device Flow client ID>."
            }
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("com.android.billingclient:billing:9.1.0")
    implementation("androidx.health.connect:connect-client:1.1.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.12.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
