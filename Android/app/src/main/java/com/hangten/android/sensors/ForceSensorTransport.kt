package com.hangten.android.sensors

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.SystemClock
import androidx.core.content.ContextCompat
import java.util.UUID
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.locks.ReentrantLock
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch

data class NotificationQueueState(
    val capacityFrames: Int,
    val pendingFrames: Int = 0,
    val isTerminal: Boolean = false,
    val terminalMessage: String? = null,
)

class SensorNotificationOverloadException(capacityFrames: Int) : IllegalStateException(
    "Sensor notification queue capacity ($capacityFrames) was reached; sensor stream stopped before another frame was captured.",
)

/** The production callback order for a remote disconnect while a write is pending. */
internal class GattRemoteDisconnectSequence(status: Int) {
    private val writeError = IllegalStateException("Sensor disconnected while writing (GATT $status).")
    private val transportError = IllegalStateException("Sensor disconnected (GATT $status).")

    fun dispatch(
        failPendingWrite: (Throwable) -> Unit,
        publishTransportError: (Throwable) -> Unit,
    ) {
        failPendingWrite(writeError)
        publishTransportError(transportError)
    }
}

/**
 * Moves callback-thread frames through a single serial pump. The callback only
 * copies/enqueues; when delivery is slow, the pump suspends off the callback
 * thread. The finite pending-frame budget makes the first overload terminal,
 * rather than silently dropping or continuing to capture frames.
 */
internal class SerialNotificationQueue(
    private val scope: CoroutineScope,
    private val capacityFrames: Int = 128,
    private val onTerminal: (Throwable) -> Unit,
) {
    private val ingress = ArrayBlockingQueue<ByteArray>(capacityFrames)
    private val admissionLock = ReentrantLock()
    private val terminalRequested = AtomicBoolean(false)
    private val isDraining = AtomicBoolean(false)
    private val pendingFrames = AtomicInteger(0)
    private val isTerminal = AtomicBoolean(false)
    private var drainJob: Job? = null
    private val outgoing = Channel<ByteArray>(Channel.RENDEZVOUS)
    private val _state = MutableStateFlow(NotificationQueueState(capacityFrames))
    val state: StateFlow<NotificationQueueState> = _state.asStateFlow()
    val notifications: Flow<ByteArray> = flow {
        for (frame in outgoing) {
            try {
                emit(frame)
            } finally {
                delivered()
            }
        }
    }

    fun enqueue(frame: ByteArray): Boolean {
        if (terminalRequested.get()) return false
        if (!admissionLock.tryLock()) {
            terminalRequested.set(true)
            return false
        }
        try {
            if (terminalRequested.get() || isTerminal.get()) {
                terminalLocked()
                return false
            }
            val pending = pendingFrames.get()
            if (pending >= capacityFrames || !ingress.offer(frame.copyOf())) {
                terminalLocked()
                return false
            }
            pendingFrames.incrementAndGet()
            publishState(pending + 1)
            if (isDraining.compareAndSet(false, true)) drainJob = scope.launch { drain() }
            if (terminalRequested.get()) terminalLocked()
            return true
        } finally {
            admissionLock.unlock()
        }
    }

    fun stop() {
        admissionLock.lock()
        try {
            drainJob?.cancel()
            drainJob = null
            isDraining.set(false)
            ingress.clear()
            pendingFrames.set(0)
            publishState(0)
        } finally {
            admissionLock.unlock()
        }
    }

    fun reset() {
        stop()
        admissionLock.lock()
        try {
            terminalRequested.set(false)
            isTerminal.set(false)
            _state.value = NotificationQueueState(capacityFrames)
        } finally {
            admissionLock.unlock()
        }
    }

    private suspend fun drain() {
        while (true) {
            val frame = ingress.poll()
            if (frame != null) {
                outgoing.send(frame)
                continue
            }
            isDraining.set(false)
            if (ingress.isEmpty() || !isDraining.compareAndSet(false, true)) return
        }
    }

    /** Must run while [admissionLock] is held; callers never block a BLE callback. */
    private fun terminalLocked() {
        terminalRequested.set(true)
        if (isTerminal.compareAndSet(false, true)) {
            val error = SensorNotificationOverloadException(capacityFrames)
            publishState(pendingFrames.get(), error)
            onTerminal(error)
        }
    }

    private fun delivered() {
        while (true) {
            val pending = pendingFrames.get()
            if (pending == 0) return
            if (pendingFrames.compareAndSet(pending, pending - 1)) {
                publishState(pending - 1)
                return
            }
        }
    }

    private fun publishState(pending: Int, terminalError: Throwable? = null) {
        _state.value = NotificationQueueState(
            capacityFrames = capacityFrames,
            pendingFrames = pending,
            isTerminal = isTerminal.get(),
            terminalMessage = terminalError?.message ?: _state.value.terminalMessage,
        )
    }
}

