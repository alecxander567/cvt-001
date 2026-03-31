from pydantic import BaseModel, EmailStr
from typing import Optional


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


class Image(BaseModel):
    id: Optional[str] = None
    user_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    url: str
    public_id: str
    features: Optional[list[float]] = None
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
    url: str
    public_id: str
    created_at: str


class UpdateImagePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


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
