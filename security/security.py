from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization
import os
import secrets
import base64

def gen_assymetric_key():
    """ Generate a pair of assymetric key (private and public), using RSA algorithm.

    :return: a tuple of private and public key"""

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_key, public_key


def sign_message(message, private_key):
    """ Sign a message using the private key.
    
    :param message: the message to sign
    :param private_key: the private key to use
    
    :return: the signature of the message"""

    message = message.__repr__().encode('utf-8')

    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(message)
    msg_digest = digest.finalize()

    signature = private_key.sign(
        msg_digest,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return signature.hex()


def verify_signature(message, signature, public_key):
    """ Verify the signature of a message using the public key.
    
    :param message: the message
    :param signature: the signature of the message
    :param public_key: the public key to use
    
    :return: True if the signature is valid, False otherwise"""

    signature = bytes.fromhex(signature)
    message = message.__repr__().encode('utf-8')
    public_key = serialization.load_pem_public_key(public_key.encode('utf-8'), backend=default_backend())

    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(message)
    msg_digest = digest.finalize()

    try:
        public_key.verify(
            signature,
            msg_digest,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


def gen_symmetric_key():
    """ Generate a symmetric key, using AES algorithm.

    :return: the symetric key"""

    salt = os.urandom(32)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    password = secrets.token_hex(16) 
    key = kdf.derive(password.encode())

    return key


def encrypt_number(number, key):
    """
    Encrypt a number using the symetric key.
    
    :param number: the number to encrypt
    :param key: the symetric key to use
    
    :return: the encrypted number
    """

    iv = os.urandom(16)
    if not isinstance(number, bytes):
        number_bytes = number.to_bytes(64, byteorder='big')
    else:
        number_bytes = number
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(number_bytes) + encryptor.finalize()
    return iv+ct

def decrypt_number(encrypted_number, key, flag=0):
    """
    Decrypt a number using the symetric key.
    
    :param encrypted_number: the encrypted number
    :param key: the symetric key to use
    :param flag: if 1, return the decrypted number as an integer, else return the decrypted number as bytes
    
    :return: the decrypted number
    """
    iv = encrypted_number[:16]
    encrypted_number = encrypted_number[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    pt = decryptor.update(encrypted_number) + decryptor.finalize()
    if flag:
        pt = int.from_bytes(pt, byteorder='big')
    return pt


def main():
    pass


if __name__ == "__main__":
    main()