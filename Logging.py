import logging
import sys

import constants
from Utilities import OSInfo


class ColorManage:
    @staticmethod
    def RGB(red=None, green=None, blue=None, bg=False):
        if bg is False and red is not None and green is not None and blue is not None:
            return f'\u001b[38;2;{red};{green};{blue}m'
        elif bg is True and red is not None and green is not None and blue is not None:
            return f'\u001b[48;2;{red};{green};{blue}m'
        elif red is None and green is None and blue is None:
            return '\u001b[0m'


class CustomFormatter(logging.Formatter):
    linux_grey = "\x1B[38;5;7"
    linux_yellow = "\x1B[38;5;11m"
    linux_red = "\x1B[38;5;1m"
    linux_bold_red = "\x1B[38;5;9m"
    linux_green = "\x1B[38;5;10m"
    linux_cyan = "\x1B[38;5;14m"
    linux_reset = "\x1B[0m"
    format = '[%(asctime)s] [] [%(levelname)s] %(message)s'

    windows_grey = ColorManage.RGB(226, 226, 226)
    windows_yellow = ColorManage.RGB(255, 255, 0)
    windows_orange = ColorManage.RGB(255, 141, 79)
    windows_red = ColorManage.RGB(255, 0, 0)
    windows_green = ColorManage.RGB(105, 255, 79)
    windows_reset = ColorManage.RGB()

    os_info = OSInfo()
    is_xterm = os_info.display_info()

    if is_xterm is True:
        FORMATS = {
            logging.DEBUG: linux_grey + format + linux_reset,
            logging.INFO: linux_green + format + linux_reset,
            logging.WARNING: linux_yellow + format + linux_reset,
            logging.ERROR: linux_red + format + linux_reset,
            logging.CRITICAL: linux_bold_red + format + linux_reset
        }
    elif os_info.which_os() == 'windows' and os_info.which_term() is not None:
        FORMATS = {
            logging.DEBUG: windows_grey + format + windows_reset,
            logging.INFO: windows_green + format + windows_reset,
            logging.WARNING: windows_yellow + format + windows_reset,
            logging.ERROR: windows_orange + format + windows_reset,
            logging.CRITICAL: windows_red + format + windows_reset
        }
    else:
        FORMATS = {
            logging.DEBUG: format,
            logging.INFO: format,
            logging.WARNING: format,
            logging.ERROR: format,
            logging.CRITICAL: format
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logging:

    def __init__(self, name, level=constants.__console_log_level__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(constants.__console_log_level__)
        console_handler.setFormatter(CustomFormatter())
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def set_console_handler(self):
        return self.logger

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

