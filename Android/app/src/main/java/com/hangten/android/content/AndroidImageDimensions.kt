package com.hangten.android.content

import android.graphics.BitmapFactory
import java.io.InputStream

internal fun decodePngImageDimensions(data: ByteArray): ContentImageDimensions? {
    val options = bitmapBoundsOptions()
    BitmapFactory.decodeByteArray(data, 0, data.size, options)
    return options.pngDimensions()
}

internal fun decodePngImageDimensions(input: InputStream): ContentImageDimensions? {
    val options = bitmapBoundsOptions()
    BitmapFactory.decodeStream(input, null, options)
    return options.pngDimensions()
}

private fun bitmapBoundsOptions(): BitmapFactory.Options =
    BitmapFactory.Options().apply { inJustDecodeBounds = true }

private fun BitmapFactory.Options.pngDimensions(): ContentImageDimensions? =
    takeIf { outMimeType == "image/png" && outWidth > 0 && outHeight > 0 }
        ?.let { ContentImageDimensions(width = outWidth, height = outHeight) }
