package com.hangten.android.editor

import com.hangten.android.content.JsonParser
import com.hangten.android.content.asArray
import com.hangten.android.content.asObject
import com.hangten.android.content.asString
import com.hangten.android.content.optional
import com.hangten.android.content.required
import com.hangten.android.content.requiredString
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

data class DeviceChallenge(
    val deviceCode: String,
    val userCode: String,
    val verificationUri: String,
    val expiresInSeconds: Long,
    val intervalSeconds: Long,
)

sealed interface DevicePollResult {
    data object AuthorizationPending : DevicePollResult
    data object SlowDown : DevicePollResult
    data class Authorized(val token: String) : DevicePollResult
    data object Denied : DevicePollResult
    data object Expired : DevicePollResult
}

sealed interface DeviceFlowOutcome {
    data class Authorized(val username: String) : DeviceFlowOutcome
    data object Expired : DeviceFlowOutcome
    data object Denied : DeviceFlowOutcome
    data object Cancelled : DeviceFlowOutcome
    data class Failed(val message: String) : DeviceFlowOutcome
}

interface GitHubTokenStore {
    fun save(token: String)
    fun load(): String?
    fun clear()
}

interface GitHubDeviceApi {
    suspend fun requestDeviceCode(clientId: String): DeviceChallenge
    suspend fun pollDeviceCode(clientId: String, deviceCode: String): DevicePollResult
    suspend fun authenticatedUser(token: String): String
}

/** OAuth Device Flow. Only the registered public client ID is accepted. */
class GitHubDeviceFlow(
    private val api: GitHubDeviceApi,
    private val tokenStore: GitHubTokenStore,
    private val clock: () -> Long = { System.currentTimeMillis() },
    private val wait: suspend (Long) -> Unit = { delay(it) },
) {
    suspend fun authorize(clientId: String, onChallenge: (DeviceChallenge) -> Unit): DeviceFlowOutcome {
        try {
            if (!PUBLIC_CLIENT_ID.matches(clientId)) return DeviceFlowOutcome.Failed("GitHub sign-in is not configured.")
            val challenge = api.requestDeviceCode(clientId)
            validateChallenge(challenge)
            onChallenge(challenge)
            val deadline = clock() + challenge.expiresInSeconds * 1_000L
            var interval = challenge.intervalSeconds * 1_000L
            while (true) {
                if (clock() >= deadline) return DeviceFlowOutcome.Expired
                wait(minOf(interval, deadline - clock()))
                if (clock() >= deadline) return DeviceFlowOutcome.Expired
                when (val result = api.pollDeviceCode(clientId, challenge.deviceCode)) {
                    DevicePollResult.AuthorizationPending -> Unit
                    DevicePollResult.SlowDown -> interval += SLOW_DOWN_MILLIS
                    DevicePollResult.Denied -> return DeviceFlowOutcome.Denied
                    DevicePollResult.Expired -> return DeviceFlowOutcome.Expired
                    is DevicePollResult.Authorized -> {
                        if (result.token.isBlank()) return DeviceFlowOutcome.Failed("GitHub returned an empty authorization token.")
                        val username = api.authenticatedUser(result.token)
                        tokenStore.save(result.token)
                        return DeviceFlowOutcome.Authorized(username)
                    }
                }
            }
        } catch (_: CancellationException) {
            return DeviceFlowOutcome.Cancelled
        } catch (error: GitHubSyncException) {
            return DeviceFlowOutcome.Failed(error.message.orEmpty())
        } catch (error: Throwable) {
            return DeviceFlowOutcome.Failed(error.message ?: "Unable to authorize with GitHub.")
        }
        error("Unreachable device flow state.")
    }

    private fun validateChallenge(challenge: DeviceChallenge) {
        if (challenge.deviceCode.isBlank() || challenge.userCode.isBlank() || !httpsUrl(challenge.verificationUri) ||
            challenge.expiresInSeconds <= 0 || challenge.intervalSeconds <= 0
        ) throw GitHubSyncException.InvalidResponse("GitHub returned invalid device authorization data.")
    }

    private companion object {
        val PUBLIC_CLIENT_ID = Regex("[A-Za-z0-9_-]+")
        const val SLOW_DOWN_MILLIS = 5_000L
    }
}

data class GitHubPackageFile(val path: String, val data: ByteArray)
data class PulledBoardPackage(
    val head: String,
    val boardJson: ByteArray,
    val imagePath: String,
    val image: ByteArray,
)

interface GitHubPackageApi {
    suspend fun defaultBranch(token: String): String
    suspend fun branchHead(token: String, branch: String): String?
    suspend fun createBranch(token: String, branch: String, fromHead: String)
    suspend fun pullPackage(token: String, branch: String, slug: String): PulledBoardPackage
    suspend fun pushPackage(token: String, branch: String, expectedHead: String, files: List<GitHubPackageFile>, message: String): String
    suspend fun createPullRequest(token: String, title: String, head: String, base: String, body: String): String
}

