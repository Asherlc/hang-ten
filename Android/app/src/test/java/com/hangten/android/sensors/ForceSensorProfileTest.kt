package com.hangten.android.sensors

import org.junit.Assert.assertEquals
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ForceSensorProfileTest {
    @Test
    fun `profile service UUIDs include notification and write services`() {
        assertEquals(
            setOf(PitchSixProtocolAdapter.FORCE_SERVICE_UUID, PitchSixProtocolAdapter.MODE_SERVICE_UUID),
            ForceSensorProfile.PitchSix.serviceUuids,
        )
    }

    @Test
    fun progressorRecognizesNamedAndGenericProfilesAndDecodesLittleEndianSamples() {
        val named = ProgressorProtocolAdapter(ForceSensorProfile.Progressor)
        val generic = ProgressorProtocolAdapter(ForceSensorProfile.GenericProgressor)
        assertTrue(named.matches(ForceSensorAdvertisement(name = "Progressor 3000")))
        assertTrue(generic.matches(ForceSensorAdvertisement(serviceUuids = setOf(ProgressorProtocolAdapter.SERVICE_UUID))))
        assertArrayEquals(byteArrayOf(0x64), named.payload(ForceSensorCommand.Tare))
        assertEquals(12.5, named.decode(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0), 3L)!!.single().kilogramsForce, 0.0001)
    }

    @Test
    fun pitchSixRequiresExactNameUsesBigEndian24BitPoundsAndRejectsMalformedFrames() {
        val adapter = PitchSixProtocolAdapter()
        assertTrue(adapter.matches(ForceSensorAdvertisement(name = "Force Board")))
        assertArrayEquals(byteArrayOf(5), adapter.payload(ForceSensorCommand.Tare))
        assertEquals(1.0 / 2.20462262185, adapter.decode(byteArrayOf(0, 1, 0, 0, 1), 4L)!!.single().kilogramsForce, 0.0001)
        assertNull(adapter.decode(byteArrayOf(0, 2, 0, 0, 1), 4L))
    }
}
