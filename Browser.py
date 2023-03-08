import json
import os
import re
import sys
from pathlib import Path
import requests

from selenium import webdriver
from selenium.common import exceptions as se

import constants
import Utilities
from Logging import Logging

log_stream = Logging('browser')

os_info = Utilities.OSInfo()
operating_system = os_info.which_os()

selenium_timeout = constants.__timeout__
script_execute_path = Utilities.get_script_exec_path()


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
    message = 'There is something wrong with the driver installed for ' + user_browser + '.'
    message = message + 'Please refer to the documentation in the README on how to download and '
    message = message + 'install the correct driver for your operating system ' + operating_system
    log_stream.critical(message)
    log_stream.critical(str(error))


def get_gecko_latest_version():
    gecko_download_url = None
    latest_version_url = constants.__mozilla_driver_url__
    request_response = requests.get(latest_version_url)
    gekco_releases = json.loads(request_response.content.decode())
    os_download_patterns = re.compile('.*' + constants.gecko_remote_patterns[operating_system] + '$')
    for asset in gekco_releases[0]['assets']:
        if os_download_patterns.match(asset['name']):
            gecko_download_url = asset['browser_download_url']
            break
    if gecko_download_url is not None:
        return gecko_download_url
    else:
        log_stream.critical('Unable to download gecko driver for Firefox')
        return None


def download_gecko_driver():
    gecko_download_url = get_gecko_latest_version()
    if gecko_download_url is not None:
        try:
            get_driver = requests.get(gecko_download_url)
        except requests.exceptions.RequestException as e:
            log_stream.critical('Unable to download driver. ' + str(e))
            return
        if get_driver.status_code == 200:
            with open('drivers/' + constants.gecko_local_archive[operating_system], 'wb') as driver_file:
                driver_file.write(get_driver.content)
            driver_file.close()
            driver_archive = 'drivers/' + constants.gecko_local_archive[operating_system]
            local_file = 'drivers/' + constants.gecko_local_file[operating_system]
            try:
                os.remove(local_file)
            except FileNotFoundError:
                pass
            if operating_system == 'windows':
                return Utilities.extract_zip_archive(driver_archive)

            if operating_system != 'windows':
                return Utilities.extract_tgz_archive(driver_archive)
        else:
            log_stream.critical('Unable to download gecko driver for Firefox')
            return False
    else:
        log_stream.critical('Unable to download gecko driver for Firefox')
        return False


def get_chrome_latest_version():
    latest_version_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
    request_response = requests.get(latest_version_url)
    latest_chrome_driver_version = request_response.content.decode()
    return latest_chrome_driver_version


def download_chromedriver():
    chrome_driver_base_url = 'https://chromedriver.storage.googleapis.com/'
    version = get_chrome_latest_version()
    chrome_driver_base_url = chrome_driver_base_url + version + '/'
    chrome_file = constants.chrome_remote_files[operating_system]
    chrome_driver_download_url = chrome_driver_base_url + chrome_file
    log_stream.info('Downloading driver from ' + chrome_driver_download_url)
    get_driver = requests.get(chrome_driver_download_url)
    driver_archive = 'drivers/' + constants.chrome_remote_files[operating_system]
    if get_driver.status_code == 200:
        with open(driver_archive, 'wb') as driver_file:
            driver_file.write(get_driver.content)
        driver_file.close()
        local_file = 'drivers/' + constants.chrome_local_file[operating_system]
        try:
            os.remove(local_file)
        except FileNotFoundError:
            pass
        return Utilities.extract_zip_archive(driver_archive)
    else:
        log_stream.critical('Unable to download chromedriver for Chrome')
        return False


def verify_drivers(user_browser):
    drivers = None
    driver_executable = None
    if user_browser not in constants.valid_browsers:
        log_stream.critical('unknown browser specified.browsers currently supported:')
        log_stream.critical(','.join(constants.valid_browsers))
        raise SystemExit(1)

    driver_files = None
    if operating_system == 'linux' or operating_system == 'macos':
        os.environ['PATH'] += ":" + script_execute_path + '/drivers'
        drivers = script_execute_path + '/drivers/'

    elif operating_system == 'windows':
        os.environ['PATH'] += ";" + script_execute_path + '\\drivers\\'
        drivers = script_execute_path + '\\drivers\\'
    else:
        log_stream.critical('Unknown OS type ' + sys.platform)
        raise SystemExit(1)

    if Path(drivers).is_dir() is False:
        log_stream.critical('Missing drivers directory')
        log_stream.info('Creating drivers directory')
        try:
            os.mkdir(drivers)
        except OSError as e:
            log_stream.critical('Unable to create drivers directory')
            log_stream.critical(str(e))

    if user_browser == 'chrome':
        driver_executable = str(drivers + constants.chrome_local_file[operating_system])
    if user_browser == 'firefox':
        driver_executable = str(drivers + constants.gecko_local_file[operating_system])

    # if Path(driver).is_file() is False:
    #     log_stream.critical('The driver for browser ' + user_browser + ' cannot be found at ' +
    #                         str(drivers + driver_files[user_browser]))
    #     log_stream.info('Attempting to download the driver for ' + user_browser)
    #     if user_browser == 'firefox':
    #         get_browser_driver = download_gecko_driver()
    #     if user_browser == 'chrome':
    #         get_browser_driver = download_chromedriver()
    #
    #     if get_browser_driver is False:
    #         log_stream.critical(
    #             'Please download the driver for ' + user_browser + ' manually using the instructions in the README')
    #         raise SystemExit(1)
    return driver_executable


