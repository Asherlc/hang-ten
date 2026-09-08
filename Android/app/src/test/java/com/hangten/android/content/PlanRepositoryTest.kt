package com.hangten.android.content

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
        return runCatching { pngHeaderDimensions(file) }.getOrNull()
    }
}

private fun pngHeaderDimensions(file: File): ContentImageDimensions? {
    val header = ByteArray(24)
    file.inputStream().use { input ->
        var offset = 0
        while (offset < header.size) {
            val count = input.read(header, offset, header.size - offset)
            if (count < 0) return null
            offset += count
        }
    }
    if (!header.copyOfRange(0, PNG_SIGNATURE.size).contentEquals(PNG_SIGNATURE) ||
        !header.copyOfRange(12, 16).contentEquals(byteArrayOf(0x49, 0x48, 0x44, 0x52))
    ) return null
    val width = header.bigEndianInt(16)
    val height = header.bigEndianInt(20)
    return if (width > 0 && height > 0) ContentImageDimensions(width, height) else null
}

private fun ByteArray.bigEndianInt(offset: Int): Int =
    ((this[offset].toInt() and 0xff) shl 24) or
        ((this[offset + 1].toInt() and 0xff) shl 16) or
        ((this[offset + 2].toInt() and 0xff) shl 8) or
        (this[offset + 3].toInt() and 0xff)

private val PNG_SIGNATURE = byteArrayOf(
    0x89.toByte(),
    0x50,
    0x4e,
    0x47,
    0x0d,
    0x0a,
    0x1a,
    0x0a,
)
