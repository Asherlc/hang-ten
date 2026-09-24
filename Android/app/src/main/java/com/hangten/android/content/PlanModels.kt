package com.hangten.android.content

enum class ContactSelectionPolicy(
    val portableValue: String,
) {
    SINGLE("single"),
    BILATERAL_PAIR("bilateralPair"),
    ;

    companion object {
        internal fun fromPortable(value: String): ContactSelectionPolicy? =
            entries.firstOrNull { it.portableValue == value }
    }
}

/**
 * A factual physical-contact requirement (iOS `ContactRequirement`). Catalog
 * requirements carry no contact IDs; they resolve against the selected board.
 */
data class ContactRequirement(
    val contactId: String? = null,
    val kind: String? = null,
    val shape: String? = null,
    val depth: HoldDepth? = null,
    val fingerCapacity: Int? = null,
    val handCapacity: Int? = null,
    val selection: ContactSelectionPolicy = ContactSelectionPolicy.SINGLE,
)

/** A work segment's prescription: athlete-chosen holds, or concrete contact requirements. */
sealed interface SegmentTarget {
    data object SelfSelected : SegmentTarget
    data class Requirements(val requirements: List<ContactRequirement>) : SegmentTarget
}

data class TrainingSegment(
    val kind: String,
    /** Present only on work segments; rest segments never carry a target. */
    val target: SegmentTarget?,
    val timing: String,
    val durationSeconds: Float?,
)

enum class GripType(
    val portableValue: String,
) {
    OPEN_HAND("openHand"),
    HALF_CRIMP("halfCrimp"),
    FULL_CRIMP("fullCrimp"),
    FOUR_FINGER_POCKET("fourFingerPocket"),
    THREE_FINGER_POCKET("threeFingerPocket"),
    TWO_FINGER_POCKET("twoFingerPocket"),
    SLOPER("sloper"),
    ;

    companion object {
        internal fun fromPortable(value: String): GripType? = entries.firstOrNull { it.portableValue == value }
    }
}

enum class FingerSlot(
    val portableValue: String,
) {
    INDEX("index"),
    MIDDLE("middle"),
    RING("ring"),
    PINKY("pinky"),
    ;

    companion object {
        internal fun fromPortable(value: String): FingerSlot? = entries.firstOrNull { it.portableValue == value }
    }
}

data class FingerConfiguration(
    val engagedFingers: List<FingerSlot>,
)

data class TrainingStep(
    val id: String,
    val title: String,
    val instruction: String,
    val accessory: String,
    val durationSeconds: Float,
    val phase: String,
    /** `double`, `single`, or `either`; constrains bilateral-pair resolution. */
    val handUse: String,
    /** `both`, `left`, or `right`. */
    val side: String,
    val segments: List<TrainingSegment>,
    val activeDurationSeconds: Float?,
    val gripType: GripType?,
    val fingerConfiguration: FingerConfiguration?,
) {
    /** Every contact requirement prescribed by this step's work segments, in segment order. */
    val contactRequirements: List<ContactRequirement>
        get() = segments.flatMap { segment ->
            (segment.target as? SegmentTarget.Requirements)?.requirements.orEmpty()
        }
}

data class TrainingPlan(
    val id: String,
    val title: String,
    val subtitle: String,
    val level: String,
    val sourceLabel: String,
    val sourceUrl: String?,
    val provenance: String,
    val boardId: String?,
    val steps: List<TrainingStep>,
)