def browser_debugging_options(options):
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")


def setup_browser(user_browser, use_debug):
    """Sets up and returns a Selenium webdriver instance for the specified browser.

    Args:
        user_browser (str): The name of the browser ('firefox' or 'chrome') to use.
        use_debug (bool): Whether to enable debug mode or not.

    Returns:
        Tuple: A tuple containing the webdriver instance and a boolean indicating
               whether the driver was successfully loaded or not.

    Raises:
        WebDriverException: If the webdriver for the specified browser could not be loaded.

    """
    driver = None
    is_driver_loaded: bool = False
    browser_options = None

    # if user_browser == 'firefox':
    # from selenium.webdriver.firefox.options import Options as Firefox
    # browser_options = Firefox()
    # if os_info.which_os() == 'linux':
    #     driver_executable, binary_location = gecko_from_snap()
    #     if binary_location is not None:
    #         browser_options.binary_location = binary_location
    #     else:
    #         driver_executable = verify_drivers('firefox')
    # elif user_browser == 'chrome':
    #     from selenium.webdriver.chrome.options import Options as Chrome
    #     browser_options = Chrome()
    #     browser_options.add_argument("--disable-dev-shm-usage")
    #     driver_executable = verify_drivers('chrome')
    #
    # if operating_system == 'windows' and user_browser == 'chrome':
    #     try:
    #         browser_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    #     except se.NoSuchAttributeException:
    #         log_stream.info('Unable to add Experimental Options')
    #     # Chrome on Win32 requires basic authentication on PING page, prior to form authentication
    #     first_page = first_page[0:8] + username + ':' + password + '@' + first_page[8:]

    if user_browser == 'firefox':
        from selenium.webdriver.firefox.options import Options as Firefox
        browser_options = Firefox()
        if use_debug is False:
            browser_debugging_options(browser_options)
        if os_info.which_os() == 'linux':
            driver_executable, binary_location = gecko_from_snap()
            if binary_location is not None:
                browser_options.binary_location = binary_location
            else:
                driver_executable = verify_drivers('firefox')
        else:
            driver_executable = verify_drivers('firefox')

        try:
            driver = webdriver.Firefox(executable_path=driver_executable, options=browser_options)
            is_driver_loaded = True
        except se.WebDriverException as e:
            download_gecko_driver()
            try:
                driver = webdriver.Firefox(executable_path=driver_executable, options=browser_options)
                is_driver_loaded = True
            except se.WebDriverException as missing_browser_driver_error:
                missing_browser_message(user_browser, missing_browser_driver_error)
    elif user_browser == 'chrome':
        from selenium.webdriver.chrome.options import Options as Chrome
        browser_options = Chrome()
        if use_debug is False:
            browser_debugging_options(browser_options)
        browser_options.add_argument("--disable-dev-shm-usage")
        driver_executable = verify_drivers('chrome')

        if operating_system == 'windows':
            try:
                browser_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            except se.NoSuchAttributeException:
                log_stream.info('Unable to add Experimental Options')
            # Chrome on Win32 requires basic authentication on PING page, prior to form authentication
            # first_page = first_page[0:8] + username + ':' + password + '@' + first_page[8:]
        try:
            driver = webdriver.Chrome(executable_path=driver_executable, options=browser_options)
            is_driver_loaded = True
        except se.WebDriverException:
            log_stream.info('Attempting to download the latest chromedriver')
            download_chromedriver()
            try:
                driver = webdriver.Chrome(executable_path=driver_executable, options=browser_options)
                is_driver_loaded = True
            except se.WebDriverException as missing_browser_driver_error:
                missing_browser_message(user_browser, missing_browser_driver_error)
        except se.WebDriverException:
            log_stream.info('Attempting to download the latest chromedriver')
            download_chromedriver()
            try:
                driver = webdriver.Chrome(executable_path=driver_executable, options=browser_options)
                is_driver_loaded = True
            except se.WebDriverException as missing_browser_driver_error:
                missing_browser_message(user_browser, missing_browser_driver_error)
    return driver, is_driver_loaded
