package com.hangten.android.sensors

enum class ForceSensorProfile(
    val displayName: String,
    val notificationCharacteristics: Set<ForceSensorCharacteristic>,
    val writeCharacteristic: ForceSensorCharacteristic?,
) {
    Automatic("Automatic", emptySet(), null),
    Motherboard(
        "Motherboard",
        setOf(ForceSensorCharacteristic(MotherboardProtocol.SERVICE_UUID, MotherboardProtocol.TX_UUID)),
        ForceSensorCharacteristic(MotherboardProtocol.SERVICE_UUID, MotherboardProtocol.RX_UUID),
    ),
    Progressor(
        "Tindeq Progressor",
        setOf(ForceSensorCharacteristic(ProgressorProtocolAdapter.SERVICE_UUID, ProgressorProtocolAdapter.NOTIFICATION_UUID)),
        ForceSensorCharacteristic(ProgressorProtocolAdapter.SERVICE_UUID, ProgressorProtocolAdapter.WRITE_UUID),
    ),
    PitchSix(
        "PitchSix Force Board",
        setOf(ForceSensorCharacteristic(PitchSixProtocolAdapter.FORCE_SERVICE_UUID, PitchSixProtocolAdapter.FORCE_NOTIFICATION_UUID)),
        ForceSensorCharacteristic(PitchSixProtocolAdapter.MODE_SERVICE_UUID, PitchSixProtocolAdapter.MODE_WRITE_UUID),
    ),
    GenericProgressor(
        "Generic Progressor-compatible",
        setOf(ForceSensorCharacteristic(ProgressorProtocolAdapter.SERVICE_UUID, ProgressorProtocolAdapter.NOTIFICATION_UUID)),
        ForceSensorCharacteristic(ProgressorProtocolAdapter.SERVICE_UUID, ProgressorProtocolAdapter.WRITE_UUID),
    );

    val serviceUuids: Set<String>
        get() = linkedSetOf<String>().also { serviceUuids ->
            notificationCharacteristics.forEach { characteristic -> serviceUuids += characteristic.serviceUuid }
            writeCharacteristic?.serviceUuid?.let { serviceUuids += it }
        }

    companion object {
        val connectable = entries.filter { it != Automatic }
        val automaticCandidates = listOf(Motherboard, Progressor, PitchSix)
    }
}

enum class ForceSensorCommand { Tare, Start, Stop }

data class ForceSensorCharacteristic(val serviceUuid: String, val characteristicUuid: String)

data class ForceSensorAdvertisement(
    val name: String? = null,
    val serviceUuids: Set<String> = emptySet(),
)

data class ForceSensorSample(val kilogramsForce: Double, val receivedAtMs: Long)

class ProgressorProtocolAdapter(val profile: ForceSensorProfile) {
    init { require(profile == ForceSensorProfile.Progressor || profile == ForceSensorProfile.GenericProgressor) }

    fun matches(advertisement: ForceSensorAdvertisement): Boolean = when (profile) {
        ForceSensorProfile.Progressor -> advertisement.name?.startsWith("Progressor") == true
        ForceSensorProfile.GenericProgressor -> SERVICE_UUID in advertisement.serviceUuids
        else -> false
    }

    fun payload(command: ForceSensorCommand): ByteArray = when (command) {
        ForceSensorCommand.Tare -> byteArrayOf(0x64)
        ForceSensorCommand.Start -> byteArrayOf(0x65)
        ForceSensorCommand.Stop -> byteArrayOf(0x66)
    }

    fun decode(frame: ByteArray, receivedAtMs: Long): List<ForceSensorSample>? {
        if (frame.size < 2 || frame[0].u8() != 1) return null
        val length = frame[1].u8()
        if (frame.size - 2 != length || length % 8 != 0) return null
        return (2 until frame.size step 8).map { offset ->
            val bits = frame.uint32LittleEndian(offset)
            val force = Float.fromBits(bits.toInt()).toDouble()
            if (!force.isFinite() || force < 0) return null
            ForceSensorSample(force, receivedAtMs)
        }
    }

    companion object {
        const val SERVICE_UUID = "7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57"
        const val NOTIFICATION_UUID = "7E4E1702-1EA6-40C9-9DCC-13D34FFEAD57"
        const val WRITE_UUID = "7E4E1703-1EA6-40C9-9DCC-13D34FFEAD57"
    }
}

class PitchSixProtocolAdapter {
    fun matches(advertisement: ForceSensorAdvertisement): Boolean = advertisement.name == "Force Board"

    fun payload(command: ForceSensorCommand): ByteArray = when (command) {
        ForceSensorCommand.Start -> byteArrayOf(0x04)
        ForceSensorCommand.Tare -> byteArrayOf(0x05)
        ForceSensorCommand.Stop -> byteArrayOf(0x07)
    }

    fun decode(frame: ByteArray, receivedAtMs: Long): List<ForceSensorSample>? {
        if (frame.size < 2) return null
        val count = frame[0].u8() shl 8 or frame[1].u8()
        if (count <= 0 || frame.size != 2 + count * 3) return null
        return (0 until count).map { sampleIndex ->
            val offset = 2 + sampleIndex * 3
            val pounds = frame[offset].u8() * 32_768.0 + frame[offset + 1].u8() * 256.0 + frame[offset + 2].u8()
            ForceSensorSample(pounds / POUNDS_PER_KILOGRAM_FORCE, receivedAtMs)
        }
    }

    companion object {
        const val FORCE_SERVICE_UUID = "9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0"
        const val FORCE_NOTIFICATION_UUID = "9A88D682-8DF2-4AFE-9E0D-C2BBBE773DD0"
        const val MODE_SERVICE_UUID = "467A8516-6E39-11EB-9439-0242AC130002"
        const val MODE_WRITE_UUID = "467A8517-6E39-11EB-9439-0242AC130002"
        private const val POUNDS_PER_KILOGRAM_FORCE = 2.20462262185
    }
}

private fun Byte.u8(): Int = toInt() and 0xff

private fun ByteArray.uint32LittleEndian(offset: Int): UInt =
    (this[offset].u8().toUInt()) or
        (this[offset + 1].u8().toUInt() shl 8) or
        (this[offset + 2].u8().toUInt() shl 16) or
        (this[offset + 3].u8().toUInt() shl 24)
