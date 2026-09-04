package com.hangten.android.content

data class Point(
    val x: Float,
    val y: Float,
)

data class BoardCordSize(
    val width: Float,
    val height: Float,
)

data class BoardCordRect(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float,
)

sealed interface BoardCordRig {
    data class DirectTwoAnchor(
        val sceneSize: BoardCordSize,
        val sourceFrame: BoardCordRect,
        val innerFaceFrame: BoardCordRect,
        val attachmentPoints: List<Point>,
        val pullPoint: Point,
        val eyeletRadius: Float,
    ) : BoardCordRig
}

data class BoardGeometryRotationAnchor(
    val x: Float,
    val y: Float,
) {
    companion object {
        val Center = BoardGeometryRotationAnchor(0.5f, 0.5f)
    }
}

data class NormalizedFrame(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float,
)

sealed interface PathCommand {
    data class Move(val to: Point) : PathCommand
    data class Line(val to: Point) : PathCommand
    data class Quad(val to: Point, val control: Point) : PathCommand
    data class Curve(val to: Point, val control1: Point, val control2: Point) : PathCommand
    data object Close : PathCommand
}

sealed interface HoldShape {
    data class RoundedRect(val cornerRadiusFraction: Float) : HoldShape
    data class Path(val commands: List<PathCommand>) : HoldShape
}

data class BoardGeometry(
    val frame: NormalizedFrame,
    val shape: HoldShape,
)

data class SemanticHoldMapping(
    val holdIds: List<String> = emptyList(),
    val kind: String? = null,
)

data class BoardHold(
    val id: String,
    val name: String,
    val kind: String,
    val features: Set<String> = emptySet(),
    val fingerCapacity: Int? = null,
    val presentationId: String,
    val geometry: List<BoardGeometry>,
)

data class BoardPresentation(
    val id: String,
    val name: String,
    val assetPath: String,
    val aspectRatio: Float,
    val isDefault: Boolean,
    val sourcePresentationId: String? = null,
    val isInverted: Boolean = false,
    val rotationDegrees: Float? = null,
    val geometryRotationAnchor: BoardGeometryRotationAnchor? = null,
    val cordRig: BoardCordRig? = null,
    val availableHoldIds: List<String>? = null,
) {
    val resolvedRotationDegrees: Float
        get() = rotationDegrees ?: if (isInverted) 180f else 0f
}

data class Board(
    val id: String,
    val manufacturer: String,
    val name: String,
    val subtitle: String,
    val productUrl: String,
    val aspectRatio: Float,
    val presentations: List<BoardPresentation>,
    val holds: List<BoardHold>,
    val semanticHolds: Map<String, SemanticHoldMapping> = emptyMap(),
    val packageName: String = id,
) {
    val defaultPresentation: BoardPresentation?
        get() = presentations.firstOrNull { it.isDefault } ?: presentations.firstOrNull()

    fun presentation(id: String?): BoardPresentation? =
        presentations.firstOrNull { it.id == id }

    fun canonicalPresentation(presentation: BoardPresentation): BoardPresentation? =
        presentation(presentation.sourcePresentationId ?: presentation.id)

    fun resolvedCordRig(presentation: BoardPresentation): BoardCordRig? =
        canonicalPresentation(presentation)?.cordRig

    fun artworkPresentation(presentation: BoardPresentation): BoardPresentation? =
        if (resolvedCordRig(presentation) == null && presentation.rotationDegrees == null) {
            presentation
        } else {
            canonicalPresentation(presentation)
        }

    fun holdPresentationId(presentation: BoardPresentation): String =
        presentation.sourcePresentationId ?: presentation.id

    fun effectiveHolds(presentation: BoardPresentation): List<BoardHold> {
        val canonicalPresentationId = holdPresentationId(presentation)
        val availableHoldIds = presentation.availableHoldIds?.toSet()
        return holds.filter { hold ->
            hold.presentationId == canonicalPresentationId &&
                (availableHoldIds == null || hold.id in availableHoldIds)
        }
    }

    fun presentationContaining(
        holdIds: Set<String>,
        preferredPresentationId: String? = null,
    ): BoardPresentation? {
        val candidates = buildList {
            presentation(preferredPresentationId)?.let(::add)
            defaultPresentation?.let(::add)
            addAll(presentations)
        }.distinctBy { it.id }

        return candidates.firstOrNull { candidate ->
            val availableIds = effectiveHolds(candidate).mapTo(mutableSetOf()) { it.id }
            availableIds.containsAll(holdIds)
        }
    }
}

internal class ContentDecodingException(message: String) : IllegalArgumentException(message)

internal sealed interface JsonValue {
    data class Object(val fields: Map<String, JsonValue>) : JsonValue
    data class Array(val values: List<JsonValue>) : JsonValue
    data class StringValue(val value: String) : JsonValue
    data class Number(val value: Double) : JsonValue
    data class BooleanValue(val value: Boolean) : JsonValue
    data object Null : JsonValue
}

