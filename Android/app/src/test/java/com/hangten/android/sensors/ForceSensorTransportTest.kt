package com.hangten.android.sensors

import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ForceSensorTransportTest {
    @Test
    fun concurrentCallbacksNeverAdmitAfterTheFiniteQueueTurnsTerminal() {
        val terminalErrors = mutableListOf<Throwable>()
        val queue = SerialNotificationQueue(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.Default),
            capacityFrames = 1,
            onTerminal = { terminalErrors += it },
        )
        val start = CountDownLatch(1)
        val accepted = AtomicInteger(0)
        val executor = Executors.newFixedThreadPool(8)
        try {
            val callbacks = (1..8).map { frame ->
                executor.submit {
                    start.await()
                    if (queue.enqueue(byteArrayOf(frame.toByte()))) accepted.incrementAndGet()
                }
            }
            start.countDown()
            assertTrue(callbacks.all { it.get(1, TimeUnit.SECONDS); true })

            assertEquals(1, accepted.get())
            assertTrue(terminalErrors.single() is SensorNotificationOverloadException)
            assertFalse(queue.enqueue(byteArrayOf(9)))
        } finally {
            queue.stop()
            executor.shutdownNow()
        }
    }

    @Test
    fun productionGattDisconnectSequenceFailsWriteBeforePublishingRemoteError() {
        val observed = mutableListOf<String>()

        GattRemoteDisconnectSequence(status = 133).dispatch(
            failPendingWrite = { observed += it.message!! },
            publishTransportError = { observed += it.message!! },
        )

        assertEquals(
            listOf("Sensor disconnected while writing (GATT 133).", "Sensor disconnected (GATT 133)."),
            observed,
        )
    }

    @Test
    fun boundedFakeStopsAtCapacityAndPublishesTerminalOverload() = runTest {
        val transport = FakeForceSensorTransport(notificationCapacity = 2, notificationScope = this)
        transport.emit(byteArrayOf(1))
        transport.emit(byteArrayOf(2))
        transport.emit(byteArrayOf(3))

        val terminal = transport.errors.first()
        assertTrue(terminal is SensorNotificationOverloadException)
        assertEquals(2, transport.notificationQueueState.value.pendingFrames)
        assertTrue(transport.notificationQueueState.value.isTerminal)
        val received = async { transport.notifications.take(2).map { it.single().toInt() }.toList() }
        advanceUntilIdle()

        assertEquals(listOf(1, 2), received.await())
        assertEquals(0, transport.notificationQueueState.value.pendingFrames)
        assertTrue(transport.notificationQueueState.value.isTerminal)
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
