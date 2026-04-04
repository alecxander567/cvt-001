from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, images, albums, categories, activity, user
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from utils.image_compare import _get_clip

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Warming up CLIP model...")
    _get_clip()
    print("CLIP model ready.")
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "https://cvt-client.vercel.app",
    "https://cvt-client-git-main-alecxander567s-projects.vercel.app",
    "https://cvt-client-d1v7dtukr-alecxander567s-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