interface ForceSensorTransport {
    val notifications: Flow<ByteArray>
    val notificationQueueState: StateFlow<NotificationQueueState>
    val errors: Flow<Throwable>
    suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement>
    suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile)
    suspend fun subscribe(characteristic: ForceSensorCharacteristic)
    suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray)
    fun disconnect()
}

/** Test-only deterministic transport; it never talks to Bluetooth hardware. */
class FakeForceSensorTransport(
    notificationCapacity: Int = 128,
    notificationScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Unconfined),
) : ForceSensorTransport {
    private val discovered = mutableListOf<ForceSensorAdvertisement>()
    private val errorEvents = Channel<Throwable>(Channel.UNLIMITED)
    private val events = SerialNotificationQueue(notificationScope, notificationCapacity, ::reportError)
    val operations = mutableListOf<String>()
    var connectFailure: Throwable? = null
    var writeFailure: Throwable? = null
    var writeBarrier: kotlinx.coroutines.CompletableDeferred<Unit>? = null
    var connectBarrier: kotlinx.coroutines.CompletableDeferred<Unit>? = null
    override val notifications: Flow<ByteArray> = events.notifications
    override val notificationQueueState: StateFlow<NotificationQueueState> = events.state
    override val errors: Flow<Throwable> = errorEvents.receiveAsFlow()

    fun enqueue(advertisement: ForceSensorAdvertisement) { discovered += advertisement }
    fun emit(value: ByteArray) { events.enqueue(value) }
    fun fail(error: Throwable) { reportError(error) }

    /** Mirrors the production GATT callback: fail the pending write, then emit the remote error. */
    fun onRemoteGattDisconnected(status: Int) {
        GattRemoteDisconnectSequence(status).dispatch(
            failPendingWrite = { error ->
                if (writeBarrier?.isCompleted == false) {
                    writeFailure = error
                    writeBarrier?.complete(Unit)
                }
            },
            publishTransportError = ::reportError,
        )
    }

    override suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement> {
        operations += "scan:${profile.name}"
        return discovered.toList()
    }

    override suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile) {
        operations += "connect:${profile.name}"
        events.reset()
        connectBarrier?.await()
        connectFailure?.let { throw it }
    }

    override suspend fun subscribe(characteristic: ForceSensorCharacteristic) {
        operations += "subscribe:${characteristic.characteristicUuid}"
    }

    override suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray) {
        operations += "write:${characteristic.characteristicUuid}:${value.joinToString("") { "%02x".format(it) }}"
        writeBarrier?.await()
        writeFailure?.let { throw it }
    }

    override fun disconnect() {
        operations += "disconnect"
        events.stop()
        if (writeBarrier?.isCompleted == false) {
            writeFailure = IllegalStateException("Sensor disconnected while writing.")
            writeBarrier?.complete(Unit)
        }
    }

    private fun reportError(error: Throwable) { check(errorEvents.trySend(error).isSuccess) }
}

object BlePermissionRequirements {
    fun permissions(sdkInt: Int = Build.VERSION.SDK_INT): Set<String> = if (sdkInt >= Build.VERSION_CODES.S) {
        setOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        setOf(Manifest.permission.ACCESS_FINE_LOCATION)
    }
}

/**
 * Production Android BLE transport. The UI must request [BlePermissionRequirements]
 * following an explicit Connect sensor tap before calling this transport.
 */
