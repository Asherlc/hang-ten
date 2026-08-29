package com.hangten.android.editor

import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.hangten.android.content.Board
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.HoldShape
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.PathCommand
import com.hangten.android.content.Point
import kotlinx.coroutines.awaitCancellation
import org.junit.Rule
import org.junit.Test

class BoardEditorUiTest {
    @get:Rule val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun deterministicDeviceFlowShowsThenCancelsTheUserCode() {
        val tokens = UiMemoryTokenStore()
        val session = GitHubSyncSession(
            deviceFlow = GitHubDeviceFlow(UiFakeDeviceApi(), tokens, wait = { awaitCancellation() }),
            tokenStore = tokens,
            clientId = "review-client",
        )
        composeRule.setContent {
            BoardEditorListScreen(listOf(fixtureBoard()), session, onOpenBoard = {}, contentPadding = PaddingValues())
        }

        composeRule.onNodeWithContentDescription("Connect GitHub").performClick()
        composeRule.waitUntil(timeoutMillis = 5_000) { session.state.value.challenge != null }
        composeRule.onNodeWithText("Enter ABCD-EFGH at https://github.com/login/device").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Cancel GitHub sign-in").performClick()
        composeRule.onNodeWithContentDescription("Connect GitHub").assertIsDisplayed()
        session.close()
    }
}

private class UiMemoryTokenStore : GitHubTokenStore {
    override fun save(token: String) = Unit
    override fun load(): String? = null
    override fun clear() = Unit
}

private class UiFakeDeviceApi : GitHubDeviceApi {
    override suspend fun requestDeviceCode(clientId: String) = DeviceChallenge("device", "ABCD-EFGH", "https://github.com/login/device", 900, 60)
    override suspend fun pollDeviceCode(clientId: String, deviceCode: String) = DevicePollResult.AuthorizationPending
    override suspend fun authenticatedUser(token: String) = "review-user"
}

private fun fixtureBoard() = Board(
    id = "fixture-board",
    manufacturer = "Fixture",
    name = "Fixture board",
    subtitle = "Fixture",
    productUrl = "https://example.com",
    aspectRatio = 2f,
    presentations = listOf(BoardPresentation("primary", "Primary", "assets/primary.png", 2f, true)),
    holds = listOf(
        BoardHold(
            id = "edge", name = "Edge", kind = "edge", presentationId = "primary",
            geometry = listOf(BoardGeometry(NormalizedFrame(0.1f, 0.1f, 0.2f, 0.2f), HoldShape.Path(listOf(
                PathCommand.Move(Point(0f, 0f)), PathCommand.Line(Point(1f, 0f)), PathCommand.Line(Point(1f, 1f)), PathCommand.Close,
            )))),
        ),
    ),
)
