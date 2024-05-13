# coding=utf-8
import uuid

from selenium.common import exceptions as se
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import constants
from Logging import Logging

log_stream = Logging('providers')

saml_page_title = "Amazon Web Services Sign-In"

xpath_locator = By.XPATH
class_name_locator = By.CLASS_NAME
id_locator = By.ID
link_text_locator = By.LINK_TEXT
name_locator = By.NAME
css_locator = By.CSS_SELECTOR


def click_okta_mfa(wait):
    try:
        # Select the push notification option and click it
        log_stream.info('Select Push Notification')
        send_push_notification = wait.until(ec.element_to_be_clickable(
            (css_locator, constants.security_method_labels['push_notify'])))
        send_push_notification.click()
    except se.ElementClickInterceptedException:
        saml_response = "CouldNotEnterFormData"
        return saml_response


def click_okta_fastpass(wait):
    try:
        # Select the push notification option and click it
        log_stream.info('Select Okta Fast Pass Notification')
        send_push_notification = wait.until(ec.element_to_be_clickable(
            (css_locator, constants.security_method_labels['fast_pass'])))
        send_push_notification.click()
    except se.ElementClickInterceptedException:
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
        # Define XPath selectors for various page elements
        username_next_button = 'button-primary'
        select_use_password = '/html/body/div[2]/div[2]/main/div[2]/div/div/div[2]/form/div[2]/div/div[3]/div[2]/div[2]'
        password_next_button = 'button-primary'

        username_field = "identifier"
        password_field = "password-with-toggle"

        if not use_dsso:
            username_next_button = wait.until(ec.element_to_be_clickable((class_name_locator, username_next_button)))
            log_stream.info('Use Okta Login')
            try:
                # Enter the username and click the "Next" button
                log_stream.info('Enter Username')
                username_dialog = driver.find_element(name_locator, username_field)
                username_dialog.clear()
                username_dialog.send_keys(username)
                log_stream.info('Click Button')
                username_next_button.click()
            except se.NoSuchElementException:
                saml_response = "CouldNotEnterFormData"
                return saml_response
        if driver.capabilities['browserName'] == 'chrome':
            log_stream.info('Checking for DSSO')
            try:
                wait.until(ec.url_to_be(dsso_url))
                log_stream.info('Follow DSSO Path')
                if use_okta_fastpass is True:
                    saml_response = click_okta_fastpass(wait)
                else:
                    saml_response = click_okta_mfa(wait)
                use_dsso = True
                if saml_response == "CouldNotEnterFormData":
                    return saml_response
            except se.TimeoutException:
                log_stream.info('Follow DSSO Path')
                log_stream.info('Not using DSSO')
        if not use_dsso:
            try:
                # Enter the password and click the "Next" button
                log_stream.info('Enter Password')
                password_dialog = wait.until(ec.element_to_be_clickable((class_name_locator, password_field)))
                password_dialog.clear()
                password_dialog.send_keys(password)
                log_stream.info('Click Button')
                password_next_button = driver.find_element(class_name_locator, password_next_button)
                password_next_button.click()
            except se.NoSuchElementException:
                saml_response = "CouldNotEnterFormData"
                return saml_response

            if use_okta_fastpass is True:
                saml_response = click_okta_fastpass(wait)
            else:
                saml_response = click_okta_mfa(wait)
            if saml_response == "CouldNotEnterFormData":
                return saml_response

        try:
            completed_login = wait.until(ec.title_is(saml_page_title))
        except se.TimeoutException:
            log_stream.fatal('Timeout waiting for MFA')
            log_stream.info('Saving screenshot for debugging')
            screenshot = 'failed_login_screenshot-' + str(uuid.uuid4()) + '.png'
            driver.save_screenshot(screenshot)
            raise SystemExit(1)
        return completed_login

    # @staticmethod
    # def ping_sign_in(wait, driver, username, password, completed_login=False, saml_response=None):
    #     """
    #     This is a static method called 'ping_sign_in' that signs in to a federated login page.
    #
    #     Args:
    #         wait: An instance of a WebDriverWait object.
    #         driver: An instance of a web driver.
    #         username: A string containing the username.
    #         password: A string containing the password.
    #         completed_login: A boolean indicating if the login process is completed.
    #         saml_response: A string containing the SAML response.
    #
    #     Returns:
    #         Returns a boolean indicating if the login process is completed.
    #
    #     Raises:
    #         NoSuchElementException: If an element is not found on the page.
    #         ElementClickInterceptedException: If the button click is intercepted by another element.
    #         TimeoutException: If an element is not found within a specified timeout period.
    #
    #     The function starts by locating the sign-on button element and clicking it. It then attempts to enter the
    #     provided username and password into their respective textboxes, and then clicks the sign-on button.
    #     f any of these actions fail, it returns a message indicating that it could not enter form data.
    #
    #     The function then waits for the SAML page title to load, and if it times out, it attempts to press the
    #     enter key in the password field to bypass multifactor authentication. If that also times out,
    #     it logs an error message and saves a screenshot of the failed login for debugging purposes.
    #
    #     Finally, the function returns the 'completed_login' variable which indicates whether the login
    #     process was completed successfully or not.
    #     """
    #     global saml_page_title
    #     textbox_username = 'username'
    #     textbox_password = 'password'
    #     button_signon = 'ping-button'
    #     button_retry = '.primary'
    #     link_retry_mfa = 'Retry mobile'
    #
    #     sign_on_button = wait.until(ec.element_to_be_clickable((class_name_locator, button_signon)))
    #     log_stream.info('Use Federated Login Page')
    #     try:
    #         log_stream.info('Enter Username')
    #         username_dialog = driver.find_element(id_locator, textbox_username)
    #         username_dialog.clear()
    #         username_dialog.send_keys(username)
    #     except se.NoSuchElementException:
    #         saml_response = "CouldNotEnterFormData"
    #         return saml_response
    #     try:
    #         log_stream.info('Enter Password')
    #         password_dialog = driver.find_element(id_locator, textbox_password)
    #         password_dialog.clear()
    #         log_stream.debug(password)
    #         password_dialog.send_keys(password)
    #     except se.NoSuchElementException:
    #         saml_response = "CouldNotEnterFormData"
    #         return saml_response
    #     try:
    #         log_stream.info('Click Sign On Button')
    #         sign_on_button.click()
    #     except se.ElementClickInterceptedException:
    #         saml_response = "CouldNotClickButton"
    #         return saml_response
    #     try:
    #         completed_login = wait.until(ec.title_is(saml_page_title))
    #     except se.TimeoutException:
    #         sign_in_continue = False
    #         try:
    #             password_dialog = driver.find_element(id_locator, textbox_password)
    #             log_stream.info('Button did not respond to click, press enter in password field')
    #             password_dialog.send_keys(Keys.ENTER)
    #             sign_in_continue = True
    #         except se.NoSuchElementException:
    #             try:
    #                 retry_mfa_button = driver.find_element(class_name_locator, button_retry)
    #                 retry_mfa_button.click()
    #                 sign_in_continue = True
    #             except se.InvalidSelectorException:
    #                 try:
    #                     retry_mfa_link = driver.find_element(link_text_locator, link_retry_mfa)
    #                     retry_mfa_link.click()
    #                     sign_in_continue = True
    #                 except se.NoSuchElementException as e:
    #                     log_stream.critical('Unknown login error')
    #                     log_stream.critical(str(e))
    #         except se.StaleElementReferenceException:
    #             pass
    #         finally:
    #             if sign_in_continue is True:
    #                 try:
    #                     completed_login = wait.until(ec.title_is(saml_page_title))
    #                 except se.TimeoutException as mfa_timeout_error:
    #                     log_stream.info('Timeout waiting for MFA: ' + str(mfa_timeout_error))
    #                     log_stream.info('Saving screenshot for debugging')
    #                     screenshot = 'failed_login_screenshot-' + str(uuid.uuid4()) + '.png'
    #                     driver.save_screenshot(screenshot)
    #                 except se.StaleElementReferenceException as e:
    #                     pass
    #                 finally:
    #                     saml_response = 'WaitMFATimeout'
    #             else:
    #                 saml_response = 'WaitMFATimeout'
    #
    #     return completed_login
