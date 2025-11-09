from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes import router

app = FastAPI(title=settings.app_name)

# CORS for frontend dev server (preflight OPTIONS support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # safe for local dev; tighten in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
