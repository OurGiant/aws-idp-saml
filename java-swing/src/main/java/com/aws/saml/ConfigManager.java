package com.aws.saml;

import org.ini4j.Ini;
import org.ini4j.Profile;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Manages configuration reading from samlsts file
 */
public class ConfigManager {
    private static final Logger logger = LoggerFactory.getLogger(ConfigManager.class);

    private final String configFilePath;
    private Ini config;
    private final DatabaseManager databaseManager;

    public ConfigManager() {
        // Use same path as Python version: ~/.aws/samlsts
        String homeDir = System.getProperty("user.home");
        Path awsDir = Paths.get(homeDir, ".aws");
        this.configFilePath = awsDir.resolve("samlsts").toString();
        this.databaseManager = new DatabaseManager();

        loadConfig();
    }

    private void loadConfig() {
        try {
            File configFile = new File(configFilePath);
            if (!configFile.exists()) {
                throw new RuntimeException("Configuration file not found: " + configFilePath +
                    "\nPlease copy samlsts.demo to ~/.aws/samlsts and configure it.");
            }
            config = new Ini(configFile);
            logger.info("Configuration loaded from: {}", configFilePath);
        } catch (Exception e) {
            logger.error("Failed to load configuration", e);
            throw new RuntimeException("Failed to load configuration: " + e.getMessage(), e);
        }
    }

    /**
     * Get list of available profile names (excluding provider sections)
     */
    public List<String> getAvailableProfiles() {
        List<String> profiles = new ArrayList<>();
        Set<String> sections = config.keySet();

        for (String section : sections) {
            if (!section.startsWith("Fed-")) {
                profiles.add(section);
            }
        }

        return profiles;
    }

    /**
     * Get profile configuration
     */
    public Profile.Section getProfile(String profileName) {
        return config.get(profileName);
    }

    /**
     * Get provider configuration
     */
    public Profile.Section getProvider(String providerName) {
        return config.get(providerName);
    }

    /**
     * Get global configuration section
     */
    public Profile.Section getGlobalConfig() {
        return config.get("global");
    }

    /**
     * Get AWS region for a profile
     */
    public String getAwsRegion(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String region = profile.get("awsregion");
            if (region != null) {
                return region;
            }
        }

        // Fall back to global config
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            String region = global.get("awsregion");
            if (region != null) {
                return region;
            }
            return "us-east-1";
        }

        return "us-east-1";
    }

    /**
     * Get account number for a profile
     */
    public String getAccountNumber(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String accountNumber = profile.get("accountnumber");
            if (accountNumber != null) {
                return accountNumber;
            }
        }

        // Fall back to global config
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            return global.get("accountnumber");
        }

        return null;
    }

    /**
     * Get IAM role for a profile
     */
    public String getIamRole(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String iamRole = profile.get("iamrole");
            if (iamRole != null) {
                return iamRole;
            }
        }

        // Fall back to global config
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            return global.get("iamrole");
        }

        return null;
    }

    /**
     * Get SAML provider for a profile
     */
    public String getSamlProvider(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String samlProvider = profile.get("samlprovider");
            if (samlProvider != null) {
                return samlProvider;
            }
        }

        // Fall back to global config
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            return global.get("samlprovider");
        }

        return null;
    }

    /**
     * Get username for a profile
     */
    public String getUsername(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String username = profile.get("username");
            if (username != null) {
                return username;
            }
        }

        // Fall back to global config - also check lowercase variant
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            String username = global.get("username");
            if (username != null) {
                return username;
            }
            return global.get("User");
        }

        return null;
    }

    /**
     * Get session duration for a profile
     */
    public int getSessionDuration(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String duration = profile.get("sessionduration");
            if (duration != null) {
                try {
                    return Integer.parseInt(duration);
                } catch (NumberFormatException e) {
                    logger.warn("Invalid session duration for profile {}: {}", profileName, duration);
                }
            }
        }

        // Fall back to global config
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            String duration = global.get("sessionduration");
            if (duration != null) {
                try {
                    return Integer.parseInt(duration);
                } catch (NumberFormatException e) {
                    logger.warn("Invalid global session duration: {}", duration);
                }
            }
        }

        return databaseManager.getSessionDuration(); // Use database default (4 hours)
    }

    /**
     * Get GUI name for a profile
     */
    public String getGuiName(String profileName) {
        Profile.Section profile = getProfile(profileName);
        if (profile != null) {
            String guiName = profile.get("guiname");
            if (guiName != null) {
                return guiName.trim();
            }
        }
        return null;
    }

    /**
     * Get browser type from global config
     */
    public String getBrowserType() {
        Profile.Section global = getGlobalConfig();
        if (global != null) {
            return global.get("browser", "chrome");
        }
        return "chrome";
    }
}