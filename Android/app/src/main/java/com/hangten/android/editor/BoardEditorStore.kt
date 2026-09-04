package com.hangten.android.editor

import com.hangten.android.content.AssetBoardRepository
import com.hangten.android.content.ContentAssets
import com.hangten.android.content.ContentImageDimensions
import com.hangten.android.content.Board
import com.hangten.android.content.JsonParser
import com.hangten.android.content.JsonValue
import com.hangten.android.content.asArray
import com.hangten.android.content.asObject
import com.hangten.android.content.asString
import com.hangten.android.content.required
import com.hangten.android.content.requiredString
import com.hangten.android.content.decodePngImageDimensions
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption.ATOMIC_MOVE
import java.nio.file.StandardCopyOption.REPLACE_EXISTING
import java.util.UUID

/** App-private editor packages. Bundled packages are copied, never modified. */
class BoardEditorStore(
    private val editedRoot: File,
    private val source: BoardPackageSource,
    private val imageDimensionsDecoder: (ByteArray) -> ContentImageDimensions? = { data ->
        decodePngImageDimensions(data)
    },
) {
    fun startEditing(slug: String): File {
        requireSlug(slug)
        val destination = packageDirectory(slug)
        if (File(destination, BOARD_JSON).isFile) return destination
        val sourceFiles = source.filesFor(slug)
        if (sourceFiles.none { it.path == BOARD_JSON } || sourceFiles.none { it.path.startsWith("assets/") }) {
            throw BoardEditorException.MissingSource(slug)
        }
        sourceFiles.forEach { file ->
            require(BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/${file.path}")) {
                "Source package contains an unsafe path."
            }
            val target = File(destination, file.path)
            target.parentFile?.mkdirs()
            target.outputStream().use { output -> output.write(file.data) }
        }
        validate(slug, readBoardJson(slug))
        return destination
    }

    fun readBoardJson(slug: String): String = boardFile(slug).readText()

    fun loadBoard(slug: String): Board = decode(slug, readBoardJson(slug))

    fun readPackageFile(slug: String, relativePath: String): ByteArray {
        if (!BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/$relativePath")) {
            throw BoardEditorException.InvalidPath("Path is outside this board package.")
        }
        return File(packageDirectory(slug), relativePath).readBytes()
    }

    /**
     * Moves one explicitly selected stored command point and saves the same
     * canonical document. It cannot add paths, infer outlines, or inspect
     * presentation pixels.
     */
    fun movePathPoint(
        slug: String,
        holdId: String,
        geometryIndex: Int,
        commandIndex: Int,
        field: EditablePathPoint,
        x: Double,
        y: Double,
    ): String {
        require(x.isFinite() && y.isFinite()) { "Path coordinates must be finite." }
        val root = JsonParser(readBoardJson(slug)).parse().asObject(BOARD_JSON)
        val fields = root.fields.toMutableMap()
        val holds = root.required("holds", BOARD_JSON).asArray("$BOARD_JSON.holds").toMutableList()
        val holdIndex = holds.indexOfFirst { candidate ->
            candidate.asObject("$BOARD_JSON.holds").requiredString("id", "$BOARD_JSON.holds") == holdId
        }
        if (holdIndex < 0) throw BoardEditorException.InvalidPath("Unknown hold $holdId.")
        val hold = holds[holdIndex].asObject("$BOARD_JSON.holds[$holdIndex]")
        val holdFields = hold.fields.toMutableMap()
        val geometry = hold.required("geometry", "$BOARD_JSON.holds[$holdIndex]")
            .asArray("$BOARD_JSON.holds[$holdIndex].geometry").toMutableList()
        if (geometryIndex !in geometry.indices) throw BoardEditorException.InvalidPath("Unknown geometry piece.")
        val piece = geometry[geometryIndex].asObject("geometry")
        val pieceFields = piece.fields.toMutableMap()
        val shape = piece.required("shape", "geometry").asObject("shape")
        if (shape.requiredString("type", "shape") != "path") {
            throw BoardEditorException.InvalidPath("Only an existing canonical path can be edited.")
        }
        val shapeFields = shape.fields.toMutableMap()
        val commands = shape.required("commands", "shape").asArray("shape.commands").toMutableList()
        if (commandIndex !in commands.indices) throw BoardEditorException.InvalidPath("Unknown path command.")
        val command = commands[commandIndex].asObject("shape.commands[$commandIndex]")
        val commandFields = command.fields.toMutableMap()
        val key = field.jsonKey
        val existing = commandFields[key]?.asArray("shape.commands[$commandIndex].$key")
            ?: throw BoardEditorException.InvalidPath("The selected command has no $key point.")
        if (existing.size != 2) throw BoardEditorException.InvalidPath("The selected point is malformed.")
        commandFields[key] = JsonValue.Array(listOf(JsonValue.Number(x), JsonValue.Number(y)))
        commands[commandIndex] = JsonValue.Object(commandFields)
        shapeFields["commands"] = JsonValue.Array(commands)
        pieceFields["shape"] = JsonValue.Object(shapeFields)
        geometry[geometryIndex] = JsonValue.Object(pieceFields)
        holdFields["geometry"] = JsonValue.Array(geometry)
        holds[holdIndex] = JsonValue.Object(holdFields)
        fields["holds"] = JsonValue.Array(holds)
        val edited = JsonPrinter.print(JsonValue.Object(fields))
        save(slug, edited)
        return edited
    }

    /** Validates before atomically replacing board.json; failures leave it untouched. */
    fun save(slug: String, boardJson: String) {
        validate(slug, boardJson)
        atomicReplace(boardFile(slug), boardJson.encodeToByteArray())
    }

    fun boardDirectory(slug: String): File = packageDirectory(slug)

    fun persistPulledImage(slug: String, assetPath: String, data: ByteArray) {
        if (!BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/$assetPath") || !assetPath.startsWith("assets/")) {
            throw BoardEditorException.InvalidPath("Pulled image path is outside this board package.")
        }
        atomicReplace(File(packageDirectory(slug), assetPath), data)
    }

    /**
     * Validates the complete remote board, including its declared package slug
     * and presentation image, before changing either local package file.
     */
    fun applyPulledPackage(slug: String, payload: PulledBoardPackage) {
        if (!BoardPackagePaths.isValidSlug(slug)) {
            throw BoardEditorException.InvalidPath("Pulled package has an invalid board slug.")
        }
        val defaultAssetPath = runCatching { defaultPresentationAssetPath(slug, payload.boardJson) }
            .getOrElse { throw BoardEditorException.InvalidBoard(it.message.orEmpty()) }
        if (!BoardPackagePaths.isAllowed(slug, "Hangboards/$slug/${payload.imagePath}") ||
            defaultAssetPath != payload.imagePath
        ) throw BoardEditorException.InvalidPath("Pulled package is outside this board package.")
        validate(
            slug,
            payload.boardJson.decodeToString(),
            mapOf(payload.imagePath to payload.image),
        )
        atomicReplace(File(packageDirectory(slug), payload.imagePath), payload.image)
        atomicReplace(boardFile(slug), payload.boardJson)
    }

    private fun validate(
        slug: String,
        boardJson: String,
        stagedAssets: Map<String, ByteArray> = emptyMap(),
    ) {
        requireSlug(slug)
        val board = decode(slug, boardJson, stagedAssets)
        if (board.id != slug) throw BoardEditorException.InvalidBoard("board ID must match the package slug.")
    }

    private fun decode(
        slug: String,
        boardJson: String,
        stagedAssets: Map<String, ByteArray> = emptyMap(),
    ): Board = AssetBoardRepository(
        EditorContentAssets(
            root = editedRoot,
            slug = slug,
            candidateBoardJson = boardJson,
            stagedAssets = stagedAssets,
            imageDimensionsDecoder = imageDimensionsDecoder,
        ),
    ).loadBoards().getOrElse { throw BoardEditorException.InvalidBoard(it.message.orEmpty()) }.single()

    private fun atomicReplace(destination: File, data: ByteArray) {
        destination.parentFile?.mkdirs()
        val temporary = File(destination.parentFile, "${destination.name}.tmp-${UUID.randomUUID()}")
        try {
            FileOutputStream(temporary).use { output ->
                output.write(data)
                output.fd.sync()
            }
            Files.move(temporary.toPath(), destination.toPath(), ATOMIC_MOVE, REPLACE_EXISTING)
        } catch (error: Throwable) {
            temporary.delete()
            throw BoardEditorException.WriteFailed(error.message.orEmpty())
        }
    }

    private fun boardFile(slug: String): File {
        val result = File(packageDirectory(slug), BOARD_JSON)
        if (!result.isFile) throw BoardEditorException.MissingEditedPackage(slug)
        return result
    }

    private fun packageDirectory(slug: String): File {
        requireSlug(slug)
        editedRoot.mkdirs()
        return File(editedRoot, slug)
    }

    private fun requireSlug(slug: String) {
        if (!SLUG.matches(slug)) throw BoardEditorException.InvalidSlug(slug)
    }

    private companion object {
        const val BOARD_JSON = "board.json"
        val SLUG = Regex("[a-z0-9]+(?:-[a-z0-9]+)*")
    }
}

