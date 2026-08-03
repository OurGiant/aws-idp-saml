"""
Batch authentication: reuse one SAML assertion across profiles sharing the same
(samlProvider, username) identity — one browser login per group instead of one per profile.

Mirrors the Java UI feature from PR #126 (OurGiant/aws-idp-saml-ui).
"""

import configparser
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add the script's directory to sys.path so we can import the existing modules
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import AWS
import Config
import Login
import Password
from Logging import Logging

log_stream = Logging('batch_auth')


def load_profile_identity(aws_dir: Path, profiles: list[str]) -> dict[str, dict]:
    """
    Load profile config and return identity info for grouping.
    Returns dict of profile_name -> {saml_provider, username, account_number, iam_role, aws_region, session_duration, ...}
    """
    config = configparser.ConfigParser()
    config.read(str(aws_dir / "samlsts"))

    # Read global defaults
    global_username = None
    global_provider = None
    global_region = "us-east-1"
    global_duration = 14400

    if config.has_section("global"):
        global_username = config.get("global", "username", fallback=None)
        global_provider = config.get("global", "samlprovider", fallback=None)
        global_region = config.get("global", "awsregion", fallback="us-east-1")
        dur = config.get("global", "sessionduration", fallback=None)
        if dur:
            try:
                global_duration = int(dur)
            except ValueError:
                pass

    profile_info = {}
    for profile in profiles:
        if not config.has_section(profile):
            continue

        section = config[profile]
        saml_provider = section.get("samlprovider", fallback=global_provider)
        username = section.get("username", fallback=global_username)
        account_number = section.get("accountnumber", fallback=None)
        iam_role = section.get("iamrole", fallback=None)
        aws_region = section.get("awsregion", fallback=global_region)
        gui_name = section.get("guiname", fallback=None)
        dur = section.get("sessionduration", fallback=None)
        session_duration = int(dur) if dur else global_duration

        if not saml_provider or not account_number or not iam_role:
            log_stream.warning(f"Skipping profile {profile}: missing provider/account/role")
            continue

        # Build ARNs
        provider_name = saml_provider.split("-", 1)[1] if "-" in saml_provider else saml_provider
        role_arn = f"arn:aws:iam::{account_number}:role/{iam_role}"
        principal_arn = f"arn:aws:iam::{account_number}:saml-provider/{provider_name}"

        profile_info[profile] = {
            "saml_provider": saml_provider,
            "username": username,
            "account_number": account_number,
            "iam_role": iam_role,
            "aws_region": aws_region,
            "session_duration": session_duration,
            "role_arn": role_arn,
            "principal_arn": principal_arn,
            "gui_name": gui_name,
        }

    return profile_info


def group_by_identity(profile_info: dict[str, dict]) -> dict[tuple, list[str]]:
    """Group profiles by (samlProvider, username) for shared login."""
    groups = defaultdict(list)
    for profile, info in profile_info.items():
        key = (info["saml_provider"], info["username"])
        groups[key].append(profile)
    return dict(groups)


