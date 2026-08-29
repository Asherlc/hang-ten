package com.hangten.android.sensors

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MotherboardProtocolTest {
    @Test
    fun parserBuffersFragmentsAndDecodesSigned24BitPackets() {
        val parser = MotherboardProtocolParser()
        assertTrue(parser.append("34126400020100fe".encodeToByteArray(), 42L).isEmpty())

        assertEquals(
            listOf(
                MotherboardProtocolEvent.RawPacket(
                    MotherboardRawPacket(0x1234u, 0x64u, listOf(0x000102, -2, 0x010203, 0)),
                    42L,
                ),
            ),
            parser.append("ffff030201000000\r\n".encodeToByteArray(), 42L),
        )
    }

    @Test
    fun parserAcceptsCalibrationStreamAndRejectsOversizedFramesWithoutLosingFollowingFrame() {
        val parser = MotherboardProtocolParser(maximumBufferSize = 9)

        assertEquals(
            listOf(
                MotherboardProtocolEvent.Error("Motherboard response exceeded the receive buffer limit."),
                MotherboardProtocolEvent.StreamStarted(30),
            ),
            parser.append("1234567890\r\nStream:30\r\n".encodeToByteArray(), 1L),
        )
        val normalParser = MotherboardProtocolParser()
        assertEquals(
            listOf(MotherboardProtocolEvent.Calibration(MotherboardCalibrationRow(0, 1, 2.5, 100))),
            normalParser.append("0,1,2.5,100,\r\n".encodeToByteArray(), 1L),
        )
    }

    @Test
    fun calibrationInterpolatesClampsAndDecodingAppliesPolarityBeforeTare() {
        val calibration = linearCalibration()
        assertEquals(0.0, calibration.massKgf(0, -50)!!, 0.0001)
        assertEquals(10.0, calibration.massKgf(0, 150)!!, 0.0001)

        val measurement = MotherboardProtocol.decode(
            MotherboardRawPacket(1u, 2u, listOf(90, 60, 70, 100)),
            timestampMs = 1L,
            calibration = calibration,
            tareKgf = listOf(1.0, -8.0, -9.0, 4.0),
        )
        assertEquals(listOf(8.0, 2.0, 2.0, 6.0), measurement.sensorLoadsKgf)
        assertEquals(12.0, measurement.aggregateLoadKgf, 0.0001)
    }

    private fun linearCalibration() = MotherboardCalibration(
        (0..3).flatMap { sensor ->
            listOf(
                MotherboardCalibrationRow(sensor, 0, 0.0, 0),
                MotherboardCalibrationRow(sensor, 1, 10.0, 100),
            )
        },
    )
}
