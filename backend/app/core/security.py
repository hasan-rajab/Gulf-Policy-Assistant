from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.token_expiry_minutes)).timestamp()),
        "aud": "gcc-enterprise-rag",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_demo_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="gcc-enterprise-rag",
        )
        subject = payload.get("sub")
        if not subject:
            raise ValueError("missing subject")
        return subject
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc


async def current_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> str:
    """Resolve the employee identity.

    demo mode: application JWT for local portability.
    iap mode: the backend is private to the web service's Cloud Run identity; the
    web tier forwards the IAP-authenticated employee email in X-User-Email.
    """
    settings = get_settings()

    if settings.auth_mode == "iap":
        if not x_user_email:
            raise HTTPException(status_code=401, detail="Missing IAP user identity")
        return x_user_email.removeprefix("accounts.google.com:")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    return _decode_demo_token(authorization.split(" ", 1)[1].strip())
