from fastapi import APIRouter, Depends, HTTPException
from models.User import UserUpdate
from utils.auth import get_current_user
from config.database import supabase
from passlib.context import CryptContext

router = APIRouter(prefix="/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.put("/profile")
def update_profile(payload: UserUpdate, user_id: int = Depends(get_current_user)):
    update_data = {}

    if payload.username:
        update_data["username"] = payload.username

    if payload.email:
        update_data["email"] = payload.email

    if payload.password:
        update_data["password_hash"] = pwd_context.hash(payload.password)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    response = supabase.table("user").update(update_data).eq("id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Profile updated successfully", "data": response.data[0]}
