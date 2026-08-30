package com.hangten.android.content

data class PlanTarget(
    val semantic: String? = null,
    val semantics: List<String>? = null,
    val holdIds: List<String>? = null,
    val kind: String? = null,
    val feature: String? = null,
    val fallbackFeatures: List<String> = emptyList(),
    val fingerCapacity: Int? = null,
)

data class TrainingSegment(
    val kind: String,
    val targets: List<PlanTarget>,
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
    val targets: List<PlanTarget>,
    val segments: List<TrainingSegment>,
    val activeDurationSeconds: Float?,
    val gripType: GripType?,
    val fingerConfiguration: FingerConfiguration?,
)

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
