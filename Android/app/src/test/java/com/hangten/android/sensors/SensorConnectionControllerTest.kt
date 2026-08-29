package com.hangten.android.sensors

import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
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
        val transport = FakeForceSensorTransport(notificationCapacity = 512).apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
        }
        val controller = SensorConnectionController(
            transport = transport,
            initialProfile = ForceSensorProfile.Progressor,
            measurementHandoffCapacity = 512,
            scope = this,
        )
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        val received = mutableListOf<UShort>()
        val collection = launch { controller.measurements.collect { received += it.sampleNumber } }
        advanceUntilIdle()
        repeat(256) { transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0)) }
        advanceUntilIdle()
        assertEquals(256.toUShort(), controller.state.value.latestMeasurement!!.sampleNumber)
        assertEquals((1..256).map(Int::toUShort), received)
        collection.cancel()
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun remoteErrorTearsDownCollectorSoLateFramesCannotUpdateTheMeter() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        val received = mutableListOf<MotherboardMeasurement>()
        val collection = launch { controller.measurements.collect { received += it } }
        transport.fail(IllegalStateException("gone")); advanceUntilIdle()
        transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0)); advanceUntilIdle()
        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertEquals(null, controller.state.value.latestMeasurement)
        assertTrue(received.isEmpty())
        collection.cancel()
    }

    @Test
    fun terminalNotificationOverloadIsVisibleToControllerAndStopsMeasurements() = runTest {
        val transport = FakeForceSensorTransport(notificationCapacity = 2, notificationScope = this).apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        repeat(3) { transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0)) }
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("notification queue"))
        assertEquals(null, controller.state.value.latestMeasurement)
        assertEquals(0, transport.notificationQueueState.value.pendingFrames)
    }

    @Test
    fun slowOrAbsentWorkoutConsumerTriggersTerminalMeasurementHandoffOverload() = runTest {
        val transport = FakeForceSensorTransport(notificationCapacity = 512, notificationScope = this).apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
        }
        val controller = SensorConnectionController(
            transport = transport,
            initialProfile = ForceSensorProfile.Progressor,
            measurementHandoffCapacity = 2,
            scope = this,
        )
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        repeat(3) { transport.emit(byteArrayOf(1, 8, 0, 0, 72, 65, 7, 0, 0, 0)) }
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("measurement handoff"))
        assertEquals(null, controller.state.value.latestMeasurement)
    }

    @Test
    fun startWriteFailureBecomesVisibleControllerError() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")); writeFailure = IllegalStateException("write failed") }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("write failed"))
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun tareWriteFailureBecomesVisibleControllerError() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.writeFailure = IllegalStateException("tare failed")
        controller.tare(); advanceUntilIdle()
        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("tare failed"))
        transport.writeFailure = null
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun motherboardStreamWriteFailureBecomesVisibleControllerError() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Motherboard")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Motherboard, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.writeFailure = IllegalStateException("stream failed")
        calibration().forEach { transport.emit("$it\r\n".encodeToByteArray()) }
        advanceUntilIdle()
        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("stream failed"))
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun remoteTerminalCannotBeResurrectedByLateMotherboardStreamOrParserError() = runTest {
        val writeBarrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Motherboard"))
            this.writeBarrier = writeBarrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Motherboard, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()

        calibration().take(15).forEach { transport.emit("$it\r\n".encodeToByteArray()) }
        advanceUntilIdle()
        val finalCalibration = calibration().last()
        transport.emit("$finalCalibration\r\nStream:30\r\nError: late parser callback\r\n".encodeToByteArray())
        advanceUntilIdle()
        assertTrue(transport.operations.contains("write:${ForceSensorProfile.Motherboard.writeCharacteristic!!.characteristicUuid}:533330"))

        transport.fail(IllegalStateException("Sensor disconnected (GATT 133)"))
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("GATT 133"))
    }

    @Test
    fun stopWriteFailureBecomesVisibleControllerError() = runTest {
        val transport = FakeForceSensorTransport().apply { enqueue(ForceSensorAdvertisement(name = "Progressor 200")) }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.writeFailure = IllegalStateException("stop failed")
        controller.disconnect(); advanceUntilIdle()
        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("stop failed"))
    }

    @Test
    fun pendingStartWriteDisconnectBecomesVisibleControllerFailure() = runTest {
        val barrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
            writeBarrier = barrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.disconnect(); advanceUntilIdle()

        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("disconnected while writing"))
        transport.writeFailure = null
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun remoteGattDisconnectDuringPendingWriteWinsTheTerminalStateRace() = runTest {
        val barrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
            writeBarrier = barrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.onRemoteGattDisconnected(status = 133); advanceUntilIdle()

        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("GATT 133"))
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun remoteDisconnectWinsWhenPendingWriteFailureIsAlreadyScheduled() = runTest {
        val barrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
            writeBarrier = barrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.writeFailure = IllegalStateException("write callback failed")
        barrier.complete(Unit)
        transport.onRemoteGattDisconnected(status = 133)
        advanceUntilIdle()

        assertEquals(SensorConnectionState.Disconnected, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("GATT 133"))
        controller.disconnect(); advanceUntilIdle()
    }

    @Test
    fun delayedWriteCallbackErrorBecomesVisibleControllerFailure() = runTest {
        val barrier = CompletableDeferred<Unit>()
        val transport = FakeForceSensorTransport().apply {
            enqueue(ForceSensorAdvertisement(name = "Progressor 200"))
            writeBarrier = barrier
        }
        val controller = SensorConnectionController(transport, ForceSensorProfile.Progressor, scope = this)
        controller.connectAfterPermissionsGranted(); advanceUntilIdle()
        transport.writeFailure = IllegalStateException("callback write failed")
        barrier.complete(Unit); advanceUntilIdle()

        assertEquals(SensorConnectionState.Failed, controller.state.value.connection)
        assertTrue(controller.state.value.error!!.contains("callback write failed"))
        transport.writeFailure = null
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
