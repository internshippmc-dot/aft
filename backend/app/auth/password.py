from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

# SECURITY.md section 2: argon2id, 64 MB memory, 3 iterations, parallelism 4.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, InvalidHash):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)
