from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from models.User import CategoryCreate, CategoryResponse, CategoryUpdate
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
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


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("categories")
            .select("id, user_id, name, created_at")
            .eq("user_id", int(current_user["user_id"]))
            .order("name")
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = (
            supabase.table("categories")
            .insert(
                {
                    "user_id": int(current_user["user_id"]),
                    "name": payload.name.strip(),
                }
            )
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Insert returned no data")

        new_category = result.data[0]

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="CREATE",
                entity="category",
                entity_id=new_category["id"],
                description=f"Created category '{new_category['name']}'",
            )
        except Exception as e:
            print("Logging failed:", e)

        return new_category
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409, detail="Category with this name already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("categories")
            .select("id, user_id, name")
            .eq("id", category_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Category not found")

        result = (
            supabase.table("categories")
            .update({"name": payload.name.strip()})
            .eq("id", category_id)
            .execute()
        )

        updated_category = result.data[0]

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="UPDATE",
                entity="category",
                entity_id=category_id,
                description=f"Renamed category '{existing.data[0]['name']}' to '{updated_category['name']}'",
            )
        except Exception as e:
            print("Logging failed:", e)

        return updated_category
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409, detail="Category with this name already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        existing = (
            supabase.table("categories")
            .select("id, user_id, name")
            .eq("id", category_id)
            .eq("user_id", int(current_user["user_id"]))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Category not found")

        category_name = existing.data[0]["name"]

        supabase.table("categories").delete().eq("id", category_id).execute()

        try:
            log_activity(
                user_id=int(current_user["user_id"]),
                action="DELETE",
                entity="category",
                entity_id=category_id,
                description=f"Deleted category '{category_name}'",
            )
        except Exception as e:
            print("Logging failed:", e)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
