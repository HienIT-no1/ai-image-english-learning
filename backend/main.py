from fastapi import FastAPI
from app.routers.quizzes import router as quizzes_router
from app.routers.learning import router as learning_router
from app.routers.collections import router as collections_router
from app.routers.topics import router as topics_router

from app.routers.auth import router as auth_router
from app.routers.database import router as database_router
from app.routers.users import router as users_router
from app.routers.vocabularies import router as vocabularies_router
app = FastAPI(
    title="English Pose Learning API",
    description="Backend API for an English learning app using pose recognition",
    version="0.1.0",
)


app.include_router(quizzes_router)
app.include_router(learning_router)
app.include_router(collections_router)
app.include_router(topics_router)
app.include_router(auth_router)
app.include_router(database_router)
app.include_router(users_router)
app.include_router(vocabularies_router)
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