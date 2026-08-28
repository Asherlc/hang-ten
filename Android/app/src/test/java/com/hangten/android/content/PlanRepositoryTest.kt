package com.hangten.android.content

import org.junit.Assert.assertEquals
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
}
