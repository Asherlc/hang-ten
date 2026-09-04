package com.hangten.android.editor

import com.hangten.android.content.ContentImageDimensions
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
    fun presentationAvailabilitySurvivesAPathEdit() {
        val root = createTempDirectory("board-editor-availability").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val boardFile = File(source, "demo/board.json")
            boardFile.writeText(
                boardFile.readText().replaceFixture(
                    "\"default\":true",
                    "\"default\":true,\"availableHoldIDs\":[\"edge\"]",
                ),
            )
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

            assertTrue(edited.contains("\"availableHoldIDs\":[\"edge\"]"))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun routedCordRigSurvivesAPathEditWithoutLosingRequiredArrays() {
        val root = createTempDirectory("board-editor-routed-cord").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val boardFile = File(source, "demo/board.json")
            boardFile.writeText(routedBoardJson())
            val store = BoardEditorStore(
                File(root, "edited"),
                FileBoardPackageSource(source),
                imageDimensionsDecoder = { ContentImageDimensions(width = 1000, height = 1000) },
            )

            store.startEditing("demo")
            val originalRig = store.loadBoard("demo").presentations.single().cordRig
            val edited = store.movePathPoint(
                slug = "demo",
                holdId = "edge",
                geometryIndex = 0,
                commandIndex = 1,
                field = EditablePathPoint.To,
                x = 0.75,
                y = 0.25,
            )

            assertEquals(originalRig, store.loadBoard("demo").presentations.single().cordRig)
            assertTrue(edited.contains("\"paths\":[]"))
            assertTrue(edited.contains("\"occlusions\":[]"))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun pulledRoutedImageAspectMismatchLeavesBoardAndImageUntouched() {
        val root = createTempDirectory("board-editor-pull-image-aspect").toFile()
        try {
            val source = File(root, "source").also { it.mkdirs() }
            writeSourcePackage(source)
            val dimensionsByFixture = mapOf(
                "fixture-image" to ContentImageDimensions(width = 1000, height = 1000),
                "remote-image" to ContentImageDimensions(width = 2000, height = 1000),
            )
            val store = BoardEditorStore(
                File(root, "edited"),
                FileBoardPackageSource(source),
                imageDimensionsDecoder = { data -> dimensionsByFixture[data.decodeToString()] },
            )
            store.startEditing("demo")
            val originalBoard = store.readBoardJson("demo")
            val originalImage = store.readPackageFile("demo", "assets/primary.png")

            val failure = runCatching {
                store.applyPulledPackage(
                    "demo",
                    PulledBoardPackage(
                        head = "head",
                        boardJson = routedBoardJson().encodeToByteArray(),
                        imagePath = "assets/primary.png",
                        image = "remote-image".encodeToByteArray(),
                    ),
                )
            }.exceptionOrNull()

            assertTrue(failure is BoardEditorException.InvalidBoard)
            assertTrue(failure?.message?.contains("innerFaceFrame aspect ratio") == true)
            assertEquals(originalBoard, store.readBoardJson("demo"))
            assertEquals(originalImage.toList(), store.readPackageFile("demo", "assets/primary.png").toList())
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
                        boardJson = boardJson().replaceFixture("\"id\":\"demo\"", "\"id\":\"other\"")
                            .encodeToByteArray(),
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

    private fun routedBoardJson(): String = boardJson()
        .replaceFixture("\"aspectRatio\":2.0", "\"aspectRatio\":1.0", expectedOccurrences = 2)
        .replaceFixture(
            "\"default\":true}",
            "\"default\":true,\"cordRig\":${routedCordRigJson()}}",
        )

    private fun routedCordRigJson(): String = """
        {
          "type":"routed",
          "sceneSize":{"width":1000,"height":1000},
          "sourceFrame":{"x":0,"y":0,"width":1000,"height":1000},
          "innerFaceFrame":{"x":0,"y":0,"width":1000,"height":1000},
          "style":{"diameter":12,"outlineColor":"#101010","baseColor":"#2255AA","braidColors":["#FFD000","#0055CC"]},
          "ports":[
            {"id":"body-left","space":"body","point":{"x":200,"y":650}},
            {"id":"world-left","space":"world","point":{"x":400,"y":100}}
          ],
          "tensionGroups":[
            {"id":"main","bodyPortIDs":["body-left"],"worldPortIDs":["world-left"],"pairing":"declared","layer":"behindFace"}
          ],
          "paths":[],
          "occlusions":[]
        }
    """.trimIndent()

    private fun String.replaceFixture(
        old: String,
        new: String,
        expectedOccurrences: Int = 1,
    ): String {
        val actualOccurrences = windowedSequence(old.length).count { it == old }
        check(actualOccurrences == expectedOccurrences) {
            "Expected fixture fragment $old exactly $expectedOccurrences time(s), found $actualOccurrences."
        }
        return replace(old, new)
    }
}
