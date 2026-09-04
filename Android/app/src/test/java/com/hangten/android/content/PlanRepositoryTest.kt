package com.hangten.android.content

import java.io.File
import javax.imageio.ImageIO
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
                          "boardMappings": [],
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
                                  "targets": [],
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
                                  "targets": [],
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
        val assets = StagedContentAssets(File("build/generated/assets/canonical"))

        val boards = AssetBoardRepository(assets).loadBoards().getOrThrow()
        val steps = AssetPlanRepository(assets).loadPlans().getOrThrow()
            .flatMap { it.steps }
        val maxHang = steps.first { it.id == "max-hangs-1" }

        assertTrue(boards.isNotEmpty())
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
                          "boardMappings": [],
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
                                  "targets": [],
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
}

private class StagedContentAssets(
    private val root: File,
) : ContentAssets {
    override fun list(path: String): List<String>? = File(root, path).list()?.toList()

    override fun read(path: String): String? = File(root, path).takeIf(File::isFile)?.readText()

    override fun exists(path: String): Boolean = File(root, path).isFile

    override fun imageDimensions(path: String): ContentImageDimensions? {
        val file = File(root, path).takeIf(File::isFile) ?: return null
        return runCatching {
            ImageIO.createImageInputStream(file)?.use { input ->
                val readers = ImageIO.getImageReaders(input)
                if (!readers.hasNext()) return@use null
                val reader = readers.next()
                try {
                    reader.input = input
                    ContentImageDimensions(width = reader.getWidth(0), height = reader.getHeight(0))
                } finally {
                    reader.dispose()
                }
            }
        }.getOrNull()
    }
}
