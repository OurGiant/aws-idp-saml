# coding=utf-8
import uuid

from selenium.common import exceptions as se
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from Logging import Logging
from ScreenshotRecorder import ScreenshotRecorder
from SeleniumHelper import SeleniumHelper

log_stream = Logging('providers')

saml_page_title = "Amazon Web Services Sign-In"
xpath_locator = By.XPATH
class_name_locator = By.CLASS_NAME
id_locator = By.ID
link_text_locator = By.LINK_TEXT
name_locator = By.NAME


def check_for_mfa_screen(driver, wait, use_okta_fastpass):
    """
    Check if the MFA screen is already displayed (fully managed device scenario).
    Uses the isMfa flag in Okta's modelDataBag to reliably detect MFA pages.
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
        use_okta_fastpass: Boolean indicating which MFA method to use
        
    Returns:
        tuple: (is_mfa_screen, saml_response) where is_mfa_screen is bool and 
               saml_response is the result if MFA was clicked
    """
    try:
        # Check if page source contains the isMfa flag in modelDataBag
        # This is the most reliable indicator from Okta
        page_source = driver.page_source
        
        # Check for isMfa flag in the modelDataBag JSON
        # The flag appears as either "isMfa":true or encoded as \x22isMfa\x22\x3Atrue
        if ('"isMfa":true' in page_source or '"isMfa"\\x3Atrue' in page_source or 
            '\x22isMfa\x22\x3Atrue' in page_source):
            log_stream.info('MFA screen detected via isMfa flag - fully managed device, skipping username and password entry')
            ScreenshotRecorder.capture(driver, "managed_device_mfa_screen")
            
            # Give the page a moment to fully render the MFA options
            import time
            time.sleep(1)
            
            # Click the appropriate MFA button
            if use_okta_fastpass:
                saml_response = click_okta_fastpass(wait, driver)
            else:
                saml_response = click_okta_mfa(wait, driver)
                
            return True, saml_response
        
        # Not on MFA screen
        return False, None
        
    except Exception as e:
        log_stream.warning(f'Error checking for MFA screen: {str(e)}')
        # On any error, assume we're not on MFA screen and continue normal flow
        return False, None


def click_okta_mfa(wait, driver):
    """Click the MFA push notification button."""
    select_push_notification = "//a[@aria-label='Select to get a push notification to the Okta Verify app.']"
    helper = SeleniumHelper(driver, wait)
    
    try:
        log_stream.info('Select Push Notification')
        ScreenshotRecorder.capture(driver, "before_mfa_selection")
        helper.click_element((xpath_locator, select_push_notification), "MFA push notification")
        ScreenshotRecorder.capture(driver, "after_mfa_selection")
    except se.ElementClickInterceptedException:
        ScreenshotRecorder.capture(driver, "mfa_click_intercepted")
        saml_response = "CouldNotEnterFormData"
        return saml_response


def click_okta_fastpass(wait, driver):
    """Click the Okta FastPass button."""
    select_push_notification = "//a[@aria-label='Select Okta Verify.']"
    helper = SeleniumHelper(driver, wait)
    
    try:
        log_stream.info('Select Okta Fast Pass Notification')
        ScreenshotRecorder.capture(driver, "before_fastpass_selection")
        helper.click_element((xpath_locator, select_push_notification), "Okta FastPass button")
        ScreenshotRecorder.capture(driver, "after_fastpass_selection")
    except se.ElementClickInterceptedException:
        ScreenshotRecorder.capture(driver, "fastpass_click_intercepted")
        saml_response = "CouldNotEnterFormData"
        return saml_response


