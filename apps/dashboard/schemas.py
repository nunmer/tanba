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


# ---- links ----
class LinkCreate(BaseModel):
    slug: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")
    type: str = Field(default="redirect", pattern=r"^(redirect|multi|landing)$")


class LinkOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    code: str
    slug: str | None
    type: str
    is_active: bool

    model_config = {"from_attributes": True}


# ---- destinations ----
class DestinationCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str = Field(default="", max_length=120)
    kind: str = Field(default="url", max_length=20)
    priority: int = 100
    weight: int = Field(default=1, ge=1)
    match: dict | None = None


class DestinationOut(BaseModel):
    id: uuid.UUID
    smartlink_id: uuid.UUID
    label: str
    url: str
    kind: str
    priority: int
    weight: int
    is_active: bool

    model_config = {"from_attributes": True}
