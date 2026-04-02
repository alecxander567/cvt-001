from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from dotenv import load_dotenv
import os
from models.User import AlbumCreate, AlbumResponse, ImageResponse
from jose import jwt, JWTError
from typing import List
from utils.activity_logger import log_activity

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

        new_album = result.data[0]

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="CREATE",
                entity="album",
                entity_id=new_album["id"],
                description=f"Created album '{new_album['name']}'",
            )
        except Exception as e:
            print("Logging failed:", e)

        return new_album

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
    try:
        album = (
            supabase.table("albums")
            .select("id, name")
            .eq("id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not album.data:
            raise HTTPException(status_code=404, detail="Album not found")

        album_name = album.data[0]["name"]

        image_ids: list = payload.get("image_ids", [])
        removed_ids: list = payload.get("removed_ids", [])

        if image_ids:
            supabase.table("images").update({"album_id": album_id}).in_(
                "id", image_ids
            ).eq("user_id", int(current_user["user_id"])).execute()

        if removed_ids:
            supabase.table("images").update({"album_id": None}).in_(
                "id", removed_ids
            ).eq("user_id", int(current_user["user_id"])).execute()

        if image_ids:
            try:
                log_activity(
                    user_id=int(current_user["user_id"]),
                    action="UPDATE",
                    entity="album",
                    entity_id=album_id,
                    description=f"Added {len(image_ids)} image(s) to album '{album_name}'",
                )
            except Exception as e:
                print("Logging failed:", e)

        if removed_ids:
            try:
                log_activity(
                    user_id=int(current_user["user_id"]),
                    action="UPDATE",
                    entity="album",
                    entity_id=album_id,
                    description=f"Removed {len(removed_ids)} image(s) from album '{album_name}'",
                )
            except Exception as e:
                print("Logging failed:", e)

        return {"updated": len(image_ids), "removed": len(removed_ids)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{album_id}", status_code=204)
async def delete_album(album_id: str, current_user: dict = Depends(get_current_user)):
    try:
        existing = (
            supabase.table("albums")
            .select("id, name")
            .eq("id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Album not found")

        album_data = existing.data[0]

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="DELETE",
                entity="album",
                entity_id=album_id,
                description=f"Deleted album '{album_data['name']}'",
            )
        except Exception as e:
            print("Logging failed:", e)

        # Remove album_id from images
        supabase.table("images").update({"album_id": None}).eq(
            "album_id", album_id
        ).execute()

        # Delete album
        supabase.table("albums").delete().eq("id", album_id).eq(
            "user_id", int(current_user["user_id"])
        ).execute()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
