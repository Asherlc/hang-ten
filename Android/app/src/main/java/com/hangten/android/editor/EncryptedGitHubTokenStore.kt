package com.hangten.android.editor

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Storage and cipher seams keep the plaintext-storage contract JVM-testable. */
internal interface CiphertextStorage {
    fun read(): String?
    fun write(value: String)
    fun clear()
}

internal interface TokenCipher {
    fun encrypt(plaintext: String): String
    fun decrypt(ciphertext: String): String
}

internal class CiphertextGitHubTokenStore(
    private val storage: CiphertextStorage,
    private val cipher: TokenCipher,
) : GitHubTokenStore {
    override fun save(token: String) {
        require(token.isNotBlank()) { "GitHub token must not be blank." }
        storage.write(cipher.encrypt(token))
    }

    override fun load(): String? = runCatching {
        storage.read()?.let(cipher::decrypt)?.takeIf(String::isNotBlank)
    }.getOrElse {
        clear()
        null
    }

    override fun clear() = storage.clear()
}

/**
 * Stores the OAuth bearer credential encrypted with a non-exportable Android
 * Keystore AES key. Preferences receive only AES-GCM ciphertext and a random
 * IV, never a token or reusable credential in clear text.
 */
class EncryptedGitHubTokenStore(context: Context) : GitHubTokenStore {
    private val delegate = CiphertextGitHubTokenStore(
        SharedPreferencesCiphertextStorage(
            context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE),
        ),
        AndroidKeystoreTokenCipher(),
    )

    override fun save(token: String) = delegate.save(token)
    override fun load(): String? = delegate.load()
    override fun clear() = delegate.clear()

    private companion object {
        const val PREFERENCES = "hangten.github.encrypted"
    }
}

private class SharedPreferencesCiphertextStorage(
    private val preferences: SharedPreferences,
) : CiphertextStorage {
    override fun read(): String? = preferences.getString(TOKEN, null)
    override fun write(value: String) {
        check(preferences.edit().putString(TOKEN, value).commit()) { "Unable to save encrypted GitHub credential." }
    }
    override fun clear() {
        check(preferences.edit().remove(TOKEN).commit()) { "Unable to clear encrypted GitHub credential." }
    }

    private companion object { const val TOKEN = "oauth_token" }
}

private class AndroidKeystoreTokenCipher : TokenCipher {
    override fun encrypt(plaintext: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        return Base64.encodeToString(cipher.iv + cipher.doFinal(plaintext.encodeToByteArray()), Base64.NO_WRAP)
    }

    override fun decrypt(ciphertext: String): String {
        val combined = Base64.decode(ciphertext, Base64.NO_WRAP)
        require(combined.size > IV_BYTES) { "Encrypted GitHub credential is malformed." }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, combined.copyOfRange(0, IV_BYTES)))
        return cipher.doFinal(combined.copyOfRange(IV_BYTES, combined.size)).decodeToString()
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "com.hangten.training.github.device-flow.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
        const val TAG_BITS = 128
    }
}
