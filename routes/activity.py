from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from jose import jwt, JWTError
from fastapi import HTTPException
import os
from dotenv import load_dotenv

router = APIRouter(prefix="/activity", tags=["Activity"])

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

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


@router.get("/")
def get_activity_logs(current_user: dict = Depends(get_current_user)):
    response = (
        supabase.table("activity_logs")
        .select("*")
        .eq("user_id", int(current_user["user_id"]))
        .order("created_at", desc=True)
        .execute()
    )
    return response.data
