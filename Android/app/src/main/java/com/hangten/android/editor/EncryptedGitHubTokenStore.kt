package com.hangten.android.editor

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Stores the OAuth bearer credential encrypted with a non-exportable Android
 * Keystore AES key. The preference value is ciphertext plus its random IV,
 * never a token or reusable credential in clear text.
 */
class EncryptedGitHubTokenStore(context: Context) : GitHubTokenStore {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    override fun save(token: String) {
        require(token.isNotBlank()) { "GitHub token must not be blank." }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encoded = Base64.encodeToString(cipher.iv + cipher.doFinal(token.encodeToByteArray()), Base64.NO_WRAP)
        check(preferences.edit().putString(TOKEN, encoded).commit()) { "Unable to save encrypted GitHub credential." }
    }

    override fun load(): String? = runCatching {
        val encoded = preferences.getString(TOKEN, null) ?: return null
        val combined = Base64.decode(encoded, Base64.NO_WRAP)
        if (combined.size <= IV_BYTES) return null
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, combined.copyOfRange(0, IV_BYTES)))
        cipher.doFinal(combined.copyOfRange(IV_BYTES, combined.size)).decodeToString().takeIf(String::isNotBlank)
    }.getOrElse {
        clear()
        null
    }

    override fun clear() {
        check(preferences.edit().remove(TOKEN).commit()) { "Unable to clear encrypted GitHub credential." }
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
        const val PREFERENCES = "hangten.github.encrypted"
        const val TOKEN = "oauth_token"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "com.hangten.training.github.device-flow.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
        const val TAG_BITS = 128
    }
}
