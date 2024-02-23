# coding=utf-8
import configparser
import json
import re
from pathlib import Path

import AWS
import constants
from Logging import Logging

log_stream = Logging('config')


def missing_config_file_message():
    message = "You are missing the core config file required for the proper operation of this utility.\nThis " \
              "file should be located in the .aws directory, found in your home directory "
    message = message + "\nThis file contains ini style configuration sections containing information about the " \
                        "accounts you are trying to access. "
    message = message + "\nFor example:"
    message = message + "\n\t[cloud1-prod]"
    message = message + "\n\tawsRegion = us-east-1"
    message = message + "\n\taccount_number ="
    message = message + "\n\tIAMRole = PING-DevOps"
    message = message + "\n\tsamlProvider = PING"
    message = message + "\n\tusername=adUsername"
    message = message + "\n\tguiName=production"
    message = message + "\n\tsessionDuration=14400"
    message = message + "\n\nThe configuration must also contain a section for the Authentication provider you " \
                        "are using, ie: PING. Each provider section name must be prefixed with 'Fed-'"
    message = message + "\nFor example:"
    message = message + "\n\t[Fed-PING]"
    message = message + "\n\tloginpage = https: //ping.mycompanydomain.com/idp/ping " \
                        "startSSO.ping?PartnerSpId = urn:amazon: webservices "
    message = message + "\n\nA sample file can be found in the same repository as the utility"
    print(message)
    raise SystemExit(1)


def validate_aws_cred_format(aws_access_id, aws_secret_key, aws_session_token):
    valid_key_pattern = re.compile(r'^[a-zA-Z0-9]{16,128}$')
    valid_secret_pattern = re.compile(r'^[a-zA-Z0-9\/+]{30,50}$')
    valid_token_pattern = re.compile(r'^[a-zA-Z0-9\/+]{400,500}$')

    if not (bool(valid_key_pattern.match(aws_access_id)) or bool(valid_secret_pattern.match(aws_secret_key)) or bool(
            valid_token_pattern.match(aws_session_token))
    ):
        return False
    else:
        return True


def get_aws_variables(conf_region, conf_duration, arg_aws_region, arg_session_duration):
    if conf_region is None and arg_aws_region is None:
        log_stream.info('Defaulting the region to us-east-1')
        log_stream.info('A custom region may be provided using the config file or the command line argument.')
        aws_region = 'us-east-1'
    elif arg_aws_region is None:
        aws_region = conf_region
    else:
        aws_region = arg_aws_region

    if conf_duration is None and arg_session_duration == 0:
        log_stream.info('Defaulting the session duration to one hour')
        log_stream.info('A custom duration may be provided using the config file or the command line argument.')
        aws_session_duration = 3600
    elif arg_session_duration == 0:
        aws_session_duration = conf_duration
    else:
        aws_session_duration = arg_session_duration

    return aws_region, aws_session_duration


