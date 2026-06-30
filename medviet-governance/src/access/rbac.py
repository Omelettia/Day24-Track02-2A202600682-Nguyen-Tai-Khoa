# src/access/rbac.py
import os
import casbin
from functools import wraps
from fastapi import HTTPException, Header
from typing import Optional

# Danh sách user giả lập (production dùng JWT + DB)
MOCK_USERS = {
    "token-alice": {"username": "alice", "role": "admin"},
    "token-bob":   {"username": "bob",   "role": "ml_engineer"},
    "token-carol": {"username": "carol", "role": "data_analyst"},
    "token-dave":  {"username": "dave",  "role": "intern"},
}

# Resolve config paths relative to this file so the enforcer works regardless of CWD.
_BASE = os.path.dirname(os.path.abspath(__file__))
enforcer = casbin.Enforcer(
    os.path.join(_BASE, "model.conf"),
    os.path.join(_BASE, "policy.csv"),
)


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Parse Bearer token and return user info. 401 if invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ")[1]
    user = MOCK_USERS.get(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user


def require_permission(resource: str, action: str):
    """Decorator that enforces RBAC via Casbin. 403 if the role lacks the permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # current_user is injected by FastAPI via Depends(get_current_user)
            current_user = kwargs.get("current_user")
            role = current_user["role"]

            allowed = enforcer.enforce(role, resource, action)

            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{role}' cannot '{action}' on '{resource}'",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
