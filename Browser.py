import json
import re
import sys

import requests

from selenium import webdriver
from selenium.common import exceptions as se

from version import __version__
import Utilities

log_stream = Utilities.Logging('browser')

os_info = Utilities.OSInfo()
operating_system = os_info.which_os()

chrome_remote_files = {
    "windows": "chromedriver_win32.zip",
    "linux": "chromedriver_linux64.zip",
    "macos": "chromedriver_mac64.zip"
}

chrome_local_files = {
    "windows": "chromedriver.exe",
    "linux": "chromedriver",
    "macos": "chromedriver"
}

gecko_remote_patterns = {
    "windows": "win64.zip",
    "linux": "linux64.tar.gz",
    "macos": "macos.tar.gz"
}

gecko_local_files = {
    "windows": "win_gecko.zip",
    "linux": "linux_gecko.tar.gz",
    "macos": "macos_gecko.tar.gz"
}


def get_gecko_latest_version():
    gecko_download_url = None
    latest_version_url = 'https://api.github.com/repos/mozilla/geckodriver/releases'
    request_response = requests.get(latest_version_url)
    gekco_releases = json.loads(request_response.content.decode())
    os_download_patterns = re.compile('.*' + gecko_remote_patterns[operating_system] + '$')
    for asset in gekco_releases[0]['assets']:
        if os_download_patterns.match(asset['name']):
            gecko_download_url = asset['browser_download_url']
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
            with open('drivers/' + gecko_local_files[operating_system], 'wb') as driver_file:
                driver_file.write(get_driver.content)
            driver_file.close()
            driver_archive = 'drivers/' + gecko_local_files[operating_system]
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


def missing_browser_message(browser, error):
    message = 'There is something wrong with the driver installed for ' + browser + '.'
    message = message + 'Please refer to the documentation in the README on how to download and '
    message = message + 'install the correct driver for your operating system ' + sys.platform
    log_stream.critical(message)
    log_stream.critical(str(error))


def download_chromedriver():
    chrome_driver_base_url = 'https://chromedriver.storage.googleapis.com/'
    version = get_chrome_latest_version()
    chrome_driver_base_url = chrome_driver_base_url + version + '/'
    chrome_file = chrome_remote_files[operating_system]
    # URL like
    # https://chromedriver.storage.googleapis.com/110.0.5481.77/chromedriver_linux64.zip
    chrome_driver_download_url = chrome_driver_base_url + chrome_file
    log_stream.info('Downloading driver from' + chrome_driver_download_url)
    get_driver = requests.get(chrome_driver_download_url)
    driver_archive = 'drivers/' + chrome_local_files[operating_system]
    if get_driver.status_code == 200:
        with open(driver_archive, 'wb') as driver_file:
            driver_file.write(get_driver.content)
        driver_file.close()
        return Utilities.extract_zip_archive(driver_archive)
    else:
        log_stream.critical('Unable to download chromedriver for Chrome')
        return False


def setup_browser(browser, driver_executable, use_debug, first_page, username, password):
    """Sets up and returns a Selenium webdriver instance for the specified browser.

    Args:
        browser (str): The name of the browser ('firefox' or 'chrome') to use.
        driver_executable (str): The path to the driver executable file.
        use_debug (bool): Whether to enable debug mode or not.
        first_page (str): The URL of the first page to visit.
        username (str): The username for basic authentication (if required).
        password (str): The password for basic authentication (if required).

    Returns:
        Tuple: A tuple containing the webdriver instance and a boolean indicating
               whether the driver was successfully loaded or not.

    Raises:
        WebDriverException: If the webdriver for the specified browser could not be loaded.

    """
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

    if operating_system == 'windows' and browser == 'chrome':
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
        except se.WebDriverException:
            download_gecko_driver()
            try:
                driver = webdriver.Firefox(executable_path=driver_executable, options=browser_options)
                is_driver_loaded = True
            except se.WebDriverException as missing_browser_driver_error:
                missing_browser_message(browser, missing_browser_driver_error)
    elif browser == 'chrome':
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
                missing_browser_message(browser, missing_browser_driver_error)
        except se.SessionNotCreatedException:
            log_stream.info('Attempting to download the latest chromedriver')
            download_chromedriver()
            try:
                driver = webdriver.Chrome(executable_path=driver_executable, options=browser_options)
                is_driver_loaded = True
            except se.WebDriverException as missing_browser_driver_error:
                missing_browser_message(browser, missing_browser_driver_error)
    return driver, is_driver_loaded
