# coding=utf-8

import sys
import AWS
import Config
import Login
import Password
import SAMLSelector
import Utilities
from Logging import Logging
from ScreenshotRecorder import ScreenshotRecorder
from typing  import Any, Dict, List


log_stream = Logging('get_credentials')

args = Utilities.Arguments()
config = Config.Config()


def _validate_screenshot_dir(screenshot_dir):
    """
    Validate screenshot directory path to prevent path traversal attacks.
    
    Args:
        screenshot_dir (str): Directory path from command line
        
    Returns:
        str: Validated directory path, or None if invalid
    """
    import os
    from pathlib import Path
    
    if not screenshot_dir:
        return None
    
    # Reject absolute paths
    if os.path.isabs(screenshot_dir):
        log_stream.warning(f'Absolute paths not allowed for screenshot directory: {screenshot_dir}')
        return None
    
    # Reject paths with directory traversal attempts
    if '..' in screenshot_dir or screenshot_dir.startswith('/'):
        log_stream.warning(f'Path traversal attempt detected: {screenshot_dir}')
        return None
    
    # Normalize the path to prevent tricks
    normalized = os.path.normpath(screenshot_dir)
    
    # Double-check after normalization
    if normalized.startswith('..') or os.path.isabs(normalized):
        log_stream.warning(f'Invalid path after normalization: {normalized}')
        return None
    
    # Ensure path is relative to current directory
    if normalized.startswith('/'):
        log_stream.warning(f'Path resolves to absolute: {normalized}')
        return None
    
    log_stream.debug(f'Screenshot directory validated: {normalized}')
    return normalized


def main():
    use_okta_fastpass, use_debug, use_gui, arg_browser_type, aws_profile_name, arg_store_password, \
        arg_session_duration, arg_aws_region, text_menu, use_idp, arg_username, arg_encrypted, \
        enable_screenshots, screenshot_dir, show_credentials = args.parse_args()

    # Validate screenshot_dir to prevent path traversal attacks
    if screenshot_dir:
        screenshot_dir = _validate_screenshot_dir(screenshot_dir)
        if not screenshot_dir:
            log_stream.fatal('Invalid screenshot directory path')
            raise SystemExit(1)

    # Initialize screenshot recorder
    ScreenshotRecorder.initialize(enable=enable_screenshots, output_dir=screenshot_dir)

    principle_arn, role_arn, username, config_aws_region, first_page, config_session_duration, \
        saml_provider_name, idp_login_title, gui_name, config_browser_type, config_store_password, account_number, \
        dsso_url \
        = config.read_config(aws_profile_name, text_menu, use_idp, arg_username)

    aws_region, aws_session_duration = Config.get_aws_variables(config_aws_region, config_session_duration,
                                                                arg_aws_region, arg_session_duration)

    browser_type = arg_browser_type if arg_browser_type is not None else config_browser_type
    if browser_type is None:
        log_stream.fatal('A browser type must be specified either on the command line'
                         ' or in the global section in the config file')
        raise SystemExit(1)

    pass_key, pass_file = config.return_stored_pass_config()

    if arg_store_password is False and config_store_password is False:
        password = Password.get_password()
        confirm_store: str = input('Would you like to store this password for future use? [Y/N]')

        if confirm_store == 'Y' or confirm_store == 'y':
            Password.store_password(password, pass_key, pass_file)
    else:
        password: str = Password.retrieve_password(pass_key, pass_file)

    saml_response = Login.browser_login(username,
                                        password,
                                        first_page,
                                        use_debug,
                                        use_gui,
                                        browser_type,
                                        saml_provider_name,
                                        idp_login_title,
                                        role_arn, gui_name, dsso_url,use_okta_fastpass)

    log_stream.info('SAML Response Size: ' + str(len(saml_response)))
    if len(saml_response) < 50:
        log_stream.fatal("Issue with logging into Identity Provider: " + saml_response)
        raise SystemExit(1)

    if text_menu is True:

        account_map = config.read_map_file()

        all_roles, table_object = SAMLSelector.get_roles_from_saml_response(saml_response, account_map)
        selected_role = SAMLSelector.select_role_from_text_menu(all_roles, table_object)
        role_arn = selected_role['arn']
        principle_arn = selected_role['principle']
        profile_name = selected_role['rolename']
        used_profile_name_param = False
        try:
            account_name = selected_role['account_name']
        except KeyError:
            account_name: str = selected_role['account_number']
        
        account_number: str = selected_role['account_number']
    else:
        profile_name = aws_profile_name
        used_profile_name_param = True
        account_name = gui_name

    get_sts = AWS.STS.aws_assume_role(aws_region, role_arn, principle_arn, saml_response, aws_session_duration)

    if len(get_sts) > 0:
        aws_access_id, aws_secret_key, aws_session_token, sts_expiration \
            = AWS.STS.get_sts_details(get_sts)

        if Config.validate_aws_cred_format(aws_access_id, aws_secret_key, aws_session_token):
            profile_block, clean_profile_name = config.write_aws_config(aws_access_id, aws_secret_key,
                                                                        aws_session_token, profile_name, aws_region,
                                                                        account_number, used_profile_name_param)
        else:
            log_stream.fatal('There seems to be an issue with one of the credentials generated, please try again')
            raise SystemExit(1)

        aws_user_id = AWS.STS.get_aws_caller_id(clean_profile_name)

        sts_expires_local_time: str = sts_expiration.strftime("%c")
        log_stream.info('Token issued for ' + str(aws_user_id) + ' in account ' + str(account_name))
        log_stream.info('Token will expire at ' + sts_expires_local_time)

        if arg_encrypted:
            encrypted_string = Utilities.encrypt_credentials(aws_access_id, aws_secret_key, aws_session_token)
            log_stream.info('Encrypted credentials generated (use --encrypted flag to display)')
            # Only print if explicitly requested and in non-interactive mode
            if sys.stdout.isatty():
                print('\nEncrypted Credentials String:\n' + encrypted_string + '\n')
            else:
                # In non-interactive mode, only log it
                log_stream.debug(f'Encrypted credentials: {encrypted_string}')

        if config.check_global_in_saml_config():
            configure_globals: str = input('Save the settings from this section for all sessions? [Y/N]')
            configure_globals = configure_globals.upper()
            if configure_globals.startswith('Y'):
                config.write_global_to_saml_config(browser_type, username, aws_region, aws_session_duration)

        # Display credentials in plaintext if requested
        if show_credentials:
            print('\n' + '='*60)
            print('AWS CREDENTIALS (PLAINTEXT)')
            print('='*60)
            print(f'AWS_ACCESS_KEY_ID={aws_access_id}')
            print(f'AWS_SECRET_ACCESS_KEY={aws_secret_key}')
            print(f'AWS_SESSION_TOKEN={aws_session_token}')
            print('='*60)
            print(f'Expires: {sts_expires_local_time}')
            print('='*60 + '\n')

        # Print profile info without sensitive credentials
        profile_info = f'\nProfile: {clean_profile_name}\nRegion: {aws_region}\nAccount: {account_name}\n'
        print(profile_info)
        log_stream.info(f'Profile {clean_profile_name} configured successfully')

    else:
        log_stream.fatal("Corrupt or Unavailable STS Response")
        raise SystemExit(1)


if __name__ == "__main__":
    log_stream.info('start login process')
    main()
