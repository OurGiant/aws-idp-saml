# coding=utf-8
import datetime

from boto3 import Session as BotoSession
from botocore import errorfactory as err

from version import __version__
import Utilities
log_stream = Utilities.Logging('aws')


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
    def get_sts_details(sts_object, region,aws_profile_name):
        aws_access_id = sts_object['Credentials']['AccessKeyId']
        aws_secret_key = sts_object['Credentials']['SecretAccessKey']
        aws_session_token = sts_object['Credentials']['SessionToken']

        profile_block = "[" + aws_profile_name + "]\n" "region = " + region + "\naws_access_key_id =  " + \
                        aws_access_id + "\naws_secret_access_key =  " + aws_secret_key + "\naws_session_token =  " \
                        + aws_session_token

        sts_expiration = sts_object['Credentials']['Expiration']
        local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        sts_expiration_local = sts_expiration.astimezone(local_timezone)

        return aws_access_id, aws_secret_key, aws_session_token, sts_expiration_local, profile_block