enum class EditablePathPoint(internal val jsonKey: String) { To("to"), Control("control"), Control1("control1"), Control2("control2") }

sealed class BoardEditorException(message: String) : IllegalStateException(message) {
    class InvalidSlug(slug: String) : BoardEditorException("Invalid board slug: $slug")
    class MissingSource(slug: String) : BoardEditorException("Missing bundled board package: $slug")
    class MissingEditedPackage(slug: String) : BoardEditorException("No editable board package: $slug")
    class InvalidPath(message: String) : BoardEditorException(message)
    class InvalidBoard(message: String) : BoardEditorException(message)
    class WriteFailed(message: String) : BoardEditorException("Could not atomically save board.json: $message")
}

data class BoardPackageSourceFile(val path: String, val data: ByteArray)

interface BoardPackageSource { fun filesFor(slug: String): List<BoardPackageSourceFile> }

class FileBoardPackageSource(private val root: File) : BoardPackageSource {
    override fun filesFor(slug: String): List<BoardPackageSourceFile> {
        val directory = File(root, slug)
        return directory.walkTopDown().filter(File::isFile).map { file ->
            BoardPackageSourceFile(file.relativeTo(directory).invariantSeparatorsPath, file.readBytes())
        }.toList()
    }
}

/** All repository paths are checked before pull, local persistence, and push. */
object BoardPackagePaths {
    private val slug = Regex("[a-z0-9]+(?:-[a-z0-9]+)*")

