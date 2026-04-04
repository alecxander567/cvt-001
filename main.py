from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, images, albums, categories, activity, user
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
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(activity.router)
app.include_router(user.router)


@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.get("/ping")
def ping():
    return {"status": "ok", "message": "Server is alive"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "image-recognition-backend"}
