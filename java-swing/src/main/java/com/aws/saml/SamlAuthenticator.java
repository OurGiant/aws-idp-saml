package com.aws.saml;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.firefox.FirefoxOptions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.auth.credentials.AwsSessionCredentials;
import software.amazon.awssdk.auth.credentials.AnonymousCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sts.StsClient;
import software.amazon.awssdk.services.sts.model.AssumeRoleWithSamlRequest;
import software.amazon.awssdk.services.sts.model.AssumeRoleWithSamlResponse;
import software.amazon.awssdk.services.sts.model.Credentials;

import javax.swing.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;

/**
 * Handles SAML authentication and AWS credential generation
 */
public class SamlAuthenticator {
    private static final Logger logger = LoggerFactory.getLogger(SamlAuthenticator.class);

    private final ConfigManager configManager;
    private final CredentialManager credentialManager;
    private final PasswordManager passwordManager;

    public SamlAuthenticator() {
        this.configManager = new ConfigManager();
        this.credentialManager = new CredentialManager();
        this.passwordManager = new PasswordManager(new DatabaseManager());
    }

    /**
     * Main method to request credentials for a profile
     */
    public void requestCredentials(String profileName, boolean useOktaFastPass) throws Exception {
        logger.info("Starting credential request for profile: {}", profileName);

        // Get profile configuration
        String samlProvider = configManager.getSamlProvider(profileName);
        String accountNumber = configManager.getAccountNumber(profileName);
        String iamRole = configManager.getIamRole(profileName);
        String username = configManager.getUsername(profileName);
        String awsRegion = configManager.getAwsRegion(profileName);
        int sessionDuration = configManager.getSessionDuration(profileName);

        if (samlProvider == null || accountNumber == null || iamRole == null) {
            throw new IllegalArgumentException("Incomplete profile configuration for: " + profileName);
        }

        // Get provider configuration
        var providerConfig = configManager.getProvider(samlProvider);
        if (providerConfig == null) {
            throw new IllegalArgumentException("SAML provider not found: " + samlProvider);
        }

        String loginUrl = providerConfig.get("loginpage");
        String loginTitle = providerConfig.get("logintitle");

        if (loginUrl == null || loginTitle == null) {
            throw new IllegalArgumentException("Incomplete provider configuration for: " + samlProvider);
        }

        // Perform browser login and get SAML response
        String samlResponse = performBrowserLogin(loginUrl, loginTitle, username, useOktaFastPass);

        // Parse SAML and get role ARN
        SamlParser samlParser = new SamlParser();
        var roles = samlParser.parseRolesFromSaml(samlResponse);

        // Find the matching role
        String roleArn = findMatchingRole(roles, accountNumber, iamRole);
        String principalArn = "arn:aws:iam::" + accountNumber + ":saml-provider/" + samlProvider.substring(4); // Remove "Fed-" prefix

        // Assume role with SAML
        var awsCredentials = assumeRoleWithSaml(principalArn, roleArn, samlResponse, awsRegion, sessionDuration);

        // Save credentials
        credentialManager.saveCredentials(profileName, awsCredentials);

        logger.info("Successfully obtained and saved credentials for profile: {}", profileName);
    }

    /**
     * Perform browser login and capture SAML response
     */
    private String performBrowserLogin(String loginUrl, String loginTitle, String username, boolean useOktaFastPass) throws Exception {
        logger.info("Starting browser login to: {}", loginUrl);

        WebDriver driver = createWebDriver();
        try {
            BrowserLoginHandler loginHandler = new BrowserLoginHandler(driver, useOktaFastPass, passwordManager);
            return loginHandler.performLogin(loginUrl, loginTitle, username);
        } finally {
            if (driver != null) {
                driver.quit();
            }
        }
    }

    /**
     * Create WebDriver instance based on configuration
     */
    private WebDriver createWebDriver() {
        String browserType = configManager.getBrowserType().toLowerCase();

        switch (browserType) {
            case "firefox":
                return createFirefoxDriver();
            case "chrome":
            default:
                return createChromeDriver();
        }
    }

