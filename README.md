# AWS IDP-SAML Token Utility

Log into your IdP and retrieve a SAML assertion for AWS. Use SAML assertion to assume an AWS role for use with SDK and CLI.

## Table of Contents
- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installing](#installing)
- - [Configuration](#configuration)
- - - [Lazy Configuration](#lazy-configuration)
- - - [Quick Start Configuration](#quick-start-configuration)
- - [Virtual Environment](#virtual-environment)
- - [Dependencies](#dependancies)
- - - [Using Poetry](#using-poetry--preferred-)
- - - [Using pip](#using-pip)
- - [MacOS Users Special Instructions](#macos-users-special-instructions)
- [Drivers](#drivers)
- [Usage](#usage)
- - [Configuration file](#configuration-file)
- - - [Providers Section](#providers-section)
- - - [Global Section](#global-section)
- - [Full Configuration mode](#full-configuration-mode)
- - [Text Menu mode](#text-menu-mode)
- - [Docker](#docker)
- - [Additional Indentity Providers](#additional-indentity-providers)
- [Installing Poetry](#installing-poetry)
- [Troubleshooting](#troubleshooting)
- [Known Issues](#known-issues)
- [To Do](#to-do)
- [System Information](#system-information)
- [Contributing](#contributing)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Getting Started

Clone this repository to your local system. The latest verstion will be tagged ***LATEST*** in GitHub.

### Prerequisites

- [Python3](https://www.python.org/download/releases/3.0/)
- Chrome or Filefox drivers specific to your operating system (see [Drivers](#drivers) section) (see [Known Issue](#known-issues) session)
- Python libraries from requirements.txt (see [Installing](#installing) section)

## Quick Start

```bash
python3 getCredentials.py --textmenu
```

## Installing

### Configuration 

See [Configuration File](#configuration-file) for details

#### Lazy Configuration

If you provide no configuration files at start up and use only the --textmenu flag at start up the utility will attempt to build and store configurations for you in the appropriate files. 
You can then reference these configurations in future runs. The more you use the utility for different accounts, the more complete your configurations will become.

Files built:
-  ***~/.aws/samlsts***
-  ***~/.aws/account-map.json***

If you want to configure the files head of the first run, follow the instructions found in this README


#### Quick Start Configuration
Linux
```bash
cp samlsts.demo ~/.aws/samlsts
chmod 700 ~/.aws/
```

Windows
```powershell
Copy-Item -Path .\samlsts.demo -Destination $HOME\.aws\samlsts
```
These commands may need to be run from an Administrator shell, if the Set-Acl presents a permissions error.
If you do not already have the ***~/.aws*** directory you can create it with ```aws configure```, Mock values can be used to create a [default] profile.

### Virtual Environment
from the aws-idp-saml root:
linux: 
```bash
python -m venv venv
source venv/bin/activate
```

Windows:
```powershell
python -m venv venv
powershell Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\activate
```

#### Dependancies

There are two methods for installing dependencies, using pip to install the dependancies listed in requirements.txt, or using ***poetry*** to manage the python packages for the application


##### Using Poetry (preferred)
Install Poetry (see [Installing Poetry](#installing-poetry) )
Start your virtual environment prior to the poetry install (see [Virtual Environment](#virtual-environment))

```bash
  poetry install
  poetry update
```

##### Using pip
from the application root run:
```bash
  pip3 install -r requirements.txt
```


### MacOS Users Special Instructions

After downloading the webdriver to INSTALL_DIR/drivers you may experience a security warning when attempting to execute the utility. To fix this, execute the following

```bash
xattr -d com.apple.quarantine chromedriver
```

This example is for chromedriver, but will also work on geckodriver (firefox)

## Drivers

The application will attempt to install the driver for which ever browser you choose, if it is not already there. If you want to install the drivers ahead of time, do so manually.

If you are running this on macOS or Windows you will need to download the appropriate driver from <https://github.com/mozilla/geckodriver> or <https://chromedriver.chromium.org/downloads>.

The driver needs to be placed in the ***drivers*** directory. This directory is in the root of the utility directory. MacOS and Linux drivers do not have an extension, the latest Windows drivers for each have the '.exe' extension.

You must have either Chrome or Firefox installed on your system for this utility to function correctly. Chromium may not be supported in the Chrome driver. If you have only Chromium installed, reference the browser as "chrome"

The Chrome driver will attempt to update itself if the driver version is out of sync with the browser version

## Usage

### Configuration file

You may run the utility without first having an ***~/.aws/samlsts*** configuration file. The utility will attempt to create one for you by asking the following questions:

- What is the name of your provider? [PING,OKTA]
- What is the application login URL for your IdP? 
- What is the HTML title on the login page? 

With these answers it will create the file and add this provider section. 

You may also copy the ***samlsts.demo*** file from this repository into your ***~/.aws*** directory and rename it **samlsts**.

If you do not already have the ***~/.aws*** directory you can create it with ```aws configure```, Mock values can be used to create a [default] profile.

You do not need to define a [global](#global-section) section or [profile](#full-configuration-mode) sections. You may use the utility with --textmenu, --username, --idp, and --browser


#### Providers Section
The ***samlsts** configuration file will need to be configured with a minimum of one Identity Provider section. The name of the section must contain the prefix 'Fed' and the name of the IDP in uppercase letters.

***[Fed-PING]***

***[Fed-OKTA]***

The provider block must also contain the following parameters
- loginpage - This is the page provided by your IdP administrator which allows you direct access to the AWS application in your IdP
- loginTitle - This is the HTML title of the login page. 

```ini
[Fed-PING]
loginpage=https://login.company.com/idp/startSSO.ping?PartnerSpId=urn:amazon:webservices
loginTitle=Sign On
```

This utility supports PING and OKTA as Identity Providers. Additional identity providers can be configured, see [Additional Identity Providers](#additional-indentity-providers) for details.

#### Global Section
A 'global' parameters block can be added to the configuration file to store values otherwise provided on the command line. Settings specified in this section will be overriden by values in the profile blocks, or on the command line. 

```ini
[global]
browser=firefox
sessionDuration=14400
savedPassword=true
username=this.user
awsRegion=us-east-1
```


The utility can be run in either ***full-configuration*** mode using the **samlsts** configuration file in ~/.aws/ (see [Full Configuration](#full-configuration-mode) or using a text based menu (see [Text Based Menu](#text-menu-mode)) to specify which account to use.

### Full Configuration mode

- The profilename should match the profilename in brackets in the samlsts config file (see [Full Configuration](#full-configuration-mode) section for details).

***required parameters:***

```shell
python getCredentials.py --profilename PROFILENAME --browser BROWSER
```

```bash
Other options:

- `--region`: (type: str) the AWS profile name for this session, choices: ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
- `--storedpw`: (type: bool) use a stored password
- `--debug`: (type: bool) show browser during SAML attempt
- `--duration`: (type: str) desire token length, not to be greater than max length set by AWS administrator
- `--gui`: (type: bool) open the session in a browser as well

```

### Text Menu mode

***required parameters:***

```shell
python getCredentials.py --textmenu --idp IDPNAME --browser [chrome|firefox]
```

```bash
Other options:

  - `--username:` (type: bool) username for logging into SAML provider, required for text menu
  - `--region`: (type: str) the AWS profile name for this session, choices: ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
  - `--duration`: (type: str) desire token length, not to be greater than max length set by AWS administrator
  - `--storedpw`: (type: bool) use a stored password
  - `--debug`: (type: bool) show browser during SAML attempt

```

See 


### All runtime options

***some may not be combined***

```bash
    `--username:` (type: bool) username for logging into SAML provider, required for text menu
    `--profilename`: (type: str) the AWS profile name for this session
    `--region`: (type: str) the AWS profile name for this session, choices: ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
    `--idp`: (type: str) Id Provider, choices: ['okta', 'ping']
    `--duration`: (type: str) desire token length, not to be greater than max length set by AWS administrator
    `--browser`: (type: str) your browser of choice
    `--storedpw`: (type: bool) use a stored password
    `--gui`: (type: bool) open the session in a browser as well
    `--textmenu`: (type: bool) display text menu of accounts. cannot be used with gui option
    `--debug`: (type: bool) show browser during SAML attempt
```

### Browser Driver Information

This utility makes use of [Selinium](#prerequisites) to run a headless browser session for login. 

The along with adding the aws credentials in the ***~/.aws/credentials*** file, the [gui option](#all-runtime-options) will open a browser with the AWS Console for the profile name selected. This shouldn't be used for long-term operations as the geckodriver browser is not known for speed. This is a quick way to gt a console session while still getting CLI credentials.

The debug option opens a browser window just before log in allowing the user to track activity then closes once the token is recieved. This a fully interactive browser window.

### Shell Shortcuts

#### Linux

a function alias can be added to .bash_aliases that allows the user to quickrun the utility. Alter the alias if you ae using a python virtual environment

```bash
  getsaml() {
    saml_home='[REPO CLONE LOCATION]'
    profilename=$1
    used_stored_password=$2
    use_debug=$3
    if [ $use_debug ] 
    then
      echo "Use stored password and debug";  /usr/bin/python3 ${saml_home}/getCredentials.py --duration 14400 --browser firefox --profilename ${profilename} --storedpw --region us-east-1 --debug 
    elif [ $used_stored_password ]
    then
      echo "Use stored password";  /usr/bin/python3 ${saml_home}/getCredentials.py --duration 14400 --browser firefox --profilename ${profilename} --storedpw --region us-east-1 
    else
      /usr/bin/python3  ${saml_home}/getCredentials.py --profilename ${profilename} --duration 14400 --browser firefox --region us-east-1
    fi
  }
```

To use aws profile name ***my-profile-name*** with a stored password and debugging off

```bash
getsaml my-profile-name yes
```

#### Powershell

Powershell 7 only instructions

If you do not already have a profile file for your Windows account create one
```powershell
New-Item -ItemType File -Path $PROFILE -Force
```

Open the file in the editor of your choice
```powershell
notepad $PROFILE
```

Add the alias and save the file
```powershell
function getsaml {
    Push-Location .
	Set-Location C:\Users\ryanm\Projects\aws-idp-saml
	Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
	& "venv\Scripts\activate"
    python .\getCredentials.py --textmenu --idp ping --browser chrome
    deactivate
    Pop-Location
}

function getsaml($profilename) {
    Push-Location .
	Set-Location C:\Users\ryanm\Projects\aws-idp-saml
	Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
	& "venv\Scripts\activate"
    python getCredentials.py --profilename companyA-admin --browser chrome --storedpw
	deactivate
    Pop-Location
}
```

Open a new powershell window to load the latest profile settings.

## Full Configuration Mode

To use Full Configuration mode, by specifying a profile name on the command line, a profile configuration block must be added to ***~/.aws/*****samlsts**.

Configuration parameters are:

- **awsRegion** used in boto3 calls during utility execution
- **accountNumber** used to build the principle and role arns
- **IAMRole** role to assume after logging in
- **samlProvider** IdP used to provide authentication. Must match IdP name from IdP configuration block
- **username** the username used to log into IdP
- **guiName** AWS account alias as displayed in the SAML response
- **sessionDuration** how long to persist the credentials once the role is assumed



***example:***

```bash
[cloud1-blackbox]
awsRegion = us-east-1
accountNumber = 123456123456
IAMRole = PING-Architect
samlProvider = Fed-PING
username=idp.username
guiName=company-blackbox
sessionDuration=14400
```

## Text Menu Mode

In text menu mode, you presented with a list of accounts from which to choose a role to assume. 
By default, the list will include the selector ID, the Account Number and the Role Name.

Choose which role you want to assume and type it into the prompt.

```
╒══════╤══════════════════╤═══════════════════════╕
│   Id │   Account Number │ Role Name             │
╞══════╪══════════════════╪═══════════════════════╡
│    0 │     123456123456 │ DataBaseAdmin         │
├──────┼──────────────────┼───────────────────────┤
│    1 │     123456123456 │ Infrastructure        │
├──────┼──────────────────┼───────────────────────┤
│    2 │     123412341234 │ NOCSupport            │
├──────┼──────────────────┼───────────────────────┤
...
├──────┼──────────────────┼───────────────────────┤
│   10 │     180055512120 │ Administrator         │
├──────┼──────────────────┼───────────────────────┤
│   11 │     180055512120 │ DevOps                │
├──────┼──────────────────┼───────────────────────┤
│   12 │     113058675309 │ BackupAdministrator   │
├──────┼──────────────────┼───────────────────────┤
│   13 │     160016001600 │ Operations            │
╘══════╧══════════════════╧═══════════════════════╛
Enter the Id of the role to assume: 

```

You can configure an account alisas to account number JSON map in ***~/.aws/account-map.json*** using the example below.
This file will also be built for you by running the application. The more accounts you access the larger the map will become.

```json
[
	{
		"name": "productline-db",
		"number": "123456123456"
	}, {
		"name": "productline-app",
		"number": "123412341234"
	}, {
		"name": "company-coderepo",
		"number": "180055512120"
	}
]
```

This will display the account aliases in the text menu list, rather than numbers. If you have a large number of accounts, this will make selecting the correct one easier. 

```
╒══════╤══════════════════╤═══════════════════════╕
│   Id │   Account Name   │ Role Name             │
╞══════╪══════════════════╪═══════════════════════╡
│    0 │   productline-db │ DataBaseAdmin         │
├──────┼──────────────────┼───────────────────────┤
│    1 │  productline-app │ Infrastructure        │
├──────┼──────────────────┼───────────────────────┤
│    2 │ productline-logs │ NOCSupport            │
├──────┼──────────────────┼───────────────────────┤
...
├──────┼──────────────────┼───────────────────────┤
│   10 │   company-master │ Administrator         │
├──────┼──────────────────┼───────────────────────┤
│   11 │ company-coderepo │ DevOps                │
├──────┼──────────────────┼───────────────────────┤
│   12 │disaster-recovery │ BackupAdministrator   │
├──────┼──────────────────┼───────────────────────┤
│   13 | productB-monitor │ Operations            │
╘══════╧══════════════════╧═══════════════════════╛
Enter the Id of the role to assume: 

```

### Docker

This utility should be considered "container friendly". There are example docker files in the ***docker** directory which demonstrate how a user could set up their container to run the utility along side whatever other application they are going to deploy in the container. These docker files were tested and are known to be working.

- ubuntu container must use firefox, installed as a debian package
- most other distributions will install Chromium and reference the browser as Chrome
- running the utility AS a docker container with docker run is possible, allthough in order to do so you would need to mount your ~/.aws directory at runtime and this could cause UID/permissions issues. This was tested and determined not to be a high priority use case.   


## Additional Indentity Providers

The [original version](https://github.com/OurGiant/aws-ping-saml) of this utility was written to allow users to obtain STS credentials where there was a fixed IdP, PING. A need to accomodate an additional IdP was found and that lead to the development changes which resulted in this iteration of the utilitiy.

There are many Identity Providers on the market:

- Auth0 (now Okta)
- Microsoft Azure Active Directory
- OneLogin
- Google Cloud Identity
- AWS Identity and Access Management (IAM)
- ForgeRock
- IBM Security Access Manager
- Salesforce Identity
- RSA SecurID Access
- Centrify

Each of these providers has a specific way to log in, which triggers the AWS SAML page. Without access to these providers, 
I am unable to offer development support. If you would like to use this utility for a provider not already supported, 
you can add your provider's steps in the Providers.UseIdP() class. 
I would ask that if possible, create a feature branch for your additions, so it can be integrated with the main branch.

## Installing Poetry

Documentation:  [https://python-poetry.org/docs/](https://python-poetry.org/docs/)
Follow the installation instructions for your operating system found in the documentation

Either add the poetry bin location to your path as provided in the installation output. 

In Windows the executable is $Env:APPDATA\Python\Scripts\poetry.exe
In Linux the executable is ~/.local/bin/poetry

## Troubleshooting

If you have issues please create an issue on the project for review. [https://github.com/OurGiant/aws-idp-saml/issues](https://github.com/OurGiant/aws-idp-saml/issues)

## Known Issues

## To Do
- check and pull the latest chrome driver
- better table layout for textmenu

## System Information

The utility was developed on Windows and Linux, with testing support provided by users on macOS.

## Contributing

create a branch with your suggested updated and create a pull request for review

## Versioning

version 1.0

previously version 1.5 of aws-ping-saml project

## Authors

- Ryan Leach

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Acknowledgments

***testing and contributions made by:***

- Craig Dobson
- Tim Dady
- Mary James
- Basheer Shaik
- Luis Langa