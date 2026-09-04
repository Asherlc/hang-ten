package com.hangten.android.content

import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

interface ContentAssets {
    fun list(path: String): List<String>?
    fun read(path: String): String?
    fun exists(path: String): Boolean
    fun imageDimensions(path: String): ContentImageDimensions?
}

data class ContentImageDimensions(val width: Int, val height: Int)

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
        val boards = packages.map { packageName ->
            val boardPath = "$BOARDS_ROOT/$packageName/board.json"
            val source = assets.read(boardPath) ?: fail("Missing board document $boardPath.")
            val board = decodeBoard(JsonParser(source).parse().asObject(boardPath), boardPath, packageName)
            if (!boardIds.add(board.id)) fail("Duplicate board ID \"${board.id}\".")
            board
        }
        val semanticHoldsByBoardId = decodeSemanticHoldsByBoardId(boards)
        boards.map { board -> board.copy(semanticHolds = semanticHoldsByBoardId[board.id].orEmpty()) }
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
        val presentationsById = presentations.associateBy { it.id }
        presentations.forEach { presentation ->
            val assetPath = "$BOARDS_ROOT/$packageName/${presentation.assetPath}"
            if (!assets.exists(assetPath)) fail("Board $boardId is missing presentation asset ${presentation.assetPath}.")
            if (presentation.cordRig != null &&
                (presentation.sourcePresentationId != null || presentation.resolvedRotationDegrees != 0f)
            ) {
                fail("Board $boardId presentation ${presentation.id}.cordRig must be owned by a canonical non-inverted presentation.")
            }
            presentation.geometryRotationAnchor?.let { anchor ->
                if (anchor.x !in 0f..1f || anchor.y !in 0f..1f) {
                    fail("Board $boardId presentation ${presentation.id}.geometryRotationAnchor must contain normalized coordinates.")
                }
                if (presentation.sourcePresentationId == null || presentation.resolvedRotationDegrees == 0f) {
                    fail("Board $boardId presentation ${presentation.id}.geometryRotationAnchor requires an inverted or explicitly rotated alias.")
                }
            }
            if (presentation.rotationDegrees != null && presentation.sourcePresentationId == null) {
                fail("Board $boardId presentation ${presentation.id}.rotationDegrees requires sourcePresentationID.")
            }
            presentation.sourcePresentationId?.let { sourceId ->
                val source = presentationsById[sourceId]
                if (sourceId == presentation.id || source == null || source.sourcePresentationId != null) {
                    fail("Board $boardId presentation ${presentation.id} must reference a canonical presentation.")
                }
                if (!aspectRatiosMatch(presentation.aspectRatio, source.aspectRatio, ALIAS_ASPECT_RATIO_TOLERANCE)) {
                    fail("Board $boardId presentation ${presentation.id}.aspectRatio must match its source presentation.")
                }
                presentation.rotationDegrees?.let { rotationDegrees ->
                    if (presentation.assetPath != source.assetPath) {
                        fail(
                            "Board $boardId presentation ${presentation.id}.assetPath must reuse " +
                                "source presentation assetPath for an explicit rotation.",
                        )
                    }
                    if (rotationDegrees != 0f && rotationDegrees != 180f && source.cordRig == null) {
                        fail(
                            "Board $boardId presentation ${presentation.id} non-180 rotation requires " +
                                "a canonical cordRig to prevent artwork clipping.",
                        )
                    }
                }
            }
            val artworkPresentation = presentation.sourcePresentationId
                ?.let { presentationsById[it] }
                ?: presentation
            (artworkPresentation.cordRig as? BoardCordRig.DirectTwoAnchor)?.let { rig ->
                validateDirectTwoAnchorCordPresentation(
                    boardId = boardId,
                    presentation = presentation,
                    rig = rig,
                )
            }
        }
        validateCordRigImageAspects(boardId, packageName, presentations, presentationsById)

        val holds = objectValue.required("holds", path)
            .asArray("$path.holds")
            .mapIndexed { index, value -> decodeHold(value.asObject("$path.holds[$index]"), "$path.holds[$index]") }
        if (holds.isEmpty()) fail("$path.holds must not be empty.")
        if (holds.map { it.id }.toSet().size != holds.size) fail("$path.holds contains duplicate IDs.")
        val presentationIds = presentations.map { it.id }.toSet()
        val canonicalPresentationIds = presentations
            .filter { it.sourcePresentationId == null }
            .mapTo(mutableSetOf()) { it.id }
        holds.forEach { hold ->
            if (hold.presentationId !in presentationIds) {
                fail("Board $boardId hold ${hold.id} references missing presentation ${hold.presentationId}.")
            }
            if (hold.presentationId !in canonicalPresentationIds) {
                fail("Board $boardId hold ${hold.id} must be owned by a canonical presentation.")
            }
        }
        val holdsById = holds.associateBy { it.id }
        presentations.forEach { presentation ->
            val availableHoldIds = presentation.availableHoldIds ?: return@forEach
            val canonicalPresentationId = presentation.sourcePresentationId ?: presentation.id
            availableHoldIds.forEach { holdId ->
                val hold = holdsById[holdId]
                    ?: fail("Board $boardId presentation ${presentation.id}.availableHoldIDs references unknown hold $holdId.")
                if (hold.presentationId != canonicalPresentationId) {
                    fail(
                        "Board $boardId presentation ${presentation.id}.availableHoldIDs hold $holdId " +
                            "must belong to canonical presentation $canonicalPresentationId.",
                    )
                }
            }
        }
        validateAliasProjections(boardId, presentations, holds)

        return Board(
            id = boardId,
            manufacturer = objectValue.requiredString("manufacturer", path),
            name = objectValue.requiredString("name", path),
            subtitle = objectValue.requiredString("subtitle", path),
            productUrl = objectValue.requiredString("productURL", path),
            aspectRatio = positiveFiniteFloat(objectValue.required("aspectRatio", path), "$path.aspectRatio"),
            presentations = presentations,
            holds = holds,
            packageName = packageName,
        )
    }

    private fun validateCordRigImageAspects(
        boardId: String,
        packageName: String,
        presentations: List<BoardPresentation>,
        presentationsById: Map<String, BoardPresentation>,
    ) {
        val dimensionsByAssetPath = mutableMapOf<String, ContentImageDimensions>()
        presentations.forEach { presentation ->
            val canonical = presentation.sourcePresentationId
                ?.let(presentationsById::get)
                ?: presentation
            val rig = canonical.cordRig ?: return@forEach
            val assetPath = "$BOARDS_ROOT/$packageName/${presentation.assetPath}"
            val dimensions = dimensionsByAssetPath[assetPath] ?: assets.imageDimensions(assetPath)
            if (dimensions == null || dimensions.width <= 0 || dimensions.height <= 0) {
                fail(
                    "Board $boardId presentation ${presentation.id} asset ${presentation.assetPath} " +
                        "must be a decodable PNG.",
                )
            }
            dimensionsByAssetPath[assetPath] = dimensions
            val expectedAspectRatio = rig.innerFaceFrame.width / rig.innerFaceFrame.height
            val imageAspectRatio = dimensions.width.toFloat() / dimensions.height.toFloat()
            if (!aspectRatiosMatch(
                    expectedAspectRatio,
                    imageAspectRatio,
                    PRESENTATION_ASPECT_RATIO_TOLERANCE,
                )
            ) {
                fail(
                    "Board $boardId presentation ${canonical.id}.cordRig.innerFaceFrame aspect ratio " +
                        "must match presentation image width/height within 0.1%.",
                )
            }
        }
    }

    private fun validateAliasProjections(
        boardId: String,
        presentations: List<BoardPresentation>,
        holds: List<BoardHold>,
    ) {
        val presentationsById = presentations.associateBy { it.id }
        presentations.filter { it.resolvedRotationDegrees != 0f }.forEach { presentation ->
            val sourcePresentationId = presentation.sourcePresentationId ?: return@forEach
            val sourcePresentation = presentationsById[sourcePresentationId] ?: return@forEach
            val anchor = presentation.geometryRotationAnchor ?: BoardGeometryRotationAnchor.Center
            val rotationRadians = Math.toRadians(presentation.resolvedRotationDegrees.toDouble())
            val cosine = cos(rotationRadians)
            val sine = sin(rotationRadians)
            val rig = sourcePresentation.cordRig

            val canvasWidth = rig?.sceneSize?.width?.toDouble() ?: 1.0
            val canvasHeight = rig?.sceneSize?.height?.toDouble() ?: 1.0
            val anchorX = canvasWidth * anchor.x.toDouble()
            val anchorY = canvasHeight * anchor.y.toDouble()
            val faceX = rig?.let { it.sourceFrame.x + it.innerFaceFrame.x }?.toDouble() ?: 0.0
            val faceY = rig?.let { it.sourceFrame.y + it.innerFaceFrame.y }?.toDouble() ?: 0.0
            val faceWidth = rig?.innerFaceFrame?.width?.toDouble() ?: 1.0
            val faceHeight = rig?.innerFaceFrame?.height?.toDouble() ?: 1.0
            val tolerance = max(canvasWidth, canvasHeight) * 1e-6

            val availableHoldIds = presentation.availableHoldIds?.toSet()
            holds.filter {
                it.presentationId == sourcePresentationId &&
                    (availableHoldIds == null || it.id in availableHoldIds)
            }.forEach { hold ->
                hold.geometry.forEach { geometry ->
                    val frame = geometry.frame
                    val corners = listOf(
                        Point(frame.x, frame.y),
                        Point(frame.x + frame.width, frame.y),
                        Point(frame.x, frame.y + frame.height),
                        Point(frame.x + frame.width, frame.y + frame.height),
                    )
                    val isInside = corners.all { point ->
                        val sourceX = faceX + faceWidth * point.x.toDouble()
                        val sourceY = faceY + faceHeight * point.y.toDouble()
                        val deltaX = sourceX - anchorX
                        val deltaY = sourceY - anchorY
                        val projectedX = anchorX + cosine * deltaX - sine * deltaY
                        val projectedY = anchorY + sine * deltaX + cosine * deltaY
                        projectedX >= -tolerance && projectedY >= -tolerance &&
                            projectedX <= canvasWidth + tolerance &&
                            projectedY <= canvasHeight + tolerance
                    }
                    if (!isInside) {
                        fail(
                            "Board $boardId presentation ${presentation.id} projects source " +
                                "hold geometry outside the normalized canvas.",
                        )
                    }
                }
            }
        }
    }

    private fun validateDirectTwoAnchorCordPresentation(
        boardId: String,
        presentation: BoardPresentation,
        rig: BoardCordRig.DirectTwoAnchor,
    ) {
        val sceneWidth = rig.sceneSize.width.toDouble()
        val sceneHeight = rig.sceneSize.height.toDouble()
        val sourceX = rig.sourceFrame.x.toDouble()
        val sourceY = rig.sourceFrame.y.toDouble()
        val pullX = sourceX + rig.pullPoint.x.toDouble()
        val pullY = sourceY + rig.pullPoint.y.toDouble()
        val rotationAnchor = presentation.geometryRotationAnchor ?: BoardGeometryRotationAnchor.Center
        val anchorX = rotationAnchor.x.toDouble() * sceneWidth
        val anchorY = rotationAnchor.y.toDouble() * sceneHeight
        val rotationRadians = Math.toRadians(presentation.resolvedRotationDegrees.toDouble())
        val cosine = cos(rotationRadians)
        val sine = sin(rotationRadians)
        val attachments = rig.attachmentPoints.map { point ->
            val pointX = sourceX + point.x.toDouble()
            val pointY = sourceY + point.y.toDouble()
            val deltaX = pointX - anchorX
            val deltaY = pointY - anchorY
            PointD(
                x = anchorX + cosine * deltaX - sine * deltaY,
                y = anchorY + sine * deltaX + cosine * deltaY,
            )
        }
        val centerlineX = listOf(
            pullX + CORD_SUPPORT_MIN_X_OFFSET,
            pullX + CORD_SUPPORT_MAX_X_OFFSET,
            pullX - CORD_PULL_EXIT_HALF_SPACING,
            pullX + CORD_PULL_EXIT_HALF_SPACING,
        ) + attachments.map { it.x }
        val centerlineY = listOf(
            pullY + CORD_SUPPORT_MIN_Y_OFFSET,
            pullY + CORD_SUPPORT_MAX_Y_OFFSET,
        ) + attachments.map { it.y }
        val tolerance = max(sceneWidth, sceneHeight) * 1e-9
        if (
            centerlineX.minOrNull()!! - CORD_SHADOW_X_MARGIN < -tolerance ||
            centerlineX.maxOrNull()!! + CORD_SHADOW_X_MARGIN > sceneWidth + tolerance ||
            centerlineY.minOrNull()!! - CORD_SHADOW_Y_MARGIN < -tolerance ||
            centerlineY.maxOrNull()!! + CORD_SHADOW_Y_MARGIN > sceneHeight + tolerance
        ) {
            fail("Board $boardId presentation ${presentation.id} cord drawing must remain inside sceneSize.")
        }
        if (attachments.any { it.y <= pullY + tolerance }) {
            fail(
                "Board $boardId presentation ${presentation.id} cord pull exits must remain " +
                    "above both attachment points.",
            )
        }
    }

    private fun decodePresentation(objectValue: JsonValue.Object, path: String): BoardPresentation {
        objectValue.rejectUnknownKeys(
            setOf(
                "id",
                "name",
                "assetPath",
                "aspectRatio",
                "default",
                "sourcePresentationID",
                "availableHoldIDs",
                "isInverted",
                "rotationDegrees",
                "geometryRotationAnchor",
                "cordRig",
            ),
            path,
        )
        val assetPath = objectValue.requiredString("assetPath", path)
        if (!assetPath.startsWith("assets/") || assetPath.split('/').any { it == ".." || it.isBlank() }) {
            fail("$path.assetPath must be a relative assets path.")
        }
        val isDefault = (objectValue.required("default", path) as? JsonValue.BooleanValue)?.value
            ?: fail("$path.default must be a boolean.")
        val aspectRatio = positiveFiniteFloat(objectValue.required("aspectRatio", path), "$path.aspectRatio")
        val sourcePresentationId = objectValue.optional("sourcePresentationID")?.asString("$path.sourcePresentationID")
            ?.also { requireContentId(it, "$path.sourcePresentationID") }
        val availableHoldIds = objectValue.optional("availableHoldIDs")?.asArray("$path.availableHoldIDs")
            ?.mapIndexed { index, value ->
                value.asString("$path.availableHoldIDs[$index]")
                    .also { requireContentId(it, "$path.availableHoldIDs[$index]") }
            }
            ?.also { values ->
                if (values.isEmpty()) fail("$path.availableHoldIDs must not be empty.")
                if (values.toSet().size != values.size) fail("$path.availableHoldIDs must be unique.")
            }
        val isInverted = objectValue.optional("isInverted")?.let {
            (it as? JsonValue.BooleanValue)?.value ?: fail("$path.isInverted must be a boolean.")
        } ?: false
        if (objectValue.optional("isInverted") != null && objectValue.optional("rotationDegrees") != null) {
            fail("$path must not declare both isInverted and rotationDegrees.")
        }
        val rotationDegrees = objectValue.optional("rotationDegrees")?.asFiniteFloat("$path.rotationDegrees")
        if (rotationDegrees != null && rotationDegrees !in 0f..<360f) {
            fail("$path.rotationDegrees must be normalized to [0, 360).")
        }
        val geometryRotationAnchor = objectValue.optional("geometryRotationAnchor")?.let {
            decodeRotationAnchor(it.asObject("$path.geometryRotationAnchor"), "$path.geometryRotationAnchor")
        }
        val cordRig = objectValue.optional("cordRig")?.let {
            decodeCordRig(it.asObject("$path.cordRig"), "$path.cordRig")
        }
        if (cordRig != null && !aspectRatiosMatch(
                aspectRatio,
                cordRig.sceneSize.width / cordRig.sceneSize.height,
                PRESENTATION_ASPECT_RATIO_TOLERANCE,
            )
        ) {
            fail("$path.aspectRatio must match cordRig.sceneSize within 0.1%.")
        }
        return BoardPresentation(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            assetPath = assetPath,
            aspectRatio = aspectRatio,
            isDefault = isDefault,
            sourcePresentationId = sourcePresentationId,
            isInverted = isInverted,
            rotationDegrees = rotationDegrees,
            geometryRotationAnchor = geometryRotationAnchor,
            cordRig = cordRig,
            availableHoldIds = availableHoldIds,
        )
    }

    private fun decodeRotationAnchor(objectValue: JsonValue.Object, path: String): BoardGeometryRotationAnchor {
        objectValue.rejectUnknownKeys(setOf("x", "y"), path)
        return BoardGeometryRotationAnchor(
            x = objectValue.required("x", path).asFiniteFloat("$path.x"),
            y = objectValue.required("y", path).asFiniteFloat("$path.y"),
        )
    }

    private fun decodeCordRig(objectValue: JsonValue.Object, path: String): BoardCordRig {
        return when (objectValue.requiredString("type", path)) {
            "directTwoAnchor" -> decodeDirectTwoAnchorCordRig(objectValue, path)
            "routed" -> decodeRoutedCordRig(objectValue, path)
            else -> fail("$path.type is unsupported.")
        }
    }

    private fun decodeDirectTwoAnchorCordRig(
        objectValue: JsonValue.Object,
        path: String,
    ): BoardCordRig.DirectTwoAnchor {
        objectValue.rejectUnknownKeys(
            setOf(
                "type",
                "sceneSize",
                "sourceFrame",
                "innerFaceFrame",
                "attachmentPoints",
                "pullPoint",
                "eyeletRadius",
            ),
            path,
        )
        val sceneSizeObject = objectValue.required("sceneSize", path).asObject("$path.sceneSize")
        val sourceFrameObject = objectValue.required("sourceFrame", path).asObject("$path.sourceFrame")
        val innerFaceFrameObject = objectValue.required("innerFaceFrame", path).asObject("$path.innerFaceFrame")
        sceneSizeObject.rejectUnknownKeys(setOf("width", "height"), "$path.sceneSize")
        val attachmentPoints = objectValue.required("attachmentPoints", path)
            .asArray("$path.attachmentPoints")
            .mapIndexed { index, value ->
                decodeCordPoint(value.asObject("$path.attachmentPoints[$index]"), "$path.attachmentPoints[$index]")
            }
        val rig = BoardCordRig.DirectTwoAnchor(
            sceneSize = BoardCordSize(
                width = positiveFiniteFloat(sceneSizeObject.required("width", "$path.sceneSize"), "$path.sceneSize.width"),
                height = positiveFiniteFloat(sceneSizeObject.required("height", "$path.sceneSize"), "$path.sceneSize.height"),
            ),
            sourceFrame = decodeCordRect(sourceFrameObject, "$path.sourceFrame"),
            innerFaceFrame = decodeCordRect(innerFaceFrameObject, "$path.innerFaceFrame"),
            attachmentPoints = attachmentPoints,
            pullPoint = decodeCordPoint(
                objectValue.required("pullPoint", path).asObject("$path.pullPoint"),
                "$path.pullPoint",
            ),
            eyeletRadius = positiveFiniteFloat(objectValue.required("eyeletRadius", path), "$path.eyeletRadius"),
        )
        if (rig.attachmentPoints.size != 2 || rig.attachmentPoints[0] == rig.attachmentPoints[1]) {
            fail("$path.attachmentPoints must contain two distinct finite points.")
        }
        return rig
    }

    private fun decodeRoutedCordRig(
        objectValue: JsonValue.Object,
        path: String,
    ): BoardCordRig.Routed {
        objectValue.rejectUnknownKeys(
            setOf(
                "type",
                "sceneSize",
                "sourceFrame",
                "innerFaceFrame",
                "style",
                "ports",
                "tensionGroups",
                "paths",
                "occlusions",
            ),
            path,
        )
        val sceneSizeObject = objectValue.required("sceneSize", path).asObject("$path.sceneSize")
        sceneSizeObject.rejectUnknownKeys(setOf("width", "height"), "$path.sceneSize")
        val sceneSize = BoardCordSize(
            width = positiveFiniteFloat(sceneSizeObject.required("width", "$path.sceneSize"), "$path.sceneSize.width"),
            height = positiveFiniteFloat(sceneSizeObject.required("height", "$path.sceneSize"), "$path.sceneSize.height"),
        )
        val sourceFrame = decodeCordRect(
            objectValue.required("sourceFrame", path).asObject("$path.sourceFrame"),
            "$path.sourceFrame",
        )
        val innerFaceFrame = decodeCordRect(
            objectValue.required("innerFaceFrame", path).asObject("$path.innerFaceFrame"),
            "$path.innerFaceFrame",
        )

        val stylePath = "$path.style"
        val styleObject = objectValue.required("style", path).asObject(stylePath)
        styleObject.rejectUnknownKeys(setOf("diameter", "outlineColor", "baseColor", "braidColors"), stylePath)
        val braidColors = styleObject.required("braidColors", stylePath)
            .asArray("$stylePath.braidColors")
            .mapIndexed { index, value -> decodeRoutedColor(value, "$stylePath.braidColors[$index]") }
        if (braidColors.size != 2) fail("$stylePath.braidColors must contain exactly two colors.")
        val style = BoardRoutedCordStyle(
            diameter = positiveFiniteFloat(styleObject.required("diameter", stylePath), "$stylePath.diameter"),
            outlineColor = decodeRoutedColor(styleObject.required("outlineColor", stylePath), "$stylePath.outlineColor"),
            baseColor = decodeRoutedColor(styleObject.required("baseColor", stylePath), "$stylePath.baseColor"),
            braidColors = braidColors,
        )

        val portsPath = "$path.ports"
        val ports = objectValue.required("ports", path).asArray(portsPath).mapIndexed { index, value ->
            val portPath = "$portsPath[$index]"
            val portObject = value.asObject(portPath)
            portObject.rejectUnknownKeys(setOf("id", "space", "point"), portPath)
            BoardRoutedCordPort(
                id = decodeRoutedIdentifier(portObject.required("id", portPath), "$portPath.id"),
                space = decodeRoutedSpace(portObject.required("space", portPath), "$portPath.space"),
                point = decodeCordPoint(
                    portObject.required("point", portPath).asObject("$portPath.point"),
                    "$portPath.point",
                ),
            )
        }
        if (ports.isEmpty()) fail("$portsPath must be a non-empty array.")
        if (ports.map { it.id }.toSet().size != ports.size) fail("$portsPath must have unique IDs.")
        val portsById = ports.associateBy { it.id }

        val groupsPath = "$path.tensionGroups"
        val tensionGroups = objectValue.required("tensionGroups", path)
            .asArray(groupsPath)
            .mapIndexed { index, value ->
                val groupPath = "$groupsPath[$index]"
                val groupObject = value.asObject(groupPath)
                groupObject.rejectUnknownKeys(
                    setOf("id", "bodyPortIDs", "worldPortIDs", "pairing", "layer"),
                    groupPath,
                )
                val bodyPortIds = decodeRoutedIdArray(
                    groupObject.required("bodyPortIDs", groupPath),
                    "$groupPath.bodyPortIDs",
                )
                val worldPortIds = decodeRoutedIdArray(
                    groupObject.required("worldPortIDs", groupPath),
                    "$groupPath.worldPortIDs",
                )
                if (bodyPortIds.size != worldPortIds.size) {
                    fail("$groupPath port lists must have equal cardinality.")
                }
                if (bodyPortIds.any { portsById[it]?.space != BoardRoutedCordSpace.Body }) {
                    fail("$groupPath.bodyPortIDs must reference body ports.")
                }
                if (worldPortIds.any { portsById[it]?.space != BoardRoutedCordSpace.World }) {
                    fail("$groupPath.worldPortIDs must reference world ports.")
                }
                BoardRoutedCordTensionGroup(
                    id = decodeRoutedIdentifier(groupObject.required("id", groupPath), "$groupPath.id"),
                    bodyPortIds = bodyPortIds,
                    worldPortIds = worldPortIds,
                    pairing = decodeRoutedPairing(groupObject.required("pairing", groupPath), "$groupPath.pairing"),
                    layer = decodeRoutedLayer(groupObject.required("layer", groupPath), "$groupPath.layer"),
                )
            }
        if (tensionGroups.isEmpty()) fail("$groupsPath must be a non-empty array.")
        if (tensionGroups.map { it.id }.toSet().size != tensionGroups.size) {
            fail("$groupsPath must have unique IDs.")
        }

        val pathsPath = "$path.paths"
        val paths = objectValue.required("paths", path).asArray(pathsPath).mapIndexed { index, value ->
            val routedPath = "$pathsPath[$index]"
            val pathObject = value.asObject(routedPath)
            pathObject.rejectUnknownKeys(setOf("id", "space", "layer", "commands"), routedPath)
            BoardRoutedCordPath(
                id = decodeRoutedIdentifier(pathObject.required("id", routedPath), "$routedPath.id"),
                space = decodeRoutedSpace(pathObject.required("space", routedPath), "$routedPath.space"),
                layer = decodeRoutedLayer(pathObject.required("layer", routedPath), "$routedPath.layer"),
                commands = decodeRoutedCommands(
                    pathObject.required("commands", routedPath),
                    "$routedPath.commands",
                    requireClosed = false,
                ),
            )
        }
        if (paths.map { it.id }.toSet().size != paths.size) fail("$pathsPath must have unique IDs.")

        val occlusionsPath = "$path.occlusions"
        val occlusions = objectValue.required("occlusions", path)
            .asArray(occlusionsPath)
            .mapIndexed { index, value ->
                val occlusionPath = "$occlusionsPath[$index]"
                val occlusionObject = value.asObject(occlusionPath)
                when (occlusionObject.requiredString("type", occlusionPath)) {
                    "radialLip" -> {
                        occlusionObject.rejectUnknownKeys(
                            setOf("type", "bodyPortID", "radius", "chordOffset"),
                            occlusionPath,
                        )
                        val bodyPortId = decodeRoutedIdentifier(
                            occlusionObject.required("bodyPortID", occlusionPath),
                            "$occlusionPath.bodyPortID",
                        )
                        if (portsById[bodyPortId]?.space != BoardRoutedCordSpace.Body) {
                            fail("$occlusionPath radialLip must reference a body port.")
                        }
                        val radius = positiveFiniteFloat(
                            occlusionObject.required("radius", occlusionPath),
                            "$occlusionPath.radius",
                        )
                        val chordOffset = positiveFiniteFloat(
                            occlusionObject.required("chordOffset", occlusionPath),
                            "$occlusionPath.chordOffset",
                        )
                        if (chordOffset >= radius) {
                            fail("$occlusionPath must satisfy 0 < chordOffset < radius.")
                        }
                        BoardRoutedCordOcclusion.RadialLip(bodyPortId, radius, chordOffset)
                    }
                    "facePatch" -> {
                        occlusionObject.rejectUnknownKeys(setOf("type", "commands"), occlusionPath)
                        BoardRoutedCordOcclusion.FacePatch(
                            decodeRoutedCommands(
                                occlusionObject.required("commands", occlusionPath),
                                "$occlusionPath facePatch commands",
                                requireClosed = true,
                            ),
                        )
                    }
                    else -> fail("$occlusionPath.type is unsupported.")
                }
            }
        occlusions.filterIsInstance<BoardRoutedCordOcclusion.RadialLip>().forEachIndexed { index, lip ->
            val incidentSpanCount = tensionGroups.sumOf { group ->
                group.bodyPortIds.count { it == lip.bodyPortId }
            }
            if (incidentSpanCount != 1) {
                fail("$occlusionsPath[$index] radialLip body port must have exactly one incident tension-group span.")
            }
        }

        return BoardCordRig.Routed(
            sceneSize = sceneSize,
            sourceFrame = sourceFrame,
            innerFaceFrame = innerFaceFrame,
            style = style,
            ports = ports,
            tensionGroups = tensionGroups,
            paths = paths,
            occlusions = occlusions,
        )
    }

    private fun decodeRoutedCommands(
        value: JsonValue,
        path: String,
        requireClosed: Boolean,
    ): List<BoardRoutedCordPathCommand> {
        val commands = value.asArray(path).mapIndexed { index, commandValue ->
            val commandPath = "$path[$index]"
            val commandObject = commandValue.asObject(commandPath)
            when (commandObject.requiredString("command", commandPath)) {
                "move" -> {
                    commandObject.rejectUnknownKeys(setOf("command", "to"), commandPath)
                    BoardRoutedCordPathCommand.Move(
                        decodePoint(commandObject.required("to", commandPath), "$commandPath.to"),
                    )
                }
                "line" -> {
                    commandObject.rejectUnknownKeys(setOf("command", "to"), commandPath)
                    BoardRoutedCordPathCommand.Line(
                        decodePoint(commandObject.required("to", commandPath), "$commandPath.to"),
                    )
                }
                "quad" -> {
                    commandObject.rejectUnknownKeys(setOf("command", "control", "to"), commandPath)
                    BoardRoutedCordPathCommand.Quad(
                        control = decodePoint(
                            commandObject.required("control", commandPath),
                            "$commandPath.control",
                        ),
                        to = decodePoint(commandObject.required("to", commandPath), "$commandPath.to"),
                    )
                }
                "curve" -> {
                    commandObject.rejectUnknownKeys(
                        setOf("command", "control1", "control2", "to"),
                        commandPath,
                    )
                    BoardRoutedCordPathCommand.Curve(
                        control1 = decodePoint(
                            commandObject.required("control1", commandPath),
                            "$commandPath.control1",
                        ),
                        control2 = decodePoint(
                            commandObject.required("control2", commandPath),
                            "$commandPath.control2",
                        ),
                        to = decodePoint(commandObject.required("to", commandPath), "$commandPath.to"),
                    )
                }
                "close" -> {
                    commandObject.rejectUnknownKeys(setOf("command"), commandPath)
                    BoardRoutedCordPathCommand.Close
                }
                else -> fail("$commandPath.command is unsupported.")
            }
        }
        if (commands.firstOrNull() !is BoardRoutedCordPathCommand.Move ||
            commands.count { it is BoardRoutedCordPathCommand.Move } != 1
        ) {
            fail("$path must begin with exactly one move command.")
        }
        if (commands.none {
                it is BoardRoutedCordPathCommand.Line ||
                    it is BoardRoutedCordPathCommand.Quad ||
                    it is BoardRoutedCordPathCommand.Curve
            }
        ) {
            fail("$path must contain at least one line, quad, or curve.")
        }
        val closeIndexes = commands.indices.filter { commands[it] is BoardRoutedCordPathCommand.Close }
        if (closeIndexes.isNotEmpty() && closeIndexes != listOf(commands.lastIndex)) {
            fail("$path close command must appear only at the end.")
        }
        if (requireClosed && commands.lastOrNull() !is BoardRoutedCordPathCommand.Close) {
            fail("$path must be closed.")
        }
        return commands
    }

    private fun decodeRoutedIdentifier(value: JsonValue, path: String): String {
        val identifier = value.asString(path)
        if (!ROUTED_IDENTIFIER.matches(identifier)) fail("$path must be identifier-shaped.")
        return identifier
    }

    private fun decodeRoutedIdArray(value: JsonValue, path: String): List<String> {
        val ids = value.asArray(path).mapIndexed { index, item ->
            decodeRoutedIdentifier(item, "$path[$index]")
        }
        if (ids.isEmpty()) fail("$path must be a non-empty array.")
        if (ids.toSet().size != ids.size) fail("$path must be unique.")
        return ids
    }

    private fun decodeRoutedColor(value: JsonValue, path: String): String =
        value.asString(path).also { color ->
            if (!ROUTED_COLOR.matches(color)) fail("$path must be a #RRGGBB color.")
        }

    private fun decodeRoutedSpace(value: JsonValue, path: String): BoardRoutedCordSpace =
        when (value.asString(path)) {
            "body" -> BoardRoutedCordSpace.Body
            "world" -> BoardRoutedCordSpace.World
            else -> fail("$path space is unsupported.")
        }

    private fun decodeRoutedLayer(value: JsonValue, path: String): BoardRoutedCordLayer =
        when (value.asString(path)) {
            "behindFace" -> BoardRoutedCordLayer.BehindFace
            "aboveFace" -> BoardRoutedCordLayer.AboveFace
            "overpass" -> BoardRoutedCordLayer.Overpass
            else -> fail("$path layer is unsupported.")
        }

    private fun decodeRoutedPairing(value: JsonValue, path: String): BoardRoutedCordPairing =
        when (value.asString(path)) {
            "declared" -> BoardRoutedCordPairing.Declared
            "screenOrder" -> BoardRoutedCordPairing.ScreenOrder
            else -> fail("$path pairing is unsupported.")
        }

    private fun decodeCordRect(objectValue: JsonValue.Object, path: String): BoardCordRect {
        objectValue.rejectUnknownKeys(setOf("x", "y", "width", "height"), path)
        return BoardCordRect(
            x = objectValue.required("x", path).asFiniteFloat("$path.x"),
            y = objectValue.required("y", path).asFiniteFloat("$path.y"),
            width = positiveFiniteFloat(objectValue.required("width", path), "$path.width"),
            height = positiveFiniteFloat(objectValue.required("height", path), "$path.height"),
        )
    }

    private fun decodeCordPoint(objectValue: JsonValue.Object, path: String): Point {
        objectValue.rejectUnknownKeys(setOf("x", "y"), path)
        return Point(
            x = objectValue.required("x", path).asFiniteFloat("$path.x"),
            y = objectValue.required("y", path).asFiniteFloat("$path.y"),
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

    private fun decodeFeatures(value: JsonValue?, path: String): Set<String> {
        val features = value?.asArray(path)?.mapIndexed { index, feature ->
            feature.asString("$path[$index]").also { requireContentId(it, "$path[$index]") }
        } ?: emptyList()
        if (features.toSet().size != features.size) fail("$path must not contain duplicates.")
        return features.toSet()
    }

    private fun decodeSemanticHoldsByBoardId(boards: List<Board>): Map<String, Map<String, SemanticHoldMapping>> {
        val source = assets.read(PLAN_LIBRARY_PATH) ?: return emptyMap()
        val root = JsonParser(source).parse().asObject(PLAN_LIBRARY_PATH)
        val mappings = root.optional("boardMappings")?.asArray("$PLAN_LIBRARY_PATH.boardMappings") ?: return emptyMap()
        val boardsById = boards.associateBy { it.id }
        val result = linkedMapOf<String, Map<String, SemanticHoldMapping>>()
        mappings.forEachIndexed { index, value ->
            val mappingPath = "$PLAN_LIBRARY_PATH.boardMappings[$index]"
            val objectValue = value.asObject(mappingPath)
            val boardId = objectValue.requiredString("boardID", mappingPath)
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

    private fun aspectRatiosMatch(lhs: Float, rhs: Float, tolerance: Float): Boolean =
        lhs.isFinite() && rhs.isFinite() && lhs > 0f && rhs > 0f &&
            kotlin.math.abs(lhs - rhs) / rhs <= tolerance

    private fun JsonValue.asFingerCapacity(path: String): Int {
        val value = (this as? JsonValue.Number)?.value ?: fail("$path must be a number.")
        if (!value.isFinite() || value != value.toInt().toDouble() || value.toInt() !in FINGER_CAPACITY_RANGE) {
            fail("$path must be an integer within $FINGER_CAPACITY_RANGE.")
        }
        return value.toInt()
    }

    private fun JsonValue.Object.rejectUnknownKeys(allowedKeys: Set<String>, path: String) {
        fields.keys.firstOrNull { it !in allowedKeys }?.let { unknownKey ->
            fail("$path contains unknown key $unknownKey.")
        }
    }

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)

    private companion object {
        const val BOARDS_ROOT = "Hangboards"
        const val PLAN_LIBRARY_PATH = "PlanLibrary.json"
        const val PRESENTATION_ASPECT_RATIO_TOLERANCE = 0.001f
        const val ALIAS_ASPECT_RATIO_TOLERANCE = 0.000001f
        const val CORD_PULL_EXIT_HALF_SPACING = 22.0
        const val CORD_SUPPORT_MIN_X_OFFSET = -30.0
        const val CORD_SUPPORT_MAX_X_OFFSET = 31.0
        const val CORD_SUPPORT_MIN_Y_OFFSET = -177.0
        const val CORD_SUPPORT_MAX_Y_OFFSET = 0.0
        const val CORD_SHADOW_X_MARGIN = 23.8
        const val CORD_SHADOW_Y_MARGIN = 24.8
        val ROUTED_IDENTIFIER = Regex("[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?")
        val ROUTED_COLOR = Regex("#[0-9A-Fa-f]{6}")
        val FINGER_CAPACITY_RANGE = 1..4
    }

    private data class PointD(val x: Double, val y: Double)
}
