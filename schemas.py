"""Pydantic models: request validation and response shapes."""
import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
MIN_DOB = date(1900, 1, 1)


def _blank_to_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Aarav Sharma"])
    date_of_birth: date = Field(..., examples=["2004-05-17"])
    email: Optional[str] = Field(None, examples=["aarav@example.com"])
    phone: Optional[str] = Field(None, examples=["+91 98765 43210"])
    course: Optional[str] = Field(None, max_length=100, examples=["Python Backend"])
    address: Optional[str] = Field(None, max_length=300)
    enrollment_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        if v < MIN_DOB:
            raise ValueError("date_of_birth must be on or after 1900-01-01")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        v = _blank_to_none(v)
        if v is None:
            return None
        if not isinstance(v, str) or not EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v.lower()

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, v):
        v = _blank_to_none(v)
        if v is None:
            return None
        if not isinstance(v, str) or not PHONE_RE.match(v):
            raise ValueError("invalid phone number (7-20 digits; may include + - ( ) and spaces)")
        return v

    @field_validator("course", "address", mode="before")
    @classmethod
    def _optional_text(cls, v):
        return _blank_to_none(v)

    @model_validator(mode="after")
    def _cross_checks(self):
        if not self.email and not self.phone:
            raise ValueError("at least one of email or phone is required")
        if self.enrollment_date and self.enrollment_date < self.date_of_birth:
            raise ValueError("enrollment_date cannot be before date_of_birth")
        return self


class StudentUpdate(BaseModel):
    """Partial update (PATCH): only the fields that are sent are changed.
    The merged result is re-validated with StudentCreate in the route."""
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class StudentOut(BaseModel):
    id: int
    name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class Question(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["How many students are there?"])


class Answer(BaseModel):
    question: str
    answer: str
    model: str
    records_used: int
    context: str
