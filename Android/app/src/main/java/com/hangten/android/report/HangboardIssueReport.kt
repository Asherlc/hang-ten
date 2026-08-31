package com.hangten.android.report

import android.net.Uri
import com.hangten.android.content.Board
import com.hangten.android.content.BoardPresentation
import com.hangten.training.BuildConfig

class HangboardIssueReportContext private constructor(
    val boardID: String,
    val boardName: String,
    val manufacturer: String,
    val presentationID: String,
    val presentationName: String,
    val platform: String,
    val appVersion: String,
    val build: String,
) {
    constructor(
        board: Board,
        presentation: BoardPresentation,
        appVersion: String = BuildConfig.VERSION_NAME,
        build: String = BuildConfig.VERSION_CODE.toString(),
    ) : this(
        boardID = board.id,
        boardName = board.name,
        manufacturer = board.manufacturer,
        presentationID = presentation.id,
        presentationName = presentation.name,
        platform = "Android",
        appVersion = appVersion,
        build = build,
    )
}

object HangboardIssueReportUrl {
    fun make(formUrl: String, context: HangboardIssueReportContext): Uri? {
        val formUri = validatedFormUri(formUrl) ?: return null

        return formUri.buildUpon()
            .clearQuery()
            .appendQueryParameter("board_id", context.boardID)
            .appendQueryParameter("board_name", context.boardName)
            .appendQueryParameter("manufacturer", context.manufacturer)
            .appendQueryParameter("presentation_id", context.presentationID)
            .appendQueryParameter("presentation_name", context.presentationName)
            .appendQueryParameter("platform", context.platform)
            .appendQueryParameter("app_version", context.appVersion)
            .appendQueryParameter("build", context.build)
            .build()
    }

    private fun validatedFormUri(rawValue: String): Uri? {
        if (rawValue.isBlank()) return null

        val uri = runCatching { Uri.parse(rawValue) }.getOrNull() ?: return null
        val host = uri.host?.lowercase() ?: return null
        return uri.takeIf {
            uri.scheme.equals("https", ignoreCase = true) &&
                uri.userInfo == null &&
                (host == "tally.so" || host.endsWith(".tally.so"))
        }
    }
}
