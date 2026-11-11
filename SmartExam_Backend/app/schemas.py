from typing import Literal
from unicodedata import normalize
from uuid import uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StrictBool,
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


class QuestionOptionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=1000)
    is_correct: StrictBool = False


class QuestionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(default="", max_length=5000)
    difficulty: Difficulty
    is_active: StrictBool = True
    options: list[QuestionOptionWrite] = Field(min_length=2, max_length=6)

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: list[QuestionOptionWrite]) -> list[QuestionOptionWrite]:
        if sum(option.is_correct for option in options) != 1:
            raise ValueError("Câu hỏi phải có đúng một đáp án đúng.")
        if len({option.id for option in options}) != len(options):
            raise ValueError("Mã phương án không được trùng trong cùng câu hỏi.")
        return options


class QuestionPatch(QuestionWrite):
    subject_id: str | None = Field(default=None, min_length=1, max_length=36)
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=5000)
    difficulty: Difficulty | None = None
    is_active: StrictBool | None = None
    options: list[QuestionOptionWrite] | None = Field(default=None, min_length=2, max_length=6)

    @model_validator(mode="before")
    @classmethod
    def reject_empty_or_null_fields(cls, value: object) -> object:
        if isinstance(value, dict):
            if not value:
                raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
            if any(field is None for field in value.values()):
                raise ValueError("Trường cập nhật không được là null.")
        return value


class QuestionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    is_correct: bool


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    text: str
    explanation: str
    difficulty: Difficulty
    is_active: bool
    options: list[QuestionOptionResponse]
