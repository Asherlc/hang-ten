package com.hangten.android

import android.content.pm.PackageManager
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SentryStartupSmokeTest {
    @Test
    fun emptySentryConfigurationLaunchesWithoutAutomaticSentryProviders() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val providers = context.packageManager
            .getPackageInfo(
                context.packageName,
                PackageManager.GET_PROVIDERS,
            )
            .providers
            .orEmpty()

        assertTrue(
            "Sentry must only initialize through the explicit configured diagnostics adapter.",
            providers.none { it.name == SENTRY_INIT_PROVIDER || it.name == SENTRY_PERFORMANCE_PROVIDER },
        )

        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity -> assertTrue(activity is MainActivity) }
        }
    }

    private companion object {
        const val SENTRY_INIT_PROVIDER = "io.sentry.android.core.SentryInitProvider"
        const val SENTRY_PERFORMANCE_PROVIDER = "io.sentry.android.core.SentryPerformanceProvider"
    }
}