    fun isValidSlug(value: String): Boolean = slug.matches(value)

    fun isAllowed(slug: String, path: String): Boolean {
        if (!isValidSlug(slug)) return false
        val prefix = "Hangboards/$slug/"
        if (!path.startsWith(prefix) || path.contains("\\") || path.split('/').any { it == ".." || it == "." || it.isEmpty() }) return false
        val relative = path.removePrefix(prefix)
        return relative == "board.json" || (relative.startsWith("assets/") && relative.length > "assets/".length && !relative.endsWith('/'))
    }
}

private class EditorContentAssets(
    private val root: File,
    private val slug: String,
    private val candidateBoardJson: String,
    private val stagedAssets: Map<String, ByteArray>,
    private val imageDimensionsDecoder: (ByteArray) -> ContentImageDimensions?,
) : ContentAssets {
    override fun list(path: String): List<String>? = when (path) {
        "Hangboards" -> listOf(slug)
        else -> null
    }

    override fun read(path: String): String? = when (path) {
        "Hangboards/$slug/board.json" -> candidateBoardJson
        else -> null
    }

    override fun exists(path: String): Boolean {
        val expectedPrefix = "Hangboards/$slug/"
        if (!path.startsWith(expectedPrefix)) return false
        val relative = path.removePrefix(expectedPrefix)
        return relative in stagedAssets || File(File(root, slug), relative).isFile
    }

    override fun imageDimensions(path: String): ContentImageDimensions? {
        val expectedPrefix = "Hangboards/$slug/"
        if (!path.startsWith(expectedPrefix)) return null
        val relative = path.removePrefix(expectedPrefix)
        val data = stagedAssets[relative] ?: runCatching {
            File(File(root, slug), relative).takeIf(File::isFile)?.readBytes()
        }.getOrNull() ?: return null
        return runCatching { imageDimensionsDecoder(data) }.getOrNull()
    }
}

private object JsonPrinter {
    fun print(value: JsonValue): String = when (value) {
        is JsonValue.Array -> value.values.joinToString(prefix = "[", postfix = "]", separator = ",") { print(it) }
        is JsonValue.BooleanValue -> value.value.toString()
        JsonValue.Null -> "null"
        is JsonValue.Number -> value.value.toString()
        is JsonValue.Object -> value.fields.entries.joinToString(prefix = "{", postfix = "}", separator = ",") {
            "${quoted(it.key)}:${print(it.value)}"
        }
        is JsonValue.StringValue -> quoted(value.value)
    }

    private fun quoted(value: String): String = buildString {
        append('"')
        value.forEach { character ->
            when (character) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\b' -> append("\\b")
                '\u000C' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> if (character.code < 0x20) append("\\u%04x".format(character.code)) else append(character)
            }
        }
        append('"')
    }
}