    private WebDriver createChromeDriver() {
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless"); // Run headless
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");

        // Set webdriver.chrome.driver if not set
        if (System.getProperty("webdriver.chrome.driver") == null) {
            String driverPath = findBrowserDriver("chromedriver.exe");
            if (driverPath != null) {
                System.setProperty("webdriver.chrome.driver", driverPath);
            }
        }

        return new ChromeDriver(options);
    }

    private WebDriver createFirefoxDriver() {
        FirefoxOptions options = new FirefoxOptions();
        options.addArguments("--headless");

        // Set webdriver.gecko.driver if not set
        if (System.getProperty("webdriver.gecko.driver") == null) {
            String driverPath = findBrowserDriver("geckodriver.exe");
            if (driverPath != null) {
                System.setProperty("webdriver.gecko.driver", driverPath);
            }
        }

        return new FirefoxDriver(options);
    }

    /**
     * Find browser driver in common locations
     */
    private String findBrowserDriver(String driverName) {
        // Check current directory
        Path currentDir = Paths.get(".");
        Path driverPath = currentDir.resolve("drivers").resolve(driverName);
        if (Files.exists(driverPath)) {
            return driverPath.toAbsolutePath().toString();
        }

        // Check drivers directory in project root
        Path projectRoot = Paths.get(".").toAbsolutePath();
        while (projectRoot.getParent() != null && !Files.exists(projectRoot.resolve("pom.xml"))) {
            projectRoot = projectRoot.getParent();
        }
        driverPath = projectRoot.resolve("drivers").resolve(driverName);
        if (Files.exists(driverPath)) {
            return driverPath.toAbsolutePath().toString();
        }

        // Check system PATH
        String pathEnv = System.getenv("PATH");
        if (pathEnv != null) {
            for (String path : pathEnv.split(";")) {
                driverPath = Paths.get(path, driverName);
                if (Files.exists(driverPath)) {
                    return driverPath.toAbsolutePath().toString();
                }
            }
        }

        logger.warn("Browser driver not found: {}", driverName);
        return null;
    }

    /**
     * Find matching role from SAML response
     */
    private String findMatchingRole(java.util.List<SamlRole> roles, String accountNumber, String iamRole) {
        for (SamlRole role : roles) {
            if (role.getAccountNumber().equals(accountNumber) && role.getRoleName().equals(iamRole)) {
                return role.getRoleArn();
            }
        }
        throw new RuntimeException("Matching role not found in SAML response: " + accountNumber + "/" + iamRole);
    }

    /**
     * Assume AWS role using SAML assertion
     */
    private CredentialManager.AwsCredentials assumeRoleWithSaml(String principalArn, String roleArn,
                                                               String samlAssertion, String region, int durationSeconds) {
        logger.info("Assuming role: {}", roleArn);

        try (StsClient stsClient = StsClient.builder()
                .region(Region.of(region))
                .credentialsProvider(AnonymousCredentialsProvider.create())
                .build()) {

            AssumeRoleWithSamlRequest request = AssumeRoleWithSamlRequest.builder()
                    .roleArn(roleArn)
                    .principalArn(principalArn)
                    .samlAssertion(samlAssertion)
                    .durationSeconds(durationSeconds)
                    .build();

            AssumeRoleWithSamlResponse response = stsClient.assumeRoleWithSAML(request);
            Credentials credentials = response.credentials();

            logger.debug("AWS Credentials expiration: {} (type: {})", credentials.expiration(), credentials.expiration().getClass());

            return new CredentialManager.AwsCredentials(
                    credentials.accessKeyId(),
                    credentials.secretAccessKey(),
                    credentials.sessionToken(),
                    credentials.expiration()
            );

        } catch (Exception e) {
            logger.error("Failed to assume role with SAML", e);
            throw new RuntimeException("AWS STS error: " + e.getMessage(), e);
        }
    }
}