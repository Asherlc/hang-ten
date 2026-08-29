package com.hangten.android.sensors

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ForceSensorTransportTest {
    @Test
    fun boundedFakeSerializesOverflowBurstWithoutDroppingFrames() = runTest {
        val transport = FakeForceSensorTransport(notificationCapacity = 2, notificationScope = this)
        transport.emit(byteArrayOf(1))
        transport.emit(byteArrayOf(2))
        transport.emit(byteArrayOf(3))

        assertEquals(3, transport.notificationQueueState.value.pendingFrames)
        assertTrue(transport.notificationQueueState.value.isOverCapacity)
        val received = async { transport.notifications.take(3).map { it.single().toInt() }.toList() }
        advanceUntilIdle()

        assertEquals(listOf(1, 2, 3), received.await())
        assertEquals(0, transport.notificationQueueState.value.pendingFrames)
        assertTrue(!transport.notificationQueueState.value.isOverCapacity)
    }

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
