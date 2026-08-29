package com.hangten.android.sensors

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ForceSensorTransportTest {
    @Test
    fun deterministicTransportScansConnectsSubscribesWritesAndEmitsNotifications() = runTest {
        val transport = FakeForceSensorTransport()
        val profile = ForceSensorProfile.Progressor
        transport.enqueue(ForceSensorAdvertisement(name = "Progressor 200"))

        assertEquals(listOf("Progressor 200"), transport.scan(profile).map { it.name })
        transport.connect(ForceSensorAdvertisement(name = "Progressor 200"), profile)
        transport.subscribe(profile.notificationCharacteristics.single())
        transport.write(profile.writeCharacteristic!!, byteArrayOf(0x65))
        transport.emit(byteArrayOf(1, 0))

        assertEquals(byteArrayOf(1, 0).toList(), transport.notifications.first().toList())
        assertTrue(transport.operations.contains("connect:Progressor"))
    }
}
