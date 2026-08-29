package com.hangten.android.sensors

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class SensorConnectionState { Idle, Scanning, Calibrating, Streaming, Failed, Disconnected }

data class SensorMeterState(
    val connection: SensorConnectionState = SensorConnectionState.Idle,
    val profile: ForceSensorProfile,
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
    private var notificationJob: Job? = null
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
                transport.connect(matched, active)
                active.notificationCharacteristics.forEach { characteristic -> transport.subscribe(characteristic) }
                listen(active)
                if (active == ForceSensorProfile.Motherboard) {
                    resetMotherboardSession()
                    _state.value = state.value.copy(connection = SensorConnectionState.Calibrating)
                    transport.write(active.writeCharacteristic!!, MotherboardProtocol.command("C"))
                } else {
                    commandPayload(active, ForceSensorCommand.Start)?.let { transport.write(active.writeCharacteristic!!, it) }
                    _state.value = state.value.copy(connection = SensorConnectionState.Streaming)
                }
            } catch (error: Throwable) {
                _state.value = state.value.copy(connection = SensorConnectionState.Failed, error = error.message ?: "Unable to connect to sensor.")
            }
        }
    }

    fun tare() {
        val active = state.value.profile
        if (state.value.connection != SensorConnectionState.Streaming) return
        if (active == ForceSensorProfile.Motherboard) {
            tareAccumulator = List(4) { 0.0 }
            _state.value = state.value.copy(isTaring = true, tareSamplesCollected = 0)
        } else {
            scope.launch {
                commandPayload(active, ForceSensorCommand.Tare)?.let { transport.write(active.writeCharacteristic!!, it) }
                _state.value = state.value.copy(tareCompletionCount = state.value.tareCompletionCount + 1)
            }
        }
    }

    fun disconnect() {
        notificationJob?.cancel()
        notificationJob = null
        transport.disconnect()
        _state.value = state.value.copy(connection = SensorConnectionState.Disconnected)
    }

    private fun listen(active: ForceSensorProfile) {
        notificationJob?.cancel()
        notificationJob = scope.launch {
            transport.notifications.collect { frame ->
                if (active == ForceSensorProfile.Motherboard) onMotherboardFrame(frame) else onForceFrame(active, frame)
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
                        transport.write(ForceSensorProfile.Motherboard.writeCharacteristic!!, MotherboardProtocol.streamCommand(30))
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

    private fun onForceFrame(profile: ForceSensorProfile, frame: ByteArray) {
        val samples = when (profile) {
            ForceSensorProfile.Progressor, ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).decode(frame, System.currentTimeMillis())
            ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().decode(frame, System.currentTimeMillis())
            else -> null
        } ?: run {
            _state.value = state.value.copy(error = "${profile.displayName} sent an invalid force sample.")
            return
        }
        samples.forEachIndexed { index, sample ->
            publish(MotherboardMeasurement(sample.receivedAtMs, index.toUShort(), 0u, emptyList(), emptyList(), sample.kilogramsForce))
        }
    }

    private fun publish(measurement: MotherboardMeasurement) {
        val meter = state.value
        if (meter.isTaring && measurement.sensorLoadsKgf.size == 4) {
            tareAccumulator = tareAccumulator.zip(measurement.sensorLoadsKgf).map { (total, load) -> total + load }
            val count = meter.tareSamplesCollected + 1
            if (count >= tareSampleCount.coerceAtLeast(1)) {
                tareKgf = tareKgf.zip(tareAccumulator.map { it / count }).map { (old, average) -> old + average }
                _state.value = meter.copy(latestMeasurement = measurement, isTaring = false, tareSamplesCollected = 0, tareCompletionCount = meter.tareCompletionCount + 1)
            } else _state.value = meter.copy(latestMeasurement = measurement, tareSamplesCollected = count)
        } else _state.value = meter.copy(latestMeasurement = measurement)
    }

    private fun resetMotherboardSession() {
        calibrationRows.clear()
        calibration = null
        tareKgf = List(4) { 0.0 }
        tareAccumulator = List(4) { 0.0 }
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
}
