"""管理认证:密码哈希 + 会话 token。"""

import hashlib
import secrets
import time

from . import database

TOKEN_TTL = 7 * 24 * 3600  # token 有效期 7 天
_tokens: dict[str, float] = {}


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode()).hexdigest() == digest


def ensure_default_password() -> None:
    """首次初始化时写入默认密码 admin123。"""
    if database.get_setting("password_hash") is None:
        database.set_setting("password_hash", hash_password("admin123"))


def change_password(old_password: str, new_password: str) -> bool:
    stored = database.get_setting("password_hash")
    if stored is None or not verify_password(old_password, stored):
        return False
    database.set_setting("password_hash", hash_password(new_password))
    return True


def create_token() -> str:
    token = secrets.token_hex(24)
    _tokens[token] = time.time() + TOKEN_TTL
    return token


def check_token(token: str | None) -> bool:
    if not token:
        return False
    exp = _tokens.get(token)
    if exp is None:
        return False
    if time.time() > exp:
        _tokens.pop(token, None)
        return False
    return True


def revoke_token(token: str | None) -> None:
    if token:
        _tokens.pop(token, None)


def extract_bearer(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    return None
