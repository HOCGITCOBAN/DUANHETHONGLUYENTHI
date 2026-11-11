from typing import Literal
from unicodedata import normalize

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(
        min_length=1, max_length=120, validation_alias=AliasChoices("name", "full_name")
    )
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        # App policy: the complete email address is case-insensitive.
        # Compose equivalent Unicode spellings before casefold changes combining marks.
        # Validate the final form because Unicode casefold can expand its length.
        return normalize("NFC", value.strip()).casefold() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("Mật khẩu không được chỉ chứa khoảng trắng.")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return normalize("NFC", value.strip()).casefold() if isinstance(value, str) else value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(validation_alias="full_name")
    email: EmailStr
    role: Literal["student", "admin"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class SubjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    is_active: bool = True


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
