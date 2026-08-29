package com.hangten.android.editor

import android.content.Context
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

/** Runs against AndroidKeyStore and EncryptedSharedPreferences on an emulator/device. */
class EncryptedGitHubTokenStoreDeviceTest {
    private val context: Context
        get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test
    fun realKeystoreAndEncryptedPreferencesStoreReadClearAndRecoverFromCorruption() {
        val token = "device-oauth-token"
        val store = EncryptedGitHubTokenStore(context)
        store.clear()

        store.save(token)

        assertEquals(token, store.load())
        val raw = context.getSharedPreferences("hangten.github.encrypted", Context.MODE_PRIVATE)
        assertFalse(raw.all.toString().contains(token))

        store.clear()
        assertNull(store.load())

        val corruptStorage = InstrumentationCiphertextStorage("malformed")
        val corruptStore = CiphertextGitHubTokenStore(corruptStorage, AndroidKeystoreTokenCipher())
        assertNull(corruptStore.load())
        assertNull(corruptStorage.value)
    }
}

private class InstrumentationCiphertextStorage(initial: String?) : CiphertextStorage {
    var value: String? = initial
    override fun read(): String? = value
    override fun write(value: String) { this.value = value }
    override fun clear() { value = null }
}
