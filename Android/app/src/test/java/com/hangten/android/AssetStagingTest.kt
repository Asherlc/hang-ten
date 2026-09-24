package com.hangten.android

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

class AssetStagingTest {
    @Test
    fun stagedAssetsContainPlanAndEveryBoardManifest() {
        val root = File("build/generated/assets/canonical")
        assertTrue(File(root, "PlanLibrary.json").isFile)
        val packages = File(root, "Hangboards").listFiles().orEmpty()
        assertTrue(packages.isNotEmpty())
        // CAD-backed packages commit no board.json; staging generates it from the FCStd.
        assertTrue(packages.all { File(it, "board.json").isFile })
    }

    @Test
    fun cadAuthoringSourcesAreGeneratedIntoBoardManifestsAndNeverStaged() {
        val repository = File("../..").canonicalFile
        val staged = File("build/generated/assets/canonical/Hangboards")
        val cadPackages = File(repository, "Hangboards").listFiles().orEmpty()
            .filter { File(it, "${it.name}.FCStd").isFile }
        assertTrue(cadPackages.isNotEmpty())
        cadPackages.forEach { assertTrue(File(staged, "${it.name}/board.json").isFile) }
        assertTrue(staged.walkTopDown().none { it.name.endsWith(".FCStd") })
    }
}
