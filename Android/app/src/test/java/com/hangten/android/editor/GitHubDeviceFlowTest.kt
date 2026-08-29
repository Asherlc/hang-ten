package com.hangten.android.editor

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GitHubDeviceFlowTest {
    @Test
    fun slowDownExtendsTheNextPollIntervalBeforeAuthorization() = runTest {
        val api = FakeGitHubDeviceApi(listOf(DevicePollResult.SlowDown, DevicePollResult.Authorized("token")), expiresInSeconds = 50)
        val waits = mutableListOf<Long>()
        val tokenStore = MemoryTokenStore()
        val flow = GitHubDeviceFlow(
            api = api,
            tokenStore = tokenStore,
            clock = { 0L },
            wait = { waits += it },
        )

        val result = flow.authorize("public-client") {}

        assertEquals(DeviceFlowOutcome.Authorized("octocat"), result)
        assertEquals(listOf(5_000L, 10_000L), waits)
        assertEquals("token", tokenStore.load())
    }

    @Test
    fun expiredChallengeDoesNotPollOrPersistCredentials() = runTest {
        val api = FakeGitHubDeviceApi(emptyList())
        val tokenStore = MemoryTokenStore()
        var now = 0L
        val flow = GitHubDeviceFlow(
            api = api,
            tokenStore = tokenStore,
            clock = { now },
            wait = { now = 10_000L },
        )

        val result = flow.authorize("public-client") {}

        assertEquals(DeviceFlowOutcome.Expired, result)
        assertEquals(0, api.polls)
        assertEquals(null, tokenStore.load())
    }

    @Test
    fun cancellationLeavesExistingCredentialUntouched() = runTest {
        val tokenStore = MemoryTokenStore("existing")
        val flow = GitHubDeviceFlow(
            api = FakeGitHubDeviceApi(emptyList()),
            tokenStore = tokenStore,
            clock = { 0L },
            wait = { throw CancellationException("cancelled") },
        )

        val result = flow.authorize("public-client") {}

        assertEquals(DeviceFlowOutcome.Cancelled, result)
        assertEquals("existing", tokenStore.load())
    }

    @Test
    fun remoteHeadConflictPreventsPackagePush() = runTest {
        val api = FakeGitHubPackageApi(currentHead = "new-head")
        val sync = GitHubPackageSync(api)

        val result = sync.push(
            token = "token",
            slug = "demo",
            branch = "hangten/demo",
            expectedHead = "old-head",
            boardJson = boardJsonWithDefaultAsset("assets/primary.png").encodeToByteArray(),
            imagePath = "assets/primary.png",
            image = byteArrayOf(1),
            message = "Edit geometry",
        )

        assertEquals(PackageSyncResult.Conflict, result)
        assertFalse(api.pushed)
    }

    @Test
    fun unreferencedAssetCannotBeIncludedInBoardPush() = runTest {
        val api = FakeGitHubPackageApi(currentHead = "head")
        val result = GitHubPackageSync(api).push(
            token = "token",
            slug = "demo",
            branch = "hangten/demo",
            expectedHead = "head",
            boardJson = boardJsonWithDefaultAsset("assets/primary.png").encodeToByteArray(),
            imagePath = "assets/unrelated.png",
            image = byteArrayOf(1),
            message = "Edit geometry",
        )

        assertTrue(result is PackageSyncResult.Failed)
        assertFalse(api.pushed)
    }

    @Test
    fun malformedSlugIsRejectedBeforePullingRemotePackage() = runTest {
        val api = FakeGitHubPackageApi(currentHead = "head")

        val result = GitHubPackageSync(api).pull("token", "../demo", "main")

        assertTrue(result is PackageSyncResult.Failed)
        assertEquals(0, api.pulls)
    }

    @Test
    fun aDraftBranchIsUniqueThenReusableAfterItsPullRequestExists() = runTest {
        val api = ReusableBranchApi()
        val sync = GitHubPackageSync(api)
        val board = boardJsonWithDefaultAsset("assets/primary.png").encodeToByteArray()
        val branch = GitHubBranchName.newForBoard("demo") { "review-1" }

        val first = sync.push("token", "demo", branch, "base", board, "assets/primary.png", byteArrayOf(1), "Edit geometry")
        val pushed = first as PackageSyncResult.Pushed
        val second = sync.push(
            "token", "demo", branch, pushed.commit, board, "assets/primary.png", byteArrayOf(2), "Edit geometry again",
            existingPullRequestUrl = pushed.pullRequestUrl,
        )

        assertEquals("hangten/android-demo-review-1", branch)
        assertTrue(second is PackageSyncResult.Pushed)
        assertEquals(1, api.pullRequests)
        assertEquals(2, api.pushes)
    }
}