def perform_batch_auth(
    profiles: list[str],
    use_fastpass: bool = False,
    use_debug: bool = False,
    show_encrypted: bool = False,
    status_callback=None,
) -> dict[str, bool]:
    """
    Authenticate multiple profiles with shared SAML login.

    Groups profiles by (samlProvider, username), performs one browser login per group,
    then assumes roles for all profiles in the group using the same assertion.

    Returns dict of profile_name -> success (bool).
    """
    aws_dir = Path.home() / ".aws"
    config_obj = Config.Config()
    results = {}

    # Load profile identity info
    profile_info = load_profile_identity(aws_dir, profiles)

    missing = [p for p in profiles if p not in profile_info]
    if missing:
        for p in missing:
            if status_callback:
                status_callback(f"SKIP", p, "Missing or incomplete config")
            results[p] = False

    # Group by shared identity
    groups = group_by_identity(profile_info)

    if status_callback:
        status_callback("INFO", None, f"Batch auth: {len(profiles)} profiles in {len(groups)} login group(s)")

    # Get password once for all groups
    pass_key, pass_file = config_obj.return_stored_pass_config()
    password = Password.retrieve_password(pass_key, pass_file)

    for (saml_provider, username), group_profiles in groups.items():
        provider_name = saml_provider.split("-", 1)[1] if "-" in saml_provider else saml_provider

        if status_callback:
            status_callback("LOGIN", None, f"Logging in as {username} via {provider_name} for {len(group_profiles)} profile(s)")

        # Read provider config for login URL
        samlsts_config = configparser.ConfigParser()
        samlsts_config.read(str(aws_dir / "samlsts"))

        try:
            first_page = samlsts_config.get(saml_provider, "loginpage")
            idp_login_title = samlsts_config.get(saml_provider, "logintitle").replace('"', '')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            log_stream.critical(f"Provider config error for {saml_provider}: {e}")
            for p in group_profiles:
                results[p] = False
                if status_callback:
                    status_callback("FAIL", p, f"Provider config error: {e}")
            continue

        # Check for DSSO URL
        try:
            dsso_url = samlsts_config.get(saml_provider, "dssourl")
        except (configparser.NoSectionError, configparser.NoOptionError):
            dsso_url = None

        # Get browser type
        browser_type = samlsts_config.get("global", "browser", fallback="chrome")

        # Perform ONE browser login for the group
        saml_response = Login.browser_login(
            username=username,
            password=password,
            first_page=first_page,
            use_debug=use_debug,
            use_gui=False,
            browser=browser_type,
            saml_provider_name=provider_name,
            idp_login_title=idp_login_title,
            iam_role=profile_info[group_profiles[0]]["iam_role"],
            gui_name=profile_info[group_profiles[0]].get("gui_name"),
            dsso_url=dsso_url,
            use_okta_fastpass=use_fastpass,
        )

        # Check if login succeeded
        if len(saml_response) < 50:
            log_stream.critical(f"Login failed for group ({provider_name}/{username}): {saml_response}")
            for p in group_profiles:
                results[p] = False
                if status_callback:
                    status_callback("FAIL", p, f"Login failed: {saml_response}")
            continue

        log_stream.info(f"SAML assertion captured ({len(saml_response)} bytes), assuming roles for {len(group_profiles)} profile(s)")

        # Assume role for each profile in the group using the shared assertion
        for profile in group_profiles:
            info = profile_info[profile]

            try:
                sts_response = AWS.STS.aws_assume_role(
                    region=info["aws_region"],
                    role=info["role_arn"],
                    principle=info["principal_arn"],
                    saml_assertion=saml_response,
                    duration=info["session_duration"],
                )

                aws_access_id, aws_secret_key, aws_session_token, sts_expiration = \
                    AWS.STS.get_sts_details(sts_response)

                if Config.validate_aws_cred_format(aws_access_id, aws_secret_key, aws_session_token):
                    config_obj.write_aws_config(
                        aws_access_id, aws_secret_key, aws_session_token,
                        profile, info["aws_region"], info["account_number"], True
                    )
                    results[profile] = True

                    if status_callback:
                        status_callback("OK", profile, f"Expires {sts_expiration.strftime('%H:%M:%S')}")

                    if show_encrypted:
                        try:
                            import Utilities
                            encrypted = Utilities.encrypt_credentials(aws_access_id, aws_secret_key, aws_session_token)
                            print(f"\nEncrypted Credentials ({profile}):\n{encrypted}\n")
                        except Exception:
                            pass
                else:
                    results[profile] = False
                    if status_callback:
                        status_callback("FAIL", profile, "Invalid credential format from STS")

            except SystemExit:
                results[profile] = False
                if status_callback:
                    status_callback("FAIL", profile, "AssumeRoleWithSAML failed")
            except Exception as e:
                results[profile] = False
                if status_callback:
                    status_callback("FAIL", profile, str(e))

    return results
