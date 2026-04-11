import logging
import sys

import constants
from OSInfo import OSInfo

os_info = OSInfo()


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
    linux_dark_violet = "\x1B[38:5:128m"
    linux_reset = "\x1B[0m"
    default_format = '[%(asctime)s] [] [%(levelname)s] %(message)s'

    windows_grey = ColorManage.RGB(226, 226, 226)
    windows_yellow = ColorManage.RGB(255, 255, 0)
    windows_orange = ColorManage.RGB(255, 141, 79)
    windows_red = ColorManage.RGB(255, 0, 0)
    windows_green = ColorManage.RGB(105, 255, 79)
    windows_reset = ColorManage.RGB()

    is_xterm = os_info.display_info()

    if is_xterm is True:
        FORMATS = {
            logging.DEBUG: linux_grey + default_format + linux_reset,
            logging.INFO: linux_green + default_format + linux_reset,
            logging.WARNING: linux_yellow + default_format + linux_reset,
            logging.ERROR: linux_red + default_format + linux_reset,
            logging.CRITICAL: linux_bold_red + default_format + linux_reset,
            logging.FATAL: linux_dark_violet + default_format + linux_reset
        }
    elif os_info.which_os() == 'windows' and os_info.which_term() is not None:
        FORMATS = {
            logging.DEBUG: windows_grey + default_format + windows_reset,
            logging.INFO: windows_green + default_format + windows_reset,
            logging.WARNING: windows_yellow + default_format + windows_reset,
            logging.ERROR: windows_orange + default_format + windows_reset,
            logging.CRITICAL: windows_red + default_format + windows_reset,
            logging.FATAL: windows_red + default_format + windows_reset
        }
    else:
        FORMATS = {
            logging.DEBUG: default_format,
            logging.INFO: default_format,
            logging.WARNING: default_format,
            logging.ERROR: default_format,
            logging.CRITICAL: default_format,
            logging.FATAL: default_format
        }

    # Cache Formatter objects for each log level
    FORMATTER_CACHE = {level: logging.Formatter(pattern) for level, pattern in FORMATS.items()}

    def format(self, record):
        formatter = self.FORMATTER_CACHE.get(record.levelno)
        if formatter is None:
            formatter = logging.Formatter(self.default_format)
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

    def fatal(self, message):
        self.logger.critical(message)

