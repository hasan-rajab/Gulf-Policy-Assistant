from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _normalize(values: Iterable[str] | None) -> frozenset[str]:
    return frozenset(str(value).strip().lower() for value in (values or []) if str(value).strip())


@dataclass(frozen=True)
class AccessContext:
    """Identity-derived authorization context used during retrieval.

    Access is intentionally evaluated before candidate scoring. Restricted
    documents are therefore excluded from the search corpus rather than fetched
    and filtered after retrieval.
    """

    email: str
    roles: frozenset[str]
    departments: frozenset[str]

    @classmethod
    def create(
        cls,
        email: str,
        roles: Iterable[str] | None = None,
        departments: Iterable[str] | None = None,
    ) -> "AccessContext":
        return cls(
            email=email.strip().lower(),
            roles=_normalize(roles) or frozenset({"employee"}),
            departments=_normalize(departments),
        )

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles or "knowledge_admin" in self.roles

    def can_read(
        self,
        visibility: str | None,
        allowed_roles: Iterable[str] | None = None,
        allowed_departments: Iterable[str] | None = None,
    ) -> bool:
        visibility_n = (visibility or "public").strip().lower()
        if visibility_n == "public" or self.is_admin:
            return True

        role_acl = _normalize(allowed_roles)
        department_acl = _normalize(allowed_departments)

        # A restricted document with no ACL grants is admin-only by design.
        if not role_acl and not department_acl:
            return False
        return bool(self.roles & role_acl or self.departments & department_acl)
