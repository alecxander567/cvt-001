from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from models.User import UserSignUp, UserLogin
from datetime import datetime, timedelta, timezone
import bcrypt
import os
from dotenv import load_dotenv
from jose import jwt, JWTError

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Guard: ensure all required env vars are present
if not SUPABASE_URL or not SUPABASE_KEY or not SECRET_KEY:
    raise RuntimeError("Missing required environment variables. Check your .env file.")

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Router + Bearer scheme
router = APIRouter()
security = HTTPBearer()


# Helpers
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    """Generate a JWT token with expiration"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token, raises JWTError on failure"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# Routes
@router.post("/signup", status_code=201)
def signup(user: UserSignUp):
    existing = supabase.table("user").select("*").eq("email", user.email).execute()
    if existing.data and len(existing.data) > 0:
        raise HTTPException(status_code=400, detail="Email already registered")

    data = {
        "username": user.username,
        "email": user.email,
        "password_hash": hash_password(user.password),
    }

    response = supabase.table("user").insert(data).execute()
    return {"message": "User created successfully", "user_id": response.data[0]["id"]}


@router.post("/login")
def login(user: UserLogin):
    result = supabase.table("user").select("*").eq("email", user.email).execute()
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    user_data = result.data[0]

    if not verify_password(user.password, user_data["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token_data = {"user_id": user_data["id"], "email": user_data["email"]}
    access_token = create_access_token(token_data)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Stateless JWT logout — validates the token is well-formed,
    then instructs the client to discard it.
    For true token invalidation, add a server-side blocklist here.
    """
    try:
        decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"message": "Logged out successfully"}