sealed interface PackageSyncResult {
    data class Pulled(val payload: PulledBoardPackage) : PackageSyncResult
    data class Pushed(val pullRequestUrl: String, val commit: String, val branch: String) : PackageSyncResult
    data object Conflict : PackageSyncResult
    data class Failed(val message: String) : PackageSyncResult
}

/** Branch-aware package pull/push that admits exactly board.json plus assets. */
class GitHubPackageSync(private val api: GitHubPackageApi) {
    suspend fun defaultBranch(token: String): String = api.defaultBranch(token)

    suspend fun pull(token: String, slug: String, branch: String): PackageSyncResult {
        if (!BoardPackagePaths.isValidSlug(slug)) {
            return PackageSyncResult.Failed("GitHub returned an invalid board package slug.")
        }
        return try {
        val payload = api.pullPackage(token, branch, slug)
        if (!BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/board.json") ||
            !BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/${payload.imagePath}") ||
            defaultPresentationAssetPath(slug, payload.boardJson) != payload.imagePath
        ) return PackageSyncResult.Failed("GitHub returned an unsafe board-package path.")
        PackageSyncResult.Pulled(payload)
    } catch (error: GitHubSyncException.Conflict) {
        PackageSyncResult.Conflict
    } catch (error: Throwable) {
        PackageSyncResult.Failed(error.message ?: "Unable to pull board package.")
        }
    }

    suspend fun push(
        token: String,
        slug: String,
        branch: String,
        expectedHead: String,
        boardJson: ByteArray,
        imagePath: String,
        image: ByteArray,
        message: String,
        existingPullRequestUrl: String? = null,
    ): PackageSyncResult {
        return try {
        if (!BoardPackagePaths.isValidSlug(slug) || message.isBlank() || !BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/board.json") ||
            !BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/$imagePath") ||
            defaultPresentationAssetPath(slug, boardJson) != imagePath
        ) return PackageSyncResult.Failed("Only this board's board.json and referenced asset may be pushed.")
        val base = api.defaultBranch(token)
        val existing = api.branchHead(token, branch)
        val currentHead = existing ?: api.branchHead(token, base)?.also { api.createBranch(token, branch, it) }
            ?: return PackageSyncResult.Failed("GitHub default branch has no head.")
        if (currentHead != expectedHead) return PackageSyncResult.Conflict
        val commit = api.pushPackage(
            token,
            branch,
            expectedHead,
            listOf(
                GitHubPackageFile("Hangboards/$slug/board.json", boardJson),
                GitHubPackageFile("Hangboards/$slug/$imagePath", image),
            ),
            message,
        )
        val url = existingPullRequestUrl ?: api.createPullRequest(
            token, message, branch, base, "Updated Hang Ten board geometry from Android.",
        )
        if (!httpsUrl(url)) return PackageSyncResult.Failed("GitHub returned an invalid pull request URL.")
        PackageSyncResult.Pushed(url, commit, branch)
    } catch (error: GitHubSyncException.Conflict) {
        PackageSyncResult.Conflict
    } catch (error: Throwable) {
        PackageSyncResult.Failed(error.message ?: "Unable to push board package.")
        }
    }
}

/** A new draft gets its own branch; later edits retain that draft branch and PR. */
object GitHubBranchName {
    fun newForBoard(slug: String, nonce: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "") }): String {
        require(BoardPackagePaths.isValidSlug(slug)) { "Invalid board package slug." }
        val suffix = nonce()
        require(suffix.matches(Regex("[A-Za-z0-9][A-Za-z0-9-]*"))) { "Invalid branch nonce." }
        return "hangten/android-$slug-$suffix"
    }
}

sealed class GitHubSyncException(message: String) : IllegalStateException(message) {
    class Conflict(message: String) : GitHubSyncException(message)
    class Unauthorized(message: String) : GitHubSyncException(message)
    class InvalidResponse(message: String) : GitHubSyncException(message)
    class Transport(message: String) : GitHubSyncException(message)
}

