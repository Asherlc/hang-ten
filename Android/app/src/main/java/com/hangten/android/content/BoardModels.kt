package com.hangten.android.content

data class Point(
    val x: Float,
    val y: Float,
)

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

enum class HoldSize(
    val portableValue: String,
    /** Community-convention depth range in millimeters, matching iOS `HoldSize.depthRange`. */
    val depthRangeMillimeters: ClosedFloatingPointRange<Double>,
) {
    TINY("tiny", 0.0..8.0),
    SMALL("small", 8.0..15.0),
    MEDIUM("medium", 15.0..25.0),
    LARGE("large", 25.0..50.0),
    ;

    companion object {
        internal fun fromPortable(value: String): HoldSize? = entries.firstOrNull { it.portableValue == value }
    }
}

/** A contact or requirement depth: exactly one of a size category or a millimeter range. */
sealed interface HoldDepth {
    data class Category(val size: HoldSize) : HoldDepth
    data class Range(val minimum: Double, val maximum: Double) : HoldDepth

    /** Whether this requirement depth has enough evidence to match [contactDepth] (iOS `HoldDepth.matches`). */
    fun matches(contactDepth: HoldDepth?): Boolean = when {
        contactDepth == null -> false
        this is Category && contactDepth is Category -> size == contactDepth.size
        this is Category && contactDepth is Range ->
            size.depthRangeMillimeters.start <= contactDepth.maximum &&
                size.depthRangeMillimeters.endInclusive >= contactDepth.minimum
        this is Range && contactDepth is Range -> minimum <= contactDepth.maximum && maximum >= contactDepth.minimum
        else -> false
    }
}

/**
 * A physical contact from a schema v3 board package. On Android a contact is
 * drawn on the one original raster presentation whose `contactGeometry` owns it.
 */
data class BoardHold(
    val id: String,
    val name: String,
    val kind: String,
    val fingerCapacity: Int? = null,
    val handCapacity: Int? = null,
    val shape: String? = null,
    val depth: HoldDepth? = null,
    val gripTypes: Set<GripType> = emptySet(),
    val presentationId: String,
    val geometry: List<BoardGeometry>,
)

data class BoardPresentation(
    val id: String,
    val name: String,
    val assetPath: String,
    val aspectRatio: Float,
    val isDefault: Boolean,
    val orientation: BoardOrientation? = null,
    val suspension: BoardSuspension? = null,
)

data class BoardPosition(
    val id: String,
    val presentationId: String,
    val contactIds: List<String>,
)

data class BoardOrientation(
    val pivot: String,
    val rotations: Map<String, List<Float>>,
)

/**
 * Parsed suspension declaration retained for future Android model rendering.
 * Android currently has no 3D renderer, so the declaration's nested geometry
 * is intentionally not modeled here.
 */
data class BoardSuspension(
    val type: String,
)

data class Board(
    val id: String,
    val manufacturer: String,
    val name: String,
    val subtitle: String,
    val productUrl: String,
    val aspectRatio: Float,
    val presentations: List<BoardPresentation>,
    /** Physical contacts (schema v3 `contacts`) in canonical board order. */
    val holds: List<BoardHold>,
    val positions: List<BoardPosition> = emptyList(),
    /** Asset package identity; deliberately separate from the public logical board ID. */
    val packageSlug: String = id,
)

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

internal fun JsonValue.asCanonicalNineDecimalFloat(path: String): Float {
    val number = this as? JsonValue.Number
        ?: throw ContentDecodingException("$path must be a number.")
    val value = number.value
    if (!value.isFinite()) throw ContentDecodingException("$path must be finite.")
    val decimal = java.math.BigDecimal.valueOf(value)
    if (decimal.setScale(9, java.math.RoundingMode.HALF_EVEN).compareTo(decimal) != 0) {
        throw ContentDecodingException("$path must be rounded to nine decimal places.")
    }
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

internal fun JsonValue.Object.rejectUnknownKeys(path: String, allowed: Set<String>) {
    fields.keys.firstOrNull { it !in allowed }?.let { unknown ->
        throw ContentDecodingException("$path contains unknown key $unknown.")
    }
}

internal fun requireContentId(value: String, path: String) {
    if (value.isBlank()) throw ContentDecodingException("$path must not be blank.")
}

internal val CONTACT_KINDS = setOf("jug", "edge", "pocket", "pinch", "sloper", "gaston")
internal val CONTACT_SHAPES = setOf("flat", "round", "incut", "slot")
internal val FINGER_CAPACITY_RANGE = 1..4
internal val HAND_CAPACITY_RANGE = 1..2

internal fun JsonValue.asIntegerIn(range: IntRange, path: String): Int {
    val value = (this as? JsonValue.Number)?.value ?: throw ContentDecodingException("$path must be a number.")
    if (!value.isFinite() || value != value.toInt().toDouble() || value.toInt() !in range) {
        throw ContentDecodingException("$path must be an integer within $range.")
    }
    return value.toInt()
}

/** Decodes `{"category": size}` or `{"range": {"minimum", "maximum"}}`, exactly one of the two. */
internal fun decodeHoldDepth(value: JsonValue, path: String): HoldDepth {
    val objectValue = value.asObject(path)
    objectValue.rejectUnknownKeys(path, setOf("category", "range"))
    val category = objectValue.optional("category")
    val range = objectValue.optional("range")
    if ((category == null) == (range == null)) {
        throw ContentDecodingException("$path must contain exactly one of category or range.")
    }
    if (category != null) {
        val size = category.asString("$path.category")
        return HoldDepth.Category(
            HoldSize.fromPortable(size) ?: throw ContentDecodingException("$path.category is unsupported: $size."),
        )
    }
    val rangeObject = range!!.asObject("$path.range")
    rangeObject.rejectUnknownKeys("$path.range", setOf("minimum", "maximum"))
    val minimum = (rangeObject.required("minimum", "$path.range") as? JsonValue.Number)?.value
        ?: throw ContentDecodingException("$path.range.minimum must be a number.")
    val maximum = (rangeObject.required("maximum", "$path.range") as? JsonValue.Number)?.value
        ?: throw ContentDecodingException("$path.range.maximum must be a number.")
    if (minimum < 0 || minimum > maximum) {
        throw ContentDecodingException("$path.range must be non-negative and ordered.")
    }
    return HoldDepth.Range(minimum, maximum)
}
