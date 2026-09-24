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
    /**
     * Loads every bundled schema v3 board package. Android has no 3D renderer,
     * so model-only packages are validated shallowly and then omitted; raster
     * packages become canvas boards.
     */
    override fun loadBoards(): Result<List<Board>> = runCatching {
        val packages = assets.list(BOARDS_ROOT)
            ?.sorted()
            ?.also { if (it.isEmpty()) fail("$BOARDS_ROOT contains no board packages.") }
            ?: fail("Missing $BOARDS_ROOT asset directory.")
        val boardIds = mutableSetOf<String>()
        packages.mapNotNull { packageName ->
            val boardPath = "$BOARDS_ROOT/$packageName/board.json"
            val source = assets.read(boardPath) ?: fail("Missing board document $boardPath.")
            val board = decodeBoard(
                JsonParser(source).parse().asObject(boardPath),
                boardPath,
                packageName,
            ) ?: return@mapNotNull null
            if (!boardIds.add(board.id)) fail("Duplicate board ID \"${board.id}\".")
            board
        }
    }

    private fun decodeBoard(
        objectValue: JsonValue.Object,
        path: String,
        packageName: String,
    ): Board? {
        val schemaVersion = (objectValue.required("schemaVersion", path) as? JsonValue.Number)?.value
            ?: fail("$path.schemaVersion must be a number.")
        if (schemaVersion != SCHEMA_VERSION) fail("$path.schemaVersion must be 3; found $schemaVersion.")
        objectValue.rejectUnknownKeys(
            path,
            setOf(
                "schemaVersion", "id", "revisionID", "manufacturer", "name", "subtitle", "productURL",
                "aspectRatio", "presentations", "contacts", "dimensions", "handCapacity",
                "unilateralHandResolution", "equipmentObjects", "positions", "positionTransitions",
            ),
        )

        val boardId = objectValue.requiredString("id", path)
        objectValue.requiredString("revisionID", path)
        objectValue.optional("handCapacity")?.asIntegerIn(HAND_CAPACITY_RANGE, "$path.handCapacity")
        val equipmentObjectIds = decodeEquipmentObjectIds(objectValue.optional("equipmentObjects"), "$path.equipmentObjects")

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
        if (mediaTypes.any { it != "raster" && it != "model" }) fail("$path.presentations contains unsupported media.")
        if (mediaTypes.contains("model") && mediaTypes.contains("raster")) {
            fail("$path.presentations may not mix model and raster media.")
        }

        val presentations = presentationObjects.mapIndexed { index, presentation ->
            val presentationPath = "$path.presentations[$index]"
            presentation.rejectUnknownKeys(
                presentationPath,
                setOf("id", "name", "aspectRatio", "isDefault", "derivation", "media"),
            )
            if (mediaTypes[index] == "model") {
                decodeModelPresentation(presentation, presentationPath)
            } else {
                decodeRasterPresentation(presentation, presentationPath)
            }
        }
        if (presentations.count { it.isDefault } != 1) fail("$path.presentations must contain exactly one default presentation.")
        if (presentations.map { it.id }.toSet().size != presentations.size) fail("$path.presentations contains duplicate IDs.")
        presentations.forEachIndexed { index, presentation ->
            if (mediaTypes[index] == "model") return@forEachIndexed
            val assetPath = "$BOARDS_ROOT/$packageName/${presentation.assetPath}"
            if (!assets.exists(assetPath)) fail("Board $boardId is missing presentation asset ${presentation.assetPath}.")
        }

        val contacts = objectValue.required("contacts", path)
            .asArray("$path.contacts")
            .mapIndexed { index, value -> decodeContact(value.asObject("$path.contacts[$index]"), "$path.contacts[$index]") }
        if (contacts.isEmpty()) fail("$path.contacts must not be empty.")
        if (contacts.map { it.first.id }.toSet().size != contacts.size) fail("$path.contacts contains duplicate IDs.")
        contacts.forEach { (contact, equipmentObjectId) ->
            if (equipmentObjectId !in equipmentObjectIds) {
                fail("$path contact ${contact.id} references unknown equipment object $equipmentObjectId.")
            }
        }
        val contactIds = contacts.map { it.first.id }

        val positions = decodePositions(
            objectValue.optional("positions"),
            "$path.positions",
            presentations,
            contactIds,
        )
        if (mediaTypes.any { it == "model" }) {
            if (mediaTypes.count { it == "model" } != 1) {
                fail("$path.presentations must contain at most one model presentation.")
            }
            val orientation = presentations.single().orientation
            val positionIds = positions.map { it.id }.toSet()
            if (orientation != null) {
                if (positionIds.size < 2) fail("orientation is not allowed for a fixed model.")
                if (orientation.rotations.keys != positionIds) {
                    fail("orientation rotation IDs must exactly match model position IDs.")
                }
            }
            val explicitContactInventory = objectValue.optional("positions")?.asArray("$path.positions")?.mapIndexed { index, value ->
                value.asObject("$path.positions[$index]").optional("contactIDs") != null
            } ?: emptyList()
            if (explicitContactInventory.any { it } && explicitContactInventory.any { !it }) {
                fail("positions contactIDs must be explicitly provided for every model position.")
            }
            if (orientation != null || explicitContactInventory.any { it }) {
                validateModelPositionInventories(positions, contactIds, "$path.positions")
            }
            return null
        }

        val knownContactIds = contactIds.toSet()
        val geometryByContactId = linkedMapOf<String, Pair<String, List<BoardGeometry>>>()
        presentationObjects.forEachIndexed { index, presentationObject ->
            val presentationPath = "$path.presentations[$index]"
            val derivation = decodeDerivation(
                presentationObject.required("derivation", presentationPath),
                "$presentationPath.derivation",
                presentations.map { it.id }.toSet(),
            )
            val contactGeometry = presentationObject.required("media", presentationPath)
                .asObject("$presentationPath.media")
                .required("contactGeometry", "$presentationPath.media")
                .asObject("$presentationPath.media.contactGeometry")
                .fields
            contactGeometry.forEach { (contactId, value) ->
                if (contactId !in knownContactIds) {
                    fail("$presentationPath.media.contactGeometry references unknown contact $contactId.")
                }
                val geometryPath = "$presentationPath.media.contactGeometry.$contactId"
                val geometry = value.asArray(geometryPath)
                    .mapIndexed { geometryIndex, geometryValue ->
                        decodeGeometry(
                            geometryValue.asObject("$geometryPath[$geometryIndex]"),
                            "$geometryPath[$geometryIndex]",
                        )
                    }
                if (geometry.isEmpty()) fail("$geometryPath must not be empty.")
                // Derived (e.g. inverted) presentations re-show an original surface;
                // the canvas draws each contact on its one original presentation.
                if (derivation != "original") return@forEach
                if (geometryByContactId.put(contactId, presentations[index].id to geometry) != null) {
                    fail("$path.presentations assigns contact $contactId to multiple original raster presentations.")
                }
            }
        }
        val holds = contacts.map { (contact, _) ->
            val (presentationId, geometry) = geometryByContactId[contact.id]
                ?: fail("$path.presentations must assign contact ${contact.id} to one original raster presentation.")
            contact.copy(presentationId = presentationId, geometry = geometry)
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
            positions = positions,
            packageSlug = packageName,
        )
    }

    private fun decodeEquipmentObjectIds(value: JsonValue?, path: String): Set<String> {
        val objects = value?.asArray(path) ?: return setOf("primary")
        if (objects.isEmpty()) fail("$path must not be empty.")
        val ids = objects.mapIndexed { index, objectValue ->
            val objectPath = "$path[$index]"
            val equipmentObject = objectValue.asObject(objectPath)
            equipmentObject.rejectUnknownKeys(objectPath, setOf("id"))
            equipmentObject.requiredString("id", objectPath)
        }
        if (ids.toSet().size != ids.size) fail("$path contains duplicate IDs.")
        return ids.toSet()
    }

    /** Returns `original` or `derived` after validating the derivation's closed key set. */
    private fun decodeDerivation(value: JsonValue, path: String, presentationIds: Set<String>): String {
        val derivation = value.asObject(path)
        return when (val type = derivation.requiredString("type", path)) {
            "original" -> {
                derivation.rejectUnknownKeys(path, setOf("type"))
                type
            }
            "derived" -> {
                derivation.rejectUnknownKeys(path, setOf("type", "sourcePresentationID", "isInverted"))
                val sourceId = derivation.requiredString("sourcePresentationID", path)
                if (derivation.required("isInverted", path) !is JsonValue.BooleanValue) {
                    fail("$path.isInverted must be a boolean.")
                }
                if (sourceId !in presentationIds) fail("$path references unknown presentation $sourceId.")
                type
            }
            else -> fail("$path.type is unsupported: $type.")
        }
    }

    /** Returns the contact and its equipment object ID; geometry is attached from raster media later. */
    private fun decodeContact(objectValue: JsonValue.Object, path: String): Pair<BoardHold, String> {
        objectValue.rejectUnknownKeys(
            path,
            setOf(
                "id", "equipmentObjectID", "name", "kind", "gripTypes", "depth", "shape",
                "fingerCapacity", "handCapacity", "side", "pairedContactID",
            ),
        )
        val kind = objectValue.requiredString("kind", path)
        if (kind !in CONTACT_KINDS) fail("$path.kind is unsupported: $kind.")
        if (kind == "gaston") {
            objectValue.requiredString("pairedContactID", path)
        } else if (objectValue.optional("pairedContactID") != null) {
            fail("$path.pairedContactID is only allowed for gaston contacts.")
        }
        val shape = objectValue.optional("shape")?.asString("$path.shape")?.also {
            if (it !in CONTACT_SHAPES) fail("$path.shape is unsupported: $it.")
        }
        objectValue.optional("side")?.asString("$path.side")?.also {
            if (it != "left" && it != "right") fail("$path.side is unsupported: $it.")
        }
        val gripTypeValues = objectValue.required("gripTypes", path).asArray("$path.gripTypes")
            .mapIndexed { index, value -> value.asString("$path.gripTypes[$index]") }
        if (gripTypeValues.toSet().size != gripTypeValues.size) fail("$path.gripTypes must be unique.")
        val gripTypes = gripTypeValues.mapTo(linkedSetOf()) {
            GripType.fromPortable(it) ?: fail("$path.gripTypes contains unsupported grip type $it.")
        }
        val contact = BoardHold(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            kind = kind,
            fingerCapacity = objectValue.optional("fingerCapacity")?.asIntegerIn(FINGER_CAPACITY_RANGE, "$path.fingerCapacity"),
            handCapacity = objectValue.optional("handCapacity")?.asIntegerIn(HAND_CAPACITY_RANGE, "$path.handCapacity"),
            shape = shape,
            depth = objectValue.optional("depth")?.let { decodeHoldDepth(it, "$path.depth") },
            gripTypes = gripTypes,
            presentationId = "",
            geometry = emptyList(),
        )
        return contact to objectValue.requiredString("equipmentObjectID", path)
    }

    private fun decodeModelPresentation(
        objectValue: JsonValue.Object,
        path: String,
    ): BoardPresentation {
        val media = objectValue.required("media", path).asObject("$path.media")
        media.rejectUnknownKeys(
            "$path.media",
            setOf("type", "assetPath", "descriptorPath", "display", "suspension", "orientation", "instances"),
        )
        media.required("descriptorPath", "$path.media")
        media.required("display", "$path.media")
        if (media.optional("instances") != null &&
            (media.optional("orientation") != null || media.optional("suspension") != null)
        ) {
            fail("$path.media.instances may not use legacy pose mechanisms.")
        }
        val orientation = media.optional("orientation")?.let { decodeOrientation(it, "$path.media.orientation") }
        val suspension = media.optional("suspension")?.let { decodeSuspension(it, "$path.media.suspension") }
        return BoardPresentation(
            id = objectValue.requiredString("id", path),
            name = objectValue.requiredString("name", path),
            assetPath = media.requiredString("assetPath", "$path.media"),
            aspectRatio = positiveFiniteFloat(objectValue.required("aspectRatio", path), "$path.aspectRatio"),
            isDefault = (objectValue.required("isDefault", path) as? JsonValue.BooleanValue)?.value
                ?: fail("$path.isDefault must be a boolean."),
            orientation = orientation,
            suspension = suspension,
        )
    }

    private fun decodeSuspension(value: JsonValue, path: String): BoardSuspension {
        val objectValue = value.asObject(path)
        val type = objectValue.requiredString("type", path)
        val allowedKeys = when (type) {
            "twoBranchCord" -> setOf("type", "passages", "branches", "anchor", "canonicalPoses")
            "pairedLeadCord" -> setOf("type", "attachments", "passages", "anchor", "cord", "canonicalPoses")
            else -> fail("$path.type is unsupported: $type.")
        }
        objectValue.rejectUnknownKeys(path, allowedKeys)
        allowedKeys.forEach { objectValue.required(it, path) }
        return BoardSuspension(type = type)
    }

    private fun decodeRasterPresentation(objectValue: JsonValue.Object, path: String): BoardPresentation {
        val media = objectValue.required("media", path).asObject("$path.media")
        media.rejectUnknownKeys("$path.media", setOf("type", "assetPath", "contactGeometry"))
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

    private fun decodePositions(
        value: JsonValue?,
        path: String,
        presentations: List<BoardPresentation>,
        contactIds: List<String>,
    ): List<BoardPosition> {
        val presentationIds = presentations.mapTo(mutableSetOf()) { it.id }
        val positions = value?.asArray(path)?.mapIndexed { index, positionValue ->
            val positionPath = "$path[$index]"
            val position = positionValue.asObject(positionPath)
            position.rejectUnknownKeys(positionPath, setOf("id", "presentationID", "contactIDs"))
            val explicitContactIds = position.optional("contactIDs")?.asArray("$positionPath.contactIDs")
                ?.mapIndexed { contactIndex, contactValue ->
                    contactValue.asString("$positionPath.contactIDs[$contactIndex]").also {
                        requireContentId(it, "$positionPath.contactIDs[$contactIndex]")
                    }
                }
            if (explicitContactIds != null && explicitContactIds.isEmpty()) {
                fail("$positionPath.contactIDs must not be empty.")
            }
            val positionContactIds = explicitContactIds ?: contactIds
            if (positionContactIds.toSet().size != positionContactIds.size) {
                fail("$positionPath.contactIDs must not contain duplicates.")
            }
            BoardPosition(
                id = position.requiredString("id", positionPath),
                presentationId = position.requiredString("presentationID", positionPath),
                contactIds = positionContactIds,
            )
        } ?: presentations.map { presentation ->
            BoardPosition(presentation.id, presentation.id, contactIds)
        }
        if (positions.isEmpty() || positions.map { it.id }.toSet().size != positions.size) {
            fail("$path must contain unique positions.")
        }
        positions.forEach { position ->
            if (position.presentationId !in presentationIds) {
                fail("$path position ${position.id} references unknown presentation ${position.presentationId}.")
            }
            position.contactIds.firstOrNull { it !in contactIds }?.let {
                fail("$path position ${position.id} references unknown contact $it.")
            }
        }
        return positions
    }

    private fun validateModelPositionInventories(
        positions: List<BoardPosition>,
        contactIds: List<String>,
        path: String,
    ) {
        val seen = mutableSetOf<String>()
        positions.forEachIndexed { index, position ->
            if (position.contactIds != contactIds.filter { it in position.contactIds }) {
                fail("$path[$index].contactIDs must follow canonical board contact order.")
            }
            seen.addAll(position.contactIds)
        }
        if (seen != contactIds.toSet()) {
            fail("model positions contactIDs must cover all board contacts (union coverage).")
        }
    }

    private fun decodeOrientation(value: JsonValue, path: String): BoardOrientation {
        val objectValue = value.asObject(path)
        objectValue.rejectUnknownKeys(path, setOf("pivot", "rotations"))
        if (objectValue.fields.keys.toList() != listOf("pivot", "rotations")) {
            fail("$path must contain canonical pivot and rotations members")
        }
        val pivot = objectValue.requiredText("pivot", path)
        if (pivot != "modelBoundsCenter") fail("$path pivot must be modelBoundsCenter.")
        val rotationsObject = objectValue.required("rotations", path).asObject("$path.rotations")
        if (rotationsObject.fields.isEmpty()) fail("$path.rotations must not be empty.")
        if (rotationsObject.fields.keys.toList() != rotationsObject.fields.keys.sorted()) {
            fail("$path.rotations must be sorted by position ID")
        }
        val rotations = linkedMapOf<String, List<Float>>()
        rotationsObject.fields.forEach { (positionID, value) ->
            requireContentId(positionID, "$path.rotations")
            val components = value.asArray("$path.rotations.$positionID")
            if (components.size != 4) fail("$path.rotations.$positionID must contain [x,y,z,w].")
            val quaternion = components.mapIndexed { index, component ->
                component.asCanonicalNineDecimalFloat("$path.rotations.$positionID[$index]")
            }
            val norm = kotlin.math.sqrt(quaternion.sumOf { it.toDouble() * it.toDouble() })
            if (!norm.isFinite() || kotlin.math.abs(norm - 1.0) > 1e-6) {
                fail("$path.rotations.$positionID must be a unit quaternion in [x,y,z,w] order.")
            }
            rotations[positionID] = quaternion
        }
        return BoardOrientation(pivot = pivot, rotations = rotations)
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

    private fun validateAssetPath(assetPath: String, path: String) {
        if (!assetPath.startsWith("assets/") || assetPath.split('/').any { it == ".." || it.isBlank() }) {
            fail("$path must be a relative assets path.")
        }
    }

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)

    private companion object {
        const val BOARDS_ROOT = "Hangboards"
        const val SCHEMA_VERSION = 3.0
    }
}