/** HTTPS-only GitHub REST client. It has no secret-bearing configuration. */
class OkHttpGitHubApi(
    private val client: OkHttpClient = OkHttpClient(),
    private val apiBase: String = "https://api.github.com",
    private val oauthBase: String = "https://github.com",
    private val owner: String = "Asherlc",
    private val repository: String = "hang-ten",
) : GitHubDeviceApi, GitHubPackageApi {
    override suspend fun requestDeviceCode(clientId: String): DeviceChallenge {
        val json = formJson(oauthBase, "/login/device/code", listOf("client_id" to clientId, "scope" to "repo read:org"))
        return DeviceChallenge(
            json.requiredString("device_code"), json.requiredString("user_code"), json.requiredString("verification_uri"),
            json.requiredLong("expires_in"), json.requiredLong("interval"),
        )
    }

    override suspend fun pollDeviceCode(clientId: String, deviceCode: String): DevicePollResult {
        val json = formJson(oauthBase, "/login/oauth/access_token", listOf(
            "client_id" to clientId,
            "device_code" to deviceCode,
            "grant_type" to "urn:ietf:params:oauth:grant-type:device_code",
        ))
        json.optString("access_token").takeIf { it.isNotBlank() }?.let { return DevicePollResult.Authorized(it) }
        return when (json.optString("error")) {
            "authorization_pending" -> DevicePollResult.AuthorizationPending
            "slow_down" -> DevicePollResult.SlowDown
            "access_denied" -> DevicePollResult.Denied
            "expired_token" -> DevicePollResult.Expired
            else -> throw GitHubSyncException.InvalidResponse("GitHub returned invalid device authorization data.")
        }
    }

    override suspend fun authenticatedUser(token: String): String = requestJson("GET", "/user", token = token).requiredString("login")
    override suspend fun defaultBranch(token: String): String = requestJson("GET", repositoryPath(), token = token).requiredString("default_branch")

    override suspend fun branchHead(token: String, branch: String): String? = try {
        requestJson("GET", "${repositoryPath()}/git/ref/heads/${segment(branch)}", token = token)
            .getJSONObject("object").requiredString("sha")
    } catch (_: GitHubNotFound) { null }

    override suspend fun createBranch(token: String, branch: String, fromHead: String) {
        requestJson("POST", "${repositoryPath()}/git/refs", token, JSONObject().put("ref", "refs/heads/$branch").put("sha", fromHead))
    }

    override suspend fun pullPackage(token: String, branch: String, slug: String): PulledBoardPackage {
        val head = branchHead(token, branch) ?: throw GitHubNotFound("Branch not found.")
        val tree = requestJson("GET", "${repositoryPath()}/git/trees/${segment(branch)}?recursive=1", token = token)
        if (tree.optBoolean("truncated", true)) throw GitHubSyncException.InvalidResponse("GitHub returned a truncated tree.")
        val entries = tree.getJSONArray("tree")
        fun shaFor(path: String): String? = (0 until entries.length()).asSequence().map { entries.getJSONObject(it) }
            .firstOrNull { it.optString("path") == path && it.optString("type") == "blob" }?.optString("sha")
        val boardPath = "Hangboards/$slug/board.json"
        val boardSha = shaFor(boardPath) ?: throw GitHubNotFound("Board package is unavailable.")
        val board = blob(token, boardSha)
        val imagePath = defaultImagePath(slug, board)
        val imageSha = shaFor("Hangboards/$slug/$imagePath") ?: throw GitHubNotFound("Presentation image is unavailable.")
        return PulledBoardPackage(head, board, imagePath, blob(token, imageSha))
    }

    override suspend fun pushPackage(token: String, branch: String, expectedHead: String, files: List<GitHubPackageFile>, message: String): String {
        if (files.size != 2 || files.any { !it.path.startsWith("Hangboards/") }) throw GitHubSyncException.InvalidResponse("Unsafe package write.")
        if (branchHead(token, branch) != expectedHead) throw GitHubSyncException.Conflict("The remote branch changed.")
        val commit = requestJson("GET", "${repositoryPath()}/git/commits/${segment(expectedHead)}", token = token)
        val baseTree = commit.getJSONObject("tree").requiredString("sha")
        val entries = JSONArray()
        files.forEach { file ->
            val blob = requestJson("POST", "${repositoryPath()}/git/blobs", token, JSONObject()
                .put("content", android.util.Base64.encodeToString(file.data, android.util.Base64.NO_WRAP))
                .put("encoding", "base64"))
            entries.put(JSONObject().put("path", file.path).put("mode", "100644").put("type", "blob").put("sha", blob.requiredString("sha")))
        }
        val newTree = requestJson("POST", "${repositoryPath()}/git/trees", token, JSONObject().put("base_tree", baseTree).put("tree", entries))
        val newCommit = requestJson("POST", "${repositoryPath()}/git/commits", token, JSONObject()
            .put("message", message).put("tree", newTree.requiredString("sha")).put("parents", JSONArray().put(expectedHead)))
        requestJson("PATCH", "${repositoryPath()}/git/refs/heads/${segment(branch)}", token, JSONObject().put("sha", newCommit.requiredString("sha")).put("force", false))
        return newCommit.requiredString("sha")
    }

    override suspend fun createPullRequest(token: String, title: String, head: String, base: String, body: String): String =
        requestJson("POST", "${repositoryPath()}/pulls", token, JSONObject().put("title", title).put("head", head).put("base", base).put("body", body))
            .requiredString("html_url")

    private fun blob(token: String, sha: String): ByteArray {
        val response = requestJson("GET", "${repositoryPath()}/git/blobs/${segment(sha)}", token = token)
        if (response.optString("encoding") != "base64") throw GitHubSyncException.InvalidResponse("GitHub returned unsupported blob encoding.")
        return android.util.Base64.decode(response.requiredString("content").filterNot(Char::isWhitespace), android.util.Base64.DEFAULT)
    }

    private fun defaultImagePath(slug: String, boardJson: ByteArray): String {
        val root = JsonParser(boardJson.decodeToString()).parse().asObject("board.json")
        val presentations = root.required("presentations", "board.json").asArray("board.json.presentations")
        val presentation = presentations.firstOrNull { value ->
            (value.asObject("presentation").optional("default") as? com.hangten.android.content.JsonValue.BooleanValue)?.value == true
        } ?: presentations.firstOrNull() ?: throw GitHubSyncException.InvalidResponse("Board has no presentation.")
        return defaultPresentationAssetPath(slug, boardJson)
    }

    private fun formJson(base: String, path: String, values: List<Pair<String, String>>): JSONObject {
        val form = FormBody.Builder().apply { values.forEach { add(it.first, it.second) } }.build()
        return execute("POST", base, path, null, form, deviceFlow = true)
    }

    private fun requestJson(method: String, path: String, token: String, body: JSONObject? = null): JSONObject =
        execute(method, apiBase, path, token, body?.toString()?.toRequestBody(JSON.toMediaType()), deviceFlow = false)

    private fun execute(method: String, base: String, path: String, token: String?, body: okhttp3.RequestBody?, deviceFlow: Boolean): JSONObject {
        val url = endpoint(base, path)
        val request = Request.Builder().url(url).method(method, body)
            // The OAuth endpoints require a JSON response; REST endpoints use
            // GitHub's versioned media type.
            .header("Accept", if (deviceFlow) "application/json" else "application/vnd.github+json")
            .apply {
                if (!token.isNullOrBlank()) header("Authorization", "Bearer $token")
                if (!deviceFlow) header("X-GitHub-Api-Version", "2022-11-28")
            }.build()
        client.newCall(request).execute().use { response ->
            val payload = response.body?.string().orEmpty()
            if (response.isSuccessful) return try { JSONObject(payload) } catch (_: Throwable) {
                throw GitHubSyncException.InvalidResponse("GitHub returned malformed JSON.")
            }
            val message = runCatching { JSONObject(payload).optString("message") }.getOrDefault("GitHub request failed with HTTP ${response.code}")
            when (response.code) {
                404 -> throw GitHubNotFound(message)
                409, 412, 422 -> throw GitHubSyncException.Conflict(message)
                401 -> throw GitHubSyncException.Unauthorized(message)
                else -> throw GitHubSyncException.Transport(message)
            }
        }
    }

    private fun endpoint(base: String, path: String): HttpUrl {
        if (!httpsUrl(base)) throw GitHubSyncException.InvalidResponse("GitHub endpoint must use HTTPS.")
        return (base.trimEnd('/') + path).toHttpUrl()
    }
    private fun repositoryPath() = "/repos/${segment(owner)}/${segment(repository)}"
    private fun segment(value: String) = URLEncoder.encode(value, StandardCharsets.UTF_8.name()).replace("+", "%20")
    private companion object { val JSON = "application/json; charset=utf-8" }
}

