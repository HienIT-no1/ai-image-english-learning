from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.database import router as database_router
from app.routers.users import router as users_router

app = FastAPI(
    title="English Pose Learning API",
    description="Backend API for an English learning app using pose recognition",
    version="0.1.0",
)


app.include_router(auth_router)
app.include_router(database_router)
app.include_router(users_router)

@app.get("/")
def read_root():
    return {
        "message": "English Pose Learning API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }