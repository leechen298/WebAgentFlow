"""Validation-site real backend.

Lives under the /validation-api/ prefix and is used exclusively by
``apps/validation-site`` — the self-hosted validation fixtures that let
WebAgentFlow exercise autonomous exploration without depending on
external sites (which introduce CAPTCHA/rate-limit noise).

This router serves real endpoints backed by in-memory data. It is NOT a
stubbed frontend mock — requests go over HTTP, real pydantic validation
runs, and each endpoint sleeps for a realistic amount of time so
autonomous runs see production-shaped latencies (pure-in-memory replies
would finish in < 1 ms, which does not match real-world pages).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse

router = APIRouter(prefix="/validation-api", tags=["validation"])
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Login
# ───────────────────────────────────────────────────────────────────


_EXPECTED_USERNAME = "admin"
_EXPECTED_PASSWORD = "123456"

# Login latency in seconds. Real auth round-trips almost never come
# back in < 200 ms — a local in-memory reply is unrealistically fast,
# so we sleep enough to approximate what the engine would see in prod.
_LOGIN_DELAY_SECONDS = 0.4


class LoginRequest(BaseModel):
    username: str = Field(default="")
    password: str = Field(default="")


class LoginResponseData(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=ApiResponse[LoginResponseData])
def login(payload: LoginRequest) -> ApiResponse[LoginResponseData]:
    """Login. admin/123456 → 200 with token; anything else → 401."""
    time.sleep(_LOGIN_DELAY_SECONDS)
    if (
        payload.username == _EXPECTED_USERNAME
        and payload.password == _EXPECTED_PASSWORD
    ):
        return ApiResponse(
            data=LoginResponseData(
                token=f"validation-site-token-{payload.username}",
                username=payload.username,
            ),
        )
    # HTTPException is wrapped into the {code, msg, data} envelope by
    # the global exception handler in main.py.
    raise HTTPException(status_code=401, detail="用户名或密码错误")


# ───────────────────────────────────────────────────────────────────
# User directory — seed data
# ───────────────────────────────────────────────────────────────────


UserRole = Literal["admin", "user", "guest"]
UserStatus = Literal["active", "disabled"]


class User(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    status: UserStatus
    registered_at: date
    region: str = Field(description="Dotted path, e.g. 'CN/Zhejiang/Hangzhou'.")
    department: str
    last_login_at: str = Field(description="ISO datetime string.")


# Seed ~15 users so tables have enough rows for meaningful sort / filter
# testing and so empty-state scenarios (no_match) are obviously distinct
# from the initial loaded state.
def _seed(
    uid: int,
    name: str,
    email: str,
    role: UserRole,
    status: UserStatus,
    registered: tuple[int, int, int],
    region: str,
    department: str,
    last_login: str,
) -> User:
    return User(
        id=uid,
        name=name,
        email=email,
        role=role,
        status=status,
        registered_at=date(*registered),
        region=region,
        department=department,
        last_login_at=last_login,
    )


_SEED_USERS: list[User] = [
    _seed(1,  "alice",  "alice@example.com",  "admin", "active",
          (2024, 3, 15),  "CN/Zhejiang/Hangzhou",  "Engineering", "2026-04-17T09:30:00"),
    _seed(2,  "bob",    "bob@example.com",    "user",  "active",
          (2024, 7, 22),  "CN/Zhejiang/Ningbo",    "Sales",       "2026-04-16T14:15:00"),
    _seed(3,  "carol",  "carol@example.com",  "user",  "active",
          (2025, 1, 8),   "CN/Jiangsu/Suzhou",     "Engineering", "2026-04-18T08:45:00"),
    _seed(4,  "dave",   "dave@example.com",   "admin", "disabled",
          (2023, 11, 3),  "CN/Beijing/Chaoyang",   "Operations",  "2025-12-01T11:20:00"),
    _seed(5,  "eve",    "eve@example.com",    "guest", "active",
          (2025, 9, 14),  "US/California/San Jose", "Marketing",  "2026-04-15T16:00:00"),
    _seed(6,  "frank",  "frank@example.com",  "user",  "active",
          (2024, 5, 20),  "CN/Jiangsu/Nanjing",    "Engineering", "2026-04-18T10:10:00"),
    _seed(7,  "grace",  "grace@example.com",  "user",  "disabled",
          (2024, 2, 28),  "CN/Shanghai/Pudong",    "Finance",     "2025-11-10T13:05:00"),
    _seed(8,  "henry",  "henry@example.com",  "admin", "active",
          (2023, 6, 1),   "CN/Beijing/Haidian",    "Engineering", "2026-04-17T22:40:00"),
    _seed(9,  "irene",  "irene@example.com",  "user",  "active",
          (2025, 3, 30),  "CN/Guangdong/Shenzhen", "Sales",       "2026-04-16T09:50:00"),
    _seed(10, "jack",   "jack@example.com",   "guest", "disabled",
          (2024, 12, 5),  "US/New York/Brooklyn",  "Marketing",   "2025-10-18T12:30:00"),
    _seed(11, "karen",  "karen@example.com",  "user",  "active",
          (2025, 6, 11),  "CN/Zhejiang/Hangzhou",  "Operations",  "2026-04-18T07:15:00"),
    _seed(12, "leo",    "leo@example.com",    "user",  "active",
          (2024, 8, 19),  "CN/Shanghai/Xuhui",     "Engineering", "2026-04-14T19:25:00"),
    _seed(13, "mia",    "mia@example.com",    "admin", "active",
          (2024, 10, 7),  "CN/Jiangsu/Suzhou",     "Finance",     "2026-04-17T15:00:00"),
    _seed(14, "nathan", "nathan@example.com", "user",  "active",
          (2025, 2, 2),   "CN/Beijing/Chaoyang",   "Engineering", "2026-04-18T11:35:00"),
    _seed(15, "olivia", "olivia@example.com", "guest", "active",
          (2025, 11, 25), "US/California/San Francisco", "Marketing", "2026-04-15T10:00:00"),
]


# ───────────────────────────────────────────────────────────────────
# User directory — query endpoint
# ───────────────────────────────────────────────────────────────────


_USERS_BASE_DELAY_SECONDS = 0.25
_USERS_PER_FILTER_DELAY_SECONDS = 0.08


class UserListResponse(BaseModel):
    total: int
    items: list[User]


SortKey = Literal["id", "name", "email", "role", "status", "registered_at"]


@router.get("/users", response_model=ApiResponse[UserListResponse])
def list_users(
    name: Annotated[str | None, Query(description="Substring match on name.")] = None,
    email: Annotated[str | None, Query(description="Substring match on email.")] = None,
    role: Annotated[UserRole | None, Query()] = None,
    status: Annotated[UserStatus | None, Query()] = None,
    registered_from: Annotated[date | None, Query()] = None,
    registered_to: Annotated[date | None, Query()] = None,
    region_prefix: Annotated[
        str | None,
        Query(description="Matches if region startswith this prefix; "
                          "intended for Cascader-style drill-down."),
    ] = None,
    month: Annotated[
        str | None,
        Query(description="YYYY-MM — filter registered_at to that calendar month."),
    ] = None,
    department: Annotated[
        str | None,
        Query(description="Comma-separated department list; match if "
                          "user's department is any of them."),
    ] = None,
    sort_by: Annotated[SortKey | None, Query()] = None,
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> ApiResponse[UserListResponse]:
    """Filtered user list.

    The handler is deliberately forgiving — unknown parameters are
    ignored rather than 400'd — because part of the fixture's job is
    to exercise the engine under imperfect inputs. All filtering is
    in-memory over the seed list.
    """
    filters_applied = sum(
        1
        for v in (
            name, email, role, status,
            registered_from, registered_to,
            region_prefix, month, department,
        )
        if v not in (None, "")
    )
    # Variable delay so results-heavy queries feel different from
    # trivial ones. Caps at ~970 ms to stay within Playwright's default
    # timeouts.
    time.sleep(_USERS_BASE_DELAY_SECONDS + filters_applied * _USERS_PER_FILTER_DELAY_SECONDS)

    items = list(_SEED_USERS)

    if name:
        needle = name.lower()
        items = [u for u in items if needle in u.name.lower()]
    if email:
        needle = email.lower()
        items = [u for u in items if needle in u.email.lower()]
    if role is not None:
        items = [u for u in items if u.role == role]
    if status is not None:
        items = [u for u in items if u.status == status]
    if registered_from is not None:
        items = [u for u in items if u.registered_at >= registered_from]
    if registered_to is not None:
        items = [u for u in items if u.registered_at <= registered_to]
    if region_prefix:
        items = [u for u in items if u.region.startswith(region_prefix)]
    if month:
        # Expect YYYY-MM. Silently ignore malformed input — the fixture
        # is permissive on bad params by design.
        try:
            y_str, m_str = month.split("-")
            y, m = int(y_str), int(m_str)
            items = [
                u for u in items
                if u.registered_at.year == y and u.registered_at.month == m
            ]
        except (ValueError, AttributeError):
            pass
    if department:
        depts = {d.strip() for d in department.split(",") if d.strip()}
        if depts:
            items = [u for u in items if u.department in depts]

    if sort_by is not None:
        items.sort(key=lambda u: getattr(u, sort_by), reverse=(sort_order == "desc"))

    return ApiResponse(data=UserListResponse(total=len(items), items=items))


# ───────────────────────────────────────────────────────────────────
# User directory — single record endpoint
# ───────────────────────────────────────────────────────────────────


@router.get("/users/{user_id}", response_model=ApiResponse[User])
def get_user(user_id: int) -> ApiResponse[User]:
    """Fetch one user by id — used by the Actions > View row button."""
    time.sleep(0.15)
    for u in _SEED_USERS:
        if u.id == user_id:
            return ApiResponse(data=u)
    raise HTTPException(status_code=404, detail=f"User not found: id={user_id}")


# ───────────────────────────────────────────────────────────────────
# Metadata — used by the UI to populate Cascader / Tag options so the
# fixture stays driven by one source of truth (the seed list).
# ───────────────────────────────────────────────────────────────────


class CascaderOption(BaseModel):
    value: str
    label: str
    children: list[CascaderOption] = Field(default_factory=list)


class UserMetaResponse(BaseModel):
    roles: list[UserRole]
    statuses: list[UserStatus]
    departments: list[str]
    regions: list[CascaderOption]


CascaderOption.model_rebuild()


@router.get("/users/meta/options", response_model=ApiResponse[UserMetaResponse])
def user_meta_options() -> ApiResponse[UserMetaResponse]:
    """Derive dropdown / cascader / tag options from the seed data.

    Having one source of truth (the seed list) keeps UI options and
    actual filterable values aligned; changing the seed updates the UI
    without editing two places.
    """
    time.sleep(0.1)

    roles: list[UserRole] = sorted({u.role for u in _SEED_USERS})  # type: ignore[assignment]
    statuses: list[UserStatus] = sorted({u.status for u in _SEED_USERS})  # type: ignore[assignment]
    departments = sorted({u.department for u in _SEED_USERS})

    # Build a nested Cascader tree from the dotted region paths.
    tree: dict[str, dict[str, list[str]]] = {}
    for u in _SEED_USERS:
        parts = u.region.split("/")
        if len(parts) != 3:
            continue
        country, province, city = parts
        tree.setdefault(country, {}).setdefault(province, [])
        if city not in tree[country][province]:
            tree[country][province].append(city)

    regions: list[CascaderOption] = []
    for country, provinces in sorted(tree.items()):
        country_node = CascaderOption(value=country, label=country)
        for province, cities in sorted(provinces.items()):
            prov_node = CascaderOption(value=province, label=province)
            for city in sorted(cities):
                prov_node.children.append(CascaderOption(value=city, label=city))
            country_node.children.append(prov_node)
        regions.append(country_node)

    return ApiResponse(
        data=UserMetaResponse(
            roles=roles,
            statuses=statuses,
            departments=departments,
            regions=regions,
        )
    )
