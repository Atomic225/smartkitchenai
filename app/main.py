from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine, ensure_schema
from app.routers import chef, chat, grocery, household, menus, system
from app.scheduler import start_scheduler, stop_scheduler
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    if get_settings().app_env != "test":
        start_scheduler()
    yield
    if get_settings().app_env != "test":
        stop_scheduler()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(menus.router)
app.include_router(grocery.router)
app.include_router(household.router)
app.include_router(chef.router)
app.include_router(system.router)


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name, "timezone": settings.timezone}
