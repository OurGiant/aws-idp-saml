# coding=utf-8
import configparser
import os
import re
import sys

from pathlib import Path

import Browser
import Utilities

log_stream = Utilities.Logging('config')
import constants


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
        global log_stream
        self.executePath = str(Path(__file__).resolve().parents[0])

        home = str(Path.home())
        self.AWSRoot = home + "/.aws/"
        self.awsSAMLFile = self.AWSRoot + "samlsts"

        # READ IN SAML CONFIG IF EXISTS, EXIT IF NOT
        if Path(self.awsSAMLFile).is_file() is False:
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

            self.write_aws_config()
            self.configConfig = configparser.ConfigParser()
            self.configConfig.read(self.awsConfigFile)

        self.PassFile = self.AWSRoot + "saml.pass"
        self.PassKey = self.AWSRoot + "saml.key"
        self.AccountMap = self.AWSRoot + "account-map.json"

    def write_aws_config(self):
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

    def read_config(self, aws_profile_name, text_menu, use_idp, arg_username):
        gui_name = None
        session_duration = None
        principle_arn = None
        role_arn = None
        aws_region = None
        browser = None
        username = None
        saved_password = None

        # check for global variables. read if any, these will be overwritten by CLI and configuration in account blocks
        if 'global' in self.configSAML.sections():
            log_stream.info('Read settings from global block')
            try:
                browser = self.configSAML.get('global', 'browser')
            except configparser.NoOptionError:
                pass
            try:
                session_duration = self.configSAML.get('global', 'sessionDuration')
            except configparser.NoOptionError:
                pass
            try:
                saved_password = self.configSAML.get('global', 'savedPassword')
            except configparser.NoOptionError:
                pass
            try:
                username = self.configSAML.get('global', 'username')
            except configparser.NoOptionError:
                pass
            try:
                aws_region = self.configSAML.get('global', 'awsRegion')
            except configparser.NoOptionError:
                pass
        else:
            log_stream.info('No gloabl settings found')

        if text_menu is False:
            try:
                self.configSAML.get(aws_profile_name, 'samlProvider')
            except configparser.NoSectionError as e:
                log_stream.critical('No such AWS profile ' + aws_profile_name)
                raise SystemExit(1)

            log_stream.info('Reading configuration info for profile ' + aws_profile_name)
            try:
                aws_region = self.configSAML[aws_profile_name]['awsRegion']
            except KeyError:
                aws_region = None
            try:
                session_duration = self.configSAML[aws_profile_name]['sessionDuration']
            except KeyError:
                session_duration = None
            try:
                account_number = self.configSAML[aws_profile_name]['accountNumber']
                iam_role = self.configSAML[aws_profile_name]['IAMRole']
                saml_provider = self.configSAML[aws_profile_name]['samlProvider']
                username = self.configSAML[aws_profile_name]['username']
                gui_name = self.configSAML[aws_profile_name]['guiName']
            except KeyError as missing_config_error:
                missing_config_property: str = missing_config_error.args[0]
                log_stream.critical('Missing configuration property: ' + missing_config_property)
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
            log_stream.critical('No such SAML provider ' + saml_provider_name)
            raise SystemExit(1)
        try:
            first_page = self.configSAML[saml_provider]['loginpage']
            idp_login_title = str(self.configSAML[saml_provider]['loginTitle']).replace('"', '')
        except KeyError as missing_saml_provider_error:
            missing_saml_provider_property: str = missing_saml_provider_error.args[0]
            log_stream.critical('Missing SAML provider configuration property ' + missing_saml_provider_property)
            raise SystemExit(1)

        return principle_arn, role_arn, username, aws_region, first_page, session_duration, \
            saml_provider_name, idp_login_title, gui_name, browser, saved_password

    def revoke_creds(self, profile_name):
        self.configCredentials[profile_name] = {}
        self.configConfig["profile " + profile_name] = {}
        with open(self.awsConfigFile, "w") as config:
            self.configConfig.write(config)
        with open(self.awsCredentialsFile, "w") as credentials:
            self.configCredentials.write(credentials)
        log_stream.info('Revoked token for ' + profile_name)
        pass

    def write_config(self, access_key_id, secret_access_key, aws_session_token, aws_profile_name, aws_region):
        self.configCredentials[aws_profile_name] = {}
        self.configCredentials[aws_profile_name]['aws_access_key_id'] = access_key_id
        self.configCredentials[aws_profile_name]['aws_secret_access_key'] = secret_access_key
        self.configCredentials[aws_profile_name]['aws_session_token'] = aws_session_token

        self.configConfig["profile " + aws_profile_name] = {}
        self.configConfig["profile " + aws_profile_name]['region'] = aws_region

        with open(self.awsConfigFile, "w") as config:
            self.configConfig.write(config)

        with open(self.awsCredentialsFile, "w") as credentials:
            self.configCredentials.write(credentials)