internal class JsonParser(
    private val input: String,
) {
    private var index = 0

    fun parse(): JsonValue {
        skipWhitespace()
        val value = parseValue()
        skipWhitespace()
        require(index == input.length) { "Malformed JSON: unexpected content at position $index." }
        return value
    }

    private fun parseValue(): JsonValue {
        skipWhitespace()
        return when (peek()) {
            '{' -> parseObject()
            '[' -> parseArray()
            '"' -> JsonValue.StringValue(parseString())
            't' -> parseLiteral("true", JsonValue.BooleanValue(true))
            'f' -> parseLiteral("false", JsonValue.BooleanValue(false))
            'n' -> parseLiteral("null", JsonValue.Null)
            '-', in '0'..'9' -> parseNumber()
            else -> fail("Malformed JSON: expected a value at position $index.")
        }
    }

    private fun parseObject(): JsonValue.Object {
        expect('{')
        skipWhitespace()
        val fields = linkedMapOf<String, JsonValue>()
        if (consume('}')) return JsonValue.Object(fields)
        while (true) {
            skipWhitespace()
            require(peek() == '"') { "Malformed JSON: expected an object key at position $index." }
            val key = parseString()
            require(fields[key] == null) { "Malformed JSON: duplicate object key \"$key\"." }
            skipWhitespace()
            expect(':')
            fields[key] = parseValue()
            skipWhitespace()
            if (consume('}')) return JsonValue.Object(fields)
            expect(',')
        }
    }

    private fun parseArray(): JsonValue.Array {
        expect('[')
        skipWhitespace()
        val values = mutableListOf<JsonValue>()
        if (consume(']')) return JsonValue.Array(values)
        while (true) {
            values += parseValue()
            skipWhitespace()
            if (consume(']')) return JsonValue.Array(values)
            expect(',')
        }
    }

    private fun parseString(): String {
        expect('"')
        val result = StringBuilder()
        while (index < input.length) {
            when (val character = input[index++]) {
                '"' -> return result.toString()
                '\\' -> result.append(parseEscape())
                in '\u0000'..'\u001f' -> fail("Malformed JSON: control character in string.")
                else -> result.append(character)
            }
        }
        return fail("Malformed JSON: unterminated string.")
    }

    private fun parseEscape(): Char = when (val character = next()) {
        '"', '\\', '/' -> character
        'b' -> '\b'
        'f' -> '\u000c'
        'n' -> '\n'
        'r' -> '\r'
        't' -> '\t'
        'u' -> {
            require(index + 4 <= input.length) { "Malformed JSON: incomplete unicode escape." }
            val digits = input.substring(index, index + 4)
            require(digits.all { it.digitToIntOrNull(16) != null }) {
                "Malformed JSON: invalid unicode escape."
            }
            index += 4
            digits.toInt(16).toChar()
        }
        else -> fail("Malformed JSON: invalid escape \\$character.")
    }

    private fun parseNumber(): JsonValue.Number {
        val start = index
        consume('-')
        when (peek()) {
            '0' -> index++
            in '1'..'9' -> {
                index++
                while (peek() in '0'..'9') index++
            }
            else -> fail("Malformed JSON: invalid number at position $start.")
        }
        if (consume('.')) {
            require(peek() in '0'..'9') { "Malformed JSON: invalid fraction at position $index." }
            while (peek() in '0'..'9') index++
        }
        if (peek() == 'e' || peek() == 'E') {
            index++
            if (peek() == '+' || peek() == '-') index++
            require(peek() in '0'..'9') { "Malformed JSON: invalid exponent at position $index." }
            while (peek() in '0'..'9') index++
        }
        val value = input.substring(start, index).toDoubleOrNull()
            ?: return fail("Malformed JSON: invalid number at position $start.")
        require(value.isFinite()) { "Malformed JSON: non-finite number at position $start." }
        return JsonValue.Number(value)
    }

    private fun parseLiteral(literal: String, value: JsonValue): JsonValue {
        require(input.regionMatches(index, literal, 0, literal.length)) {
            "Malformed JSON: expected $literal at position $index."
        }
        index += literal.length
        return value
    }

    private fun skipWhitespace() {
        while (peek() in listOf(' ', '\n', '\r', '\t')) index++
    }

    private fun expect(character: Char) {
        require(consume(character)) { "Malformed JSON: expected '$character' at position $index." }
    }

    private fun consume(character: Char): Boolean =
        if (peek() == character) {
            index++
            true
        } else {
            false
        }

    private fun peek(): Char? = input.getOrNull(index)

    private fun next(): Char = input.getOrNull(index++) ?: fail("Malformed JSON: unexpected end of input.")

    private fun fail(message: String): Nothing = throw ContentDecodingException(message)
}

internal fun JsonValue.asObject(path: String): JsonValue.Object =
    this as? JsonValue.Object ?: throw ContentDecodingException("$path must be an object.")

internal fun JsonValue.asArray(path: String): List<JsonValue> =
    (this as? JsonValue.Array)?.values ?: throw ContentDecodingException("$path must be an array.")

internal fun JsonValue.asString(path: String): String =
    (this as? JsonValue.StringValue)?.value ?: throw ContentDecodingException("$path must be a string.")

internal fun JsonValue.asFiniteFloat(path: String): Float {
    val value = (this as? JsonValue.Number)?.value
        ?: throw ContentDecodingException("$path must be a number.")
    val floatValue = value.toFloat()
    if (!floatValue.isFinite()) throw ContentDecodingException("$path must be finite.")
    return floatValue
}

internal fun JsonValue.Object.required(name: String, path: String): JsonValue =
    fields[name] ?: throw ContentDecodingException("$path.$name is required.")

internal fun JsonValue.Object.optional(name: String): JsonValue? = fields[name]

internal fun JsonValue.Object.requiredString(name: String, path: String): String =
    required(name, path).asString("$path.$name").also { requireContentId(it, "$path.$name") }

internal fun JsonValue.Object.requiredText(name: String, path: String): String =
    required(name, path).asString("$path.$name")

internal fun requireContentId(value: String, path: String) {
    if (value.isBlank()) throw ContentDecodingException("$path must not be blank.")
}
