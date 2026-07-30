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
    wait = WebDriverWait(driver, constants.__timeout__)

    # Try design A first
    try:
        saml_element = wait.until(ec.presence_of_element_located((By.XPATH, '//*[@id="saml_form"]/input[@name="SAMLResponse"]')))
        log_stream.info("found login design A")
        saml_response = saml_element.get_attribute("value")
        design = "A"
        return saml_response, design
    except se.TimeoutException:
        pass

    # If design A not found, try design B
    try:
        aws_signin_page_data = wait.until(ec.presence_of_element_located((By.XPATH, '//meta[@name="data"]')))
        log_stream.info("found login design B")
        
        # Parse JSON with proper error handling
        try:
            saml_data = json.loads(base64.b64decode((aws_signin_page_data.get_attribute("content"))).decode('utf-8'))
            
            # Validate response structure
            if 'SAMLResponse' not in saml_data:
                log_stream.fatal('Invalid SAML response format: missing SAMLResponse field')
                return None, None
            
            saml_response = saml_data['SAMLResponse']
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            log_stream.critical(f'Failed to parse SAML response JSON: {str(e)}')
            log_stream.debug(f'Attempted to parse content type: {type(aws_signin_page_data.get_attribute("content"))}')
            return None, None
        except UnicodeDecodeError as e:
            log_stream.critical(f'SAML response content is not valid UTF-8: {str(e)}')
            return None, None
        
        design = "B"
        return saml_response, design
    except se.TimeoutException:
        return None, None


def browser_login(username, password, first_page, use_debug, use_gui, browser, saml_provider_name,
                  idp_login_title, iam_role, gui_name, dsso_url,use_okta_fastpass) -> str:

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
            return str(saml_response)

        log_stream.info('Sign In Page Title is ' + driver.title)

        if driver.title == idp_login_title:
            # if saml_provider_name == 'PING':
            #     completed_login = Providers.UseIdP.ping_sign_in(wait, driver, username, password)
            if saml_provider_name == 'OKTA':
                completed_login = Providers.UseIdP.okta_sign_in(wait, driver, username, password, dsso_url, use_okta_fastpass)
        elif driver.title == "Amazon Web Services Sign-In":
            completed_login = True
        else:
            saml_response = "WrongLoginPageTitle"
            completed_login = False
            return saml_response

        if completed_login is True:
            log_stream.info('Waiting for SAML Response.')
            saml_response, design = get_saml_response(driver)
            if saml_response is None:
                saml_response = "SAMLResponseTimeout"
                return saml_response
            if use_gui is not True:
                driver.close()
            else:
                SAMLSelector.select_role_from_saml_page(driver, gui_name, iam_role, design)
        else:
            saml_response = "CouldNotCompleteMFA"
    else:
        saml_response = "CouldNotLoadWebDriver"

    return str(saml_response)
