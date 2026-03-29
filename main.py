from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, images, albums
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router, prefix="/auth")
app.include_router(images.router, prefix="/images")
app.include_router(albums.router, prefix="/albums")


@app.get("/")
def home():
    return {"message": "Backend is running"}
