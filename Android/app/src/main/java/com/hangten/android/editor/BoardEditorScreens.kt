package com.hangten.android.editor

import android.graphics.BitmapFactory
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.hangten.android.board.BoardCanvas
import com.hangten.android.content.Board
import com.hangten.android.content.HoldShape
import com.hangten.android.content.PathCommand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

@Composable
fun BoardEditorListScreen(
    boards: List<Board>,
    session: GitHubSyncSession,
    onOpenBoard: (String) -> Unit,
    contentPadding: PaddingValues,
) {
    val syncState by session.state.collectAsState()
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("GitHub board packages")
                    when {
                        syncState.username != null -> {
                            Text("Connected as ${syncState.username}")
                            OutlinedButton(
                                onClick = session::signOut,
                                modifier = Modifier.semantics { contentDescription = "Sign out of GitHub" },
                            ) { Text("Sign out") }
                        }
                        syncState.challenge != null -> {
                            Text("Enter ${syncState.challenge!!.userCode} at ${syncState.challenge!!.verificationUri}")
                            OutlinedButton(
                                onClick = session::cancelSignIn,
                                modifier = Modifier.semantics { contentDescription = "Cancel GitHub sign-in" },
                            ) { Text("Cancel sign-in") }
                        }
                        else -> Button(
                            onClick = session::startSignIn,
                            enabled = !syncState.signingIn,
                            modifier = Modifier.semantics { contentDescription = "Connect GitHub" },
                        ) { Text(if (syncState.signingIn) "Connecting…" else "Connect GitHub") }
                    }
                    syncState.error?.let { Text(it) }
                }
            }
        }
        item { Text("Board editor") }
        items(boards, key = Board::id) { board ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(board.name)
                    Text("${board.manufacturer} · ${board.holds.size} holds")
                    Button(
                        onClick = { onOpenBoard(board.id) },
                        modifier = Modifier.semantics { contentDescription = "Edit board ${board.name}" },
                    ) { Text("Edit local copy") }
                }
            }
        }
    }
}

