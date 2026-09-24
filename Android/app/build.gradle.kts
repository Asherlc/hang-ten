import javax.inject.Inject
import org.gradle.api.tasks.testing.Test
import org.gradle.process.ExecOperations

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val amplitudeApiKey = providers.gradleProperty("AMPLITUDE_API_KEY").orElse("").get().trim()
val sentryDsn = providers.gradleProperty("SENTRY_DSN").orElse("").get().trim().also {
    require(it.isEmpty() || it.startsWith("https://")) {
        "SENTRY_DSN must be an HTTPS DSN when configured."
    }
}

fun String.asBuildConfigString(): String {
    require(none { it == '\n' || it == '\r' }) { "Build configuration values may not contain newlines." }
    return "\"${replace("\\", "\\\\").replace("\"", "\\\"")}\""
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
        buildConfigField("String", "AMPLITUDE_API_KEY", amplitudeApiKey.asBuildConfigString())
        buildConfigField("String", "SENTRY_DSN", sentryDsn.asBuildConfigString())
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

/**
 * Stages the shared app content into the generated asset root.
 *
 * Board packages go through the same validating stager as the iOS build
 * (scripts/stage-board-packages.py, `--target android`: no Xcode environment and
 * no On-Demand Resource split, so model USDZ assets stay inline as before). It
 * generates each CAD-backed package's board.json from its FCStd, which is never
 * committed, and leaves the FCStd authoring source out of the APK.
 */
abstract class StageCanonicalAssets @Inject constructor(
    private val execOperations: ExecOperations,
    private val fileSystemOperations: FileSystemOperations,
) : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val boardPackages: ConfigurableFileCollection

    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val stagingTool: ConfigurableFileCollection

    @get:InputFile
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val planLibrary: RegularFileProperty

    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val countdownAudio: DirectoryProperty

    @get:Internal
    abstract val repositoryRoot: DirectoryProperty

    @get:OutputDirectory
    abstract val outputDirectory: DirectoryProperty

    @TaskAction
    fun stage() {
        val repository = repositoryRoot.get().asFile
        val output = outputDirectory.get().asFile
        fileSystemOperations.delete { delete(output) }
        output.mkdirs()
        execOperations.exec {
            commandLine(
                "sh",
                repository.resolve("scripts/run-supported-python.sh").path,
                repository.resolve("scripts/stage-board-packages.py").path,
                "--target",
                "android",
                "--repository-root",
                repository.path,
                "--destination",
                output.resolve("Hangboards").path,
            )
        }
        fileSystemOperations.copy {
            from(planLibrary)
            into(output)
        }
        fileSystemOperations.copy {
            from(countdownAudio)
            into(output.resolve("CountdownAudio"))
        }
    }
}

val checkoutRoot = rootProject.layout.projectDirectory.dir("..")
val stageCanonicalAssets by tasks.registering(StageCanonicalAssets::class) {
    repositoryRoot.set(checkoutRoot)
    boardPackages.from(checkoutRoot.dir("Hangboards"))
    stagingTool.from(
        checkoutRoot.file("scripts/stage-board-packages.py"),
        checkoutRoot.file("scripts/run-supported-python.sh"),
        fileTree(checkoutRoot.dir("Tools/HangboardPackages/src/hangboard_packages")) {
            include("**/*.py")
        },
    )
    planLibrary.set(checkoutRoot.file("HangTen/Resources/PlanLibrary.json"))
    countdownAudio.set(checkoutRoot.dir("HangTen/Resources/CountdownAudio"))
    outputDirectory.set(layout.buildDirectory.dir("generated/assets/canonical"))
}

android.sourceSets.getByName("main").assets.srcDir(stageCanonicalAssets)
tasks.named("preBuild").configure { dependsOn(stageCanonicalAssets) }
tasks.withType<Test>().configureEach { dependsOn(stageCanonicalAssets) }

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("com.android.billingclient:billing:9.1.0")
    implementation("androidx.health.connect:connect-client:1.1.0")
    implementation("com.amplitude:analytics-android:1.30.1")
    implementation("io.sentry:sentry-android:8.54.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.12.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
