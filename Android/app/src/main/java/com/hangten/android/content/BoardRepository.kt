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
        val unavailableBoardIds = mutableSetOf<String>()
        val boards = packages.mapNotNull { packageName ->
            val boardPath = "$BOARDS_ROOT/$packageName/board.json"
            val source = assets.read(boardPath) ?: fail("Missing board document $boardPath.")
            val board = decodeBoard(
                JsonParser(source).parse().asObject(boardPath),
                boardPath,
                packageName,
                unavailableBoardIds,
            ) ?: return@mapNotNull null
            if (!boardIds.add(board.id)) fail("Duplicate board ID \"${board.id}\".")
            board
        }
        val semanticHoldsByBoardId = decodeSemanticHoldsByBoardId(boards, unavailableBoardIds)
        boards.map { board -> board.copy(semanticHolds = semanticHoldsByBoardId[board.id].orEmpty()) }
    }

    private fun decodeBoard(
        objectValue: JsonValue.Object,
        path: String,
        packageName: String,
        unavailableBoardIds: MutableSet<String>,
    ): Board? = when (objectValue.optional("schemaVersion")) {
        null -> decodeSchemaV1Board(objectValue, path, packageName)
        else -> decodeSchemaV2Board(objectValue, path, packageName, unavailableBoardIds)
    }

    private fun decodeSchemaV1Board(
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

    private fun decodeSchemaV2Board(
        objectValue: JsonValue.Object,
        path: String,
        packageName: String,
        unavailableBoardIds: MutableSet<String>,
    ): Board? {
        val schemaVersion = (objectValue.required("schemaVersion", path) as? JsonValue.Number)?.value
            ?: fail("$path.schemaVersion must be a number.")
        if (schemaVersion != 2.0) fail("$path.schemaVersion is unsupported: $schemaVersion.")

        val boardId = objectValue.requiredString("id", path)
        val presentationObjects = objectValue.required("presentations", path)
            .asArray("$path.presentations")
            .mapIndexed { index, value ->
                value.asObject("$path.presentations[$index]")
            }
        if (presentationObjects.isEmpty()) fail("$path.presentations must not be empty.")
        val mediaTypes = presentationObjects.mapIndexed { index, presentation ->
            presentation.required("media", "$path.presentations[$index]")
                .asObject("$path.presentations[$index].media")
                .requiredString("type", "$path.presentations[$index].media")
        }
        if (mediaTypes.any { it == "model" }) {
            unavailableBoardIds += boardId
            return null
        }
        if (mediaTypes.any { it != "raster" }) fail("$path.presentations contains unsupported media.")

        val presentations = presentationObjects.mapIndexed { index, presentation ->
            decodeSchemaV2RasterPresentation(presentation, "$path.presentations[$index]")
        }
        if (presentations.count { it.isDefault } != 1) fail("$path.presentations must contain exactly one default presentation.")
        if (presentations.map { it.id }.toSet().size != presentations.size) fail("$path.presentations contains duplicate IDs.")
        presentations.forEach { presentation ->
            val assetPath = "$BOARDS_ROOT/$packageName/${presentation.assetPath}"
            if (!assets.exists(assetPath)) fail("Board $boardId is missing presentation asset ${presentation.assetPath}.")
        }

        val logicalHolds = objectValue.required("holds", path)
            .asArray("$path.holds")
            .mapIndexed { index, value -> decodeSchemaV2LogicalHold(value.asObject("$path.holds[$index]"), "$path.holds[$index]") }
        if (logicalHolds.isEmpty()) fail("$path.holds must not be empty.")
        if (logicalHolds.map { it.id }.toSet().size != logicalHolds.size) fail("$path.holds contains duplicate IDs.")

        val knownHoldIds = logicalHolds.mapTo(mutableSetOf()) { it.id }
        val geometryByHoldId = linkedMapOf<String, Pair<String, List<BoardGeometry>>>()
        presentationObjects.forEachIndexed { index, presentationObject ->
            val presentationPath = "$path.presentations[$index]"
            val derivation = presentationObject.required("derivation", presentationPath)
                .asObject("$presentationPath.derivation")
                .requiredString("type", "$presentationPath.derivation")
            if (derivation != "original") return@forEachIndexed
            val holdGeometry = presentationObject.required("media", presentationPath)
                .asObject("$presentationPath.media")
                .required("holdGeometry", "$presentationPath.media")
                .asObject("$presentationPath.media.holdGeometry")
                .fields
            holdGeometry.forEach { (holdId, value) ->
                if (holdId !in knownHoldIds) {
                    fail("$presentationPath.media.holdGeometry references unknown hold $holdId.")
                }
                val geometryPath = "$presentationPath.media.holdGeometry.$holdId"
                val geometry = value.asArray(geometryPath)
                    .mapIndexed { geometryIndex, geometryValue ->
                        decodeGeometry(
                            geometryValue.asObject("$geometryPath[$geometryIndex]"),
                            "$geometryPath[$geometryIndex]",
                        )
                    }
                if (geometry.isEmpty()) fail("$geometryPath must not be empty.")
                if (geometryByHoldId.put(holdId, presentations[index].id to geometry) != null) {
                    fail("$path.presentations assigns hold $holdId to multiple original raster presentations.")
                }
            }
        }
        val holds = logicalHolds.map { hold ->
            val (presentationId, geometry) = geometryByHoldId[hold.id]
                ?: fail("$path.presentations must assign hold ${hold.id} to one original raster presentation.")
            hold.copy(presentationId = presentationId, geometry = geometry)
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
        validateAssetPath(assetPath, "$path.assetPath")
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

    private fun decodeSchemaV2RasterPresentation(objectValue: JsonValue.Object, path: String): BoardPresentation {
        val media = objectValue.required("media", path).asObject("$path.media")
        val assetPath = media.requiredString("assetPath", "$path.media")
        validateAssetPath(assetPath, "$path.media.assetPath")
        val isDefault = (objectValue.required("isDefault", path) as? JsonValue.BooleanValue)?.value
            ?: fail("$path.isDefault must be a boolean.")
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
            features = decodeFeatures(objectValue.optional("features"), "$path.features"),
            fingerCapacity = objectValue.optional("fingerCapacity")?.asFingerCapacity("$path.fingerCapacity"),
            presentationId = objectValue.requiredString("presentationID", path),
            geometry = geometry,
        )
    }

    private fun decodeSchemaV2LogicalHold(objectValue: JsonValue.Object, path: String): BoardHold =
        BoardHold(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            kind = objectValue.requiredString("kind", path),
            features = decodeFeatures(objectValue.optional("features"), "$path.features"),
            fingerCapacity = objectValue.optional("fingerCapacity")?.asFingerCapacity("$path.fingerCapacity"),
            presentationId = "",
            geometry = emptyList(),
        )

    private fun decodeFeatures(value: JsonValue?, path: String): Set<String> {
        val features = value?.asArray(path)?.mapIndexed { index, feature ->
            feature.asString("$path[$index]").also { requireContentId(it, "$path[$index]") }
        } ?: emptyList()
        if (features.toSet().size != features.size) fail("$path must not contain duplicates.")
        return features.toSet()
    }

    private fun decodeSemanticHoldsByBoardId(
        boards: List<Board>,
        unavailableBoardIds: Set<String>,
    ): Map<String, Map<String, SemanticHoldMapping>> {
        val source = assets.read(PLAN_LIBRARY_PATH) ?: return emptyMap()
        val root = JsonParser(source).parse().asObject(PLAN_LIBRARY_PATH)
        val mappings = root.optional("boardMappings")?.asArray("$PLAN_LIBRARY_PATH.boardMappings") ?: return emptyMap()
        val boardsById = boards.associateBy { it.id }
        val result = linkedMapOf<String, Map<String, SemanticHoldMapping>>()
        mappings.forEachIndexed { index, value ->
            val mappingPath = "$PLAN_LIBRARY_PATH.boardMappings[$index]"
            val objectValue = value.asObject(mappingPath)
            val boardId = objectValue.requiredString("boardID", mappingPath)
            if (boardId in unavailableBoardIds && boardId !in boardsById) return@forEachIndexed
            val board = boardsById[boardId] ?: fail("$mappingPath references unknown board $boardId.")
            if (result.containsKey(boardId)) fail("$PLAN_LIBRARY_PATH.boardMappings contains duplicate board ID $boardId.")
            val semanticHolds = objectValue.required("semanticHolds", mappingPath)
                .asObject("$mappingPath.semanticHolds")
                .fields
                .mapValues { (semanticId, semanticValue) ->
                    requireContentId(semanticId, "$mappingPath.semanticHolds")
                    decodeSemanticHoldMapping(
                        semanticValue.asObject("$mappingPath.semanticHolds.$semanticId"),
                        "$mappingPath.semanticHolds.$semanticId",
                        board,
                    )
                }
            result[boardId] = semanticHolds
        }
        return result
    }

    private fun decodeSemanticHoldMapping(
        objectValue: JsonValue.Object,
        path: String,
        board: Board,
    ): SemanticHoldMapping {
        val holdIds = objectValue.optional("holdIDs")?.asArray("$path.holdIDs")?.mapIndexed { index, value ->
            value.asString("$path.holdIDs[$index]").also { requireContentId(it, "$path.holdIDs[$index]") }
        } ?: emptyList()
        val kind = objectValue.optional("kind")?.asString("$path.kind")
        if (holdIds.isEmpty() == (kind == null)) fail("$path must contain exactly one of holdIDs or kind.")
        if (holdIds.toSet().size != holdIds.size) fail("$path.holdIDs must not contain duplicates.")
        val knownHoldIds = board.holds.mapTo(mutableSetOf()) { it.id }
        holdIds.firstOrNull { it !in knownHoldIds }?.let { fail("$path references unknown hold $it.") }
        return SemanticHoldMapping(holdIds = holdIds, kind = kind)
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

    private fun JsonValue.asFingerCapacity(path: String): Int {
        val value = (this as? JsonValue.Number)?.value ?: fail("$path must be a number.")
        if (!value.isFinite() || value != value.toInt().toDouble() || value.toInt() !in FINGER_CAPACITY_RANGE) {
            fail("$path must be an integer within $FINGER_CAPACITY_RANGE.")
        }
        return value.toInt()
    }

    private fun validateAssetPath(assetPath: String, path: String) {
        if (!assetPath.startsWith("assets/") || assetPath.split('/').any { it == ".." || it.isBlank() }) {
            fail("$path must be a relative assets path.")
        }
    }

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)

    private companion object {
        const val BOARDS_ROOT = "Hangboards"
        const val PLAN_LIBRARY_PATH = "PlanLibrary.json"
        val FINGER_CAPACITY_RANGE = 1..4
    }
}
