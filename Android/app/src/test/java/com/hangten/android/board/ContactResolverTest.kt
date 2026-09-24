package com.hangten.android.board

import com.hangten.android.content.Board
import com.hangten.android.content.BoardGeometry
import com.hangten.android.content.BoardHold
import com.hangten.android.content.BoardPresentation
import com.hangten.android.content.ContactRequirement
import com.hangten.android.content.ContactSelectionPolicy
import com.hangten.android.content.GripType
import com.hangten.android.content.HoldDepth
import com.hangten.android.content.HoldShape
import com.hangten.android.content.HoldSize
import com.hangten.android.content.NormalizedFrame
import com.hangten.android.content.SegmentTarget
import com.hangten.android.content.TrainingSegment
import com.hangten.android.content.TrainingStep
import org.junit.Assert.assertEquals
import org.junit.Test

class ContactResolverTest {
    @Test
    fun singleRequirementSelectsTheMatchingContactNearestTheCenter() {
        val board = boardWith(
            contact("edge-left", "edge", x = 0.1f, depth = HoldDepth.Range(20.0, 20.0)),
            contact("edge-center", "edge", x = 0.45f, depth = HoldDepth.Range(20.0, 20.0)),
            contact("jug-center", "jug", x = 0.45f),
        )

        assertEquals(
            setOf("edge-center"),
            ContactResolver.resolve(step(ContactRequirement(kind = "edge")), board),
        )
    }

    @Test
    fun singleRequirementBreaksCenterDistanceTiesByContactId() {
        val board = boardWith(
            contact("edge-right", "edge", x = 0.6875f),
            contact("edge-left", "edge", x = 0.1875f),
        )

        assertEquals(
            setOf("edge-left"),
            ContactResolver.resolve(step(ContactRequirement(kind = "edge")), board),
        )
    }

    @Test
    fun depthRequirementsMatchRangesByOverlapAndCategoriesByConventionalRange() {
        val board = boardWith(
            contact("edge-12", "edge", x = 0.1f, depth = HoldDepth.Range(12.0, 12.0)),
            contact("edge-20", "edge", x = 0.3f, depth = HoldDepth.Range(20.0, 20.0)),
            contact("edge-unknown", "edge", x = 0.45f),
        )

        assertEquals(
            setOf("edge-20"),
            ContactResolver.resolve(step(ContactRequirement(kind = "edge", depth = HoldDepth.Range(15.0, 20.0))), board),
        )
        assertEquals(
            setOf("edge-12"),
            ContactResolver.resolve(
                step(ContactRequirement(kind = "edge", depth = HoldDepth.Category(HoldSize.SMALL))),
                board,
            ),
        )
    }

    @Test
    fun contactsWithGripMetadataMustAllowTheStepGrip() {
        val board = boardWith(
            contact("open-only", "edge", x = 0.5f, gripTypes = setOf(GripType.OPEN_HAND)),
            contact("unconstrained", "edge", x = 0.1f),
        )

        assertEquals(
            setOf("unconstrained"),
            ContactResolver.resolve(step(ContactRequirement(kind = "edge"), gripType = GripType.HALF_CRIMP), board),
        )
    }

    @Test
    fun bilateralPairSelectsTheOutermostMatchingPairOnADoubleHandStep() {
        val board = boardWith(
            contact("pocket-outer-left", "pocket", x = 0.05f, fingerCapacity = 3),
            contact("pocket-inner-left", "pocket", x = 0.3f, fingerCapacity = 3),
            contact("pocket-inner-right", "pocket", x = 0.6f, fingerCapacity = 3),
            contact("pocket-outer-right", "pocket", x = 0.85f, fingerCapacity = 3),
        )
        val requirement = ContactRequirement(kind = "pocket", selection = ContactSelectionPolicy.BILATERAL_PAIR)

        assertEquals(
            setOf("pocket-outer-left", "pocket-outer-right"),
            ContactResolver.resolve(step(requirement), board),
        )
        assertEquals(
            emptySet<String>(),
            ContactResolver.resolve(step(requirement, handUse = "single", side = "left"), board),
        )
    }

    @Test
    fun bilateralPairRejectsMismatchedOutermostContacts() {
        val board = boardWith(
            contact("pocket-left", "pocket", x = 0.05f, fingerCapacity = 3),
            contact("pocket-right", "pocket", x = 0.85f, fingerCapacity = 2),
        )

        assertEquals(
            emptySet<String>(),
            ContactResolver.resolve(
                step(ContactRequirement(kind = "pocket", selection = ContactSelectionPolicy.BILATERAL_PAIR)),
                board,
            ),
        )
    }

    @Test
    fun anUnresolvableRequirementLeavesTheWholeStepUnresolvedWithoutSubstitution() {
        val board = boardWith(contact("edge", "edge", x = 0.4f))

        assertEquals(
            emptySet<String>(),
            ContactResolver.resolve(
                step(ContactRequirement(kind = "edge"), ContactRequirement(kind = "sloper")),
                board,
            ),
        )
    }

    @Test
    fun onlyContactsOnTheDefaultPresentationAreCandidates() {
        val board = boardWith(
            contact("reverse-edge", "edge", x = 0.5f, presentationId = "reverse"),
            contact("front-edge", "edge", x = 0.1f),
        )

        assertEquals(
            setOf("front-edge"),
            ContactResolver.resolve(step(ContactRequirement(kind = "edge")), board),
        )
    }

    private fun contact(
        id: String,
        kind: String,
        x: Float,
        depth: HoldDepth? = null,
        fingerCapacity: Int? = null,
        gripTypes: Set<GripType> = emptySet(),
        presentationId: String = "primary",
    ) = BoardHold(
        id = id,
        name = id,
        kind = kind,
        fingerCapacity = fingerCapacity,
        depth = depth,
        gripTypes = gripTypes,
        presentationId = presentationId,
        geometry = listOf(
            BoardGeometry(NormalizedFrame(x, 0.2f, 0.125f, 0.125f), HoldShape.RoundedRect(0.1f)),
        ),
    )

    private fun step(
        vararg requirements: ContactRequirement,
        gripType: GripType? = null,
        handUse: String = "double",
        side: String = "both",
    ) = TrainingStep(
        id = "step",
        title = "Step",
        instruction = "",
        accessory = "",
        durationSeconds = 10f,
        phase = "hang",
        handUse = handUse,
        side = side,
        segments = listOf(
            TrainingSegment(
                kind = "work",
                target = SegmentTarget.Requirements(requirements.toList()),
                timing = "fixed",
                durationSeconds = 10f,
            ),
        ),
        activeDurationSeconds = null,
        gripType = gripType,
        fingerConfiguration = null,
    )

    private fun boardWith(vararg holds: BoardHold) = Board(
        id = "fixture",
        manufacturer = "Fixture",
        name = "Fixture",
        subtitle = "Fixture",
        productUrl = "https://example.invalid",
        aspectRatio = 2f,
        presentations = listOf(
            BoardPresentation(id = "primary", name = "Primary", assetPath = "assets/primary.png", aspectRatio = 2f, isDefault = true),
            BoardPresentation(id = "reverse", name = "Reverse", assetPath = "assets/reverse.png", aspectRatio = 2f, isDefault = false),
        ),
        holds = holds.toList(),
    )
}
