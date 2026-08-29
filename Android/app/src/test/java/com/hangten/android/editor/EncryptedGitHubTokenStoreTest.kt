package com.hangten.android.editor

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class EncryptedGitHubTokenStoreTest {
    @Test
    fun encryptedStoreNeverPersistsPlaintextAndClearMakesItUnreadable() {
        val storage = FakeCiphertextStorage()
        val store = CiphertextGitHubTokenStore(storage, PrefixTokenCipher())

        store.save("oauth-token-value")

        assertFalse(storage.value.orEmpty().contains("oauth-token-value"))
        assertEquals("oauth-token-value", store.load())
        store.clear()
        assertNull(storage.value)
        assertNull(store.load())
    }

    @Test
    fun corruptCiphertextIsClearedWithoutCrashingOrReturningAToken() {
        val storage = FakeCiphertextStorage().also { it.value = "corrupt-ciphertext" }
        val store = CiphertextGitHubTokenStore(storage, RejectingTokenCipher())

        assertNull(store.load())
        assertNull(storage.value)
    }
}

private class FakeCiphertextStorage : CiphertextStorage {
    var value: String? = null
    override fun read(): String? = value
    override fun write(value: String) { this.value = value }
    override fun clear() { value = null }
}

private class PrefixTokenCipher : TokenCipher {
    override fun encrypt(plaintext: String) = "cipher:${plaintext.reversed()}"
    override fun decrypt(ciphertext: String) = ciphertext.removePrefix("cipher:").reversed()
}

private class RejectingTokenCipher : TokenCipher {
    override fun encrypt(plaintext: String): String = error("not used")
    override fun decrypt(ciphertext: String): String = throw IllegalArgumentException("corrupt ciphertext")
}
