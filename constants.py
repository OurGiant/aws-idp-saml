import logging

import os

__version__ = '2.3.0'
__timeout__ = int(os.getenv('AWS_SAML_TIMEOUT', 45))  # Configurable timeout in seconds
__snap_install_dir__ = '/snap/firefox/current/usr/lib/firefox'

##
# Possible values:
# INFO
# DEBUG
# WARN
# CRITICAL
# ERROR
# FATAL
##
__console_log_level__ = logging.DEBUG

valid_browsers = ['chrome', 'firefox', 'edge']
valid_idp = ['okta']

firefox_binary_location = {
    "windows": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    "macos": "/Applications/Firefox.app/Contents/MacOS/firefox",
}
