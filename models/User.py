from pydantic import BaseModel, EmailStr
from typing import Optional
from typing import Optional
import pydantic


class User(BaseModel):
    id: Optional[int] = None
    created_at: Optional[str] = None
    username: str
    email: EmailStr
    password_hash: str


class UserSignUp(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class Image(BaseModel):
    id: Optional[str] = None
    user_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[str] = None
    url: str
    public_id: str
    features: Optional[list[float]] = None
    is_archived: Optional[bool] = False
    archived_at: Optional[str] = None
    created_at: Optional[str] = None


class ImageCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ImageResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[str] = None
    url: str
    public_id: str
    created_at: str


class UpdateImagePayload(BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True)

    name: Optional[str] = pydantic.Field(default=None)
    description: Optional[str] = pydantic.Field(default=None)
    category_id: Optional[str] = pydantic.Field(default=None)


class LabelScore(BaseModel):
    label: str
    score: float


class CompareResponse(BaseModel):
    similarity: float
    is_match: bool
    object_match: bool
    stored_labels: list[LabelScore]
    new_labels: list[LabelScore]
    shared_labels: list[str]
    verdict: str


class AlbumCreate(BaseModel):
    name: str


class AlbumResponse(BaseModel):
    id: str
    name: str
    user_id: int
    created_at: Optional[str] = None


class ImageUpload(BaseModel):
    album_id: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: str
    user_id: int
    name: str
    created_at: Optional[str] = None


class ActivityLog(BaseModel):
    id: Optional[str] = None
    user_id: int
    action: str
    entity: str
    entity_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None


class ActivityLogResponse(BaseModel):
    id: str
    user_id: int
    action: str
    entity: str
    entity_id: Optional[str]
    description: Optional[str]
    created_at: str
