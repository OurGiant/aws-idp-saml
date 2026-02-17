
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption
import os
import sys
import signal
import stat
from pathlib import Path
from getpass import getpass


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('\n\nInterrupted by user. Exiting gracefully...')
    sys.exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# User's dotaws directory is a safe location to store keys
home = str(Path.home())
AWSRoot = home + "/.aws/"
public_key_file = AWSRoot + "public_key.pem"
private_key_file = AWSRoot + "private_key.pem"

# Ensure .aws directory exists with secure permissions
aws_dir = Path(AWSRoot)
aws_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

try:
    # Generate keys
    print("Generating RSA key pair (2048-bit)...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Prompt for passphrase to encrypt private key
    print("\nEnter a passphrase to encrypt your private key (leave blank for no encryption - NOT RECOMMENDED):")
    passphrase = getpass("Passphrase: ").encode() if getpass("Passphrase: ") else None

    # Save the private key with encryption
    print(f"Saving encrypted private key to {private_key_file}")
    with open(private_key_file, "wb") as f:
        encryption = BestAvailableEncryption(passphrase) if passphrase else serialization.NoEncryption()
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        ))

    # Set strict permissions on private key (owner read/write only)
    os.chmod(private_key_file, 0o600)

    # Save the public key
    print(f"Saving public key to {public_key_file}")
    with open(public_key_file, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    # Set permissions on public key (owner read/write, others read)
    os.chmod(public_key_file, 0o644)

    print("\nKey generation complete!")
    print(f"Private key: {private_key_file} (encrypted, 0600 permissions)")
    print(f"Public key: {public_key_file} (0644 permissions)")

except KeyboardInterrupt:
    print('\n\nInterrupted by user. Exiting gracefully...')
    sys.exit(0)