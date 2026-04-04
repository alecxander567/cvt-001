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
    compare_images,
    clip_object_similarity,
)
import numpy as np
from utils.activity_logger import log_activity
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request

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

        try:
            img = load_image_from_bytes(contents)
            features = extract_features(img)
            features_list = [float(x) for x in features]
        except Exception:
            features_list = None

        result = cloudinary.uploader.upload(
            contents,
            folder="custom-vision-tagger",
            resource_type="image",
        )

        insert_result = (
            supabase.table("images")
            .insert(
                {
                    "user_id": int(current_user["user_id"]),
                    "album_id": album_id,
                    "url": result["secure_url"],
                    "public_id": result["public_id"],
                    "name": file.filename or "Untitled",
                    "features": features_list,
                }
            )
            .execute()
        )

        if not insert_result.data:
            raise HTTPException(
                status_code=500, detail="Supabase insert returned no data"
            )

        new_image = insert_result.data[0]
        image_id = new_image["id"]

        log_activity(
            user_id=int(current_user["user_id"]),
            action="CREATE",
            entity="image",
            entity_id=image_id,
            description=f"Uploaded image '{new_image['name']}'",
        )

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-image")
async def upload_image_from_device(
    file: UploadFile = File(...),
    album_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        contents = await file.read()

        try:
            img = load_image_from_bytes(contents)
            features = extract_features(img)
            features_list = [float(x) for x in features]
        except Exception:
            features_list = None

        result = cloudinary.uploader.upload(
            contents,
            folder="custom-vision-tagger",
            resource_type="image",
        )

        insert_result = (
            supabase.table("images")
            .insert(
                {
                    "user_id": int(current_user["user_id"]),
                    "album_id": album_id,
                    "url": result["secure_url"],
                    "public_id": result["public_id"],
                    "name": file.filename or "Untitled",
                    "features": features_list,
                }
            )
            .execute()
        )

        if not insert_result.data:
            raise HTTPException(
                status_code=500, detail="Supabase insert returned no data"
            )

        new_image = insert_result.data[0]
        image_id = new_image["id"]

        log_activity(
            user_id=int(current_user["user_id"]),
            action="CREATE",
            entity="image",
            entity_id=image_id,
            description=f"Uploaded image '{new_image['name']}'",
        )

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-images")
async def get_my_images(current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("images")
            .select(
                "id, user_id, name, description, category, category_id, url, public_id, album_id, created_at"
            )
            .eq("user_id", int(current_user["user_id"]))
            .eq("is_archived", False)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archived")
async def get_archived_images(current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("images")
            .select("*")
            .eq("user_id", int(current_user["user_id"]))
            .eq("is_archived", True)
            .order("archived_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/restore/{image_id}")
async def restore_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("id, name")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        supabase.table("images").update({"is_archived": False, "archived_at": None}).eq(
            "id", image_id
        ).execute()

        log_activity(
            user_id=int(current_user["user_id"]),
            action="RESTORE",
            entity="image",
            entity_id=image_id,
            description=f"Restored image '{existing.data[0]['name']}'",
        )

        return {"message": "Image restored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/permanent/{image_id}")
async def permanent_delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("id, public_id, name")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        image_data = existing.data[0]

        cloudinary.uploader.destroy(image_data["public_id"], resource_type="image")
        supabase.table("images").delete().eq("id", image_id).execute()

        log_activity(
            user_id=int(current_user["user_id"]),
            action="PERMANENT_DELETE",
            entity="image",
            entity_id=image_id,
            description=f"Permanently deleted image '{image_data['name']}'",
        )

        return {"message": "Image permanently deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-album/{album_id}")
async def compare_album(
    album_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = (
            supabase.table("images")
            .select("id, url, features")
            .eq("album_id", album_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        images = result.data

        if not images:
            raise HTTPException(status_code=404, detail="No images in album")

        contents = await file.read()
        query_img = load_image_from_bytes(contents)
        query_features = extract_features(query_img)

        results = []

        for img in images:
            stored_url = img["url"]
            stored_features_raw = img.get("features")

            if stored_features_raw:
                stored_features = np.array(stored_features_raw, dtype=np.float32)
                similarity = cosine_similarity(stored_features, query_features)
            else:
                stored_img = load_image_from_url(stored_url)
                stored_features = extract_features(stored_img)
                similarity = cosine_similarity(stored_features, query_features)

            stored_img = load_image_from_url(stored_url)
            clip_score = clip_object_similarity(stored_img, query_img)

            if similarity >= 0.75:
                verdict = "same_object"
            elif clip_score >= 0.85:
                verdict = "same_category_different_instance"
            else:
                verdict = "different"

            results.append(
                {
                    "image_id": img["id"],
                    "url": stored_url,
                    "similarity": round(float(similarity), 4),
                    "clip_score": round(float(clip_score), 4),
                    "verdict": verdict,
                }
            )

        results = sorted(results, key=lambda x: x["similarity"], reverse=True)

        return {"best_match": results[0], "matches": results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/{image_id}")
async def compare_image(
    image_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("id, user_id, url, features")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        stored_url = existing.data[0]["url"]
        stored_features_raw = existing.data[0].get("features")

        contents = await file.read()
        new_img = load_image_from_bytes(contents)

        if stored_features_raw:
            stored_features = np.array(stored_features_raw, dtype=np.float32)
            new_features = extract_features(new_img)
            similarity = cosine_similarity(stored_features, new_features)
            is_match = similarity >= 0.75

            stored_img = load_image_from_url(stored_url)
            clip_score = clip_object_similarity(stored_img, new_img)
            object_match = clip_score >= 0.85

            if is_match:
                verdict = "same_object"
            elif object_match:
                verdict = "same_category_different_instance"
            else:
                verdict = "different"

            return {
                "similarity": round(float(similarity), 4),
                "clip_score": round(float(clip_score), 4),
                "is_match": is_match,
                "object_match": object_match,
                "shared_labels": [],
                "verdict": verdict,
            }

        stored_img = load_image_from_url(stored_url)
        return compare_images(stored_img, new_img)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{image_id}", response_model=ImageResponse)
async def update_image(
    image_id: str,
    payload: UpdateImagePayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    from fastapi import Request

    try:
        existing = (
            supabase.table("images")
            .select("id, user_id, name")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        # Use the raw JSON keys so null values are preserved
        body = await request.json()
        allowed = {"name", "description", "category_id"}
        updates = {k: v for k, v in body.items() if k in allowed}

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        print(">>> updates being written:", updates)

        result = supabase.table("images").update(updates).eq("id", image_id).execute()
        updated_image = result.data[0]

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="UPDATE",
                entity="image",
                entity_id=image_id,
                description=f"Updated image '{existing.data[0]['name']}'",
            )
        except Exception as e:
            print("Logging failed:", e)

        return updated_image

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}", status_code=200)
async def archive_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("images")
            .select("id, user_id, name")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        image_data = existing.data[0]

        supabase.table("images").update(
            {"is_archived": True, "archived_at": "now()"}
        ).eq("id", image_id).execute()

        log_activity(
            user_id=int(current_user["user_id"]),
            action="ARCHIVE",
            entity="image",
            entity_id=image_id,
            description=f"Archived image '{image_data['name']}'",
        )

        return {"message": "Image archived successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
