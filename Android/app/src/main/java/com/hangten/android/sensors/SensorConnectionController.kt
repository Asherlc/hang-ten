package com.hangten.android.sensors

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow

enum class SensorConnectionState { Idle, Scanning, Calibrating, Streaming, Failed, Disconnected }

data class SensorMeterState(
    val connection: SensorConnectionState = SensorConnectionState.Idle,
    val profile: ForceSensorProfile,
    val activeProfile: ForceSensorProfile? = null,
    val latestMeasurement: MotherboardMeasurement? = null,
    val error: String? = null,
    val isTaring: Boolean = false,
    val tareSamplesCollected: Int = 0,
    val tareCompletionCount: Int = 0,
)

/**
 * Platform-neutral connection lifecycle. Calling [connectAfterPermissionsGranted]
 * is deliberately separate from [userInitiatedConnectPermissions]: UI owns the
 * Android runtime-permission prompt and invokes this method only from its result.
 */
class SensorConnectionController(
    private val transport: ForceSensorTransport,
    initialProfile: ForceSensorProfile = ForceSensorProfile.Automatic,
    private val tareSampleCount: Int = 15,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Default),
) {
    private val _state = MutableStateFlow(SensorMeterState(profile = initialProfile))
    val state: StateFlow<SensorMeterState> = _state.asStateFlow()
    private val measurementChannel = Channel<MotherboardMeasurement>(Channel.UNLIMITED)
    /** Every notification in arrival order; unlike the meter StateFlow this is not conflated. */
    val measurements = measurementChannel.receiveAsFlow()
    private var notificationJob: Job? = null
    private var transportErrorJob: Job? = null
    private val parser = MotherboardProtocolParser()
    private val calibrationRows = mutableListOf<MotherboardCalibrationRow>()
    private var calibration: MotherboardCalibration? = null
    private var tareKgf = List(4) { 0.0 }
    private var tareAccumulator = List(4) { 0.0 }

    fun selectProfile(profile: ForceSensorProfile) {
        disconnect()
        _state.value = SensorMeterState(profile = profile)
    }

    fun userInitiatedConnectPermissions(sdkInt: Int): Set<String> = BlePermissionRequirements.permissions(sdkInt)

    fun connectAfterPermissionsGranted() {
        scope.launch {
            val requested = state.value.profile
            _state.value = state.value.copy(connection = SensorConnectionState.Scanning, error = null)
            try {
                val advertised = transport.scan(requested)
                val matched = advertised.firstOrNull { matches(requested, it) }
                    ?: throw IllegalStateException("No compatible ${requested.displayName} sensor was found.")
                val active = if (requested == ForceSensorProfile.Automatic) resolveAutomatic(matched) else requested
                _state.value = state.value.copy(profile = requested, activeProfile = active)
                transport.connect(matched, active)
                active.notificationCharacteristics.forEach { characteristic -> transport.subscribe(characteristic) }
                listen(active)
                if (active == ForceSensorProfile.Motherboard) {
                    resetMotherboardSession()
                    _state.value = state.value.copy(connection = SensorConnectionState.Calibrating)
                    writeOrFail(active.writeCharacteristic!!, MotherboardProtocol.command("C"))
                } else {
                    commandPayload(active, ForceSensorCommand.Start)?.let { writeOrFail(active.writeCharacteristic!!, it) }
                    if (state.value.connection == SensorConnectionState.Failed) return@launch
                    _state.value = state.value.copy(connection = SensorConnectionState.Streaming)
                }
            } catch (error: Throwable) {
                _state.value = state.value.copy(connection = SensorConnectionState.Failed, error = error.message ?: "Unable to connect to sensor.")
            }
        }
    }

    fun tare() {
        val active = state.value.activeProfile ?: state.value.profile
        if (state.value.connection != SensorConnectionState.Streaming) return
        if (active == ForceSensorProfile.Motherboard) {
            tareAccumulator = List(4) { 0.0 }
            _state.value = state.value.copy(isTaring = true, tareSamplesCollected = 0)
        } else {
            scope.launch {
                commandPayload(active, ForceSensorCommand.Tare)?.let { writeOrFail(active.writeCharacteristic!!, it) }
                if (state.value.connection != SensorConnectionState.Failed) _state.value = state.value.copy(tareCompletionCount = state.value.tareCompletionCount + 1)
            }
        }
    }

    fun disconnect() {
        val active = state.value.activeProfile ?: state.value.profile
        notificationJob?.cancel()
        notificationJob = null
        transportErrorJob?.cancel()
        transportErrorJob = null
        val stop = commandPayload(active, ForceSensorCommand.Stop)
        val write = active.writeCharacteristic
        if (stop != null && write != null) scope.launch {
            writeOrFail(write, stop)
            transport.disconnect()
        } else transport.disconnect()
        _state.value = state.value.copy(connection = SensorConnectionState.Disconnected)
    }

    private fun listen(active: ForceSensorProfile) {
        notificationJob?.cancel()
        notificationJob = scope.launch {
            transport.notifications.collect { frame ->
                if (active == ForceSensorProfile.Motherboard) onMotherboardFrame(frame) else onForceFrame(active, frame)
            }
        }
        transportErrorJob = scope.launch {
            transport.errors.first { error ->
                notificationJob?.cancel()
                notificationJob = null
                transport.disconnect()
                _state.value = state.value.copy(
                    connection = SensorConnectionState.Disconnected,
                    activeProfile = null,
                    latestMeasurement = null,
                    isTaring = false,
                    tareSamplesCollected = 0,
                    error = error.message ?: "Sensor disconnected.",
                )
                true
            }
        }
    }

    private suspend fun onMotherboardFrame(frame: ByteArray) {
        parser.append(frame, System.currentTimeMillis()).forEach { event ->
            when (event) {
                is MotherboardProtocolEvent.Calibration -> {
                    calibrationRows.removeAll { it.sensor == event.row.sensor && it.calibrationPoint == event.row.calibrationPoint }
                    calibrationRows += event.row
                    if (completeCalibration()) {
                        calibration = MotherboardCalibration(calibrationRows)
                        writeOrFail(ForceSensorProfile.Motherboard.writeCharacteristic!!, MotherboardProtocol.streamCommand(30))
                    }
                }
                is MotherboardProtocolEvent.RawPacket -> {
                    val activeCalibration = calibration ?: return@forEach
                    if (state.value.connection != SensorConnectionState.Streaming) return@forEach
                    publish(MotherboardProtocol.decode(event.packet, event.timestampMs, activeCalibration, tareKgf))
                }
                is MotherboardProtocolEvent.StreamStarted -> if (event.rate == 30 && calibration != null) {
                    _state.value = state.value.copy(connection = SensorConnectionState.Streaming, error = null)
                }
                is MotherboardProtocolEvent.Error -> _state.value = state.value.copy(error = event.message)
            }
        }
    }

    private suspend fun onForceFrame(profile: ForceSensorProfile, frame: ByteArray) {
        val samples = when (profile) {
            ForceSensorProfile.Progressor, ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).decode(frame, System.currentTimeMillis())
            ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().decode(frame, System.currentTimeMillis())
            else -> null
        } ?: run {
            _state.value = state.value.copy(error = "${profile.displayName} sent an invalid force sample.")
            return
        }
        samples.forEach { sample ->
            nextForceSampleNumber = (nextForceSampleNumber.toInt() + 1).toUShort()
            publish(MotherboardMeasurement(sample.receivedAtMs, nextForceSampleNumber, 0u, emptyList(), emptyList(), sample.kilogramsForce))
        }
    }

    private suspend fun publish(measurement: MotherboardMeasurement) {
        val meter = state.value
        if (meter.isTaring && measurement.sensorLoadsKgf.size == 4) {
            tareAccumulator = tareAccumulator.zip(measurement.sensorLoadsKgf).map { (total, load) -> total + load }
            val count = meter.tareSamplesCollected + 1
            if (count >= tareSampleCount.coerceAtLeast(1)) {
                tareKgf = tareKgf.zip(tareAccumulator.map { it / count }).map { (old, average) -> old + average }
                _state.value = meter.copy(latestMeasurement = measurement, isTaring = false, tareSamplesCollected = 0, tareCompletionCount = meter.tareCompletionCount + 1)
            } else _state.value = meter.copy(latestMeasurement = measurement, tareSamplesCollected = count)
        } else _state.value = meter.copy(latestMeasurement = measurement)
        measurementChannel.send(measurement)
    }

    private fun resetMotherboardSession() {
        calibrationRows.clear()
        calibration = null
        tareKgf = List(4) { 0.0 }
        tareAccumulator = List(4) { 0.0 }
        nextForceSampleNumber = 0u
    }

    private fun completeCalibration(): Boolean = (0..3).all { sensor ->
        (0..3).all { point -> calibrationRows.any { it.sensor == sensor && it.calibrationPoint == point } }
    }

    private fun resolveAutomatic(advertisement: ForceSensorAdvertisement): ForceSensorProfile = ForceSensorProfile.automaticCandidates
        .firstOrNull { matches(it, advertisement) }
        ?: throw IllegalStateException("No supported force-sensor protocol matches this device.")

    private fun matches(profile: ForceSensorProfile, advertisement: ForceSensorAdvertisement): Boolean = when (profile) {
        ForceSensorProfile.Automatic -> ForceSensorProfile.automaticCandidates.any { matches(it, advertisement) }
        ForceSensorProfile.Motherboard -> advertisement.name?.contains("Motherboard", ignoreCase = true) == true
        ForceSensorProfile.Progressor, ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).matches(advertisement)
        ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().matches(advertisement)
    }

    private fun commandPayload(profile: ForceSensorProfile, command: ForceSensorCommand): ByteArray? = when (profile) {
        ForceSensorProfile.Progressor, ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).payload(command)
        ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().payload(command)
        else -> null
    }

    private suspend fun writeOrFail(characteristic: ForceSensorCharacteristic, payload: ByteArray) {
        try { transport.write(characteristic, payload) }
        catch (error: Throwable) { _state.value = state.value.copy(connection = SensorConnectionState.Failed, error = error.message ?: "Sensor write failed.") }
    }

    private var nextForceSampleNumber: UShort = 0u
}
