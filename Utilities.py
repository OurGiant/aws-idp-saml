# coding=utf-8
import argparse
import os
import re
import sys
import tarfile
import zipfile
from pathlib import Path

import constants
from Logging import Logging
import Config

config = Config.Config()


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

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--username", type=str,
                                 help="username for logging into SAML provider, required for text menu")
        self.parser.add_argument("--profilename", type=str, help="the AWS profile name for this session")
        self.parser.add_argument("--region", type=str, help="the AWS profile name for this session",
                                 choices=self.valid_regions)
        self.parser.add_argument("--idp", type=str, help="Id Provider", choices=constants.valid_idp)
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
            run_type = None
            self.log_stream.critical(
                'A profile name must be specified, or you must specify the text menu option for account selection')
            while run_type is not None:
                run_type: str = input('Please provide a profilename from ~/.aws/samlsts or textmenu to continue')
            if run_type == 'textmenu':
                self.args.textmenu = True
        elif self.args.profilename is not None:
            self.aws_profile_name = self.args.profilename
            if any(x in self.aws_profile_name for x in self.illegal_characters):
                self.log_stream.critical('bad characters in profile name, only alphanumeric and dash are allowed. ')
                raise SystemExit(1)

        if self.args.textmenu is True and self.args.username is None:
            self.username = get_user_name()
        else:
            self.username = self.args.username

        if self.args.textmenu is True and self.args.idp is None:
            get_idp = None
            self.log_stream.info('IdP must be provided to use Text Menu')
            while get_idp not in constants.valid_idp:
                get_idp = input('Please specify an to use [' + ','.join(constants.valid_idp) + '] ')
            self.use_idp = "Fed-" + str(get_idp).upper()
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

        if self.args.browser is None:
            self.browser_type = get_browser_type()
        else:
            self.browser_type = self.args.browser

        self.use_debug = self.args.debug
        self.use_gui = self.args.gui
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


def get_script_exec_path():
    return str(Path(__file__).resolve().parents[0])


def check_if_container():
    log_stream.info('run environment is a container')
    container_file = Path('/.dockerenv')
    if container_file.is_file():
        log_stream.info('Run as container')
        try:
            with open('.is_container', 'w') as fh:
                fh.write(open('/var/run/systemd/container').read())
            fh.close()
        except OSError:
            log_stream.critical('Unable to write container flag file')
            raise SystemExit(1)


def get_user_name():
    aws_region, username, *nonsense = config.read_global_settings()
    while username is None:
        username = input('Please provide your username: ')
    return username


@staticmethod
def get_browser_type():
    *nonsense, browser = config.read_global_settings()
    while browser not in constants.valid_browsers:
        browser = input(
            'Please specify a browser to use [' + ','.join(constants.valid_browsers) + '] ')
    return browser
