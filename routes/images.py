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
        except Exception as feat_err:
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

        # Extract ML features for future comparisons
        try:
            img = load_image_from_bytes(contents)
            features = extract_features(img)
            features_list = [float(x) for x in features]
        except Exception:
            features_list = None

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder="custom-vision-tagger",
            resource_type="image",
        )

        # Save to Supabase under the logged-in user
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
            .select("id, user_id")
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
            .select("id, user_id, public_id")
            .eq("id", image_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Image not found")

        public_id = existing.data[0]["public_id"]

        destroy_result = cloudinary.uploader.destroy(public_id, resource_type="image")

        if destroy_result.get("result") not in ("ok", "not found"):
            raise HTTPException(
                status_code=500, detail=f"Cloudinary delete failed: {destroy_result}"
            )

        supabase.table("images").delete().eq("id", image_id).execute()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# SPECIFIC routes must come BEFORE generic /{param} routes
# compare-album is placed here so FastAPI doesn't mistake "compare-album"
# for an image_id and route it into compare/{image_id} instead.


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

            # --- CLIP semantic comparison ---
            stored_img = load_image_from_url(stored_url)
            clip_score = clip_object_similarity(stored_img, query_img)

            # --- Verdict ---
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

        # Fast path: use stored MobileNetV2 features for similarity
        if stored_features_raw:
            stored_features = np.array(stored_features_raw, dtype=np.float32)
            new_features = extract_features(new_img)
            similarity = cosine_similarity(stored_features, new_features)
            is_match = similarity >= 0.75

            # CLIP for semantic object matching — no fixed category list
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

        # Slow path: no stored features
        stored_img = load_image_from_url(stored_url)
        return compare_images(stored_img, new_img)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
