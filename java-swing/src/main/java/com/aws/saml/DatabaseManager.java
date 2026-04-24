package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.sql.*;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Database manager for storing configuration and token state information.
 */
public class DatabaseManager {
    private static final Logger logger = LoggerFactory.getLogger(DatabaseManager.class);
    private static final String DB_NAME = "aws_saml.db";
    private Connection connection;

    public DatabaseManager() {
        initializeDatabase();
    }

    private void initializeDatabase() {
        try {
            String homeDir = System.getProperty("user.home");
            String dbPath = homeDir + File.separator + ".aws" + File.separator + DB_NAME;

            // Ensure .aws directory exists
            File awsDir = new File(homeDir + File.separator + ".aws");
            if (!awsDir.exists()) {
                awsDir.mkdirs();
            }

            connection = DriverManager.getConnection("jdbc:sqlite:" + dbPath);
            createTables();
            logger.info("Database initialized at: {}", dbPath);
        } catch (SQLException e) {
            logger.error("Failed to initialize database", e);
            throw new RuntimeException("Database initialization failed", e);
        }
    }

    private void createTables() throws SQLException {
        // Configuration table
        String createConfigTable = """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """;

        // Token state table
        String createTokenTable = """
            CREATE TABLE IF NOT EXISTS token_state (
                profile_name TEXT PRIMARY KEY,
                expiration TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """;

        try (Statement stmt = connection.createStatement()) {
            stmt.execute(createConfigTable);
            stmt.execute(createTokenTable);

            // Insert default configuration values
            insertDefaultConfig();
        }
    }

    private void insertDefaultConfig() throws SQLException {
        String[] defaults = {
            "session_duration", "14400", // 4 hours in seconds
            "min_duration", "900",      // 15 minutes in seconds
            "max_duration", "28800",    // 8 hours in seconds
            "theme", "Flat Dark"        // Default to Flat Dark theme
        };

        String insertSQL = "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(insertSQL)) {
            for (int i = 0; i < defaults.length; i += 2) {
                pstmt.setString(1, defaults[i]);
                pstmt.setString(2, defaults[i + 1]);
                pstmt.executeUpdate();
            }
        }
    }

    // Configuration methods
    public String getConfig(String key) {
        String sql = "SELECT value FROM config WHERE key = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, key);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                return rs.getString("value");
            }
        } catch (SQLException e) {
            logger.error("Failed to get config value for key: {}", key, e);
        }
        return null;
    }

    public void setConfig(String key, String value) {
        String sql = "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, key);
            pstmt.setString(2, value);
            pstmt.executeUpdate();
        } catch (SQLException e) {
            logger.error("Failed to set config value for key: {}", key, e);
        }
    }

    public int getSessionDuration() {
        String value = getConfig("session_duration");
        return value != null ? Integer.parseInt(value) : 14400; // Default 4 hours
    }

    public void setSessionDuration(int seconds) {
        setConfig("session_duration", String.valueOf(seconds));
    }

    public int getMinDuration() {
        String value = getConfig("min_duration");
        return value != null ? Integer.parseInt(value) : 900; // Default 15 minutes
    }

    public int getMaxDuration() {
        String value = getConfig("max_duration");
        return value != null ? Integer.parseInt(value) : 28800; // Default 8 hours
    }

    public int getPasswordExpirationMinutes() {
        String value = getConfig("password_expiration_minutes");
        return value != null ? Integer.parseInt(value) : 1440; // Default 24 hours (1440 minutes)
    }

    public void setPasswordExpirationMinutes(int minutes) {
        setConfig("password_expiration_minutes", String.valueOf(minutes));
    }

    public String getTheme() {
        String value = getConfig("theme");
        return value != null ? value : "Flat Dark"; // Default Flat Dark
    }

    public void setTheme(String theme) {
        setConfig("theme", theme);
    }

    // Token state methods
    public void updateExpiration(String profileName, Instant expiration) {
        if (profileName == null || expiration == null) {
            return;
        }

        String sql = """
            INSERT OR REPLACE INTO token_state (profile_name, expiration, created_at)
            VALUES (?, ?, ?)
            """;

        String now = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, profileName);
            pstmt.setString(2, expiration.toString());
            pstmt.setString(3, now);
            pstmt.executeUpdate();
            logger.debug("Updated expiration for profile {}: {}", profileName, expiration);
        } catch (SQLException e) {
            logger.error("Failed to update expiration for profile: {}", profileName, e);
        }
    }

    public Instant getExpiration(String profileName) {
        if (profileName == null) {
            return null;
        }

        String sql = "SELECT expiration FROM token_state WHERE profile_name = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, profileName);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                String expirationStr = rs.getString("expiration");
                return Instant.parse(expirationStr);
            }
        } catch (SQLException e) {
            logger.error("Failed to get expiration for profile: {}", profileName, e);
        }
        return null;
    }

    public boolean isTokenValid(String profileName) {
        Instant expiration = getExpiration(profileName);
        return expiration != null && expiration.isAfter(Instant.now());
    }

    public Map<String, Instant> getAllExpirations() {
        Map<String, Instant> expirations = new LinkedHashMap<>();
        String sql = "SELECT profile_name, expiration FROM token_state";
        try (PreparedStatement pstmt = connection.prepareStatement(sql);
             ResultSet rs = pstmt.executeQuery()) {
            while (rs.next()) {
                String profileName = rs.getString("profile_name");
                String expirationStr = rs.getString("expiration");
                try {
                    Instant expiration = Instant.parse(expirationStr);
                    expirations.put(profileName, expiration);
                } catch (Exception e) {
                    logger.warn("Invalid expiration format for profile {}: {}", profileName, expirationStr);
                }
            }
        } catch (SQLException e) {
            logger.error("Failed to get all expirations", e);
        }
        return expirations;
    }

    public void close() {
        if (connection != null) {
            try {
                connection.close();
                logger.info("Database connection closed");
            } catch (SQLException e) {
                logger.error("Failed to close database connection", e);
            }
        }
    }
}