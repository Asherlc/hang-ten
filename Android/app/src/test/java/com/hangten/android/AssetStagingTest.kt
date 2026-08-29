package com.hangten.android

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

class AssetStagingTest {
    @Test
    fun stagedAssetsContainPlanAndEveryBoardManifest() {
        val root = File("build/generated/assets/canonical")
        assertTrue(File(root, "PlanLibrary.json").isFile)
        assertTrue(File(root, "Hangboards").listFiles().orEmpty().all { File(it, "board.json").isFile })
    }
}
