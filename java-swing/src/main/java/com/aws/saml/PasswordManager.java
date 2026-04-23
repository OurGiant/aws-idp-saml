package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;

/**
 * Manages secure storage and retrieval of Okta user passwords.
 * Uses AES-GCM encryption for password storage.
 */
public class PasswordManager {
    private static final Logger logger = LoggerFactory.getLogger(PasswordManager.class);
    private static final int GCM_IV_LENGTH = 12; // 96 bits
    private static final int GCM_TAG_LENGTH = 128; // 128 bits
    private static final int KEY_SIZE = 256; // 256 bits
    private static final String CIPHER_ALGORITHM = "AES/GCM/NoPadding";
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private final DatabaseManager databaseManager;
    private SecretKey encryptionKey;

    public PasswordManager(DatabaseManager databaseManager) {
        this.databaseManager = databaseManager;
        this.encryptionKey = getOrGenerateKey();
    }

    /**
     * Get or generate the master encryption key for password storage.
     */
    private SecretKey getOrGenerateKey() {
        try {
            String encodedKey = databaseManager.getConfig("password_encryption_key");
            if (encodedKey != null && !encodedKey.isEmpty()) {
                byte[] decodedKey = Base64.getDecoder().decode(encodedKey);
                return new javax.crypto.spec.SecretKeySpec(decodedKey, 0, decodedKey.length, "AES");
            }

            // Generate new key
            KeyGenerator keyGen = KeyGenerator.getInstance("AES");
            keyGen.init(KEY_SIZE);
            SecretKey key = keyGen.generateKey();

            // Store the key
            String encodedNewKey = Base64.getEncoder().encodeToString(key.getEncoded());
            databaseManager.setConfig("password_encryption_key", encodedNewKey);
            logger.info("Generated new password encryption key");

            return key;
        } catch (Exception e) {
            logger.error("Failed to initialize encryption key", e);
            throw new RuntimeException("Password encryption key initialization failed", e);
        }
    }

    /**
     * Encrypt a password for storage.
     */
    private String encryptPassword(String password) throws Exception {
        Cipher cipher = Cipher.getInstance(CIPHER_ALGORITHM);

        // Generate cryptographically secure random IV
        byte[] iv = new byte[GCM_IV_LENGTH];
        SECURE_RANDOM.nextBytes(iv);

        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.ENCRYPT_MODE, encryptionKey, spec);

        byte[] encryptedPassword = cipher.doFinal(password.getBytes(StandardCharsets.UTF_8));

        // Combine IV and encrypted data: IV (12 bytes) + ciphertext
        ByteBuffer buffer = ByteBuffer.allocate(iv.length + encryptedPassword.length);
        buffer.put(iv);
        buffer.put(encryptedPassword);

        return Base64.getEncoder().encodeToString(buffer.array());
    }

    /**
     * Decrypt a stored password.
     */
    private String decryptPassword(String encryptedPassword) throws Exception {
        byte[] data = Base64.getDecoder().decode(encryptedPassword);
        ByteBuffer buffer = ByteBuffer.wrap(data);

        // Read IV from buffer (not hardcoded - this is read from encrypted data)
        byte[] iv = new byte[GCM_IV_LENGTH];
        buffer.get(iv);

        byte[] ciphertext = new byte[buffer.remaining()];
        buffer.get(ciphertext);

        Cipher cipher = Cipher.getInstance(CIPHER_ALGORITHM);
        // IV is read from encrypted data, not hardcoded
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.DECRYPT_MODE, encryptionKey, spec);

        byte[] decrypted = cipher.doFinal(ciphertext);
        return new String(decrypted, StandardCharsets.UTF_8);
    }

    /**
     * Store a password with expiration settings.
     */
    public void storePassword(String password) {
        try {
            String encrypted = encryptPassword(password);
            databaseManager.setConfig("okta_password", encrypted);
            databaseManager.setConfig("okta_password_stored_at", Instant.now().toString());
            logger.info("Okta password stored successfully");
        } catch (Exception e) {
            logger.error("Failed to store password", e);
            throw new RuntimeException("Password storage failed: " + e.getMessage(), e);
        }
    }

    /**
     * Retrieve and validate stored password.
     * Returns null if password doesn't exist or has expired.
     */
    public String retrievePassword() {
        try {
            String encrypted = databaseManager.getConfig("okta_password");
            String storedAtStr = databaseManager.getConfig("okta_password_stored_at");

            if (encrypted == null || encrypted.isEmpty() || storedAtStr == null) {
                logger.debug("No stored password found");
                return null;
            }

            // Check password age
            Instant storedAt = Instant.parse(storedAtStr);
            int expirationMinutes = databaseManager.getPasswordExpirationMinutes();
            long expirationMillis = expirationMinutes * 60L * 1000L;
            long ageMillis = System.currentTimeMillis() - storedAt.toEpochMilli();

            if (ageMillis > expirationMillis) {
                logger.info("Stored password has expired (age: {} minutes, expiration: {} minutes)",
                    ageMillis / 60000, expirationMinutes);
                clearPassword();
                return null;
            }

            String decrypted = decryptPassword(encrypted);
            logger.debug("Retrieved stored password (age: {} minutes)", ageMillis / 60000);
            return decrypted;
        } catch (Exception e) {
            logger.error("Failed to retrieve password", e);
            clearPassword(); // Clear if decryption fails
            return null;
        }
    }

    /**
     * Clear stored password.
     */
    public void clearPassword() {
        databaseManager.setConfig("okta_password", "");
        databaseManager.setConfig("okta_password_stored_at", "");
        logger.info("Stored password cleared");
    }

    /**
     * Check if password storage is enabled.
     */
    public boolean isPasswordStorageEnabled() {
        String enabled = databaseManager.getConfig("store_password_enabled");
        return enabled != null && enabled.equalsIgnoreCase("true");
    }

    /**
     * Enable/disable password storage.
     */
    public void setPasswordStorageEnabled(boolean enabled) {
        databaseManager.setConfig("store_password_enabled", String.valueOf(enabled));
        if (!enabled) {
            clearPassword();
        }
    }
}