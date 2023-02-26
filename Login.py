# coding=utf-8
import sys
import time
import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions as se

import SAMLSelector
from version import __version__
import Utilities
import Providers

log_stream = Utilities.Logging('login')

saml_page_title = "Amazon Web Services Sign-In"


def get_saml_response(driver):
    while len(driver.find_elements(By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')) < 1:
        print('.', end='')

    saml_response_completed_login = driver.find_elements(By.XPATH,
                                                         '//*[@id="saml_form"]/input[@name="SAMLResponse"]')

    saml_response = saml_response_completed_login[0].get_attribute("value")

    return saml_response


def missing_browser_message(browser, error):
    message = 'There is something wrong with the driver installed for ' + browser + '.'
    message = message + 'Please refer to the documentation in the README on how to download and '
    message = message + 'install the correct driver for your operating system ' + sys.platform
    log_stream.critical(message)
    log_stream.critical(str(error))


def browser_login(browser, driver_executable, use_debug, first_page, username, password):
    driver = None
    is_driver_loaded: bool = False
    browser_options = None

    if browser == 'firefox':
        from selenium.webdriver.firefox.options import Options as Firefox
        browser_options = Firefox()
    elif browser == 'chrome':
        from selenium.webdriver.chrome.options import Options as Chrome
        browser_options = Chrome()
        browser_options.add_argument("--disable-dev-shm-usage")

    if sys.platform == 'win32' and browser == 'chrome':
        try:
            browser_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        except se.NoSuchAttributeException:
            log_stream.info('Unable to add Experimental Options')
        # Chrome on Win32 requires basic authentication on PING page, prior to form authentication
        first_page = first_page[0:8] + username + ':' + password + '@' + first_page[8:]

    if use_debug is False:
        browser_options.add_argument("--headless")
        browser_options.add_argument("--no-sandbox")

    if browser == 'firefox':
        try:
            driver = webdriver.Firefox(executable_path=driver_executable, options=browser_options)
            is_driver_loaded = True
        except OSError as missing_browser_driver_error:
            missing_browser_message(browser, missing_browser_driver_error)
    elif browser == 'chrome':
        try:
            driver = webdriver.Chrome(executable_path=driver_executable, options=browser_options)
            is_driver_loaded = True
        except OSError as missing_browser_driver_error:
            missing_browser_message(browser, missing_browser_driver_error)

    return driver, is_driver_loaded


class IdPLogin:
    def __init__(self):
        self.timeout = 20
        self.executePath = str(Path(__file__).resolve().parents[0])
        pass

    def browser_login(self, username, password, first_page, use_debug, use_gui, browser,
                      driver_executable, saml_provider_name, idp_login_title, iam_role, gui_name):

        completed_login: bool = False

        driver, is_driver_loaded = browser_login(browser, driver_executable, use_debug, first_page, username, password)

        if is_driver_loaded is True:
            driver.set_window_size(1024, 768)

            wait = WebDriverWait(driver, self.timeout)
            driver.get(first_page)
            try:
                wait.until(ec.title_contains("Sign"))
            except se.TimeoutException:
                saml_response = "CouldNameLoadSignInPage"
                return saml_response

            log_stream.info('Sign In Page Title is ' + driver.title)

            if driver.title == idp_login_title:
                if saml_provider_name == 'PING':
                    completed_login = Providers.UseIdP.ping_sign_in(wait, driver, username, password)
                if saml_provider_name == 'OKTA':
                    completed_login = Providers.UseIdP.okta_sign_in(wait, driver, username, password)
            elif driver.title == "Amazon Web Services Sign-In":
                completed_login = True
            else:
                saml_response = "WrongLoginPageTitle"
                completed_login = False
                return saml_response

            time.sleep(2)

            if completed_login is True:
                log_stream.info('Waiting for SAML Response.')
                saml_response = get_saml_response(driver)

                if use_gui is not True:
                    driver.close()
                else:
                    SAMLSelector.select_role_from_saml_page(driver, gui_name, iam_role)

            else:
                saml_response = "CouldNotCompleteMFA"
        else:
            saml_response = "CouldNotLoadWebDriver"

        return saml_response
