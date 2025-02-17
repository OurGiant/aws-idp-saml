import logging

__version__ = '1.0.15'
__timeout__ = 45
__snap_install_dir__ = '/snap/firefox/current/usr/lib/firefox'
__mozilla_driver_url__ = 'https://api.github.com/repos/mozilla/geckodriver/releases'

##
# Possible values:
# INFO
# DEBUG
# WARN
# CRITICAL
# ERROR
# FATAL
##
__console_log_level__ = logging.INFO

valid_browsers = ['chrome', 'firefox']
valid_idp = ['okta']

firefox_binary_location = {
    "windows": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    "macos": "/Applications/Firefox.app/Contents/MacOS/firefox",
}


chrome_remote_files = {
    "windows": "chromedriver_win32.zip",
    "linux": "chromedriver_linux64.zip",
    "macos": "chromedriver_mac64.zip"
}

chrome_local_file = {
    "windows": "chromedriver.exe",
    "linux": "chromedriver",
    "macos": "chromedriver"
}

gecko_remote_patterns = {
    "windows": "win64.zip",
    "linux": "linux64.tar.gz",
    "macos": "macos.tar.gz"
}

gecko_local_archive = {
    "windows": "win_gecko.zip",
    "linux": "linux_gecko.tar.gz",
    "macos": "macos_gecko.tar.gz"
}

gecko_local_file = {
    "windows": "geckodriver.exe",
    "linux": "geckodriver",
    "macos": "geckodriver"
}
