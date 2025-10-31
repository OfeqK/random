# found this library that does RSA and AES automatically: https://cryptography.io/en/latest/
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives import serialization


def generate_RSA_keys() -> (rsa.RSAPrivateKey, rsa.RSAPublicKey):
    """
    Generates both private and public keys to be used in RSA algorithm.
    Uses e = 65537, and key_size = 2048  (as recommended)
    :return: A tuple: (private key, public key)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    return private_key, public_key



def serialize_public_RSA_key(public_key: rsa.RSAPublicKey) -> str:
    """
    Takes a public key object and returns a string representation (PEM format).
    :param: public_key: The public key to serialize
    :return: A string representation of the public key
    """
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError(f"public_key must be an RSAPublicKey.\n\tProvided: {public_key}")
    pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_bytes.decode('utf-8')


def deserialize_public_RSA_key(public_key_str) -> rsa.RSAPublicKey:
    """
    Takes a string representation of a public key and returns a public key object.
    :param: public_key_str: The string representation of the public key to deserialize
    :return: A string representation of the public key
    """
    pem_bytes = public_key_str.encode('utf-8')
    return serialization.load_pem_public_key(pem_bytes)


def encrypt_RSA(message: str, public_key: rsa.RSAPublicKey) -> bytes:
    """
    Encrypts the message using the provided public key.
    :param message: The message to be encrypted.
    :param public_key: The public key to encrypt with.
    :return: The encrypted message.
    """
    if not isinstance(message, str):
        raise TypeError(f"message must be a str.\n\tProvided: {message}")
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError(f"public_key must be an RSAPublicKey.\n\tProvided: {public_key}")

    cipher_text = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return cipher_text

def decrypt_RSA(cipher_text: bytes, private_key: rsa.RSAPrivateKey) -> str:
    """
    Decrypts the cipher_text using the provided private key.
    :param cipher_text: The cipher text to be decrypted.
    :param private_key: The private key to encrypt with.
    :return:
    """
    if not isinstance(cipher_text, (bytes, bytearray)):
        raise TypeError("cipher_text must be bytes")
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("private_key must be an RSAPrivateKey")

    plain_text = private_key.decrypt(
        cipher_text,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plain_text.decode()


def generate_AES_key() -> bytes:
    """
    Generates a 256-bit AES key.
    :return: The generates key
    """
    return os.urandom(32)

def serialize_AES_key(AES_key: bytes) -> str:
    """
    Takes an AES key (bytes) and returns a hex string for safe transport.
    """
    if not isinstance(AES_key, bytes):
        raise TypeError(f"AES encryption key must be of type bytes\n\tProvided: {AES_key}")
    return AES_key.hex()


def deserialize_AES_key(AES_key_str: str) -> bytes:
    """
    Takes a hex string and returns the AES key as bytes.
    """
    if not isinstance(AES_key_str, str):
        raise TypeError(f"AES encryption key must be of type string\n\tProvided: {AES_key_str}")
    return bytes.fromhex(AES_key_str)


def encrypt_AES(message: str, key: bytes) -> bytes:
    """
    Encrypts the message using AES-CBC and prepends the IV to the ciphertext.
    :param message: plaintext message
    :param key: AES key (must be 32 bytes for AES-256)
    :return: IV + ciphertext (as bytes)
    """
    if not isinstance(message, str):
        raise TypeError(f"message must be a str\n\tProvided: {message}")
    if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
        raise ValueError("key must be 32 bytes for AES-256")

    iv = os.urandom(16)  # 128-bit IV

    # pad the message to be multiple of block size
    padder = symmetric_padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()

    return iv + cipher_text  # prepend IV

def decrypt_AES(cipher_text: bytes, key: bytes) -> str:
    """
    Decrypts AES-CBC ciphertext that has IV prepended.
    :param cipher_text: IV + ciphertext
    :param key: AES key (must be 32 bytes for AES-256)
    :return: plaintext message
    """
    if not isinstance(cipher_text, (bytes, bytearray)):
        raise TypeError(f"cipher_text must be bytes\n\tProvided: {cipher_text}")
    if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
        raise ValueError("key must be 32 bytes for AES-256")

    iv = cipher_text[:16] # first 16 bytes = IV
    actual_ciphertext = cipher_text[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(actual_ciphertext) + decryptor.finalize()

    # remove the padding from the message
    unpadder = symmetric_padding.PKCS7(128).unpadder()
    plain_text = unpadder.update(decrypted_padded) + unpadder.finalize()

    return plain_text.decode()
