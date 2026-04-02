from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def log_activity(
    user_id: int,
    action: str,
    entity: str,
    entity_id: str = None,
    description: str = None,
):
    try:
        supabase.table("activity_logs").insert(
            {
                "user_id": user_id,
                "action": action,
                "entity": entity,
                "entity_id": entity_id,
                "description": description,
            }
        ).execute()
    except Exception as e:
        print("Activity log failed:", str(e))
