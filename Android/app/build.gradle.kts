plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.hangten.training"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.hangten.training"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures {
        compose = true
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

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.material3:material3")

    testImplementation("junit:junit:4.13.2")
}
