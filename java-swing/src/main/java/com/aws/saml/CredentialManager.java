package com.aws.saml;

import org.ini4j.Ini;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.HashSet;
import java.util.Set;
import java.util.HashSet;
import java.util.Set;

/**
 * Manages AWS credentials reading and display
 */
public class CredentialManager {
    private static final Logger logger = LoggerFactory.getLogger(CredentialManager.class);

    private final String credentialsFilePath;
    private final TokenStateManager tokenStateManager;
    private Ini credentials;

    public CredentialManager() {
        // Use same path as Python version: ~/.aws/credentials
        String homeDir = System.getProperty("user.home");
        Path awsDir = Paths.get(homeDir, ".aws");
        this.credentialsFilePath = awsDir.resolve("credentials").toString();
        this.tokenStateManager = new TokenStateManager();

        loadCredentials();
    }

    private void loadCredentials() {
        try {
            File credFile = new File(credentialsFilePath);
            if (!credFile.exists()) {
                credentials = new Ini();
                logger.info("Credentials file does not exist yet: {}", credentialsFilePath);
                return;
            }
            credentials = new Ini(credFile);
            logger.debug("Credentials loaded from: {}", credentialsFilePath);
        } catch (Exception e) {
            logger.error("Failed to load credentials", e);
            credentials = new Ini();
        }
    }

    /**
     * Get formatted display of active credentials
     */
    public String getActiveCredentialsDisplay() {
        loadCredentials(); // Refresh credentials

        if (credentials.isEmpty()) {
            return "No AWS credentials found.\n\nCredentials file: " + credentialsFilePath + "\n\nUse 'Request Credentials' to obtain new credentials.";
        }

        StringBuilder display = new StringBuilder();
        display.append("Active AWS Credentials:\n");
        display.append("=".repeat(50)).append("\n\n");

        for (String profile : credentials.keySet()) {
            display.append("Profile: ").append(profile).append("\n");
            display.append("-".repeat(30)).append("\n");

            Ini.Section section = credentials.get(profile);
            if (section != null) {
                String accessKey = section.get("aws_access_key_id");
                String secretKey = section.get("aws_secret_access_key");
                String sessionToken = section.get("aws_session_token");

                if (accessKey != null && !accessKey.isEmpty()) {
                    display.append("Access Key ID: ").append(maskString(accessKey)).append("\n");
                }
                if (secretKey != null && !secretKey.isEmpty()) {
                    display.append("Secret Access Key: ").append(maskString(secretKey)).append("\n");
                }
                if (sessionToken != null && !sessionToken.isEmpty()) {
                    display.append("Session Token: ").append(maskString(sessionToken)).append("\n");
                }

                Instant expiresAt = tokenStateManager.getExpiration(profile);
                if (expiresAt != null) {
                    try {
                        display.append("Expires At: ")
                               .append(LocalDateTime.ofInstant(expiresAt, ZoneId.systemDefault())
                               .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")))
                               .append("\n");
                        display.append("Status: ")
                               .append(tokenStateManager.isTokenValid(profile) ? "VALID" : "EXPIRED")
                               .append("\n");
                    } catch (Exception e) {
                        display.append("Expires At: Invalid date format\n");
                        display.append("Status: UNKNOWN\n");
                    }
                }
            }

            display.append("\n");
        }

        display.append("Credentials file: ").append(credentialsFilePath).append("\n");
        display.append("Last updated: ").append(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));

        return display.toString();
    }

    /**
     * Mask sensitive strings for display
     */
    private String maskString(String value) {
        if (value == null || value.length() <= 8) {
            return value;
        }
        return value.substring(0, 4) + "*".repeat(value.length() - 8) + value.substring(value.length() - 4);
    }

    /**
     * Check if a profile has valid credentials
     */
    public boolean hasValidCredentials(String profileName) {
        loadCredentials();
        Ini.Section section = credentials.get(profileName);
        if (section == null) {
            return false;
        }

        String accessKey = section.get("aws_access_key_id");
        String secretKey = section.get("aws_secret_access_key");
        String sessionToken = section.get("aws_session_token");

        return accessKey != null && !accessKey.isEmpty() &&
               secretKey != null && !secretKey.isEmpty() &&
               sessionToken != null && !sessionToken.isEmpty() &&
               tokenStateManager.isTokenValid(profileName);
    }

    /**
     * Get credentials for a specific profile
     */
    public AwsCredentials getCredentials(String profileName) {
        loadCredentials();
        Ini.Section section = credentials.get(profileName);
        if (section == null) {
            return null;
        }

        return new AwsCredentials(
            section.get("aws_access_key_id"),
            section.get("aws_secret_access_key"),
            section.get("aws_session_token")
        );
    }

    /**
     * Save credentials for a profile
     */
    public void saveCredentials(String profileName, AwsCredentials creds) {
        try {
            Ini.Section section = credentials.get(profileName);
            if (section == null) {
                section = credentials.add(profileName);
            }

            section.put("aws_access_key_id", creds.getAccessKeyId());
            section.put("aws_secret_access_key", creds.getSecretAccessKey());
            section.put("aws_session_token", creds.getSessionToken());

            if (creds.getExpiration() != null) {
                tokenStateManager.updateExpiration(profileName, creds.getExpiration());
            }

            // Ensure .aws directory exists
            File credFile = new File(credentialsFilePath);
            credFile.getParentFile().mkdirs();

            credentials.store(credFile);
            logger.info("Credentials saved for profile: {}", profileName);
        } catch (Exception e) {
            logger.error("Failed to save credentials for profile: {}", profileName, e);
            throw new RuntimeException("Failed to save credentials: " + e.getMessage(), e);
        }
    }

    /**
     * Get all profile names from the credentials file
     */
    public Set<String> getAllProfileNames() {
        loadCredentials();
        return new HashSet<>(credentials.keySet());
    }

    /**
     * Get the credentials Ini object (for internal use)
     */
    public Ini getCredentialsIni() {
        loadCredentials();
        return credentials;
    }

    /**
     * Simple credentials container class
     */
    public static class AwsCredentials {
        private final String accessKeyId;
        private final String secretAccessKey;
        private final String sessionToken;
        private final Instant expiration;

        public AwsCredentials(String accessKeyId, String secretAccessKey, String sessionToken) {
            this(accessKeyId, secretAccessKey, sessionToken, null);
        }

        public AwsCredentials(String accessKeyId, String secretAccessKey, String sessionToken, Instant expiration) {
            this.accessKeyId = accessKeyId;
            this.secretAccessKey = secretAccessKey;
            this.sessionToken = sessionToken;
            this.expiration = expiration;
        }

        public String getAccessKeyId() { return accessKeyId; }
        public String getSecretAccessKey() { return secretAccessKey; }
        public String getSessionToken() { return sessionToken; }
        public Instant getExpiration() { return expiration; }
    }
}