private fun boardJsonWithDefaultAsset(assetPath: String) = """
    {"id":"demo","manufacturer":"Demo","name":"Demo","subtitle":"Demo","productURL":"https://example.com","aspectRatio":2.0,"presentations":[{"id":"primary","name":"Primary","assetPath":"$assetPath","aspectRatio":2.0,"default":true}],"holds":[]}
""".trimIndent()

private class FakeGitHubDeviceApi(
    private val responses: List<DevicePollResult>,
    private val expiresInSeconds: Long = 5,
) : GitHubDeviceApi {
    var polls = 0
    override suspend fun requestDeviceCode(clientId: String) = DeviceChallenge(
        deviceCode = "device",
        userCode = "ABCD-EFGH",
        verificationUri = "https://github.com/login/device",
        expiresInSeconds = expiresInSeconds,
        intervalSeconds = 5,
    )
    override suspend fun pollDeviceCode(clientId: String, deviceCode: String): DevicePollResult = responses[polls++]
    override suspend fun authenticatedUser(token: String) = "octocat"
}

private class MemoryTokenStore(initial: String? = null) : GitHubTokenStore {
    private var value = initial
    override fun save(token: String) { value = token }
    override fun load(): String? = value
    override fun clear() { value = null }
}

private class FakeGitHubPackageApi(
    private val currentHead: String,
) : GitHubPackageApi {
    var pushed = false
    var pulls = 0
    override suspend fun branchHead(token: String, branch: String) = currentHead
    override suspend fun createBranch(token: String, branch: String, fromHead: String) = Unit
    override suspend fun defaultBranch(token: String) = "main"
    override suspend fun pullPackage(token: String, branch: String, slug: String): PulledBoardPackage {
        pulls += 1
        error("not used")
    }
    override suspend fun pushPackage(token: String, branch: String, expectedHead: String, files: List<GitHubPackageFile>, message: String): String {
        pushed = true
        return "commit"
    }
    override suspend fun createPullRequest(token: String, title: String, head: String, base: String, body: String) = "https://github.com/Asherlc/hang-ten/pull/1"
}

private class ReusableBranchApi : GitHubPackageApi {
    private val heads = mutableMapOf("main" to "base")
    var pullRequests = 0
    var pushes = 0

    override suspend fun defaultBranch(token: String) = "main"
    override suspend fun branchHead(token: String, branch: String) = heads[branch]
    override suspend fun createBranch(token: String, branch: String, fromHead: String) { heads[branch] = fromHead }
    override suspend fun pullPackage(token: String, branch: String, slug: String): PulledBoardPackage = error("not used")
    override suspend fun pushPackage(token: String, branch: String, expectedHead: String, files: List<GitHubPackageFile>, message: String): String {
        check(heads[branch] == expectedHead)
        pushes += 1
        return "commit-$pushes".also { heads[branch] = it }
    }
    override suspend fun createPullRequest(token: String, title: String, head: String, base: String, body: String): String {
        pullRequests += 1
        return "https://github.com/Asherlc/hang-ten/pull/1"
    }
}
