package com.hangten.android.sensors

import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.CompletableDeferred
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SensorConnectionControllerTest {
    @Test
    fun connectStartsOnlyAfterTheUserInitiatedPermissionRequestAndExposesLiveMeter() = runTest {
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)

        assertEquals(SensorConnectionState.Idle, controller.state.value.connection)
        assertFalse(controller.userInitiatedConnectPermissions(sdkInt = 30).isEmpty())
        controller.connectAfterPermissionsGranted()
        advanceUntilIdle()
        transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0))
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Streaming, controller.state.value.connection)
        assertEquals(12.5, controller.state.value.latestMeasurement!!.aggregateLoadKgf, 0.0001)
        assertTrue(transport.operations.contains("write:${ForceSensorProfile.Progressor.writeCharacteristic!!.characteristicUuid}:65"))
        controller.disconnect()
        advanceUntilIdle()
    }

    @Test
    fun motherboardRequiresCompleteCalibrationThenStreamsAndSoftwareTareAveragesSamples() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Motherboard")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Motherboard, tareSampleCount = 2, scope = this)
        controller.connectAfterPermissionsGranted()
        advanceUntilIdle()
        calibration().forEach { transport.emit("$it\r\n".encodeToByteArray()) }
        transport.emit("Stream:30\r\n".encodeToByteArray())
        advanceUntilIdle()
        controller.tare()
        transport.emit(packet(adc = 10))
        transport.emit(packet(adc = 10))
        transport.emit(packet(adc = 10))
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Streaming, controller.state.value.connection)
        assertEquals(1, controller.state.value.tareCompletionCount)
        assertEquals(0.0, controller.state.value.latestMeasurement!!.aggregateLoadKgf, 0.0001)
        assertTrue(transport.operations.contains("write:${ForceSensorProfile.Motherboard.writeCharacteristic!!.characteristicUuid}:43"))
        assertTrue(transport.operations.contains("write:${ForceSensorProfile.Motherboard.writeCharacteristic!!.characteristicUuid}:533330"))
        controller.disconnect()
        advanceUntilIdle()
    }

    @Test
    fun setupWaitsForTransportReadinessAndSurfacesSetupDisconnect() = runTest {
        val barrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
            connectBarrier = barrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted()
        advanceUntilIdle()
        assertEquals(SensorConnectionState.Scanning, controller.state.value.connection)
        assertTrue(transport.operations.none { it.startsWith("subscribe") || it.startsWith("write") })
        barrier.complete(Unit)
        transport.connectFailure = IllegalStateException("disconnected during discovery")
        advanceUntilIdle()
        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("disconnected during discovery"))
    }

    @Test
    fun streamingDisconnectResetsMeterAndReportsError() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.fail(IllegalStateException("remote disconnect")); advanceUntilIdle()
        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("remote disconnect"))
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun burstNotificationsKeepEveryGenericSampleInArrivalOrder() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        repeat(80) { transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0)) }
        advanceUntilIdle()
        assertEquals(80.toUShort(), controller.state.value.latestMeasurement!!.sampleNumber)
        controller.disconnect(); advanceUntilIdle()
    }

    private fun calibration(): List<String> = (0..3).flatMap { sensor ->
        (0..3).map { point -> "$sensor,$point,$point,${point * 10}" }
    }

    private fun packet(adc: Int): ByteArray {
        val channel = "%06x".format(adc)
        return "01000100$channel$channel$channel$channel\r\n".encodeToByteArray()
    }
}
