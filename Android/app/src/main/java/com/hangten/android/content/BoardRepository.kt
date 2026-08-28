package com.hangten.android.content

interface ContentAssets {
    fun list(path: String): List<String>?
    fun read(path: String): String?
    fun exists(path: String): Boolean
}

interface BoardRepository {
    fun loadBoards(): Result<List<Board>>
}

class AssetBoardRepository(
    private val assets: ContentAssets,
) : BoardRepository {
    override fun loadBoards(): Result<List<Board>> = runCatching {
        val packages = assets.list(BOARDS_ROOT)
            ?.sorted()
            ?.also { if (it.isEmpty()) fail("$BOARDS_ROOT contains no board packages.") }
            ?: fail("Missing $BOARDS_ROOT asset directory.")
        val boardIds = mutableSetOf<String>()
        packages.map { packageName ->
            val boardPath = "$BOARDS_ROOT/$packageName/board.json"
            val source = assets.read(boardPath) ?: fail("Missing board document $boardPath.")
            val board = decodeBoard(JsonParser(source).parse().asObject(boardPath), boardPath, packageName)
            if (!boardIds.add(board.id)) fail("Duplicate board ID \"${board.id}\".")
            board
        }
    }

    private fun decodeBoard(
        objectValue: JsonValue.Object,
        path: String,
        packageName: String,
    ): Board {
        val boardId = objectValue.requiredString("id", path)
        val presentations = objectValue.required("presentations", path)
            .asArray("$path.presentations")
            .mapIndexed { index, value -> decodePresentation(value.asObject("$path.presentations[$index]"), "$path.presentations[$index]") }
        if (presentations.isEmpty()) fail("$path.presentations must not be empty.")
        if (presentations.count { it.isDefault } != 1) fail("$path.presentations must contain exactly one default presentation.")
        if (presentations.map { it.id }.toSet().size != presentations.size) fail("$path.presentations contains duplicate IDs.")
        presentations.forEach { presentation ->
            val assetPath = "$BOARDS_ROOT/$packageName/${presentation.assetPath}"
            if (!assets.exists(assetPath)) fail("Board $boardId is missing presentation asset ${presentation.assetPath}.")
        }

        val holds = objectValue.required("holds", path)
            .asArray("$path.holds")
            .mapIndexed { index, value -> decodeHold(value.asObject("$path.holds[$index]"), "$path.holds[$index]") }
        if (holds.isEmpty()) fail("$path.holds must not be empty.")
        if (holds.map { it.id }.toSet().size != holds.size) fail("$path.holds contains duplicate IDs.")
        val presentationIds = presentations.map { it.id }.toSet()
        holds.forEach { hold ->
            if (hold.presentationId !in presentationIds) {
                fail("Board $boardId hold ${hold.id} references missing presentation ${hold.presentationId}.")
            }
        }

        return Board(
            id = boardId,
            manufacturer = objectValue.requiredString("manufacturer", path),
            name = objectValue.requiredString("name", path),
            subtitle = objectValue.requiredString("subtitle", path),
            productUrl = objectValue.requiredString("productURL", path),
            aspectRatio = positiveFiniteFloat(objectValue.required("aspectRatio", path), "$path.aspectRatio"),
            presentations = presentations,
            holds = holds,
        )
    }

    private fun decodePresentation(objectValue: JsonValue.Object, path: String): BoardPresentation {
        val assetPath = objectValue.requiredString("assetPath", path)
        if (!assetPath.startsWith("assets/") || assetPath.split('/').any { it == ".." || it.isBlank() }) {
            fail("$path.assetPath must be a relative assets path.")
        }
        val isDefault = (objectValue.required("default", path) as? JsonValue.BooleanValue)?.value
            ?: fail("$path.default must be a boolean.")
        return BoardPresentation(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            assetPath = assetPath,
            aspectRatio = positiveFiniteFloat(objectValue.required("aspectRatio", path), "$path.aspectRatio"),
            isDefault = isDefault,
        )
    }

    private fun decodeHold(objectValue: JsonValue.Object, path: String): BoardHold {
        val geometry = objectValue.required("geometry", path)
            .asArray("$path.geometry")
            .mapIndexed { index, value -> decodeGeometry(value.asObject("$path.geometry[$index]"), "$path.geometry[$index]") }
        if (geometry.isEmpty()) fail("$path.geometry must not be empty.")
        return BoardHold(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            kind = objectValue.requiredString("kind", path),
            presentationId = objectValue.requiredString("presentationID", path),
            geometry = geometry,
        )
    }

    private fun decodeGeometry(objectValue: JsonValue.Object, path: String): BoardGeometry =
        BoardGeometry(
            frame = decodeFrame(objectValue.required("frame", path).asObject("$path.frame"), "$path.frame"),
            shape = decodeShape(objectValue.required("shape", path).asObject("$path.shape"), "$path.shape"),
        )

    private fun decodeFrame(objectValue: JsonValue.Object, path: String): NormalizedFrame {
        val x = objectValue.required("x", path).asFiniteFloat("$path.x")
        val y = objectValue.required("y", path).asFiniteFloat("$path.y")
        val width = objectValue.required("width", path).asFiniteFloat("$path.width")
        val height = objectValue.required("height", path).asFiniteFloat("$path.height")
        if (width <= 0f || height <= 0f) {
            fail("$path must have positive normalized dimensions.")
        }
        return NormalizedFrame(x, y, width, height)
    }

    private fun decodeShape(objectValue: JsonValue.Object, path: String): HoldShape = when (
        objectValue.requiredString("type", path)
    ) {
        "roundedRect" -> {
            val radius = objectValue.required("cornerRadiusFraction", path)
                .asFiniteFloat("$path.cornerRadiusFraction")
            if (radius < 0f || radius > 0.5f) fail("$path.cornerRadiusFraction must be within [0, 0.5].")
            HoldShape.RoundedRect(radius)
        }
        "path" -> {
            val commands = objectValue.required("commands", path)
                .asArray("$path.commands")
                .mapIndexed { index, value -> decodePathCommand(value.asObject("$path.commands[$index]"), "$path.commands[$index]") }
            if (commands.isEmpty() || commands.first() !is PathCommand.Move || commands.last() !is PathCommand.Close ||
                commands.dropLast(1).any { it is PathCommand.Close }
            ) {
                fail("$path.commands must begin with move and end with close.")
            }
            HoldShape.Path(commands)
        }
        else -> fail("$path.type is unsupported.")
    }

    private fun decodePathCommand(objectValue: JsonValue.Object, path: String): PathCommand = when (
        objectValue.requiredString("command", path)
    ) {
        "move" -> PathCommand.Move(decodePoint(objectValue.required("to", path), "$path.to"))
        "line" -> PathCommand.Line(decodePoint(objectValue.required("to", path), "$path.to"))
        "quad" -> PathCommand.Quad(
            to = decodePoint(objectValue.required("to", path), "$path.to"),
            control = decodePoint(objectValue.required("control", path), "$path.control"),
        )
        "curve" -> PathCommand.Curve(
            to = decodePoint(objectValue.required("to", path), "$path.to"),
            control1 = decodePoint(objectValue.required("control1", path), "$path.control1"),
            control2 = decodePoint(objectValue.required("control2", path), "$path.control2"),
        )
        "close" -> PathCommand.Close
        else -> fail("$path.command is unsupported.")
    }

    private fun decodePoint(value: JsonValue, path: String): Point {
        val values = value.asArray(path)
        if (values.size != 2) fail("$path must contain exactly two coordinates.")
        return Point(values[0].asFiniteFloat("$path[0]"), values[1].asFiniteFloat("$path[1]"))
    }

    private fun positiveFiniteFloat(value: JsonValue, path: String): Float =
        value.asFiniteFloat(path).also { if (it <= 0f) fail("$path must be positive.") }

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)

    private companion object {
        const val BOARDS_ROOT = "Hangboards"
    }
}
