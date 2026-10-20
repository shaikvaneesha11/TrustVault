import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password):
    return _hasher.hash(password)


def verify_password(stored_hash, password):
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def new_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()