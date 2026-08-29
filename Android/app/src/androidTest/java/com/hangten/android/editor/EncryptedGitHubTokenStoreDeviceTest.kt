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
        val raw = context.getSharedPreferences("hangten.github.encrypted", Context.MODE_PRIVATE)
        val beforeSave = raw.all.toMap()

        store.save(token)

        assertEquals(token, store.load())
        assertFalse(raw.all.toString().contains(token))

        // Find the actual value inserted by EncryptedSharedPreferences, rather
        // than supplying an in-memory fake. Its key is encrypted too, so a
        // before/after diff is the only stable black-box way to identify it.
        val ciphertextEntry = raw.all.entries.single { beforeSave[it.key] != it.value }
        check(raw.edit().putString(ciphertextEntry.key, "malformed-ciphertext").commit())

        val recovered = EncryptedGitHubTokenStore(context)
        assertNull(recovered.load())
        assertFalse(raw.contains(ciphertextEntry.key))
        recovered.save("replacement-token")
        assertEquals("replacement-token", recovered.load())
        recovered.clear()
        assertNull(recovered.load())

        store.clear()
        assertNull(store.load())
    }
}
