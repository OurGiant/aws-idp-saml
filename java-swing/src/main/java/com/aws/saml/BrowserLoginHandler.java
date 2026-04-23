package com.aws.saml;

import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.swing.*;
import java.awt.*;
import java.time.Duration;

/**
 * Handles browser automation for SAML login
 */
public class BrowserLoginHandler {
    private static final Logger logger = LoggerFactory.getLogger(BrowserLoginHandler.class);

    private final WebDriver driver;
    private final WebDriverWait wait;
    private final boolean useOktaFastPass;

    public BrowserLoginHandler(WebDriver driver, boolean useOktaFastPass) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(30));
        this.useOktaFastPass = useOktaFastPass;
    }

    /**
     * Perform login and capture SAML response
     */
    public String performLogin(String loginUrl, String loginTitle, String username) throws Exception {
        logger.info("Navigating to login page: {}", loginUrl);

        try {
            // Navigate to login page
            driver.get(loginUrl);

            // Wait for login page to load
            wait.until(ExpectedConditions.titleContains(loginTitle));

            // Handle Okta login (since user specified Okta)
            return handleOktaLogin(username);

        } catch (Exception e) {
            logger.error("Login failed", e);
            throw new RuntimeException("Login process failed: " + e.getMessage(), e);
        }
    }

    /**
     * Handle Okta-specific login flow
     */
    private String handleOktaLogin(String username) throws Exception {
        logger.info("Handling Okta login for user: {}", username);

        // Detect managed-device Okta flow with pre-authenticated MFA screen first
        if (isPreAuthenticatedOktaMfaScreen()) {
            logger.info("Detected pre-authenticated Okta MFA screen; skipping username/password entry");
            clickOktaSelection();
            return waitForSamlResponse();
        }

        // Wait for and fill username field
        try {
            WebElement usernameField = wait.until(ExpectedConditions.elementToBeClickable(By.id("okta-signin-username")));
            usernameField.clear();
            usernameField.sendKeys(username);

            // Click next/sign in
            WebElement nextButton = wait.until(ExpectedConditions.elementToBeClickable(By.id("okta-signin-submit")));
            nextButton.click();
        } catch (TimeoutException e) {
            logger.info("Okta username field not found; checking for managed-device MFA flow");
            if (isPreAuthenticatedOktaMfaScreen()) {
                logger.info("Detected managed-device Okta MFA flow after missing username field");
                clickOktaSelection();
                return waitForSamlResponse();
            }
            throw e;
        }

        // Wait for password field or MFA
        try {
            // Try to find password field
            WebElement passwordField = wait.until(ExpectedConditions.elementToBeClickable(By.id("okta-signin-password")));
            String password = promptForPassword();
            passwordField.clear();
            passwordField.sendKeys(password);

            // Submit password
            WebElement signInButton = wait.until(ExpectedConditions.elementToBeClickable(By.id("okta-signin-submit")));
            signInButton.click();
        } catch (TimeoutException e) {
            // Password field not found, might be MFA or different flow
            logger.info("Password field not found, waiting for MFA or redirect");
        }

        if (useOktaFastPass) {
            clickOktaFastPassSelection();
        } else {
            clickOktaMfaSelection();
        }

        // Wait for SAML response or AWS sign-in page
        return waitForSamlResponse();
    }

    private boolean isPreAuthenticatedOktaMfaScreen() {
        try {
            WebDriverWait shortWait = new WebDriverWait(driver, Duration.ofSeconds(10));
            shortWait.until(ExpectedConditions.presenceOfElementLocated(By.linkText("Back to sign in")));
            String pageSource = driver.getPageSource();
            boolean hasMfaIndicator = pageSource.contains("class=\"button select-factor link-button\"");
            return hasMfaIndicator;
        } catch (TimeoutException e) {
            return false;
        }
    }

    private void clickOktaSelection() {
        if (useOktaFastPass) {
            clickOktaFastPassSelection();
        } else {
            clickOktaMfaSelection();
        }
    }

    private void clickOktaFastPassSelection() {
        try {
            By fastPassLocator = By.xpath(
                "//a[@aria-label='Select Okta Verify.'] | //a[contains(@aria-label,'Okta Verify')]"
            );
            WebElement fastPassOption = wait.until(ExpectedConditions.elementToBeClickable(fastPassLocator));
            fastPassOption.click();
        } catch (TimeoutException e) {
            throw new RuntimeException("Could not find Okta FastPass selection button on managed-device login screen", e);
        }
    }

    private void clickOktaMfaSelection() {
        try {
            By selectionLocator = By.xpath(
                "//a[@aria-label='Select to get a push notification to the Okta Verify app.']"
                + " | //input[@class='button button-primary' and @type='submit' and @value='Send push' and @data-type='save']"
            );
            WebElement mfaOption = wait.until(ExpectedConditions.elementToBeClickable(selectionLocator));
            mfaOption.click();
        } catch (TimeoutException e) {
            throw new RuntimeException("Could not find Okta MFA push selection button on managed-device login screen", e);
        }
    }

    /**
     * Prompt user for password using Swing dialog
     */
    private String promptForPassword() {
        JPasswordField passwordField = new JPasswordField();
        passwordField.setEchoChar('*');

        Object[] message = {
            "Enter your IdP password:",
            passwordField
        };

        int option = JOptionPane.showConfirmDialog(
            null,
            message,
            "IdP Authentication",
            JOptionPane.OK_CANCEL_OPTION,
            JOptionPane.QUESTION_MESSAGE
        );

        if (option == JOptionPane.OK_OPTION) {
            return new String(passwordField.getPassword());
        } else {
            throw new RuntimeException("Password entry cancelled by user");
        }
    }

    /**
     * Wait for SAML response to be available
     */
    private String waitForSamlResponse() throws Exception {
        logger.info("Waiting for SAML response...");

        // Wait for redirect to AWS sign-in page
        wait.until(ExpectedConditions.urlContains("signin.aws.amazon.com"));

        // Try to find SAML response in form
        try {
            WebElement samlResponseElement = wait.until(
                ExpectedConditions.presenceOfElementLocated(By.name("SAMLResponse"))
            );

            String samlResponse = samlResponseElement.getAttribute("value");
            if (samlResponse != null && !samlResponse.isEmpty()) {
                logger.info("SAML response captured successfully");
                return samlResponse;
            }
        } catch (TimeoutException e) {
            logger.warn("SAML response element not found, checking page source");
        }

        // Fallback: check page source for SAML response
        String pageSource = driver.getPageSource();
        if (pageSource.contains("SAMLResponse")) {
            // Extract SAML response from page source
            int startIndex = pageSource.indexOf("name=\"SAMLResponse\"");
            if (startIndex > 0) {
                int valueStart = pageSource.indexOf("value=\"", startIndex);
                if (valueStart > 0) {
                    valueStart += 7; // length of 'value="'
                    int valueEnd = pageSource.indexOf("\"", valueStart);
                    if (valueEnd > 0) {
                        String samlResponse = pageSource.substring(valueStart, valueEnd);
                        logger.info("SAML response extracted from page source");
                        return samlResponse;
                    }
                }
            }
        }

        throw new RuntimeException("SAML response not found in AWS sign-in page");
    }
}