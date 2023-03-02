# coding=utf-8
import argparse
import logging
import os
import re
import sys
import tarfile
import zipfile

from version import __version__

CONSOLE_LOG_LEVEL = logging.INFO


class OSInfo:
    def __init__(self):
        os_types = [
            {'name': 'windows', 'sysname': 'win32'},
            {'name': 'macos', 'sysname': 'darwin'},
            {'name': 'linux', 'sysname': 'linux'},
        ]

        for os_type in os_types:
            if os_type['sysname'] == sys.platform:
                self.operating_system = os_type['name']

        self.environment_terminal = os.environ.get('TERM')

    def display_info(self):
        xterm_pattern = re.compile('xterm.*')

        if self.operating_system == 'linux':
            if self.environment_terminal is None:
                is_xterm = False
                return is_xterm
            try:
                is_xterm = bool(xterm_pattern.match(self.environment_terminal))
            except ValueError:
                is_xterm = False
        else:
            is_xterm = False
        return is_xterm

    def which_os(self):
        return self.operating_system

    def which_term(self):
        return self.environment_terminal


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

    def __init__(self, name, level=CONSOLE_LOG_LEVEL):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(CONSOLE_LOG_LEVEL)
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


class Arguments:
    def __init__(self):
        self.username = None
        self.log_stream = Logging('args_init')
        self.use_idp = None
        self.text_menu: bool = False
        self.aws_region = None
        self.session_duration: int = 0
        self.store_password: bool = False
        self.aws_profile_name = None
        self.browser_type = None
        self.use_gui: bool = False
        self.use_debug: bool = False
        self.illegal_characters = ['!', '@', '#', '&', '(', ')', '[', '{', '}', ']', ':', ';', '\'', ',', '?', '/',
                                   '\\', '*', '~', '$', '^', '+', '=', '<', '>']

        self.valid_regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']

        self.valid_idp = ['okta', 'ping']

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--username", type=str,
                                 help="username for logging into SAML provider, required for text menu")
        self.parser.add_argument("--profilename", type=str, help="the AWS profile name for this session")
        self.parser.add_argument("--region", type=str, help="the AWS profile name for this session",
                                 choices=self.valid_regions)
        self.parser.add_argument("--idp", type=str, help="Id Provider", choices=self.valid_idp)
        self.parser.add_argument("--duration", type=str,
                                 help="desire token length, not to be greater than max length set by AWS "
                                      "administrator")
        self.parser.add_argument("--browser", type=str, help="your browser of choice")
        self.parser.add_argument("--storedpw", type=bool, default=False, nargs='?', const=True,
                                 help="use a stored password")
        self.parser.add_argument("--gui", type=bool, default=False, nargs='?', const=True,
                                 help="open the session in a browser as well")
        self.parser.add_argument("--textmenu", type=bool, default=False, nargs='?', const=True,
                                 help="display text menu of accounts. cannot be used with gui option")
        self.parser.add_argument("--debug", type=bool, default=False, nargs='?', const=True,
                                 help="show browser during SAML attempt")
        if len(sys.argv) == 0:
            self.log_stream.critical("Arguments required")
            self.parser.print_help()
            raise SystemExit(1)
        else:
            self.args = self.parser.parse_args()

    def parse_args(self):
        self.log_stream = Logging('parse_args')

        if self.args.profilename is None and self.args.textmenu is False:
            self.log_stream.critical(
                'A profile name must be specified, or you must specify the text menu option for account selection')
            sys.exit(1)
        elif self.args.profilename is not None:
            self.aws_profile_name = self.args.profilename
            if any(x in self.aws_profile_name for x in self.illegal_characters):
                self.log_stream.critical('bad characters in profile name, only alphanumeric and dash are allowed. ')
                raise SystemExit(1)

        if self.args.textmenu is True and self.args.username is None:
            self.log_stream.warning('Username must be provided to use Text Menu')
            self.username = input('Please provide your username: ')
        else:
            self.username = self.args.username

        if self.args.textmenu is True and self.args.idp is None:
            self.log_stream.critical('IdP must be provided to use Text Menu')
            raise SystemExit(1)
        else:
            self.use_idp = "Fed-" + str(self.args.idp).upper()

        if self.args.textmenu is True:
            self.aws_profile_name = "None"

        if self.args.gui is True and self.args.textmenu is True:
            self.log_stream.critical('You cannot combine GUI and Text Menu options. Please choose one or the other')
            raise SystemExit(1)

        if not self.args.duration:
            self.session_duration = 0
        else:
            self.session_duration = self.args.duration

        self.use_debug = self.args.debug
        self.use_gui = self.args.gui
        self.browser_type = self.args.browser
        self.store_password = self.args.storedpw
        self.aws_region = self.args.region
        self.text_menu = self.args.textmenu

        return self.use_debug, self.use_gui, self.browser_type, self.aws_profile_name, \
            self.store_password, self.session_duration, self.aws_region, self.text_menu, self.use_idp, self.username


log_stream = Logging('utilities')


def extract_zip_archive(archive_file_name):
    try:
        log_stream.info('unzip driver archive ' + archive_file_name)
        with zipfile.ZipFile(archive_file_name, 'r') as zip_ref:
            zip_ref.extractall(path='drivers/')
        zip_ref.close()
    except zipfile.BadZipfile as e:
        log_stream.critical(str(e))
        return False
    os.remove(archive_file_name)
    return True


def extract_tgz_archive(archive_file_name):
    try:
        log_stream.info('untar driver archive ' + archive_file_name)
        with tarfile.open(archive_file_name, 'r:gz') as tar_ref:
            tar_ref.extractall('drivers/')
        tar_ref.close()
    except tarfile.ReadError as e:
        log_stream.critical('Error reading archive:' + str(e))
        return False
    except tarfile.ExtractError as e:
        log_stream.critical('Error extracting archive:' + str(e))
        return False
    except tarfile.TarError as e:
        log_stream.critical('Error:' + str(e))
        return False
    os.remove(archive_file_name)
    return True
