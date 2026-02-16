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


def click_okta_mfa(wait, driver):
    """Click the MFA push notification button."""
    select_push_notification = '/html/body/div[2]/div[2]/main/div[2]/div/div/div[2]/form/div[2]/div/div[2]/div[2]/div[2]/a'
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
    select_push_notification = '/html/body/div[2]/div[2]/main/div[2]/div/div/div[2]/form/div[2]/div/div[3]/div[2]/div[2]/a'
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
            
            # Check if password field is already visible (username pre-filled on managed devices)
            # Use a short timeout (3 seconds) for this check since the page should already be loaded
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
