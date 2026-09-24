package com.hangten.android.content

interface PlanRepository {
    fun loadPlans(): Result<List<TrainingPlan>>
}

class AssetPlanRepository(
    private val assets: ContentAssets,
) : PlanRepository {
    override fun loadPlans(): Result<List<TrainingPlan>> = runCatching {
        val source = assets.read(PLAN_LIBRARY_PATH) ?: fail("Missing $PLAN_LIBRARY_PATH asset.")
        val root = JsonParser(source).parse().asObject(PLAN_LIBRARY_PATH)
        val blocks = decodeBlocks(root.required("blocks", PLAN_LIBRARY_PATH).asArray("$PLAN_LIBRARY_PATH.blocks"))
        decodePlans(root.required("plans", PLAN_LIBRARY_PATH).asArray("$PLAN_LIBRARY_PATH.plans"), blocks)
    }

    private fun decodeBlocks(values: List<JsonValue>): Map<String, List<TrainingStep>> {
        val blocks = linkedMapOf<String, List<TrainingStep>>()
        values.forEachIndexed { index, value ->
            val path = "$PLAN_LIBRARY_PATH.blocks[$index]"
            val objectValue = value.asObject(path)
            val id = objectValue.requiredString("id", path)
            val steps = objectValue.required("steps", path).asArray("$path.steps")
                .mapIndexed { stepIndex, step -> decodeStep(step.asObject("$path.steps[$stepIndex]"), "$path.steps[$stepIndex]") }
            if (steps.isEmpty()) fail("$path.steps must not be empty.")
            if (steps.map { it.id }.toSet().size != steps.size) fail("$path.steps contains duplicate IDs.")
            if (blocks.put(id, steps) != null) fail("Duplicate block ID \"$id\".")
        }
        if (blocks.isEmpty()) fail("$PLAN_LIBRARY_PATH.blocks must not be empty.")
        return blocks
    }

    private fun decodePlans(
        values: List<JsonValue>,
        blocks: Map<String, List<TrainingStep>>,
    ): List<TrainingPlan> {
        val planIds = mutableSetOf<String>()
        return values.mapIndexed { index, value ->
            val path = "$PLAN_LIBRARY_PATH.plans[$index]"
            val objectValue = value.asObject(path)
            val id = objectValue.requiredString("id", path)
            if (!planIds.add(id)) fail("Duplicate plan ID \"$id\".")
            val metadata = objectValue.required("metadata", path).asObject("$path.metadata")
            val steps = decodePlanSteps(
                objectValue.required("blocks", path).asArray("$path.blocks"),
                blocks,
                "$path.blocks",
            )
            TrainingPlan(
                id = id,
                title = metadata.requiredString("title", "$path.metadata"),
                subtitle = metadata.requiredString("subtitle", "$path.metadata"),
                level = metadata.requiredString("level", "$path.metadata"),
                sourceLabel = metadata.requiredString("sourceLabel", "$path.metadata"),
                sourceUrl = metadata.optional("sourceURL")?.asString("$path.metadata.sourceURL"),
                provenance = metadata.requiredString("provenance", "$path.metadata"),
                boardId = objectValue.optional("boardID")?.asString("$path.boardID"),
                steps = steps,
            )
        }.also { if (it.isEmpty()) fail("$PLAN_LIBRARY_PATH.plans must not be empty.") }
    }

    private fun decodePlanSteps(
        references: List<JsonValue>,
        blocks: Map<String, List<TrainingStep>>,
        path: String,
    ): List<TrainingStep> {
        if (references.isEmpty()) fail("$path must not be empty.")
        return references.flatMapIndexed { index, value ->
            val referencePath = "$path[$index]"
            val reference = value.asObject(referencePath)
            val blockId = reference.requiredString("blockID", referencePath)
            val block = blocks[blockId] ?: fail("$referencePath references unknown block \"$blockId\".")
            val overrides = reference.optional("stepIDs")?.asArray("$referencePath.stepIDs")
                ?.mapIndexed { overrideIndex, id -> id.asString("$referencePath.stepIDs[$overrideIndex]") }
                ?: emptyList()
            if (overrides.isNotEmpty() && overrides.size != block.size) {
                fail("$referencePath.stepIDs must match the referenced block's step count.")
            }
            if (overrides.toSet().size != overrides.size) fail("$referencePath.stepIDs must be unique.")
            val repeatCount = reference.optional("repeatCount")?.asPositiveInt("$referencePath.repeatCount") ?: 1
            (0 until repeatCount).flatMap { repetition ->
                block.mapIndexed { stepIndex, step ->
                    val sourceId = overrides.getOrElse(stepIndex) { step.id }
                    val resolvedId = if (repeatCount == 1) sourceId else "$sourceId-${repetition + 1}"
                    step.copy(id = resolvedId)
                }
            }
        }
    }

    private fun decodeStep(objectValue: JsonValue.Object, path: String): TrainingStep = TrainingStep(
        id = objectValue.requiredString("id", path),
        title = objectValue.requiredString("title", path),
        instruction = objectValue.requiredText("instruction", path),
        accessory = objectValue.requiredText("accessory", path),
        durationSeconds = nonNegativeFiniteFloat(objectValue.required("duration", path), "$path.duration"),
        phase = objectValue.requiredString("phase", path),
        handUse = objectValue.requiredString("handUse", path).also {
            if (it !in HAND_USES) fail("$path.handUse is unsupported: $it.")
        },
        side = objectValue.requiredString("side", path).also {
            if (it !in SIDES) fail("$path.side is unsupported: $it.")
        },
        segments = objectValue.required("segments", path).asArray("$path.segments").mapIndexed { index, value ->
            decodeSegment(value.asObject("$path.segments[$index]"), "$path.segments[$index]")
        },
        activeDurationSeconds = objectValue.optional("activeDuration")?.let {
            nonNegativeFiniteFloat(it, "$path.activeDuration")
        },
        gripType = objectValue.optional("gripType")?.asGripType("$path.gripType"),
        fingerConfiguration = objectValue.optional("fingerConfiguration")?.let {
            decodeFingerConfiguration(it.asObject("$path.fingerConfiguration"), "$path.fingerConfiguration")
        },
    )

    private fun JsonValue.asGripType(path: String): GripType {
        val value = asString(path)
        return GripType.fromPortable(value) ?: fail("$path is unsupported: $value.")
    }

    private fun decodeFingerConfiguration(
        objectValue: JsonValue.Object,
        path: String,
    ): FingerConfiguration {
        if (objectValue.fields.keys != setOf("engagedFingers")) {
            fail("$path must contain only engagedFingers.")
        }
        val fingers = objectValue.required("engagedFingers", path)
            .asArray("$path.engagedFingers")
            .mapIndexed { index, value ->
                val fingerPath = "$path.engagedFingers[$index]"
                val portableValue = value.asString(fingerPath)
                FingerSlot.fromPortable(portableValue) ?: fail("$fingerPath is unsupported: $portableValue.")
            }
        if (fingers.isEmpty()) fail("$path.engagedFingers must not be empty.")
        if (fingers.toSet().size != fingers.size) fail("$path.engagedFingers must not contain duplicates.")
        return FingerConfiguration(fingers)
    }

    private fun decodeSegment(objectValue: JsonValue.Object, path: String): TrainingSegment {
        objectValue.rejectUnknownKeys(path, setOf("kind", "target", "timing", "duration"))
        val kind = objectValue.requiredString("kind", path)
        if (kind !in SEGMENT_KINDS) fail("$path.kind is unsupported: $kind.")
        val target = objectValue.optional("target")?.let { decodeSegmentTarget(it.asObject("$path.target"), "$path.target") }
        if (kind == "rest" && target != null) fail("$path: rest segments must not define a target.")
        return TrainingSegment(
            kind = kind,
            target = target,
            timing = objectValue.requiredString("timing", path),
            durationSeconds = objectValue.optional("duration")?.let { nonNegativeFiniteFloat(it, "$path.duration") },
        )
    }

    private fun decodeSegmentTarget(objectValue: JsonValue.Object, path: String): SegmentTarget {
        objectValue.rejectUnknownKeys(path, setOf("kind", "requirements"))
        return when (val kind = objectValue.requiredString("kind", path)) {
            "selfSelected" -> {
                if (objectValue.optional("requirements") != null) {
                    fail("$path: self-selected segment targets cannot contain requirements.")
                }
                SegmentTarget.SelfSelected
            }
            "requirements" -> {
                val requirements = objectValue.required("requirements", path)
                    .asArray("$path.requirements")
                    .mapIndexed { index, value ->
                        decodeRequirement(value.asObject("$path.requirements[$index]"), "$path.requirements[$index]")
                    }
                if (requirements.isEmpty()) fail("$path.requirements must not be empty.")
                SegmentTarget.Requirements(requirements)
            }
            else -> fail("$path.kind is unsupported: $kind.")
        }
    }

    private fun decodeRequirement(objectValue: JsonValue.Object, path: String): ContactRequirement {
        objectValue.rejectUnknownKeys(
            path,
            setOf("contactID", "kind", "shape", "depth", "fingerCapacity", "handCapacity", "selection"),
        )
        val selectionValue = objectValue.requiredString("selection", path)
        return ContactRequirement(
            contactId = objectValue.optional("contactID")?.asString("$path.contactID")?.also {
                requireContentId(it, "$path.contactID")
            },
            kind = objectValue.optional("kind")?.asString("$path.kind")?.also {
                if (it !in CONTACT_KINDS) fail("$path.kind is unsupported: $it.")
            },
            shape = objectValue.optional("shape")?.asString("$path.shape")?.also {
                if (it !in CONTACT_SHAPES) fail("$path.shape is unsupported: $it.")
            },
            depth = objectValue.optional("depth")?.let { decodeHoldDepth(it, "$path.depth") },
            fingerCapacity = objectValue.optional("fingerCapacity")?.asIntegerIn(FINGER_CAPACITY_RANGE, "$path.fingerCapacity"),
            handCapacity = objectValue.optional("handCapacity")?.asIntegerIn(HAND_CAPACITY_RANGE, "$path.handCapacity"),
            selection = ContactSelectionPolicy.fromPortable(selectionValue)
                ?: fail("$path.selection is unsupported: $selectionValue."),
        )
    }

    private fun JsonValue.asPositiveInt(path: String): Int {
        val value = (this as? JsonValue.Number)?.value ?: fail("$path must be a number.")
        if (!value.isFinite() || value != value.toInt().toDouble() || value < 1) fail("$path must be a positive integer.")
        return value.toInt()
    }

    private fun nonNegativeFiniteFloat(value: JsonValue, path: String): Float =
        value.asFiniteFloat(path).also { if (it < 0f) fail("$path must not be negative.") }

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)

    private companion object {
        const val PLAN_LIBRARY_PATH = "PlanLibrary.json"
        val HAND_USES = setOf("double", "single", "either")
        val SIDES = setOf("both", "left", "right")
        val SEGMENT_KINDS = setOf("work", "rest")
    }
}
