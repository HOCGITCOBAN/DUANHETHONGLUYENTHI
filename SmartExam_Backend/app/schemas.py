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
    model_validator,
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
        if len(value.get_secret_value().encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 UTF-8 bytes with bcrypt.")
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


Difficulty = Literal["easy", "medium", "hard"]


class OptionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False


class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    is_correct: bool


class QuestionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=2000)
    options: list[OptionWrite] = Field(min_length=2, max_length=6)
    explanation: str | None = Field(default=None, max_length=2000)
    difficulty: Difficulty = "medium"
    is_active: bool = True

    @model_validator(mode="after")
    def require_exactly_one_correct_option(self) -> "QuestionWrite":
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("Câu hỏi phải có đúng một phương án đúng.")
        return self


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    text: str
    options: list[OptionResponse]
    explanation: str | None
    difficulty: Difficulty
    is_active: bool
