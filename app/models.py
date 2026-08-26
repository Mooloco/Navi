from pydantic import BaseModel, Field, field_validator


def _normalize_url(v: str) -> str:
    v = v.strip()
    if v and not v.startswith(("http://", "https://")):
        v = "http://" + v
    return v


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    url: str = Field(..., min_length=1)
    description: str = ""
    icon: str = ""  # emoji 或图片 URL
    category: str = "其他"

    @field_validator("url")
    @classmethod
    def url_scheme(cls, v: str) -> str:
        return _normalize_url(v)


class ServiceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None
    icon: str | None = None
    category: str | None = None

    @field_validator("url")
    @classmethod
    def url_scheme(cls, v: str | None) -> str | None:
        return _normalize_url(v) if v is not None else None


class AdminLogin(BaseModel):
    password: str


class AdminPassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)
