
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os
from pathlib import Path

# User's dotaws directory is a safe location to store keys
home = str(Path.home())
AWSRoot = home + "/.aws/"
public_key_file = AWSRoot + "public_key.pem"
private_key_file = AWSRoot + "private_key.pem"

# Generate keys
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# make a config directory if it does not exist. this will be used to save the keys
if not os.path.exists("config"):
    os.makedirs("config")

# Save the private key
with open(private_key_file, "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))
# Save the public key
with open(public_key_file, "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))