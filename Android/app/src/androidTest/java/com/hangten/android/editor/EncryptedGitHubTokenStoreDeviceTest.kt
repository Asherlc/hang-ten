package com.hangten.android.editor

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
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

        store.save(token)

        assertEquals(token, store.load())
        assertFalse(raw.all.toString().contains(token))

        store.clear()
        assertNull(store.load())

        // This is a second, real EncryptedSharedPreferences handle with the
        // same MasterKey, file, and schemes as production. The outer record is
        // valid encrypted storage, while the logical token is intentionally
        // malformed for AndroidKeystoreTokenCipher's inner AES-GCM layer.
        val encryptedPreferences = realEncryptedPreferences()
        check(encryptedPreferences.edit().putString("oauth_token", "malformed-ciphertext").commit())

        val recovered = EncryptedGitHubTokenStore(context)
        assertNull(recovered.load())
        assertNull(encryptedPreferences.getString("oauth_token", null))
        recovered.save("replacement-token")
        assertEquals("replacement-token", recovered.load())
        recovered.clear()
        assertNull(recovered.load())

    }

    private fun realEncryptedPreferences(): SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "hangten.github.encrypted",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )
}
