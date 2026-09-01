from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.core.access import AccessContext
from app.core.config import get_settings


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.token_expiry_minutes)).timestamp()),
        "aud": "nexus-enterprise-ai",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_demo_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="nexus-enterprise-ai",
        )
        subject = payload.get("sub")
        if not subject:
            raise ValueError("missing subject")
        return str(subject).lower()
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc


def _principal_for_email(email: str) -> AccessContext:
    settings = get_settings()
    profile = settings.access_profile_for(email)
    return AccessContext.create(
        email,
        roles=profile.get("roles", ["employee"]),
        departments=profile.get("departments", []),
    )


async def current_principal(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> AccessContext:
    """Resolve identity and authorization claims from trusted configuration.

    In demo mode the JWT carries only the account identity; roles/departments
    are resolved server-side from DEMO_ACCOUNTS_JSON. In IAP mode the trusted
    web tier supplies the IAP-authenticated email, and entitlements are resolved
    from ACCESS_PROFILES_JSON (or a future directory integration). Client-sent
    role/department headers are deliberately ignored.
    """
    settings = get_settings()

    if settings.auth_mode == "iap":
        if not x_user_email:
            raise HTTPException(status_code=401, detail="Missing IAP user identity")
        email = x_user_email.removeprefix("accounts.google.com:").lower()
        return _principal_for_email(email)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    email = _decode_demo_token(authorization.split(" ", 1)[1].strip())
    return _principal_for_email(email)


async def require_knowledge_admin(
    principal: AccessContext = Depends(current_principal),
) -> AccessContext:
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge administrator permission required",
        )
    return principal


# Compatibility helper for code paths that only need the stable user identifier.
async def current_user(principal: AccessContext = Depends(current_principal)) -> str:
    return principal.email