class UseIdP:

    @staticmethod
    def okta_sign_in(wait, driver, username, password, dsso_url, use_okta_fastpass):
        """
        Attempts to sign in to Okta using the given credentials.

        Args:
            use_okta_fastpass (bool): indicates whether to Use Okta FastPass for MFA
            dsso_url: (str): The url indicating DSSO is in use.
            wait (WebDriverWait): The WebDriverWait instance to wait for elements.
            driver (WebDriver): The WebDriver instance used to navigate to Okta login page.
            username (str): The username to log in with.
            password (str): The password to log in with.

        Returns:
            bool: A flag to indicate whether the login was successful or not.

        Raises:
            SystemExit: If the login times out waiting for MFA and cannot be completed.
        """
        global saml_page_title
        use_dsso = False
        helper = SeleniumHelper(driver, wait)
        
        # Define XPath selectors for various page elements
        username_next_button = 'button-primary'
        password_next_button = 'button-primary'
        username_field = "identifier"
        password_field = "password-with-toggle"
        
        if driver.capabilities['browserName'] == 'chrome':
            log_stream.info('Checking for DSSO')
            ScreenshotRecorder.capture(driver, "dsso_check_start")
            try:
                helper.wait_for_url_contains(dsso_url)
                log_stream.info('Follow DSSO Path')
                ScreenshotRecorder.capture(driver, "dsso_detected")
                if use_okta_fastpass is True:
                    saml_response = click_okta_fastpass(wait, driver)
                else:
                    saml_response = click_okta_mfa(wait, driver)
                use_dsso = True
                if saml_response == "CouldNotEnterFormData":
                    return saml_response
            except se.TimeoutException:
                log_stream.info('Not using DSSO')
                ScreenshotRecorder.capture(driver, "dsso_timeout")
        
        if not use_dsso:
            log_stream.info('Use Okta Login')
            ScreenshotRecorder.capture(driver, "okta_login_page")
            
            # Check if we're already on the MFA screen (fully managed device - both username and password pre-authenticated)
            is_mfa_screen, mfa_response = check_for_mfa_screen(driver, wait, use_okta_fastpass)
            
            if is_mfa_screen:
                # Already on MFA screen, credentials were pre-authenticated
                if mfa_response == "CouldNotEnterFormData":
                    return mfa_response
                # Skip to the completion check
                use_dsso = True  # Reuse this flag to skip password entry
            else:
                # Not on MFA screen yet, check for password field (username pre-filled on managed devices)
                short_wait = WebDriverWait(driver, 3)
                short_helper = SeleniumHelper(driver, short_wait)
                try:
                    short_helper.wait_for_element((class_name_locator, password_field), "password field")
                    log_stream.info('Password field already visible - username pre-filled, skipping username entry')
                    ScreenshotRecorder.capture(driver, "username_prefilled")
                except se.TimeoutException:
                    # Password field not visible, proceed with username entry
                    log_stream.info('Username field required - proceeding with username entry')
                    try:
                        log_stream.debug('Entering username')  # Don't log the actual username
                        helper.enter_text((name_locator, username_field), username, "username field")
                        log_stream.debug('Clicking username next button')
                        helper.click_element((class_name_locator, username_next_button), "username next button")
                        ScreenshotRecorder.capture(driver, "after_username_entry")
                    except (se.NoSuchElementException, se.TimeoutException):
                        ScreenshotRecorder.capture(driver, "username_entry_failed")
                        saml_response = "CouldNotEnterFormData"
                        return saml_response

        if not use_dsso:
            try:
                # Enter the password and click the "Next" button
                log_stream.debug('Entering password')  # Don't log the actual password
                helper.enter_text((class_name_locator, password_field), password, "password field")
                log_stream.debug('Clicking password next button')
                helper.click_element((class_name_locator, password_next_button), "password next button")
                ScreenshotRecorder.capture(driver, "after_password_entry")
            except (se.NoSuchElementException, se.TimeoutException):
                ScreenshotRecorder.capture(driver, "password_entry_failed")
                saml_response = "CouldNotEnterFormData"
                return saml_response

            if use_okta_fastpass is True:
                saml_response = click_okta_fastpass(wait, driver)
            else:
                saml_response = click_okta_mfa(wait, driver)
            if saml_response == "CouldNotEnterFormData":
                return saml_response

        try:
            completed_login = wait.until(ec.title_is(saml_page_title))
            ScreenshotRecorder.capture(driver, "login_completed")
        except se.TimeoutException:
            log_stream.fatal('Timeout waiting for MFA')
            log_stream.info('Saving screenshot for debugging')
            ScreenshotRecorder.capture(driver, "login_timeout")
            screenshot = 'failed_login_screenshot-' + str(uuid.uuid4()) + '.png'
            driver.save_screenshot(screenshot)
            raise SystemExit(1)
        return completed_login
