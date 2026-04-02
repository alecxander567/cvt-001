from fastapi import APIRouter
from supabase import create_client
import os
from dotenv import load_dotenv

router = APIRouter(prefix="/activity", tags=["Activity"])

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@router.get("/")
def get_activity_logs():
    response = (
        supabase.table("activity_logs")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data
