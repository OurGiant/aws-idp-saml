# coding=utf-8

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions as se

import SAMLSelector
import constants
import Providers
import Browser
from Logging import Logging

log_stream = Logging('login')

saml_page_title = "Amazon Web Services Sign-In"


def get_saml_response(driver):
    while len(driver.find_elements(By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')) < 1:
        print('.', end='')

    saml_response_completed_login = driver.find_elements(By.XPATH,
                                                         '//*[@id="saml_form"]/input[@name="SAMLResponse"]')

    saml_response = saml_response_completed_login[0].get_attribute("value")

    return saml_response


def browser_login(username, password, first_page, use_debug, use_gui, browser, saml_provider_name,
                  idp_login_title, iam_role, gui_name, dsso_url):

    completed_login: bool = False

    driver, is_driver_loaded = Browser.setup_browser(browser, use_debug)

    if is_driver_loaded is True:
        if use_debug is True:
            driver.set_window_size(1024, 768)

        wait = WebDriverWait(driver, constants.__timeout__)
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
                completed_login = Providers.UseIdP.okta_sign_in(wait, driver, username, password, dsso_url)
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
