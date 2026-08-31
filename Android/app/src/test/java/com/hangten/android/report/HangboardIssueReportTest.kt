package com.hangten.android.report

import com.hangten.android.content.Board
import com.hangten.android.content.BoardPresentation
import com.hangten.training.BuildConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [29])
class HangboardIssueReportTest {
    @Test
    fun encodesExactlyTheRequiredContextFields() {
        val url = checkNotNull(
            HangboardIssueReportUrl.make(
                formUrl = "https://tally.so/r/XxbJG4",
                context = fixtureContext(),
            ),
        )

        assertEquals("/r/XxbJG4", url.path)
        assertEquals(
            setOf(
                "board_id",
                "board_name",
                "manufacturer",
                "presentation_id",
                "presentation_name",
                "platform",
                "app_version",
                "build",
            ),
            url.queryParameterNames,
        )
        assertEquals("test.pocket-edge", url.getQueryParameter("board_id"))
        assertEquals("Pocket & Edge", url.getQueryParameter("board_name"))
        assertEquals("Test / Climbing", url.getQueryParameter("manufacturer"))
        assertEquals("face-b", url.getQueryParameter("presentation_id"))
        assertEquals("Face B — deep slopers", url.getQueryParameter("presentation_name"))
        assertEquals("Android", url.getQueryParameter("platform"))
        assertEquals("2.3.4 beta", url.getQueryParameter("app_version"))
        assertEquals("567", url.getQueryParameter("build"))
    }

    @Test
    fun doesNotIncludeDeviceOrInterfaceOrientationFields() {
        val names = checkNotNull(
            HangboardIssueReportUrl.make(
                formUrl = "https://tally.so/r/XxbJG4",
                context = fixtureContext(),
            ),
        ).queryParameterNames

        assertFalse(names.contains("interface_orientation"))
        assertFalse(names.contains("device_orientation"))
        assertFalse(names.contains("device"))
        assertFalse(names.contains("device_id"))
    }

    @Test
    fun contextUsesTheSelectedPhysicalPresentation() {
        val board = fixtureBoard()
        val context = HangboardIssueReportContext(
            board = board,
            presentation = board.presentations[1],
            appVersion = "1.0",
            build = "1",
        )

        val url = checkNotNull(
            HangboardIssueReportUrl.make(
                formUrl = "https://tally.so/r/XxbJG4",
                context = context,
            ),
        )

        assertEquals("face-b", url.getQueryParameter("presentation_id"))
        assertEquals("Face B — deep slopers", url.getQueryParameter("presentation_name"))
    }

    @Test
    fun roundTripsSpecialCharactersThroughUrlQueryEncoding() {
        val url = checkNotNull(
            HangboardIssueReportUrl.make(
                formUrl = "https://tally.so/r/XxbJG4",
                context = fixtureContext(),
            ),
        )

        assertEquals("Pocket & Edge", url.getQueryParameter("board_name"))
        assertEquals("Test / Climbing", url.getQueryParameter("manufacturer"))
        assertEquals("Face B — deep slopers", url.getQueryParameter("presentation_name"))
        assertEquals("2.3.4 beta", url.getQueryParameter("app_version"))
        assertTrue(url.toString().contains("Pocket%20%26%20Edge"))
    }

    @Test
    fun contextDefaultsVersionAndBuildFromTheApplicationPackage() {
        val board = fixtureBoard()
        val context = HangboardIssueReportContext(
            board = board,
            presentation = board.presentations[1],
        )

        assertEquals(BuildConfig.VERSION_NAME, context.appVersion)
        assertEquals(BuildConfig.VERSION_CODE.toString(), context.build)
    }

    @Test
    fun acceptsTallyAndTallySubdomainHttpsUrls() {
        assertEquals(
            "tally.so",
            HangboardIssueReportUrl.make(
                formUrl = "https://tally.so/r/XxbJG4",
                context = fixtureContext(),
            )?.host,
        )
        assertEquals(
            "forms.tally.so",
            HangboardIssueReportUrl.make(
                formUrl = "https://forms.tally.so/r/report",
                context = fixtureContext(),
            )?.host,
        )
    }

    @Test
    fun rejectsBlankInsecureNonTallyAndMalformedUrls() {
        val invalidValues = listOf(
            "",
            "   ",
            "http://tally.so/r/report",
            "https://example.com/r/report",
            "https://tally.so.example.com/r/report",
            "https://user@example.com@tally.so/r/report",
            "not a URL",
            "https://%",
        )

        invalidValues.forEach { value ->
            assertNull(
                "Expected invalid configuration to be rejected: $value",
                HangboardIssueReportUrl.make(
                    formUrl = value,
                    context = fixtureContext(),
                ),
            )
        }
    }

    private fun fixtureContext(): HangboardIssueReportContext {
        val board = fixtureBoard()
        return HangboardIssueReportContext(
            board = board,
            presentation = board.presentations[1],
            appVersion = "2.3.4 beta",
            build = "567",
        )
    }

    private fun fixtureBoard(): Board = Board(
        id = "test.pocket-edge",
        manufacturer = "Test / Climbing",
        name = "Pocket & Edge",
        subtitle = "Test board",
        productUrl = "https://example.com/board",
        aspectRatio = 2f,
        presentations = listOf(
            BoardPresentation(
                id = "face-a",
                name = "Face A",
                assetPath = "assets/face-a.png",
                aspectRatio = 2f,
                isDefault = true,
            ),
            BoardPresentation(
                id = "face-b",
                name = "Face B — deep slopers",
                assetPath = "assets/face-b.png",
                aspectRatio = 2f,
                isDefault = false,
            ),
        ),
        holds = emptyList(),
    )
}
