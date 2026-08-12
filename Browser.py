import os
from pathlib import Path

from selenium import webdriver
from selenium.common import exceptions as se

import constants
from Logging import Logging
from OSInfo import OSInfo

log_stream = Logging('browser')

os_info = OSInfo()
operating_system = os_info.which_os()
operating_system_type = os_info.which_os_type()

selenium_timeout = constants.__timeout__


def gecko_from_snap():
    driver_loc = None
    binary_loc = None
    install_dir = constants.__snap_install_dir__
    firefox_snap_location = Path(install_dir)
    if firefox_snap_location.is_dir():
        log_stream.info(
            'Firefox was installed using snap package management, setting browser options to use this installation')
        driver_loc = os.path.join(install_dir, "geckodriver")
        binary_loc = os.path.join(install_dir, "firefox")
    return driver_loc, binary_loc


def missing_browser_message(user_browser, error):
    message = f'There is something wrong with the browser installation for {user_browser}, or Selenium Manager '
    message += 'was unable to obtain a matching driver. Please refer to the documentation in the README on how '
    message += 'to install ' + user_browser + ' for your operating system ' + operating_system
    log_stream.critical(message)
    log_stream.critical(str(error))


def browser_debugging_options(options, user_browser):
    options.add_argument("--no-sandbox")
    if user_browser == "chrome" or user_browser == "edge":
        options.add_argument("--headless=new")
        # Suppress internal browser error messages
        options.add_argument("--log-level=3")  # Only show fatal errors
        options.add_argument("--disable-usb-keyboard-detect")  # Suppress USB errors
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
    elif user_browser == "firefox":
        options.add_argument("--headless")
    # TODO working only for Firefox
    # options.set_preference("webdriver.log.level", "OFF")
    return options


def setup_browser(user_browser, use_debug):
    """Sets up and returns a Selenium webdriver instance for the specified browser.

    Driver acquisition is delegated entirely to Selenium Manager (built into
    Selenium since 4.6): omitting a driver executable_path lets Selenium
    detect the installed browser, download a matching driver, cache it, and
    set correct permissions on its own. No manual download/extract/chmod/
    retry logic lives here anymore - see issue #93 for the migration and its
    test matrix.

    Args:
        user_browser (str): The name of the browser ('firefox', 'chrome', or 'edge') to use.
        use_debug (bool): Whether to enable debug mode or not.

    Returns:
        Tuple: A tuple containing the webdriver instance and a boolean indicating
               whether the driver was successfully loaded or not.
    """
    driver = None
    is_driver_loaded: bool = False
    browser_options = None

    if user_browser == 'firefox':
        from selenium.webdriver.firefox.options import Options as FirefoxOptions

        browser_options = FirefoxOptions()
        browser_options.log.level = "trace"
        if use_debug is False:
            browser_options = browser_debugging_options(browser_options, user_browser)
        if os_info.which_os() == 'linux':
            _, binary_location = gecko_from_snap()
            if binary_location is not None:
                browser_options.binary_location = binary_location
        else:
            binary_location = constants.firefox_binary_location.get(operating_system)
            if binary_location is not None and Path(binary_location).is_file():
                browser_options.binary_location = binary_location
        try:
            driver = webdriver.Firefox(options=browser_options)
            is_driver_loaded = True
        except se.WebDriverException as e:
            missing_browser_message(user_browser, e)
    elif user_browser == 'chrome':
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        browser_options = ChromeOptions()
        if use_debug is False:
            browser_options = browser_debugging_options(browser_options, user_browser)
        browser_options.add_argument("--disable-dev-shm-usage")
        # Suppress browser internal error messages
        browser_options.add_argument("--log-level=3")
        browser_options.add_argument("--disable-usb-keyboard-detect")
        if operating_system == 'windows':
            try:
                browser_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            except se.NoSuchAttributeException:
                log_stream.info('Unable to add Experimental Options')
            # Chrome on Win32 requires basic authentication on PING page, prior to form authentication
            # first_page = first_page[0:8] + username + ':' + password + '@' + first_page[8:]
        try:
            driver = webdriver.Chrome(options=browser_options)
            is_driver_loaded = True
        except se.WebDriverException as e:
            missing_browser_message(user_browser, e)
    elif user_browser == 'edge':
        from selenium.webdriver.edge.options import Options as EdgeOptions
        browser_options = EdgeOptions()
        if use_debug is False:
            browser_options = browser_debugging_options(browser_options, user_browser)
        browser_options.add_argument("--disable-dev-shm-usage")
        # Suppress browser internal error messages
        browser_options.add_argument("--log-level=3")
        browser_options.add_argument("--disable-usb-keyboard-detect")
        if operating_system == 'windows':
            try:
                browser_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            except se.NoSuchAttributeException:
                log_stream.info('Unable to add Experimental Options')
        try:
            driver = webdriver.Edge(options=browser_options)
            is_driver_loaded = True
        except se.WebDriverException as e:
            missing_browser_message(user_browser, e)
    return driver, is_driver_loaded
