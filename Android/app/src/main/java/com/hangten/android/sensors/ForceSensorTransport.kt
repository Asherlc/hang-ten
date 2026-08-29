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
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.first

interface ForceSensorTransport {
    val notifications: Flow<ByteArray>
    val errors: Flow<Throwable>
    suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement>
    suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile)
    suspend fun subscribe(characteristic: ForceSensorCharacteristic)
    suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray)
    fun disconnect()
}

/** Test-only deterministic transport; it never talks to Bluetooth hardware. */
class FakeForceSensorTransport : ForceSensorTransport {
    private val discovered = mutableListOf<ForceSensorAdvertisement>()
    private val events = Channel<ByteArray>(Channel.UNLIMITED)
    private val errorEvents = MutableSharedFlow<Throwable>(extraBufferCapacity = 8)
    val operations = mutableListOf<String>()
    var connectFailure: Throwable? = null
    var writeFailure: Throwable? = null
    var connectBarrier: kotlinx.coroutines.CompletableDeferred<Unit>? = null
    override val notifications: Flow<ByteArray> = events.receiveAsFlow()
    override val errors: Flow<Throwable> = errorEvents

    fun enqueue(advertisement: ForceSensorAdvertisement) { discovered += advertisement }
    fun emit(value: ByteArray) { check(events.trySend(value.copyOf()).isSuccess) }
    fun fail(error: Throwable) { check(errorEvents.tryEmit(error)) }

    override suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement> {
        operations += "scan:${profile.name}"
        return discovered.toList()
    }

    override suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile) {
        operations += "connect:${profile.name}"
        connectBarrier?.await()
        connectFailure?.let { throw it }
    }

    override suspend fun subscribe(characteristic: ForceSensorCharacteristic) {
        operations += "subscribe:${characteristic.characteristicUuid}"
    }

    override suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray) {
        operations += "write:${characteristic.characteristicUuid}:${value.joinToString("") { "%02x".format(it) }}"
        writeFailure?.let { throw it }
    }

    override fun disconnect() { operations += "disconnect" }
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
    private val notificationEvents = Channel<ByteArray>(capacity = 128)
    private val errorEvents = MutableSharedFlow<Throwable>(extraBufferCapacity = 8)
    override val notifications: Flow<ByteArray> = notificationEvents.receiveAsFlow()
    override val errors: Flow<Throwable> = errorEvents
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
                failWrite(IllegalStateException("Sensor disconnected while writing (GATT $status)."))
                errorEvents.tryEmit(IllegalStateException("Sensor disconnected (GATT $status)."))
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

    private fun enqueueNotification(value: ByteArray) {
        if (!notificationEvents.trySend(value.copyOf()).isSuccess) {
            errorEvents.tryEmit(IllegalStateException("Sensor notification queue is full; disconnect and reconnect."))
        }
    }

    private companion object {
        const val SCAN_WINDOW_MS = 4_000L
        val CLIENT_CHARACTERISTIC_CONFIGURATION: UUID = UUID.fromString("00002902-0000-1000-8000-00805F9B34FB")
    }
}
