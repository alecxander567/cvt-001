from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
import cloudinary
import cloudinary.uploader
from utils.cloud_config import configure_cloudinary
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

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
    """
    Decodes the custom JWT signed with SECRET_KEY.
    Returns the full payload dict (includes user_id and email).
    Raises 401 if token is invalid or expired.
    """
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
                "user_id": current_user["user_id"],
                "url": result["secure_url"],
                "public_id": result["public_id"],
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
