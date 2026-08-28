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