private class GitHubNotFound(message: String) : GitHubSyncException(message)
private fun httpsUrl(value: String): Boolean = value.toHttpUrlOrNull()?.isHttps == true
internal fun defaultPresentationAssetPath(slug: String, boardJson: ByteArray): String {
    val root = JsonParser(boardJson.decodeToString()).parse().asObject("board.json")
    val presentations = root.required("presentations", "board.json").asArray("board.json.presentations")
    val presentation = presentations.firstOrNull { value ->
        (value.asObject("presentation").optional("default") as? com.hangten.android.content.JsonValue.BooleanValue)?.value == true
    } ?: presentations.firstOrNull() ?: throw GitHubSyncException.InvalidResponse("Board has no presentation.")
    val assetPath = presentation.asObject("presentation").requiredString("assetPath", "presentation")
    if (!BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/$assetPath")) {
        throw GitHubSyncException.InvalidResponse("Board has an unsafe presentation image path.")
    }
    return assetPath
}
private fun JSONObject.requiredString(name: String): String = optString(name).takeIf { it.isNotBlank() }
    ?: throw GitHubSyncException.InvalidResponse("GitHub returned invalid response data.")
private fun JSONObject.requiredLong(name: String): Long = optLong(name, 0).takeIf { it > 0 }
    ?: throw GitHubSyncException.InvalidResponse("GitHub returned invalid response data.")
