package com.hangten.android.sensors

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
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
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.first

interface ForceSensorTransport {
    val notifications: Flow<ByteArray>
    suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement>
    suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile)
    suspend fun subscribe(characteristic: ForceSensorCharacteristic)
    suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray)
    fun disconnect()
}

/** Test-only deterministic transport; it never talks to Bluetooth hardware. */
class FakeForceSensorTransport : ForceSensorTransport {
    private val discovered = mutableListOf<ForceSensorAdvertisement>()
    private val events = MutableSharedFlow<ByteArray>(replay = 1, extraBufferCapacity = 32, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val operations = mutableListOf<String>()
    override val notifications: Flow<ByteArray> = events

    fun enqueue(advertisement: ForceSensorAdvertisement) { discovered += advertisement }
    fun emit(value: ByteArray) { events.tryEmit(value.copyOf()) }

    override suspend fun scan(profile: ForceSensorProfile): List<ForceSensorAdvertisement> {
        operations += "scan:${profile.name}"
        return discovered.toList()
    }

    override suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile) {
        operations += "connect:${profile.name}"
    }

    override suspend fun subscribe(characteristic: ForceSensorCharacteristic) {
        operations += "subscribe:${characteristic.characteristicUuid}"
    }

    override suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray) {
        operations += "write:${characteristic.characteristicUuid}:${value.joinToString("") { "%02x".format(it) }}"
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
    private val notificationEvents = MutableSharedFlow<ByteArray>(extraBufferCapacity = 64, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    override val notifications: Flow<ByteArray> = notificationEvents
    private var gatt: BluetoothGatt? = null
    private var scanCallback: ScanCallback? = null
    private var connectedAdvertisement: ForceSensorAdvertisement? = null
    private val scannedDevices = linkedMapOf<ForceSensorAdvertisement, BluetoothDevice>()

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
    override suspend fun connect(advertisement: ForceSensorAdvertisement, profile: ForceSensorProfile) {
        requirePermissions()
        val device = scannedDevices[advertisement]
            ?: throw IllegalStateException("Select a discovered sensor before connecting.")
        connectedAdvertisement = advertisement
        gatt = device.connectGatt(appContext, false, callback, BluetoothDevice.TRANSPORT_LE)
    }

    @SuppressLint("MissingPermission")
    override suspend fun subscribe(characteristic: ForceSensorCharacteristic) {
        requirePermissions()
        val target = gatt?.getService(UUID.fromString(characteristic.serviceUuid))
            ?.getCharacteristic(UUID.fromString(characteristic.characteristicUuid))
            ?: throw IllegalStateException("Sensor notification characteristic is unavailable.")
        check(gatt?.setCharacteristicNotification(target, true) == true) { "Unable to enable sensor notifications." }
        val descriptor = target.getDescriptor(CLIENT_CHARACTERISTIC_CONFIGURATION)
            ?: throw IllegalStateException("Sensor notification descriptor is unavailable.")
        if (Build.VERSION.SDK_INT >= 33) gatt?.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        else @Suppress("DEPRECATION") run { descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE; gatt?.writeDescriptor(descriptor) }
    }

    @SuppressLint("MissingPermission")
    override suspend fun write(characteristic: ForceSensorCharacteristic, value: ByteArray) {
        requirePermissions()
        val target = gatt?.getService(UUID.fromString(characteristic.serviceUuid))
            ?.getCharacteristic(UUID.fromString(characteristic.characteristicUuid))
            ?: throw IllegalStateException("Sensor write characteristic is unavailable.")
        if (Build.VERSION.SDK_INT >= 33) gatt?.writeCharacteristic(target, value, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT)
        else @Suppress("DEPRECATION") run { target.value = value; target.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT; gatt?.writeCharacteristic(target) }
    }

    @SuppressLint("MissingPermission")
    override fun disconnect() {
        scanCallback?.let { bluetoothAdapter?.bluetoothLeScanner?.stopScan(it) }
        scanCallback = null
        gatt?.disconnect()
        gatt?.close()
        gatt = null
        connectedAdvertisement = null
    }

    private fun requirePermissions() {
        check(BlePermissionRequirements.permissions().all { permission ->
            ContextCompat.checkSelfPermission(appContext, permission) == PackageManager.PERMISSION_GRANTED
        }) { "Bluetooth permission is required after Connect sensor is selected." }
    }

    @SuppressLint("MissingPermission")
    private val callback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS && newState == BluetoothGatt.STATE_CONNECTED) gatt.discoverServices()
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, value: ByteArray) {
            notificationEvents.tryEmit(value.copyOf())
        }

        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            notificationEvents.tryEmit(characteristic.value?.copyOf() ?: return)
        }
    }

    private fun matches(profile: ForceSensorProfile, advertisement: ForceSensorAdvertisement): Boolean = when (profile) {
        ForceSensorProfile.Automatic -> ForceSensorProfile.automaticCandidates.any { matches(it, advertisement) }
        ForceSensorProfile.Motherboard -> advertisement.name?.contains("Motherboard", ignoreCase = true) == true
        ForceSensorProfile.Progressor -> ProgressorProtocolAdapter(profile).matches(advertisement)
        ForceSensorProfile.GenericProgressor -> ProgressorProtocolAdapter(profile).matches(advertisement)
        ForceSensorProfile.PitchSix -> PitchSixProtocolAdapter().matches(advertisement)
    }

    private companion object {
        const val SCAN_WINDOW_MS = 4_000L
        val CLIENT_CHARACTERISTIC_CONFIGURATION: UUID = UUID.fromString("00002902-0000-1000-8000-00805F9B34FB")
    }
}
