# coding=utf-8
# standard library imports
import getpass
import os
import sys
import stat
from datetime import datetime

# third-party imports
from cryptography.fernet import Fernet, InvalidToken

from Logging import Logging

log_stream = Logging('password')

def check_store_perms(pass_key):
    """
    Check the permissions on the directory containing the password store file.
    Enforces strict 0700 (rwx------) permissions - owner only.

    Args:
        pass_key (str): The path to the password store file.

    Raises:
        SystemExit: If the permissions on the directory are too permissive.

    Returns:
        None.
    """
    key_path = os.path.dirname(pass_key)
    st = os.stat(key_path)
    mode = stat.S_IMODE(st.st_mode)
    
    # Strict permission check: only owner should have rwx (0o700)
    required_perms = 0o700
    
    if mode != required_perms:
        log_stream.warning(f'Fixing insecure permissions on {key_path}')
        try:
            os.chmod(key_path, required_perms)
            log_stream.info(f'Directory permissions corrected to 0700 (owner only)')
        except OSError as e:
            log_stream.fatal(f'Unable to fix directory permissions: {str(e)}')
            raise SystemExit(1)


def check_file_perms(file_path):
    """
    Check and enforce strict file permissions (0600 - owner read/write only).

    Args:
        file_path (str): Path to the file to check.

    Returns:
        None
    """
    if os.path.exists(file_path):
        st = os.stat(file_path)
        mode = stat.S_IMODE(st.st_mode)
        required_perms = 0o600
        
        if mode != required_perms:
            log_stream.warning(f'Fixing insecure permissions on {file_path}')
            try:
                os.chmod(file_path, required_perms)
                log_stream.info(f'File permissions corrected to 0600 (owner only)')
            except OSError as e:
                log_stream.fatal(f'Unable to fix file permissions: {str(e)}')
                raise SystemExit(1)


"""
Function: get_password
-----------------------
This function prompts the user to enter a password and returns the entered password. If the entered password is empty,
the function will prompt the user to enter the password again until a non-empty password is entered.

Returns:
- password (str): the entered password
"""


def get_password():
    password = getpass.getpass(prompt='Enter password: ')
    while len(password) == 0:
        password = getpass.getpass(prompt='Password cannot be empty. Enter password: ')
    return password


def check_password_status(pass_file, pass_key):
    """
    Check the age of a password file and prompt the user to create a new one if it's too old.

    Args:
        pass_file (str): Path to the password file.
        pass_key (str): Path to the key file.

    Returns:
        None
    """
    # Get the creation time of the password file and calculate its age
    pass_file_stats = os.stat(pass_file)
    pass_file_age = int(pass_file_stats.st_ctime)
    timestamp_now = int(datetime.now().timestamp())
    pass_created = timestamp_now - pass_file_age

    # Log the age of the password file
    log_stream.info('Password file age: ' + str(pass_created))

    # If the password file is too old, delete it and prompt the user to create a new password
    if pass_created > 84600:
        # Remove the file, or Windows won't be able to create a new one
        try:
            os.remove(pass_file)
        except OSError as remove_file_error:
            log_stream.critical('Unable to delete password file: ' + str(remove_file_error))

        # Prompt the user to create a new password
        log_stream.warning('Your password file is too old. Reenter the password')
        password = get_password()
        store_password(password, pass_key, pass_file)


def generate_pass_store_key(pass_key):
    """
    Generate a Fernet key and store it in a key file.

    Args:
        pass_key (str): Path to the key file.

    Returns:
        bytes: The generated key.
    """
    # Generate a Fernet key
    key = Fernet.generate_key()

    # Write the key to the key file
    with open(pass_key, "wb") as key_file:
        key_file.write(key)

    # Return the generated key
    return key


def store_password(password, pass_key, pass_file):
    """
    Encrypt and store a password in a file using a key.

    Args:
        password (str): The password to encrypt and store.
        pass_key (str): Path to the key file.
        pass_file (str): Path to the password file.

    Returns:
        None
    """
    # Check if the key file is writeable
    check_store_perms(pass_key)

    # Try to reuse existing key if it exists and is valid
    key = None
    if os.path.exists(pass_key):
        try:
            with open(pass_key, "rb") as key_file:
                existing_key = key_file.read()
            # Test if the key is valid by attempting to create a Fernet instance
            Fernet(existing_key)
            key = existing_key
            log_stream.debug('Reusing existing encryption key')
        except (FileNotFoundError, ValueError, InvalidToken):
            log_stream.debug('Existing key is invalid, generating new key')
    
    # Generate or retrieve the key from the key file
    if key is None:
        key = generate_pass_store_key(pass_key)
    
    # Set strict permissions on key file (owner read/write only)
    check_file_perms(pass_key)

    # Encode the password to bytes using UTF-8 encoding
    encoded_pass = password.encode()

    # Create a Fernet object with the key
    f = Fernet(key)

    # Encrypt the password using the Fernet object
    encrypted_pass = f.encrypt(encoded_pass)

    # Write the encrypted password to the password file
    with open(pass_file, "wb") as pass_file_handle:
        pass_file_handle.write(encrypted_pass)
    
    # Set strict permissions on password file (owner read/write only)
    check_file_perms(pass_file)

    return


def retrieve_password(pass_key, pass_file):
    """
    Retrieve a password from an encrypted file using a key.

    Args:
        pass_key (str): Path to the key file.
        pass_file (str): Path to the encrypted password file.

    Returns:
        str: The decrypted password.
    """
    try:
        check_password_status(pass_file, pass_key)
        with open(pass_key, "rb") as pass_key_handle:
            key = pass_key_handle.read()

        with open(pass_file, "rb") as pass_file_handle:
            encrypted_pass = pass_file_handle.read()

    except FileNotFoundError as no_password_file_error:
        log_stream.warning('No password found. A new pass store will be created')
        log_stream.warning(str(no_password_file_error))
        password = get_password()
        store_password(password, pass_key, pass_file)
        return password

    try:
        f = Fernet(key)
        decrypted_pass = f.decrypt(encrypted_pass)
        return decrypted_pass.decode()
    except InvalidToken as invalid_key_error:
        log_stream.critical('Your key is invalid: ' + str(invalid_key_error))
        password = get_password()
        generate_pass_store_key(pass_key)
        store_password(password, pass_key, pass_file)
        return password
