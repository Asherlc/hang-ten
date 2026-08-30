package com.hangten.android.editor

import android.content.res.AssetManager

class AndroidAssetBoardPackageSource(private val assets: AssetManager) : BoardPackageSource {
    override fun filesFor(slug: String): List<BoardPackageSourceFile> = walk("Hangboards/$slug")
        .map { path ->
            val relative = path.removePrefix("Hangboards/$slug/")
            BoardPackageSourceFile(relative, assets.open(path).use { it.readBytes() })
        }

    private fun walk(path: String): List<String> {
        val children = assets.list(path)?.toList().orEmpty()
        if (children.isEmpty()) return listOf(path)
        return children.flatMap { child -> walk("$path/$child") }
    }
}
