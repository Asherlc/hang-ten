package com.hangten.android.editor

import java.io.File
import kotlin.io.path.createTempDirectory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BoardEditorStoreTest {
    @Test
    fun selectedCanonicalPathPointIsTheOnlyGeometryMutated() {
        val root = createTempDirectory("board-editor-store").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val store = BoardEditorStore(File(root, "edited"), FileBoardPackageSource(source))

            store.startEditing("demo")
            val edited = store.movePathPoint(
                slug = "demo",
                holdId = "edge",
                geometryIndex = 0,
                commandIndex = 1,
                field = EditablePathPoint.To,
                x = 0.75,
                y = 0.25,
            )

            assertTrue(edited.contains("\"to\":[0.75,0.25]"))
            assertTrue(edited.contains("\"to\":[0.0,0.0]"))
            assertTrue(edited.contains("\"control\":[0.5,0.5]"))
            assertFalse(edited.contains("generated"))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun invalidBoardNeverReplacesPreviouslySavedDocument() {
        val root = createTempDirectory("board-editor-atomic").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val store = BoardEditorStore(File(root, "edited"), FileBoardPackageSource(source))
            store.startEditing("demo")
            val before = store.readBoardJson("demo")

            val failure = runCatching { store.save("demo", "{ not-json") }.exceptionOrNull()

            assertTrue(failure is BoardEditorException.InvalidBoard)
            assertEquals(before, store.readBoardJson("demo"))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun rejectsTraversalAndNonPackageBoardPaths() {
        assertTrue(BoardPackagePaths.isAllowed("demo", "Hangboards/demo/board.json"))
        assertTrue(BoardPackagePaths.isAllowed("demo", "Hangboards/demo/assets/primary.png"))
        assertFalse(BoardPackagePaths.isAllowed("demo", "Hangboards/other/board.json"))
        assertFalse(BoardPackagePaths.isAllowed("demo", "Hangboards/demo/../secret"))
        assertFalse(BoardPackagePaths.isAllowed("demo", "Plans/demo.json"))
    }

    @Test
    fun invalidPulledBoardDoesNotPersistItsAsset() {
        val root = createTempDirectory("board-editor-pull").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val store = BoardEditorStore(File(root, "edited"), FileBoardPackageSource(source))
            store.startEditing("demo")
            val originalImage = store.readPackageFile("demo", "assets/primary.png")

            val failure = runCatching {
                store.applyPulledPackage(
                    "demo",
                    PulledBoardPackage(
                        head = "head",
                        boardJson = "{ not-json".encodeToByteArray(),
                        imagePath = "assets/primary.png",
                        image = "remote-image".encodeToByteArray(),
                    ),
                )
            }.exceptionOrNull()

            assertTrue(failure is BoardEditorException.InvalidBoard)
            assertEquals(originalImage.toList(), store.readPackageFile("demo", "assets/primary.png").toList())
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun pulledBoardWithAnotherSlugDoesNotPersistItsAsset() {
        val root = createTempDirectory("board-editor-pull-slug").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val store = BoardEditorStore(File(root, "edited"), FileBoardPackageSource(source))
            store.startEditing("demo")
            val originalImage = store.readPackageFile("demo", "assets/primary.png")

            val failure = runCatching {
                store.applyPulledPackage(
                    "demo",
                    PulledBoardPackage(
                        head = "head",
                        boardJson = boardJson().replace("\"id\":\"demo\"", "\"id\":\"other\"").encodeToByteArray(),
                        imagePath = "assets/primary.png",
                        image = "remote-image".encodeToByteArray(),
                    ),
                )
            }.exceptionOrNull()

            assertTrue(failure is BoardEditorException.InvalidBoard)
            assertEquals(originalImage.toList(), store.readPackageFile("demo", "assets/primary.png").toList())
        } finally {
            root.deleteRecursively()
        }
    }

    private fun writeSourcePackage(root: File) {
        val packageDirectory = File(root, "demo/assets").also { it.mkdirs() }
        File(packageDirectory, "primary.png").writeText("fixture-image")
        File(root, "demo/board.json").writeText(boardJson())
    }

    private fun boardJson(): String = """
        {
          "id":"demo",
          "manufacturer":"Demo",
          "name":"Demo",
          "subtitle":"Test board",
          "productURL":"https://example.com/demo",
          "aspectRatio":2.0,
          "presentations":[{"id":"primary","name":"Primary","assetPath":"assets/primary.png","aspectRatio":2.0,"default":true}],
          "holds":[{"id":"edge","name":"Edge","kind":"edge","presentationID":"primary","geometry":[{"frame":{"x":0.1,"y":0.2,"width":0.3,"height":0.4},"shape":{"type":"path","commands":[{"command":"move","to":[0.0,0.0]},{"command":"line","to":[1.0,0.0]},{"command":"quad","control":[0.5,0.5],"to":[1.0,1.0]},{"command":"close"}]}}]}]
        }
    """.trimIndent()
}
