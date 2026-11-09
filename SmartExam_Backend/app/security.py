import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from argon2 import PasswordHasher, Type

JWT_ISSUER = "smartexam"
JWT_ACCESS_TOKEN_SECONDS = 30 * 60
# A process-local development key keeps the app usable out of the box. Deployments
# should always set JWT_SECRET_KEY to a long, stable random value.
_configured_jwt_secret = os.getenv("JWT_SECRET_KEY")
if _configured_jwt_secret and len(_configured_jwt_secret.encode("utf-8")) < 32:
    raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
JWT_SECRET_KEY = _configured_jwt_secret or secrets.token_urlsafe(48)

# Argon2id; the library generates a fresh random salt for each password.
password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_access_token(user_id: str, role: str, *, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        "iss": JWT_ISSUER,
        "sub": user_id,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + JWT_ACCESS_TOKEN_SECONDS,
    }
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(claims, separators=(',', ':')).encode())}"
    )
    signature = hmac.new(
        JWT_SECRET_KEY.encode(), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def decode_access_token(token: str, *, now: int | None = None) -> dict[str, object]:
    try:
        encoded_header, encoded_claims, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_claims}"
        supplied = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        expected = hmac.new(
            JWT_SECRET_KEY.encode(), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(supplied, expected):
            raise ValueError("Invalid signature")
        header = json.loads(
            base64.urlsafe_b64decode(encoded_header + "=" * (-len(encoded_header) % 4))
        )
        claims = json.loads(
            base64.urlsafe_b64decode(encoded_claims + "=" * (-len(encoded_claims) % 4))
        )
        current_time = int(time.time()) if now is None else now
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Invalid algorithm")
        if claims.get("iss") != JWT_ISSUER or not isinstance(claims.get("sub"), str):
            raise ValueError("Invalid claims")
        if claims.get("role") not in {"student", "admin"}:
            raise ValueError("Invalid role")
        if (
            not isinstance(claims.get("exp"), int)
            or isinstance(claims["exp"], bool)
            or claims["exp"] <= current_time
        ):
            raise ValueError("Expired token")
        return claims
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid access token") from exc
