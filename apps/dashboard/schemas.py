"""Pydantic request/response models for the dashboard API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


# ---- auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---- orgs ----
class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    branding: dict | None = None


# ---- branches ----
class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    timezone: str = Field(default="Asia/Almaty", max_length=64)


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=64)


class BranchOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    address: str | None
    timezone: str

    model_config = {"from_attributes": True}


# ---- links ----
class LinkCreate(BaseModel):
    slug: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")
    type: str = Field(default="redirect", pattern=r"^(redirect|multi|landing)$")
    branch_id: uuid.UUID | None = None
    landing_config: dict | None = None


class LinkUpdate(BaseModel):
    slug: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")
    type: str | None = Field(default=None, pattern=r"^(redirect|multi|landing)$")
    branch_id: uuid.UUID | None = None
    landing_config: dict | None = None
    is_active: bool | None = None


class LinkOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    branch_id: uuid.UUID | None
    code: str
    slug: str | None
    type: str
    is_active: bool
    landing_config: dict

    model_config = {"from_attributes": True}


# ---- destinations ----
class DestinationCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str = Field(default="", max_length=120)
    kind: str = Field(default="url", max_length=20)
    priority: int = 100
    weight: int = Field(default=1, ge=1)
    match: dict | None = None


class DestinationUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=120)
    kind: str | None = Field(default=None, max_length=20)
    priority: int | None = None
    weight: int | None = Field(default=None, ge=1)
    match: dict | None = None
    is_active: bool | None = None


class DestinationOut(BaseModel):
    id: uuid.UUID
    smartlink_id: uuid.UUID
    label: str
    url: str
    kind: str
    priority: int
    weight: int
    match: dict | None
    is_active: bool

    model_config = {"from_attributes": True}


# ---- media ----
class MediaCreate(BaseModel):
    smartlink_id: uuid.UUID
    medium_type: str = Field(pattern=r"^(nfc_card|nfc_stand|nfc_sticker|qr_stand|business_card)$")
    serial: str | None = Field(default=None, max_length=120)


class MediaOut(BaseModel):
    id: uuid.UUID
    smartlink_id: uuid.UUID
    medium_type: str
    serial: str | None

    model_config = {"from_attributes": True}


# ---- members ----
class MemberCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern=r"^(owner|admin|member)$")


class MemberUpdate(BaseModel):
    role: str = Field(pattern=r"^(owner|admin|member)$")


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str
