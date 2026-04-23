package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;

/**
 * Token state manager that delegates to DatabaseManager for persistence.
 * This class maintains backward compatibility with existing code.
 */
public class TokenStateManager {
    private static final Logger logger = LoggerFactory.getLogger(TokenStateManager.class);
    private final DatabaseManager databaseManager;

    public TokenStateManager() {
        this.databaseManager = new DatabaseManager();
    }

    public void updateExpiration(String profileName, Instant expiration) {
        databaseManager.updateExpiration(profileName, expiration);
    }

    public Instant getExpiration(String profileName) {
        return databaseManager.getExpiration(profileName);
    }

    public boolean isTokenValid(String profileName) {
        return databaseManager.isTokenValid(profileName);
    }

    public java.util.Map<String, Instant> getAllExpirations() {
        return databaseManager.getAllExpirations();
    }

    public void close() {
        databaseManager.close();
    }
}
