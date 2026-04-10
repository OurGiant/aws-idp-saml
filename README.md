# AWS IDP-SAML Token Utility

Log into your Identity Provider (IdP) via a headless browser, retrieve a SAML assertion, and use it to assume an AWS IAM role. The resulting temporary credentials are written to `~/.aws/credentials` for use with the AWS CLI and SDKs.

## Table of Contents

- [What You Need Before You Start](#what-you-need-before-you-start)
- [Installation](#installation)
  - [Python and Virtual Environment](#python-and-virtual-environment)
  - [Dependencies](#dependencies)
  - [Browser Drivers](#browser-drivers)
  - [macOS Quarantine Fix](#macos-quarantine-fix)
- [Configuration](#configuration)
  - [First Run (No Config File)](#first-run-no-config-file)
  - [Manual Configuration](#manual-configuration)
  - [Provider Section](#provider-section)
  - [Profile Sections](#profile-sections)
  - [Global Section](#global-section)
  - [Account Aliases](#account-aliases)
- [Usage](#usage)
  - [Text Menu Mode](#text-menu-mode)
  - [Profile Mode](#profile-mode)
  - [What Happens When You Run It](#what-happens-when-you-run-it)
- [CLI Reference](#cli-reference)
- [Security](#security)
- [Advanced](#advanced)
  - [Credential Encryption](#credential-encryption)
  - [Screenshot Recording](#screenshot-recording)
  - [Shell Shortcuts](#shell-shortcuts)
  - [Docker](#docker)
  - [Additional Identity Providers](#additional-identity-providers)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## What You Need Before You Start

Before installing, gather the following from your IdP administrator:

1. The SAML login URL for the AWS application in your IdP (e.g., `https://login.company.com/app/amazon_aws/exk123456789/sso/saml`)
2. The HTML page title shown on the IdP login page (e.g., `Company - Sign In`)
3. Your IdP username

You will also need:

- [Python 3.12+](https://www.python.org/downloads/)
- Chrome, Firefox, or Edge installed on your system
- The corresponding browser driver (the utility will attempt to download this for you)

## Installation

### Python and Virtual Environment

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/OurGiant/aws-idp-saml.git
cd aws-idp-saml
python -m venv venv
```

Activate the virtual environment:

Linux / macOS:
```bash
source venv/bin/activate
```

Windows (PowerShell):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\activate
```

### Dependencies

Using Poetry (preferred):
```bash
poetry install
poetry update
```

Or using pip:
```bash
pip3 install -r requirements.txt
```

If you need to install Poetry, see the [Poetry documentation](https://python-poetry.org/docs/).

### Browser Drivers

The utility will attempt to download the correct driver for your chosen browser automatically. If you prefer to install manually:

- Chrome: download from [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)
- Firefox: download from [geckodriver releases](https://github.com/mozilla/geckodriver/releases)
- Edge: download from [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)

Place the driver in the `drivers/` directory at the root of the project. On Windows, drivers have the `.exe` extension. On macOS and Linux they do not.

Chromium may not be fully supported by the Chrome driver. If you only have Chromium installed, reference the browser as `chrome`.

### macOS Quarantine Fix

macOS may block downloaded drivers with a security warning. Remove the quarantine attribute:

```bash
xattr -d com.apple.quarantine drivers/chromedriver
```

This also works for `geckodriver`.

## Configuration

The utility reads its configuration from `~/.aws/samlsts`. This is an INI-style file with three types of sections: a provider section, profile sections, and an optional global section.

### First Run (No Config File)

If no config file exists, the utility will walk you through creating one. Run:

```bash
python getCredentials.py --textmenu
```

You will be prompted for:
- Your Identity Provider name (currently supported: `okta`)
- The SAML login URL for the AWS application
- The HTML title of the login page

The utility creates `~/.aws/samlsts` with a provider section and sets secure file permissions (0600). On subsequent runs, it will also build `~/.aws/account-map.json` as you access different accounts.

### Manual Configuration

Copy the demo file and edit it:

Linux / macOS:
```bash
cp samlsts.demo ~/.aws/samlsts
chmod 600 ~/.aws/samlsts
```

Windows:
```powershell
Copy-Item -Path .\samlsts.demo -Destination $HOME\.aws\samlsts
```

### Provider Section

At minimum, the config file needs one provider section. The section name must be prefixed with `Fed-` followed by the IdP name in uppercase.

```ini
[Fed-OKTA]
loginpage=https://login.company.com/app/amazon_aws/exk123456789/sso/saml
loginTitle=Company - Sign In
```

Parameters:
- `loginpage` - The SAML login URL provided by your IdP administrator
- `loginTitle` - The HTML title displayed on the login page

### Profile Sections

Profile sections define specific AWS accounts and roles to assume. These are used with `--profilename` for repeat access without the text menu.

```ini
[cloud1-production]
awsRegion = us-east-1
accountNumber = 123456123456
IAMRole = OKTA-Architect
samlProvider = Fed-OKTA
username = your.username
guiName = production
sessionDuration = 14400
```

Parameters:
- `awsRegion` - AWS region for API calls
- `accountNumber` - The AWS account number
- `IAMRole` - The IAM role to assume after login
- `samlProvider` - Must match a provider section name (e.g., `Fed-OKTA`)
- `username` - Your IdP username
- `guiName` - Account alias as shown in the SAML response
- `sessionDuration` - Token lifetime in seconds (max set by your AWS administrator)

### Global Section

Optional defaults that apply to all sessions. These are overridden by profile sections or command line arguments.

```ini
[global]
browser = firefox
sessionDuration = 14400
savedPassword = true
username = your.username
awsRegion = us-east-1
```

### Account Aliases

To display friendly account names instead of numbers in the text menu, create `~/.aws/account-map.json`:

```json
[
    {"name": "productline-db", "number": "123456123456"},
    {"name": "productline-app", "number": "123412341234"}
]
```

This file is also built automatically as you access accounts through the text menu.

## Usage

### Text Menu Mode

Browse all available roles from your SAML response and pick one interactively:

```bash
python getCredentials.py --textmenu --idp okta --browser chrome
```

You will be prompted for your password, then presented with a table of available roles:

```text
╒══════╤══════════════════╤═══════════════════════╕
│   Id │   Account Number │ Role Name             │
╞══════╪══════════════════╪═══════════════════════╡
│    0 │     123456123456 │ DataBaseAdmin         │
├──────┼──────────────────┼───────────────────────┤
│    1 │     123456123456 │ Infrastructure        │
├──────┼──────────────────┼───────────────────────┤
│    2 │     123412341234 │ NOCSupport            │
╘══════╧══════════════════╧═══════════════════════╛
Enter the Id of the role to assume:
```

### Profile Mode

Once you have a profile section in your config file, assume a specific role directly:

```bash
python getCredentials.py --profilename cloud1-production --browser chrome
```

### What Happens When You Run It

1. A headless browser opens and navigates to your IdP login page
2. Your credentials are entered and MFA is triggered (push notification or Okta FastPass)
3. The SAML assertion is captured from the AWS sign-in page
4. `sts:AssumeRoleWithSAML` is called to get temporary credentials
5. Credentials are written to `~/.aws/credentials` under the profile name
6. The profile name, region, and account are printed to the console

On managed devices where Okta pre-authenticates the user, the utility will automatically detect the MFA screen and skip username/password entry.

## CLI Reference

| Flag | Type | Description |
|------|------|-------------|
| `--profilename` | str | AWS profile name matching a section in `~/.aws/samlsts` |
| `--textmenu` | bool | Interactive role selection from SAML response |
| `--idp` | str | Identity Provider. Choices: `okta` |
| `--browser` | str | Browser to use. Choices: `chrome`, `firefox`, `edge` |
| `--username` | str | IdP username (required for text menu if not in config) |
| `--region` | str | AWS region. Choices: `us-east-1`, `us-east-2`, `us-west-1`, `us-west-2` |
| `--duration` | str | Session duration in seconds (limited by AWS admin settings) |
| `--storedpw` | bool | Use a previously stored password |
| `--gui` | bool | Open AWS Console in a browser after login. Cannot combine with `--textmenu` |
| `--debug` | bool | Show the browser window during the login process |
| `--fastpass` | bool | Use Okta FastPass for MFA (not available on Linux) |
| `--encrypted` | bool | Generate an encrypted credentials string (requires key pair, see [Credential Encryption](#credential-encryption)) |
| `--show-credentials` | bool | Print AWS credentials to the console in plaintext (disabled by default) |
| `--enable-screenshots` | bool | Save screenshots at each login step |
| `--screenshot-dir` | str | Directory for screenshots (default: `screenshots/{timestamp}`) |

Flags marked `bool` are off by default and enabled by including them on the command line.

## Security

The utility enforces secure file permissions on all sensitive files:

- `~/.aws/` directory: `0700` (owner only)
- Credentials, config, and key files: `0600` (owner read/write only)
- Password store directory: `0700` (owner only)

Credentials are not printed to the console by default. Use `--show-credentials` to explicitly display them.

Stored passwords are encrypted using Fernet symmetric encryption and expire after 24 hours.

## Advanced

### Credential Encryption

To encrypt credentials for transfer to another system, first generate an RSA key pair:

```bash
python keygen.py
```

You will be prompted for a passphrase to protect the private key. Keys are saved to `~/.aws/public_key.pem` and `~/.aws/private_key.pem` with appropriate file permissions.

Then use the `--encrypted` flag when running the utility:

```bash
python getCredentials.py --profilename my-profile --browser chrome --encrypted
```

### Screenshot Recording

Enable screenshot capture at each step of the login process for debugging:

```bash
python getCredentials.py --textmenu --idp okta --browser chrome --enable-screenshots
```

Screenshots are saved to `screenshots/{timestamp}/` by default. Use `--screenshot-dir` to specify a custom directory.

### Shell Shortcuts

Setting up a shell alias lets you run the utility from any directory without activating the virtual environment manually.

Both examples below accept a profile name and pass any additional flags through, so you can use them like:

```
getsaml my-profile --storedpw --debug
getsaml my-profile --storedpw --duration 14400 --region us-west-2
```

#### PowerShell 7

Create a profile file if you don't have one, then open it:

```powershell
New-Item -ItemType File -Path $PROFILE -Force
notepad $PROFILE
```

Add the function:

```powershell
function getsaml {
    param (
        [string]$profilename,
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$extraArgs
    )
    Push-Location .
    Set-Location [REPO CLONE LOCATION]
    & "venv\Scripts\activate"
    $cmd = "py getCredentials.py --profilename $profilename " + ($extraArgs -join " ")
    Invoke-Expression $cmd
    deactivate
    Pop-Location
}
```

Open a new PowerShell window to load the updated profile.

If your organization uses a corporate certificate chain that Python doesn't trust by default, add `pip install pip-system-certs` to the function before the main command. This tells pip and requests to use the OS certificate store.

#### Bash

Add to `~/.bash_aliases` or `~/.bashrc`:

```bash
getsaml() {
    local saml_home='[REPO CLONE LOCATION]'
    local profilename="$1"
    shift
    source "${saml_home}/venv/bin/activate"
    python3 "${saml_home}/getCredentials.py" --profilename "${profilename}" "$@"
    deactivate
}
```

The `"$@"` passes all remaining arguments through, so any flag combination works.

### Tips

- Use `--storedpw` to avoid typing your password every time. The encrypted password is stored in `~/.aws/saml.pass` and expires after 24 hours.
- If you access many accounts, start with `--textmenu` to build up your `~/.aws/samlsts` and `~/.aws/account-map.json` files. Once populated, switch to `--profilename` for faster repeat access.
- The `--debug` flag opens a visible browser window so you can watch the login flow. Useful when troubleshooting MFA or page-load issues.
- On corporate networks with SSL inspection, Python may reject your IdP's certificate. Install `pip-system-certs` (`pip install pip-system-certs`) to use your OS trust store.
- If the Chrome driver version falls out of sync with your browser, the utility will attempt to download the correct version automatically.

### Docker

Example Dockerfiles are provided in the `docker/` directory. Notes:

- Ubuntu containers must use Firefox, installed as a debian package
- Most other distributions will install Chromium (reference the browser as `chrome`)
- Running the utility as a standalone Docker container requires mounting `~/.aws` at runtime, which may cause UID/permissions issues

### Additional Identity Providers

This utility currently supports Okta. The [original version](https://github.com/OurGiant/aws-ping-saml) supported PING.

To add support for another provider, implement a new static method in the `Providers.UseIdP` class that handles the login flow for your IdP. Please create a feature branch for contributions so it can be reviewed and integrated.

## Troubleshooting

If you have issues, please create an issue on the project: [https://github.com/OurGiant/aws-idp-saml/issues](https://github.com/OurGiant/aws-idp-saml/issues)

## Contributing

Create a branch with your suggested changes and open a pull request for review.

## Authors

- Ryan Leach

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Acknowledgments

Testing and contributions by: Craig Dobson, Tim Dady, Mary James, Basheer Shaik, Luis Langa