@Composable
fun BoardEditorScreen(
    slug: String,
    store: BoardEditorStore,
    tokenStore: GitHubTokenStore,
    packageSync: GitHubPackageSync,
    contentPadding: PaddingValues,
) {
    var board by remember(slug) { mutableStateOf<Board?>(null) }
    var localImage by remember(slug) { mutableStateOf<ImageBitmap?>(null) }
    var selectedHoldId by remember(slug) { mutableStateOf<String?>(null) }
    var selectedGeometry by remember(slug) { mutableIntStateOf(0) }
    var selectedCommand by remember(slug) { mutableIntStateOf(0) }
    var version by remember(slug) { mutableIntStateOf(0) }
    var error by remember(slug) { mutableStateOf<String?>(null) }
    var remoteHead by remember(slug) { mutableStateOf<String?>(null) }
    var draftBranch by remember(slug) { mutableStateOf<String?>(null) }
    var draftPullRequestUrl by remember(slug) { mutableStateOf<String?>(null) }
    var syncStatus by remember(slug) { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(slug, version) {
        runCatching {
            withContext(Dispatchers.IO) {
                store.startEditing(slug)
                store.loadBoard(slug)
            }
        }.onSuccess { loaded ->
            board = loaded
            localImage = withContext(Dispatchers.IO) {
                val assetPath = loaded.presentations.firstOrNull { it.isDefault }?.assetPath
                assetPath?.let { path ->
                    BitmapFactory.decodeFile(File(store.boardDirectory(slug), path).path)?.asImageBitmap()
                }
            }
        }.onFailure { error = it.message }
    }
    val current = board
    Column(
        modifier = Modifier.fillMaxSize().padding(contentPadding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Edit $slug")
        error?.let { Text(it) }
        if (current != null) {
            val selected = current.holds.firstOrNull { it.id == selectedHoldId } ?: current.holds.firstOrNull()
            BoardCanvas(
                board = current,
                activeHoldIDs = setOfNotNull(selected?.id),
                onHoldTap = { selectedHoldId = it; selectedGeometry = 0; selectedCommand = 0 },
                imageOverride = localImage,
                modifier = Modifier.pointerInput(selected, selectedGeometry, selectedCommand) {
                    var start: Pair<Double, Double>? = null
                    var totalDragX = 0f
                    var totalDragY = 0f
                    detectDragGestures(
                        onDragStart = {
                            start = selected?.pathAnchor(selectedGeometry, selectedCommand)
                            totalDragX = 0f
                            totalDragY = 0f
                        },
                        onDrag = { change, drag ->
                            val hold = selected ?: return@detectDragGestures
                            val initial = start ?: return@detectDragGestures
                            val frame = hold.geometry.getOrNull(selectedGeometry)?.frame ?: return@detectDragGestures
                            totalDragX += drag.x
                            totalDragY += drag.y
                            val x = initial.first + totalDragX / size.width / frame.width
                            val y = initial.second + totalDragY / size.height / frame.height
                            runCatching {
                                store.movePathPoint(slug, hold.id, selectedGeometry, selectedCommand, EditablePathPoint.To, x, y)
                            }.onSuccess { version += 1 }.onFailure { error = it.message }
                            change.consume()
                        },
                    )
                },
            )
            Text("Tap a hold, then drag the selected saved path anchor. Geometry is written directly to that canonical command.")
            if (selected != null) {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.weight(1f)) {
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            selected.geometry.indices.forEach { index ->
                                OutlinedButton(
                                    onClick = { selectedGeometry = index; selectedCommand = 0 },
                                    modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Select hold piece $index" },
                                ) { Text(if (index == selectedGeometry) "Selected piece $index" else "Select piece $index") }
                            }
                        }
                    }
                    val commands = (selected.geometry.getOrNull(selectedGeometry)?.shape as? HoldShape.Path)?.commands.orEmpty()
                    items(commands.indices.toList()) { index ->
                        val command = commands[index]
                        if (command is PathCommand.Move || command is PathCommand.Line || command is PathCommand.Quad || command is PathCommand.Curve) {
                            OutlinedButton(
                                onClick = { selectedCommand = index },
                                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Select path command $index" },
                            ) { Text(if (index == selectedCommand) "Selected command $index" else "Select command $index") }
                        }
                    }
                }
            }
            OutlinedButton(
                onClick = { version += 1 },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Reload saved board" },
            ) { Text("Save complete — reload board") }
            OutlinedButton(
                onClick = {
                    scope.launch {
                        val token = tokenStore.load()
                        if (token == null) {
                            syncStatus = "Connect GitHub before pulling a package."
                            return@launch
                        }
                        when (val result = withContext(Dispatchers.IO) {
                            packageSync.pull(token, slug, packageSync.defaultBranch(token))
                        }) {
                            is PackageSyncResult.Pulled -> runCatching {
                                store.applyPulledPackage(slug, result.payload)
                                remoteHead = result.payload.head
                                draftBranch = null
                                draftPullRequestUrl = null
                                version += 1
                            }.onSuccess { syncStatus = "Pulled latest package." }.onFailure { syncStatus = it.message }
                            PackageSyncResult.Conflict -> syncStatus = "GitHub reported a conflict. Pull again before editing."
                            is PackageSyncResult.Failed -> syncStatus = result.message
                            is PackageSyncResult.Pushed -> error("Unexpected push result")
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Pull latest board package" },
            ) { Text("Pull latest from GitHub") }
            Button(
                onClick = {
                    scope.launch {
                        val token = tokenStore.load()
                        val expected = remoteHead
                        val branch = draftBranch ?: GitHubBranchName.newForBoard(slug)
                        val defaultImage = current.presentations.firstOrNull { it.isDefault }?.assetPath
                        if (token == null) syncStatus = "Connect GitHub before pushing a package."
                        else if (expected == null) syncStatus = "Pull latest before committing so conflicts can be detected."
                        else if (defaultImage == null) syncStatus = "Board has no default presentation image."
                        else when (val result = withContext(Dispatchers.IO) {
                            packageSync.push(
                                token = token,
                                slug = slug,
                                branch = branch,
                                expectedHead = expected,
                                boardJson = store.readBoardJson(slug).encodeToByteArray(),
                                imagePath = defaultImage,
                                image = store.readPackageFile(slug, defaultImage),
                                message = "Update $slug board geometry",
                                existingPullRequestUrl = draftPullRequestUrl,
                            )
                        }) {
                            is PackageSyncResult.Pushed -> {
                                draftBranch = result.branch
                                draftPullRequestUrl = result.pullRequestUrl
                                remoteHead = result.commit
                                syncStatus = "Pull request opened: ${result.pullRequestUrl}"
                            }
                            PackageSyncResult.Conflict -> syncStatus = "Remote branch changed. Pull latest and resolve the conflict."
                            is PackageSyncResult.Failed -> syncStatus = result.message
                            is PackageSyncResult.Pulled -> error("Unexpected pull result")
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Commit board package and open pull request" },
            ) { Text("Commit and open pull request") }
            syncStatus?.let { Text(it) }
        }
    }
}

private fun com.hangten.android.content.BoardHold.pathAnchor(geometryIndex: Int, commandIndex: Int): Pair<Double, Double>? =
    ((geometry.getOrNull(geometryIndex)?.shape as? HoldShape.Path)?.commands?.getOrNull(commandIndex)).let { command ->
        when (command) {
            is PathCommand.Move -> command.to.x.toDouble() to command.to.y.toDouble()
            is PathCommand.Line -> command.to.x.toDouble() to command.to.y.toDouble()
            is PathCommand.Quad -> command.to.x.toDouble() to command.to.y.toDouble()
            is PathCommand.Curve -> command.to.x.toDouble() to command.to.y.toDouble()
            else -> null
        }
    }
