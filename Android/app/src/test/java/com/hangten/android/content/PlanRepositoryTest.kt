package com.hangten.android.content

import com.hangten.android.board.ContactResolver
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlanRepositoryTest {
    @Test
    fun decodesPlanStepsInDeclaredOrder() {
        val result = AssetPlanRepository(
            FixtureAssets(
                mapOf(
                    "PlanLibrary.json" to
                        """
                        {
                          "metadata": {
                            "id": "demo-library",
                            "title": "Demo Library",
                            "generatedAt": "2026-08-28",
                            "notes": []
                          },
                          "blocks": [
                            {
                              "id": "warm-up",
                              "title": "Warm-up",
                              "steps": [
                                {
                                  "id": "first-step",
                                  "title": "First",
                                  "instruction": "Keep this instruction exactly.",
                                  "accessory": "Exact accessory text",
                                  "duration": 10,
                                  "phase": "hang",
                                  "handUse": "double",
                                  "side": "both",
                                  "segments": []
                                }
                              ]
                            },
                            {
                              "id": "main",
                              "title": "Main",
                              "steps": [
                                {
                                  "id": "second-step",
                                  "title": "Second",
                                  "instruction": "Second instruction.",
                                  "accessory": "Second accessory",
                                  "duration": 20,
                                  "phase": "rest",
                                  "handUse": "double",
                                  "side": "both",
                                  "segments": []
                                }
                              ]
                            }
                          ],
                          "plans": [
                            {
                              "id": "demo.plan",
                              "metadata": {
                                "title": "Demo Plan",
                                "subtitle": "A plan for testing.",
                                "level": "All",
                                "sourceLabel": "Fixture",
                                "provenance": "custom",
                                "category": "general",
                                "tags": [],
                                "equipment": [],
                                "notes": []
                              },
                              "blocks": [
                                { "blockID": "warm-up" },
                                { "blockID": "main" }
                              ]
                            }
                          ]
                        }
                        """.trimIndent(),
                ),
            ),
        ).loadPlans()

        val plan = result.getOrThrow().single()
        assertEquals(listOf("first-step", "second-step"), plan.steps.map { it.id })
        assertEquals("Keep this instruction exactly.", plan.steps.first().instruction)
        assertEquals("Exact accessory text", plan.steps.first().accessory)
    }

    @Test
    fun replaysStagedCanonicalAssetsAndPreservesCoachingCues() {
        val root = File("build/generated/assets/canonical")
        val assets = StagedContentAssets(root)

        val boards = AssetBoardRepository(assets).loadBoards().getOrThrow()
        val steps = AssetPlanRepository(assets).loadPlans().getOrThrow()
            .flatMap { it.steps }
        val maxHang = steps.first { it.id == "max-hangs-1" }

        // Android has no 3D renderer, so model-only packages are omitted and
        // every raster package in the staged catalog becomes a canvas board.
        val stagedPackages = assets.list("Hangboards").orEmpty().sorted()
        val rasterBoardIds = stagedPackages.mapNotNull { packageName ->
            val document = JsonParser(assets.read("Hangboards/$packageName/board.json")!!).parse()
                .asObject(packageName)
            val firstMedia = document.required("presentations", packageName).asArray(packageName).first()
                .asObject(packageName).required("media", packageName).asObject(packageName)
            document.requiredString("id", packageName).takeIf { firstMedia.requiredString("type", packageName) == "raster" }
        }
        assertTrue(stagedPackages.size > rasterBoardIds.size)
        assertTrue(rasterBoardIds.isNotEmpty())
        assertEquals(rasterBoardIds, boards.map { it.id })
        assertTrue(boards.all { board ->
            board.presentations.all { presentation -> presentation.assetPath.endsWith(".png") } &&
                board.holds.all { it.geometry.isNotEmpty() }
        })
        assertFalse(boards.any { it.id == "beastmaker-1000" })
        assertFalse(boards.any { it.id == "tension.flash-board" })

        assertEquals(
            "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
            maxHang.instruction,
        )
        assertEquals("7s hang · 3m recovery · half crimp", maxHang.accessory)
        assertEquals(GripType.HALF_CRIMP, maxHang.gripType)
        assertEquals(
            listOf(FingerSlot.INDEX, FingerSlot.MIDDLE, FingerSlot.RING, FingerSlot.PINKY),
            maxHang.fingerConfiguration?.engagedFingers,
        )
        assertEquals(
            listOf(
                ContactRequirement(
                    kind = "edge",
                    depth = HoldDepth.Range(20.0, 20.0),
                    selection = ContactSelectionPolicy.SINGLE,
                ),
            ),
            maxHang.contactRequirements,
        )
        val grindstone = boards.single { it.id == "tension.grindstone" }
        assertEquals(setOf("edge-20-left"), ContactResolver.resolve(maxHang, grindstone))
    }

    @Test
    fun rejectsUnsupportedGripType() {
        val result = AssetPlanRepository(
            FixtureAssets(
                mapOf(
                    "PlanLibrary.json" to
                        """
                        {
                          "metadata": { "id": "library", "title": "Library", "generatedAt": "2026-08-28", "notes": [] },
                          "blocks": [
                            {
                              "id": "main",
                              "title": "Main",
                              "steps": [
                                {
                                  "id": "step",
                                  "title": "Step",
                                  "instruction": "Instruction",
                                  "accessory": "Accessory",
                                  "duration": 10,
                                  "phase": "hang",
                                  "handUse": "double",
                                  "side": "both",
                                  "segments": [],
                                  "gripType": "unsupportedGrip",
                                  "fingerConfiguration": { "engagedFingers": ["index", "index"] }
                                }
                              ]
                            }
                          ],
                          "plans": [
                            {
                              "id": "plan",
                              "metadata": {
                                "title": "Plan",
                                "subtitle": "Subtitle",
                                "level": "All",
                                "sourceLabel": "Fixture",
                                "provenance": "custom",
                                "category": "general",
                                "tags": [],
                                "equipment": [],
                                "notes": []
                              },
                              "blocks": [{ "blockID": "main" }]
                            }
                          ]
                        }
                        """.trimIndent(),
                ),
            ),
        ).loadPlans()

        assertFalse(result.isSuccess)
        assertTrue(result.exceptionOrNull()?.message?.contains("gripType") == true)
    }

    @Test
    fun decodesSegmentContactRequirementsAndSelfSelectedTargets() {
        val step = loadSingleStep(
            """
            [
              {
                "kind": "work",
                "timing": "fixed",
                "duration": 10,
                "target": {
                  "kind": "requirements",
                  "requirements": [
                    { "kind": "edge", "depth": { "category": "small" }, "fingerCapacity": 3, "selection": "bilateralPair" },
                    { "kind": "pocket", "shape": "round", "handCapacity": 1, "selection": "single" }
                  ]
                }
              },
              { "kind": "rest", "timing": "fixed", "duration": 5 },
              { "kind": "work", "timing": "stopwatch", "target": { "kind": "selfSelected" } }
            ]
            """,
        ).getOrThrow()

        assertEquals(
            listOf(
                ContactRequirement(
                    kind = "edge",
                    depth = HoldDepth.Category(HoldSize.SMALL),
                    fingerCapacity = 3,
                    selection = ContactSelectionPolicy.BILATERAL_PAIR,
                ),
                ContactRequirement(kind = "pocket", shape = "round", handCapacity = 1),
            ),
            step.contactRequirements,
        )
        assertEquals(null, step.segments[1].target)
        assertEquals(SegmentTarget.SelfSelected, step.segments[2].target)
    }

    @Test
    fun rejectsRestSegmentsWithATarget() {
        val result = loadSingleStep(
            """[{ "kind": "rest", "timing": "fixed", "duration": 5, "target": { "kind": "selfSelected" } }]""",
        )

        assertTrue(result.exceptionOrNull()?.message?.contains("rest segments must not define a target") == true)
    }

    @Test
    fun rejectsLegacyHoldIdAndFallbackTargetFields() {
        listOf("\"holdIDs\": [\"edge\"]", "\"fallbackFeatures\": [\"largeEdge\"]", "\"semantic\": \"jugs\"").forEach { legacy ->
            val result = loadSingleStep(
                """[{ "kind": "work", "timing": "fixed", "duration": 5, "target": { "kind": "requirements", "requirements": [{ "kind": "edge", "selection": "single", $legacy }] } }]""",
            )

            assertTrue(legacy, result.exceptionOrNull()?.message?.contains("unknown key") == true)
        }
    }

    @Test
    fun rejectsEmptyRequirementTargets() {
        val result = loadSingleStep(
            """[{ "kind": "work", "timing": "fixed", "duration": 5, "target": { "kind": "requirements", "requirements": [] } }]""",
        )

        assertTrue(result.exceptionOrNull()?.message?.contains("requirements must not be empty") == true)
    }

    private fun loadSingleStep(segmentsJson: String): Result<TrainingStep> = AssetPlanRepository(
        FixtureAssets(
            mapOf(
                "PlanLibrary.json" to
                    """
                    {
                      "metadata": { "id": "library", "title": "Library", "generatedAt": "2026-09-24", "notes": [] },
                      "blocks": [
                        {
                          "id": "main",
                          "title": "Main",
                          "steps": [
                            {
                              "id": "step",
                              "title": "Step",
                              "instruction": "Instruction",
                              "accessory": "Accessory",
                              "duration": 10,
                              "phase": "hang",
                              "handUse": "double",
                              "side": "both",
                              "segments": $segmentsJson
                            }
                          ]
                        }
                      ],
                      "plans": [
                        {
                          "id": "plan",
                          "metadata": {
                            "title": "Plan",
                            "subtitle": "Subtitle",
                            "level": "All",
                            "sourceLabel": "Fixture",
                            "provenance": "custom"
                          },
                          "blocks": [{ "blockID": "main" }]
                        }
                      ]
                    }
                    """.trimIndent(),
            ),
        ),
    ).loadPlans().map { it.single().steps.single() }
}

private class StagedContentAssets(
    private val root: File,
) : ContentAssets {
    override fun list(path: String): List<String>? = File(root, path).list()?.toList()

    override fun read(path: String): String? = File(root, path).takeIf(File::isFile)?.readText()

    override fun exists(path: String): Boolean = File(root, path).isFile
}
