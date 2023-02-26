# coding=utf-8
# standard library imports
import sys
import os
from datetime import datetime
import getpass

# third-party imports
from cryptography.fernet import Fernet, InvalidToken

from version import __version__
import Utilities

log_stream = Utilities.Logging('password')


def check_store_perms(pass_key):
    """
    Check the permissions on the directory containing the password store file.

    Args:
        pass_key (str): The path to the password store file.

    Raises:
        SystemExit: If the permissions on the directory are too permissive.

    Returns:
        None.

    """
    safe_perms = 0
    if sys.platform == 'win32':
        safe_perms = 16895
    if sys.platform == 'linux' or sys.platform == 'darwin':
        safe_perms = 16832
    key_path = os.path.dirname(pass_key)
    st = os.stat(key_path)
    mode = int(st.st_mode)
    if mode > safe_perms:
        log_stream.critical('Permissions on your store directory are too permissive. Please secure this directory from '
                            'reading by anyone other than the owner')
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
    key_file.close()

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

    # Generate or retrieve the key from the key file
    key = generate_pass_store_key(pass_key)

    # Encode the password to bytes using UTF-8 encoding
    encoded_pass = password.encode()

    # Create a Fernet object with the key
    f = Fernet(key)

    # Encrypt the password using the Fernet object
    encrypted_pass = f.encrypt(encoded_pass)

    # Write the encrypted password to the password file
    with open(pass_file, "wb") as pass_file_handle:
        pass_file_handle.write(encrypted_pass)
    pass_file_handle.close()

    # Return nothing
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
        pass_key_handle.close()

        with open(pass_file, "rb") as pass_file_handle:
            encrypted_pass = pass_file_handle.read()
        pass_file_handle.close()

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
