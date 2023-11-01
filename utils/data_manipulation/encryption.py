import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from django.conf import settings


class SecretEncryption:

    def __init__(self):
        __passcode = bytes(getattr(settings, "PASSCODE", None), 'utf-8')
        __kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"123456789", iterations=390000, )

        __key = base64.urlsafe_b64encode(__kdf.derive(__passcode))

        self.__suite = Fernet(__key)

    def __encode_secret(self, string):
        __encoded = base64.b64encode(string.encode('utf-8'))
        return __encoded

    def __decode_secret(self, string):
        __encoded_token = bytes(string, 'utf-8')
        __decoded_token = base64.b64decode(__encoded_token).decode('utf-8')
        return __decoded_token

    def encrypt_secret_string(self, string: str):
        __encoded_string = self.__encode_secret(string=string)

        __encrypted = self.__suite.encrypt(__encoded_string)
        __encrypted_password = str(__encrypted).split("'")[1].strip()
        return __encrypted_password

    def decrypt_secret_string(self, encrypted_string: str):
        __decrypted_token = (str(self.__suite.decrypt(encrypted_string)).split("'"))[1]
        __decoded_password = self.__decode_secret(string=__decrypted_token)
        return __decoded_password
