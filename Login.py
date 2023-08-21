# coding=utf-8
import base64
import json
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
    design_a_count = 0
    while len(driver.find_elements(By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')) < 1 or design_a_count < 10:
        print('.', end='')
        design_a_count += 1

    if len(driver.find_elements(By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')) > 0:
        log_stream.info("found login design A")
        saml_response_completed_login = driver.find_elements(By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')
        saml_response = saml_response_completed_login[0].get_attribute("value")
        design = "A"
        return saml_response, design

    design_b_count = 0
    while len(driver.find_elements(By.XPATH, '//meta[@name="data"]')) < 1 or design_b_count < 10:
        print('.', end='')
        design_b_count += 1

    if len(driver.find_elements(By.XPATH, '//meta[@name="data"]')) > 0:
        log_stream.info("found login design B")
        aws_signin_page_data = driver.find_elements(By.XPATH, '//meta[@name="data"]')
        saml_response = json.loads(base64.b64decode((aws_signin_page_data[0].get_attribute("content"))).decode('utf-8'))['SAMLResponse']
        design = "B"

        return saml_response, design


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
            saml_response, design = get_saml_response(driver)
            if use_gui is not True:
                driver.close()
            else:
                SAMLSelector.select_role_from_saml_page(driver, gui_name, iam_role, design)
        else:
            saml_response = "CouldNotCompleteMFA"
    else:
        saml_response = "CouldNotLoadWebDriver"

    return saml_response
