# coding=utf-8
import argparse
import os
import sys
import tarfile
import zipfile
from pathlib import Path
import shutil

import constants
import Config
from Logging import Logging

log_stream = Logging('utilities')
config = Config.Config()


class Arguments:
    def __init__(self):
        self.username = None
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
            log_stream.fatal("Arguments required")
            self.parser.print_help()
            raise SystemExit(1)
        else:
            self.args = self.parser.parse_args()

    def parse_args(self):

        if self.args.profilename is None and self.args.textmenu is False:
            run_type = None
            log_stream.critical(
                'A profile name must be specified, or you must specify the text menu option for account selection')
            while run_type is None:
                run_type = input('Please provide a profilename from ~/.aws/samlsts or textmenu to continue: ')
            if run_type == 'textmenu':
                self.args.textmenu = True
        elif self.args.profilename is not None:
            self.aws_profile_name = self.args.profilename
            if any(x in self.aws_profile_name for x in self.illegal_characters):
                log_stream.fatal('bad characters in profile name, only alphanumeric and dash are allowed. ')
                raise SystemExit(1)

        if self.args.textmenu is True and self.args.username is None:
            log_stream.warning('No username specified, checking global settings')
            self.username = get_user_name()
        else:
            self.username = self.args.username

        if self.args.textmenu is True and self.args.idp is None:
            get_idp = None
            log_stream.info('IdP must be provided to use Text Menu')
            while get_idp not in constants.valid_idp:
                get_idp = input('Please specify an to use [' + ','.join(constants.valid_idp) + '] ')
            self.use_idp = "Fed-" + str(get_idp).upper()
        else:
            self.use_idp = "Fed-" + str(self.args.idp).upper()

        if self.args.textmenu is True:
            self.aws_profile_name = "None"

        if self.args.gui is True and self.args.textmenu is True:
            log_stream.fatal('You cannot combine GUI and Text Menu options. Please choose one or the other')
            raise SystemExit(1)

        if not self.args.duration:
            log_stream.warning('No session duration specified, checking global settings')
            self.session_duration = get_session_duration()
        else:
            self.session_duration = self.args.duration

        if self.args.browser is None:
            log_stream.warning('No browser specified, checking global settings')
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


def extract_zip_archive(archive_file_name):
    try:
        log_stream.info('unzip driver archive ' + archive_file_name)
        with zipfile.ZipFile(archive_file_name, 'r') as zip_ref:
            archive_root = zip_ref.namelist()[0].split('/')[0]
            zip_ref.extractall(path='drivers/')
        zip_ref.close()
        if len(zip_ref.namelist()[0].split('/')) > 1:
            for file in os.listdir('drivers/'+archive_root+'/'):
                shutil.move('drivers/'+archive_root+'/'+file, 'drivers/')
            shutil.rmtree('drivers/'+archive_root+'/')
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
            log_stream.fatal('Unable to write container flag file')
            raise SystemExit(1)


def get_user_name():
    aws_region, username, *nonsense = config.read_global_settings()
    while username is None:
        username = input('Please provide your username: ')
    return username


def get_browser_type():
    *nonsense, browser = config.read_global_settings()
    while browser not in constants.valid_browsers:
        browser = input(
            'Please specify a browser to use [' + ','.join(constants.valid_browsers) + '] ')
    return browser


def get_session_duration():
    *nonsense, session_duration, browser = config.read_global_settings()
    if session_duration is None:
        session_duration = 0
    return session_duration
