package com.hangten.android.sensors

data class MotherboardCalibrationRow(
    val sensor: Int,
    val calibrationPoint: Int,
    val massKgf: Double,
    val adc: Int,
)

data class MotherboardRawPacket(
    val sampleNumber: UShort,
    val batteryValue: UShort,
    val adcValues: List<Int>,
)

sealed interface MotherboardProtocolEvent {
    data class Calibration(val row: MotherboardCalibrationRow) : MotherboardProtocolEvent
    data class RawPacket(val packet: MotherboardRawPacket, val timestampMs: Long) : MotherboardProtocolEvent
    data class StreamStarted(val rate: Int) : MotherboardProtocolEvent
    data class Error(val message: String) : MotherboardProtocolEvent
}

class MotherboardProtocolParser(
    private val maximumBufferSize: Int = 4_096,
) {
    private var buffer = ByteArray(0)

    fun append(bytes: ByteArray, receivedAtMs: Long): List<MotherboardProtocolEvent> {
        buffer += bytes
        val events = mutableListOf<MotherboardProtocolEvent>()
        while (true) {
            val delimiter = buffer.indexOfCrLf()
            if (delimiter < 0) break
            val line = buffer.copyOfRange(0, delimiter)
            buffer = buffer.copyOfRange(delimiter + 2, buffer.size)
            if (line.size > maximumBufferSize) {
                events += MotherboardProtocolEvent.Error(OVERFLOW_MESSAGE)
            } else {
                parse(line.decodeToString(), receivedAtMs)?.let(events::add)
            }
        }
        if (buffer.size > maximumBufferSize) {
            buffer = ByteArray(0)
            events += MotherboardProtocolEvent.Error(OVERFLOW_MESSAGE)
        }
        return events
    }

    private fun parse(line: String, receivedAtMs: Long): MotherboardProtocolEvent? =
        rawPacket(line)?.let { MotherboardProtocolEvent.RawPacket(it, receivedAtMs) }
            ?: calibrationRow(line)?.let { MotherboardProtocolEvent.Calibration(it) }
            ?: line.removePrefix("Stream:").toIntOrNull()?.takeIf { line.startsWith("Stream:") }
                ?.let(MotherboardProtocolEvent::StreamStarted)
            ?: line.takeIf { it.startsWith("Error") }?.let(MotherboardProtocolEvent::Error)

    private fun calibrationRow(line: String): MotherboardCalibrationRow? {
        val fields = line.split(',')
        if (fields.size !in 4..5 || fields.size == 5 && fields[4].isNotEmpty()) return null
        val sensor = fields[0].toIntOrNull()?.takeIf { it in 0..3 } ?: return null
        return MotherboardCalibrationRow(
            sensor = sensor,
            calibrationPoint = fields[1].toIntOrNull() ?: return null,
            massKgf = fields[2].toDoubleOrNull()?.takeIf(Double::isFinite) ?: return null,
            adc = fields[3].toIntOrNull() ?: return null,
        )
    }

    private fun rawPacket(line: String): MotherboardRawPacket? {
        if (line.length != 32 || !line.all(Char::isDigitOrHexLetter)) return null
        val bytes = line.chunked(2).map { it.toIntOrNull(16)?.toByte() ?: return null }
        return MotherboardRawPacket(
            sampleNumber = ((bytes[0].u8() or (bytes[1].u8() shl 8))).toUShort(),
            batteryValue = ((bytes[2].u8() or (bytes[3].u8() shl 8))).toUShort(),
            adcValues = (4..13 step 3).map { offset ->
                val value = bytes[offset].u8() or (bytes[offset + 1].u8() shl 8) or (bytes[offset + 2].u8() shl 16)
                if ((value and 0x800000) == 0) value else value or -0x1000000
            },
        )
    }

    private fun ByteArray.indexOfCrLf(): Int = indices.firstOrNull { index ->
        index + 1 < size && this[index] == '\r'.code.toByte() && this[index + 1] == '\n'.code.toByte()
    } ?: -1

    private fun Byte.u8(): Int = toInt() and 0xff

    private companion object {
        const val OVERFLOW_MESSAGE = "Motherboard response exceeded the receive buffer limit."
    }
}

class MotherboardCalibration(rows: List<MotherboardCalibrationRow>) {
    private val rowsBySensor = rows.filter { it.sensor in 0..3 }
        .groupBy(MotherboardCalibrationRow::sensor)
        .mapValues { (_, values) -> values.sortedBy(MotherboardCalibrationRow::adc) }

    fun massKgf(sensor: Int, adc: Int): Double? {
        val rows = rowsBySensor[sensor].orEmpty()
        val first = rows.firstOrNull() ?: return null
        if (rows.size == 1 || adc <= first.adc) return first.massKgf
        val last = rows.last()
        if (adc >= last.adc) return last.massKgf
        val upperIndex = rows.indexOfFirst { it.adc >= adc }
        val lower = rows[upperIndex - 1]
        val upper = rows[upperIndex]
        val span = (upper.adc - lower.adc).toDouble()
        if (span == 0.0) return upper.massKgf
        return lower.massKgf + (adc - lower.adc) / span * (upper.massKgf - lower.massKgf)
    }
}

data class MotherboardMeasurement(
    val timestampMs: Long,
    val sampleNumber: UShort,
    val batteryValue: UShort,
    val rawAdcValues: List<Int>,
    val sensorLoadsKgf: List<Double>,
    val aggregateLoadKgf: Double,
)

object MotherboardProtocol {
    const val SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
    const val RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    const val TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
    private val channelPolarities = listOf(1.0, -1.0, -1.0, 1.0)

    fun command(text: String): ByteArray = text.encodeToByteArray()

    fun streamCommand(rate: Int): ByteArray = command("S${rate.coerceAtLeast(1)}")

    fun decode(
        packet: MotherboardRawPacket,
        timestampMs: Long,
        calibration: MotherboardCalibration,
        tareKgf: List<Double>,
    ): MotherboardMeasurement {
        val loads = (0..3).map { sensor ->
            val calibrated = finite(calibration.massKgf(sensor, packet.adcValues.getOrElse(sensor) { 0 }) ?: 0.0)
            finite(finite(calibrated * channelPolarities[sensor]) - finite(tareKgf.getOrElse(sensor) { 0.0 }))
        }
        return MotherboardMeasurement(
            timestampMs = timestampMs,
            sampleNumber = packet.sampleNumber,
            batteryValue = packet.batteryValue,
            rawAdcValues = packet.adcValues,
            sensorLoadsKgf = loads,
            aggregateLoadKgf = loads.take(3).fold(0.0) { total, load -> finite(total + load) }.coerceAtLeast(0.0),
        )
    }

    private fun finite(value: Double): Double = when {
        value.isNaN() -> 0.0
        value == Double.POSITIVE_INFINITY -> Double.MAX_VALUE
        value == Double.NEGATIVE_INFINITY -> -Double.MAX_VALUE
        else -> value
    }
}

private fun Char.isDigitOrHexLetter(): Boolean = isDigit() || this in 'a'..'f' || this in 'A'..'F'