class AndroidBleForceSensorTransport(private val context: Context) : ForceSensorTransport {
    private val appContext = context.applicationContext
    private val bluetoothAdapter: BluetoothAdapter? = appContext.getSystemService(BluetoothManager::class.java)?.adapter
    private val notificationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val errorEvents = Channel<Throwable>(Channel.UNLIMITED)
    private val notificationEvents = SerialNotificationQueue(notificationScope, onTerminal = ::reportError)
    override val notifications: Flow<ByteArray> = notificationEvents.notifications
    override val notificationQueueState: StateFlow<NotificationQueueState> = notificationEvents.state
    override val errors: Flow<Throwable> = errorEvents.receiveAsFlow()
    private var gatt: BluetoothGatt? = null
    private var scanCallback: ScanCallback? = null
    private var connectedAdvertisement: ForceSensorAdvertisement? = null
    private val scannedDevices = linkedMapOf<ForceSensorAdvertisement, BluetoothDevice>()
    private var connectionContinuation: kotlinx.coroutines.CancellableContinuation<Unit>? = null
    private var descriptorContinuation: kotlinx.coroutines.CancellableContinuation<Unit>? = null
    private var writeContinuation: kotlinx.coroutines.CancellableContinuation<Unit>? = null

    @SuppressLint("MissingPermission")
    override suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement> {
        requirePermissions()
        val scanner = bluetoothAdapter?.bluetoothLeScanner ?: return emptyList()
        val found = linkedMapOf<String, ForceSensorAdvertisement>()
        val callback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                val name = result.device.name ?: result.scanRecord?.deviceName
                val services = result.scanRecord?.serviceUuids.orEmpty().mapTo(linkedSetOf()) { it.uuid.toString().uppercase() }
                val advertisement = ForceSensorAdvertisement(name, services)
                found[result.device.address] = advertisement
                scannedDevices[advertisement] = result.device
            }
        }
        scanCallback = callback
        val filters = profile.serviceUuids.map { service -> ScanFilter.Builder().setServiceUuid(android.os.ParcelUuid(UUID.fromString(service))).build() }
        scanner.startScan(filters, ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), callback)
        kotlinx.coroutines.delay(SCAN_WINDOW_MS)
        scanner.stopScan(callback)
        scanCallback = null
        return found.values.filter { advertisement -> matches(profile, advertisement) }
    }

    @SuppressLint("MissingPermission")
    override suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile) = suspendCancellableCoroutine { continuation ->
        requirePermissions()
        notificationEvents.reset()
        val device = scannedDevices[advertisement]
            ?: run {
                continuation.resumeWithException(IllegalStateException("Select a discovered sensor before connecting."))
                return@suspendCancellableCoroutine
            }
        connectedAdvertisement = advertisement
        connectionContinuation = continuation
        gatt = device.connectGatt(appContext, false, callback, BluetoothDevice.TRANSPORT_LE)
        if (gatt == null) failSetup(IllegalStateException("Unable to open a BLE connection."))
        continuation.invokeOnCancellation { disconnect() }
    }

    @SuppressLint("MissingPermission")
    override suspend fun subscribe(characteristic: ForceSensorCharacteristic) = suspendCancellableCoroutine { continuation ->
        requirePermissions()
        val target = gatt?.getService(UUID.fromString(characteristic.serviceUuid))
            ?.getCharacteristic(UUID.fromString(characteristic.characteristicUuid))
            ?: run { continuation.resumeWithException(IllegalStateException("Sensor notification characteristic is unavailable.")); return@suspendCancellableCoroutine }
        if (gatt?.setCharacteristicNotification(target, true) != true) {
            continuation.resumeWithException(IllegalStateException("Unable to enable sensor notifications."))
            return@suspendCancellableCoroutine
        }
        val descriptor = target.getDescriptor(CLIENT_CHARACTERISTIC_CONFIGURATION)
            ?: run { continuation.resumeWithException(IllegalStateException("Sensor notification descriptor is unavailable.")); return@suspendCancellableCoroutine }
        descriptorContinuation = continuation
        val accepted = if (Build.VERSION.SDK_INT >= 33) gatt?.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) == BluetoothStatusCodes.SUCCESS
        else @Suppress("DEPRECATION") run { descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE; gatt?.writeDescriptor(descriptor) == true }
        if (!accepted) failDescriptor(IllegalStateException("Unable to write sensor notification descriptor."))
        continuation.invokeOnCancellation { descriptorContinuation = null }
    }

    @SuppressLint("MissingPermission")
    override suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray) = suspendCancellableCoroutine { continuation ->
        requirePermissions()
        val target = gatt?.getService(UUID.fromString(characteristic.serviceUuid))
            ?.getCharacteristic(UUID.fromString(characteristic.characteristicUuid))
            ?: run { continuation.resumeWithException(IllegalStateException("Sensor write characteristic is unavailable.")); return@suspendCancellableCoroutine }
        writeContinuation = continuation
        val accepted = if (Build.VERSION.SDK_INT >= 33) gatt?.writeCharacteristic(target, value, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT) == BluetoothStatusCodes.SUCCESS
        else @Suppress("DEPRECATION") run { target.value = value; target.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT; gatt?.writeCharacteristic(target) == true }
        if (!accepted) failWrite(IllegalStateException("Sensor write request was rejected."))
        continuation.invokeOnCancellation { writeContinuation = null }
    }

    @SuppressLint("MissingPermission")
    override fun disconnect() {
        scanCallback?.let { bluetoothAdapter?.bluetoothLeScanner?.stopScan(it) }
        scanCallback = null
        gatt?.disconnect()
        gatt?.close()
        gatt = null
        connectedAdvertisement = null
        notificationEvents.stop()
        failSetup(IllegalStateException("Sensor disconnected during setup."))
        failDescriptor(IllegalStateException("Sensor disconnected while enabling notifications."))
        failWrite(IllegalStateException("Sensor disconnected while writing."))
    }

    private fun requirePermissions() {
        check(BlePermissionRequirements.permissions().all { permission ->
            ContextCompat.checkSelfPermission(appContext, permission) == PackageManager.PERMISSION_GRANTED
        }) { "Bluetooth permission is required after Connect sensor is selected." }
    }

    @SuppressLint("MissingPermission")
    private val callback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS && newState == BluetoothGatt.STATE_CONNECTED) {
                if (!gatt.discoverServices()) failSetup(IllegalStateException("Unable to discover sensor services."))
            } else if (newState == BluetoothGatt.STATE_DISCONNECTED || status != BluetoothGatt.GATT_SUCCESS) {
                failSetup(IllegalStateException("Sensor disconnected during setup (GATT $status)."))
                failDescriptor(IllegalStateException("Sensor disconnected while enabling notifications (GATT $status)."))
                GattRemoteDisconnectSequence(status).dispatch(::failWrite, ::reportError)
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) connectionContinuation?.also { continuation -> connectionContinuation = null; continuation.resume(Unit) }
            else failSetup(IllegalStateException("Sensor service discovery failed (GATT $status)."))
        }

        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) descriptorContinuation?.also { continuation -> descriptorContinuation = null; continuation.resume(Unit) }
            else failDescriptor(IllegalStateException("Sensor notification setup failed (GATT $status)."))
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) writeContinuation?.also { continuation -> writeContinuation = null; continuation.resume(Unit) }
            else failWrite(IllegalStateException("Sensor write failed (GATT $status)."))
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, value: ByteArray) {
            enqueueNotification(value)
        }

        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            enqueueNotification(characteristic.value?.copyOf() ?: return)
        }
    }

    private fun matches(profile: ForceSensorProfile, advertisement: ForceSensorAdvertisement): Boolean = when (profile) {
        ForceSensorProfile.Automatic -> ForceSensorProfile.automaticCandidates.any { matches(it, advertisement) }
        ForceSensorProfile.Motherboard -> advertisement.name?.contains("Motherboard", ignoreCase = true) == true
        ForceSensorProfile.Progressor -> ProgressorProtocolAdapter(profile).matches(advertisement)
        ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).matches(advertisement)
        ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().matches(advertisement)
    }

    private fun failSetup(error: Throwable) {
        connectionContinuation?.also { continuation -> connectionContinuation = null; continuation.resumeWithException(error) }
    }

    private fun failDescriptor(error: Throwable) {
        descriptorContinuation?.also { continuation -> descriptorContinuation = null; continuation.resumeWithException(error) }
    }

    private fun failWrite(error: Throwable) {
        writeContinuation?.also { continuation -> writeContinuation = null; continuation.resumeWithException(error) }
    }

    @SuppressLint("MissingPermission")
    private fun enqueueNotification(value: ByteArray) {
        if (!notificationEvents.enqueue(value)) gatt?.disconnect()
    }

    private fun reportError(error: Throwable) { check(errorEvents.trySend(error).isSuccess) }

    private companion object {
        const val SCAN_WINDOW_MS = 4_000L
        val CLIENT_CHARACTERISTIC_CONFIGURATION: UUID = UUID.fromString("00002902-0000-1000-8000-00805F9B34FB")
    }
}