class Config:
    def __init__(self):
        self.executePath = str(Path(__file__).resolve().parents[0])

        home = str(Path.home())
        self.AWSRoot = home + "/.aws/"
        self.awsSAMLFile = self.AWSRoot + "samlsts"

        if not Path(self.awsSAMLFile).is_file():
            log_stream.warning('No SAML-STS file, one will be built for you using a series of questions')
            idp_name: str = self.get_saml_info()
            self.configSAML = configparser.ConfigParser()
            self.configSAML.read(self.awsSAMLFile)
        elif not Path(self.awsSAMLFile).is_file() and not Path('/.dockerenv').is_file():
            missing_config_file_message()
        else:
            self.configSAML = configparser.ConfigParser()
            self.configSAML.read(self.awsSAMLFile)

        # READ IN AWS CREDENTIALS
        self.awsCredentialsFile = self.AWSRoot + "credentials"
        if Path(self.awsCredentialsFile).is_file() is True:
            self.configCredentials = configparser.ConfigParser()
            self.configCredentials.read(self.awsCredentialsFile)
        else:
            log_stream.warning(
                'AWS credentials file ' + self.awsCredentialsFile + ' is missing, this is must be the inital run')
            log_stream.info('This program will create an AWS credentials file for you.')

            with open(self.awsCredentialsFile, 'w') as creds:
                creds.write("#This is your AWS credentials file\n")
            creds.close()

        self.awsConfigFile = self.AWSRoot + "config"
        if Path(self.awsConfigFile).is_file() is True:
            self.configConfig = configparser.ConfigParser()
            self.configConfig.read(self.awsConfigFile)
        else:
            log_stream.critical('AWS config file ' + self.awsConfigFile + ' is missing, this is must be the inital run')
            log_stream.critical('This program will create an AWS config file for you.')

            self.create_aws_config()
            self.configConfig = configparser.ConfigParser()
            self.configConfig.read(self.awsConfigFile)
            log_stream.info('Return to normal operations')

        self.PassFile = self.AWSRoot + "saml.pass"
        self.PassKey = self.AWSRoot + "saml.key"
        self.AccountMap = self.AWSRoot + "account-map.json"

    def get_saml_info(self):
        idp_name = "default"
        while idp_name not in constants.valid_idp:
            idp_name: str = input('What is the name of your provider? [' + ', '.join(constants.valid_idp) + '] ').lower()
        log_stream.info('Information may be obtained from your IdP admin')
        login_page: str = input('What is the application login URL for your IdP? ')
        login_title: str = input('What is the HTML title on the login page? ')
        with open(self.awsSAMLFile, 'w+') as saml_config_file:
            saml_config_file.write(
                "[Fed-" + idp_name.upper() + "]\nloginpage=" + login_page + "\nloginTitle=" + login_title + "\n\n"
            )
        return idp_name

    def create_aws_config(self):
        with open(self.awsConfigFile, 'w') as config:
            for section in self.configSAML._sections:
                if section.startswith('Fed-', 0, 4) is False:
                    config.write(
                        "[" + section + "]\nregion=" + self.configSAML._sections[section]['awsregion'] + "\n\n")
        config.close()

    def return_stored_pass_config(self):
        return self.PassKey, self.PassFile

    def return_account_map_file(self):
        return self.AccountMap

    def create_new_map_file(self):
        with open(self.AccountMap, 'w') as mapfh:
            mapfh.write('[]')
        mapfh.close()

    def check_for_map_file(self):
        if not Path(self.AccountMap).is_file():
            log_stream.info('Starting a new accounts map file')
            self.create_new_map_file()

    def write_account_to_map_file(self, account_name, account_number):
        with open(self.AccountMap, 'r') as mapfile:
            account_map: list = json.loads(mapfile.read())
        mapfile.close()

        account_map_entry = {"name": account_name, "number": account_number}
        if not account_map_entry in account_map:
            account_map.append(account_map_entry)

        with open(self.AccountMap, 'w') as mapfile:
            mapfile.write(json.dumps(account_map))
        mapfile.close()

    def read_map_file(self):
        account_map_file = self.return_account_map_file()
        try:
            with open(account_map_file, 'r') as mapfile:
                account_map: list = json.loads(mapfile.read())
            mapfile.close()
            return account_map
        except FileNotFoundError:
            log_stream.warning('No map file found, using account numbers in display')
            log_stream.info('The accounts map configuration can be provided to you by your AWS team')
            self.check_for_map_file()
            self.read_map_file()

    def read_global_settings(self):
        aws_region = None
        username = None
        saved_password = None
        session_duration = None
        browser = None
        saml_provider = None

        log_stream.info('Read settings from global block')

        try:
            browser = self.configSAML.get('global', 'browser')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
        try:
            session_duration = self.configSAML.get('global', 'sessionDuration')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
        try:
            saved_password = self.configSAML.get('global', 'savedPassword')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
        try:
            username = self.configSAML.get('global', 'username')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
        try:
            aws_region = self.configSAML.get('global', 'awsRegion')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
        try:
            saml_provider = self.configSAML.get('global', 'samlProvider')
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass

        return aws_region, username, saved_password, session_duration, saml_provider, browser

    def read_config(self, aws_profile_name, text_menu, use_idp, arg_username):
        account_number = None
        gui_name = None
        session_duration = None
        principle_arn = None
        role_arn = None
        aws_region = None
        browser = None
        username = None
        saml_provider = None
        saved_password = None
        dsso_url = None

        # check for global variables. read if any, these will be overwritten by CLI and configuration in account blocks
        aws_region, username, saved_password, session_duration, saml_provider, browser \
            = self.read_global_settings()

        if text_menu is False and aws_profile_name is not None:
            try:
                self.configSAML.has_option(aws_profile_name, 'samlProvider')
            except configparser.NoSectionError as e:
                log_stream.fatal('No such AWS profile ' + aws_profile_name)
                raise SystemExit(1)

            log_stream.info('Reading configuration info for profile ' + aws_profile_name)
            profile = self.configSAML[aws_profile_name]
            try:
                aws_region = getattr(profile, 'awsRegion', aws_region)
            except KeyError:
                aws_region = None
            try:
                session_duration = profile['sessionDuration']
            except KeyError:
                pass
            try:
                account_number = profile['accountNumber']
                iam_role = profile['IAMRole']
                saml_provider = getattr(profile, 'samlProvider', saml_provider)
                username = getattr(profile, 'username', username)
                gui_name = profile['guiName']
            except KeyError as missing_config_error:
                missing_config_property: str = missing_config_error.args[0]
                log_stream.fatal('Missing configuration property: ' + missing_config_property)
                raise SystemExit(1)
            role_arn = "arn:aws:iam::" + account_number + ":role/" + iam_role
            saml_provider_name = saml_provider.split('-', 1)[1]
            principle_arn = "arn:aws:iam::" + account_number + ":saml-provider/" + saml_provider_name
        else:
            saml_provider = use_idp
            saml_provider_name = use_idp.split('-', 1)[1]
            username = arg_username

        log_stream.info('Reading configuration for SAML provider ' + saml_provider_name)
        try:
            self.configSAML.get(saml_provider, 'loginpage')
        except configparser.NoSectionError:
            log_stream.fatal('No such SAML provider ' + saml_provider_name)
            raise SystemExit(1)
        try:
            first_page = self.configSAML[saml_provider]['loginpage']
            idp_login_title = str(self.configSAML[saml_provider]['loginTitle']).replace('"', '')
        except KeyError as missing_saml_provider_error:
            missing_saml_provider_property: str = missing_saml_provider_error.args[0]
            log_stream.fatal('Missing SAML provider configuration property ' + missing_saml_provider_property)
            raise SystemExit(1)

        try:
            dsso_url = self.configSAML[saml_provider]['dssoUrl']
        except KeyError as missing_dsso_url:
            log_stream.info('Not configured to use DSSO. If your organization has this feature enabled and it is not configured the request will timeout')

        return principle_arn, role_arn, username, aws_region, first_page, session_duration, \
            saml_provider_name, idp_login_title, gui_name, browser, saved_password, account_number, dsso_url

    def revoke_creds(self, profile_name):
        self.configCredentials[profile_name] = {}
        self.configConfig["profile " + profile_name] = {}
        with open(self.awsConfigFile, "w") as config:
            self.configConfig.write(config)
        with open(self.awsCredentialsFile, "w") as credentials:
            self.configCredentials.write(credentials)
        log_stream.info('Revoked token for ' + profile_name)
        pass

    def write_aws_config(self, access_key_id, secret_access_key, aws_session_token, aws_profile_name, aws_region,
                         account_number, used_profile_name_param):

        self.configCredentials[aws_profile_name] = {}
        self.configCredentials[aws_profile_name]['aws_access_key_id'] = access_key_id
        self.configCredentials[aws_profile_name]['aws_secret_access_key'] = secret_access_key
        self.configCredentials[aws_profile_name]['aws_session_token'] = aws_session_token

        self.configConfig["profile " + aws_profile_name] = {}
        self.configConfig["profile " + aws_profile_name]['region'] = aws_region

        with open(self.awsConfigFile, "w") as config:
            self.configConfig.write(config)
        config.close()

        with open(self.awsCredentialsFile, "w") as credentials:
            self.configCredentials.write(credentials)
        credentials.close()

        clean_profile_name, profile_block = self.create_profile_block(aws_profile_name, access_key_id,
                                                                      secret_access_key, aws_region, aws_session_token,
                                                                      account_number, used_profile_name_param)
        if used_profile_name_param is False:
            self.configCredentials.remove_section(aws_profile_name)

            self.configCredentials[clean_profile_name] = {}
            self.configCredentials[clean_profile_name]['aws_access_key_id'] = access_key_id
            self.configCredentials[clean_profile_name]['aws_secret_access_key'] = secret_access_key
            self.configCredentials[clean_profile_name]['aws_session_token'] = aws_session_token

        with open(self.awsCredentialsFile, "w") as credentials:
            self.configCredentials.write(credentials)
        credentials.close()

        return profile_block, clean_profile_name

    def create_profile_block(self, aws_profile_name, access_key_id, secret_access_key, aws_region, aws_session_token,
                             account_number, used_profile_name_param):
        if used_profile_name_param is False:
            aws_role = aws_profile_name.split('-', 1)[1]
            account_name = AWS.IAM.get_account_alias(aws_profile_name)
            if account_name is not None:
                profile_name: str = account_name + '-' + aws_role
                self.write_account_to_map_file(account_name, account_number)
            else:
                profile_name: str = account_number + '-' + aws_role
        else:
            profile_name = aws_profile_name

        profile_block = "[" + profile_name + "]\n" "region = " + aws_region + "\naws_access_key_id =  " + \
                        access_key_id + "\naws_secret_access_key =  " + secret_access_key + "\naws_session_token =  " \
                        + aws_session_token

        return profile_name, profile_block

    def write_profile_to_saml_config(self, profile_name: str, aws_region: str, account_number: str, iam_role: str,
                                     saml_provider: str,
                                     username: str):

        role_name = iam_role.split('/')[1]

        run_time_setup = account_number + '-' + role_name + '-' + username

        profile_exists = False
        for section in self.configSAML.sections():
            try:
                profile_setup = self.configSAML.get(section, 'accountnumber') \
                                + '-' + self.configSAML.get(section, 'iamrole') \
                                + '-' + self.configSAML.get(section, 'username')

                if run_time_setup == profile_setup:
                    profile_exists = True
                    smlsts_profile_name = section
                    break
            except configparser.NoOptionError:
                pass

        if profile_exists:
            return False
        else:
            log_stream.warning('profile ' + profile_name + ' missing, creating')
            try:
                self.configSAML.add_section(profile_name)
                self.configSAML[profile_name]['awsregion'] = str(aws_region)
                self.configSAML[profile_name]['username'] = str(username)
                self.configSAML[profile_name]['samlprovider'] = str(saml_provider)
                self.configSAML[profile_name]['iamrole'] = str(role_name)
                self.configSAML[profile_name]['accountnumber'] = str(account_number)
                with open(self.awsSAMLFile, 'w') as saml_file:
                    self.configSAML.write(saml_file)
                saml_file.close()
                return True
            except configparser.DuplicateSectionError:
                log_stream.info('This profile already exists')

    def check_global_in_saml_config(self):

        if 'global' in self.configSAML.sections():
            log_stream.info('global section present')
            return False
        else:
            log_stream.warning('global section missing, creating')
            self.configSAML.add_section('global')

            with open(self.awsSAMLFile, 'w') as saml_file:
                self.configSAML.write(saml_file)
            saml_file.close()
            return True

    def write_global_to_saml_config(self, browser_type, username, aws_region, aws_session_duration):

        if 'global' in self.configSAML.sections():
            log_stream.info('global section present, updating')
            try:
                self.configSAML['global']['browser'] = str(browser_type)
                self.configSAML['global']['username'] = str(username)
                self.configSAML['global']['awsRegion'] = str(aws_region)
                self.configSAML['global']['sessionDuration'] = str(aws_session_duration)
            except TypeError:
                pass
        else:
            self.configSAML.add_section('global')

        with open(self.awsSAMLFile, 'w') as saml_file:
            self.configSAML.write(saml_file)
        saml_file.close()
