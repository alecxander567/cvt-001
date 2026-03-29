from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
import cloudinary
import cloudinary.uploader
from utils.cloud_config import configure_cloudinary
from models.User import UpdateImagePayload, ImageResponse, CompareResponse
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from utils.image_compare import (
    load_image_from_url,
    load_image_from_bytes,
    extract_features,
    cosine_similarity,
)

load_dotenv()

configure_cloudinary()

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


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    album_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        contents = await file.read()

        result = cloudinary.uploader.upload(
            contents,
            folder="custom-vision-tagger",
            resource_type="image",
        )

        supabase.table("images").insert(
            {
                "user_id": int(current_user["user_id"]),
                "album_id": album_id,
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "name": file.filename or "Untitled",
            }
        ).execute()

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-images")
async def get_my_images(
    current_user: dict = Depends(get_current_user),
):
    try:
        result = (
            supabase.table("images")
            .select("*")
            .eq("user_id", int(current_user["user_id"]))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{image_id}", response_model=ImageResponse)
async def update_image(
    image_id: str,
    payload: UpdateImagePayload,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("*")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = supabase.table("images").update(updates).eq("id", image_id).execute()
        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}", status_code=204)
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("*")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        cloudinary.uploader.destroy(existing.data[0]["public_id"])

        supabase.table("images").delete().eq("id", image_id).execute()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/{image_id}", response_model=CompareResponse)
async def compare_image(
    image_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("*")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        stored_url = existing.data[0]["url"]

        stored_img = load_image_from_url(stored_url)

        new_image_bytes = await file.read()
        new_img = load_image_from_bytes(new_image_bytes)

        stored_features = extract_features(stored_img)
        new_features = extract_features(new_img)

        similarity = cosine_similarity(stored_features, new_features)

        is_match = similarity > 0.75

        return {
            "similarity": float(similarity),
            "is_match": is_match,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
