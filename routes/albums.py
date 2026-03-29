from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from dotenv import load_dotenv
import os
from models.User import AlbumCreate, AlbumResponse, ImageResponse
from jose import jwt, JWTError
from typing import List

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

router = APIRouter()
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        if not payload.get("user_id"):
            raise HTTPException(status_code=401, detail="Token missing user_id")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/", response_model=AlbumResponse)
async def create_album(
    payload: AlbumCreate, current_user: dict = Depends(get_current_user)
):
    try:
        result = (
            supabase.table("albums")
            .insert(
                {
                    "name": payload.name,
                    "user_id": int(current_user["user_id"]),
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create album")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[AlbumResponse])
async def get_my_albums(current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("albums")
            .select("*")
            .eq("user_id", int(current_user["user_id"]))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("albums")
            .select("*")
            .eq("id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Album not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{album_id}/images", response_model=List[ImageResponse])
async def get_album_images(
    album_id: str, current_user: dict = Depends(get_current_user)
):
    """Return all images that belong to this album."""
    try:
        album = (
            supabase.table("albums")
            .select("id")
            .eq("id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not album.data:
            raise HTTPException(status_code=404, detail="Album not found")

        result = (
            supabase.table("images")
            .select("*")
            .eq("album_id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{album_id}/images", response_model=dict)
async def set_album_images(
    album_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Set images for an album.
    payload: { "image_ids": ["uuid1", "uuid2", ...], "removed_ids": ["uuid3", ...] }
    - Assigns album_id to all image_ids
    - Clears album_id from removed_ids
    """
    try:
        album = (
            supabase.table("albums")
            .select("id")
            .eq("id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not album.data:
            raise HTTPException(status_code=404, detail="Album not found")

        image_ids: list = payload.get("image_ids", [])
        removed_ids: list = payload.get("removed_ids", [])

        # Add images to album
        if image_ids:
            supabase.table("images").update({"album_id": album_id}).in_(
                "id", image_ids
            ).eq("user_id", int(current_user["user_id"])).execute()

        if removed_ids:
            supabase.table("images").update({"album_id": None}).in_(
                "id", removed_ids
            ).eq("user_id", int(current_user["user_id"])).execute()

        return {"updated": len(image_ids), "removed": len(removed_ids)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{album_id}", status_code=204)
async def delete_album(album_id: str, current_user: dict = Depends(get_current_user)):
    try:
        supabase.table("images").update({"album_id": None}).eq(
            "album_id", album_id
        ).execute()

        supabase.table("albums").delete().eq("id", album_id).eq(
            "user_id", int(current_user["user_id"])
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
