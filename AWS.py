# coding=utf-8
import datetime

import botocore
from boto3 import Session as BotoSession
from botocore import errorfactory as err

import constants
import Utilities
from Logging import Logging

log_stream = Logging('aws')


class STS:

    @staticmethod
    def get_aws_caller_id(profile):
        post_session = BotoSession(profile_name=profile)
        sts = post_session.client('sts')

        aws_caller_identity = sts.get_caller_identity()
        aws_user_id = str(aws_caller_identity['UserId']).split(":", 1)[1]

        return aws_user_id

    @staticmethod
    def aws_assume_role(region, role, principle, saml_assertion, duration):
        pre_session = BotoSession(region_name=region)
        sts = pre_session.client('sts')

        log_stream.info('Role: ' + role)
        log_stream.info('Principle: ' + principle)

        try:
            get_sts = sts.assume_role_with_saml(
                RoleArn=role,
                PrincipalArn=principle,
                SAMLAssertion=saml_assertion,
                DurationSeconds=int(duration)
            )

        except err.ClientError as e:
            error_message = "Error assuming role. Token length: " + str(len(saml_assertion))
            log_stream.critical(error_message)
            # log_stream.info(str(saml_assertion))
            log_stream.critical(str(e))
            exit(2)

        return get_sts

    @staticmethod
    def get_sts_details(sts_object):
        aws_access_id = sts_object['Credentials']['AccessKeyId']
        aws_secret_key = sts_object['Credentials']['SecretAccessKey']
        aws_session_token = sts_object['Credentials']['SessionToken']

        sts_expiration = sts_object['Credentials']['Expiration']
        local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        sts_expiration_local = sts_expiration.astimezone(local_timezone)

        return aws_access_id, aws_secret_key, aws_session_token, sts_expiration_local


class IAM:
    @staticmethod
    def get_account_alias(profile):
        account_name = None
        session = BotoSession(profile_name=profile)
        iam_client = session.client('iam')
        try:
            account_aliases = iam_client.list_account_aliases()
            account_name = account_aliases['AccountAliases'][0]
        except botocore.exceptions.ClientError as e:
            log_stream.info('Unable to get account alias')
            pass

        return account_name
